"""Clause -> Obligations (BuildSpec §4.3).

The division of labour matters more than the prompt:

- The **model** reads one clause and reports the duties in it, plus the verbatim
  sentence each came from.
- The **pipeline** supplies the citation. Page, char_span, clause_path and
  circular are copied from the clause that was sent, so a fabricated source is not
  representable — the model is never asked where something came from.
- **Code** normalises the deadline and runs the groundedness gate.

That is why extraction can use a model at all without weakening provenance.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from jinja2 import Template

from regspine.common.hashing import obligation_id
from regspine.common.llm import LLM
from regspine.common.schemas import Clause, Obligation
from regspine.interpret.deadlines import normalise_deadline
from regspine.interpret.entailment import judge
from regspine.interpret.gate import evaluate

ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT / "prompts" / "extract_obligations.j2"
TAXONOMY_PATH = ROOT / "config" / "taxonomy.yaml"
THRESHOLDS_PATH = ROOT / "config" / "thresholds.yaml"


def load_yaml(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def build_tool(taxonomy: dict) -> dict:
    """Forced-output schema. Enums come from taxonomy.yaml, so a drifting label is
    a validation error rather than a silent new category."""
    return {
        "name": "submit_obligations",
        "description": "Return the obligations stated by this clause (possibly none).",
        "input_schema": {
            "type": "object",
            "properties": {
                "obligations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action_required": {"type": "string"},
                            "obligation_type": {
                                "type": "string",
                                "enum": taxonomy["obligation_type"],
                            },
                            "applies_to": {
                                "type": "array",
                                "items": {"type": "string", "enum": taxonomy["applies_to"]},
                            },
                            "trigger_class": {
                                "type": "string",
                                "enum": taxonomy["trigger_class"],
                            },
                            "criticality": {"type": "string", "enum": taxonomy["criticality"]},
                            "evidence_artifact": {"type": ["string", "null"]},
                            "evidence_class": {
                                "type": ["string", "null"],
                                "enum": [*taxonomy["evidence_class"], None],
                            },
                            "deadline_phrase": {"type": ["string", "null"]},
                            "parameters": {"type": "object"},
                            "consequence": {"type": ["string", "null"]},
                            "rationale": {"type": ["string", "null"]},
                            "source_sentence": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                        "required": [
                            "action_required",
                            "obligation_type",
                            "applies_to",
                            "trigger_class",
                            "criticality",
                            "source_sentence",
                            "confidence",
                        ],
                    },
                }
            },
            "required": ["obligations"],
        },
    }


def render_system(taxonomy: dict) -> str:
    template = Template(PROMPT_PATH.read_text())
    return template.render(
        obligation_types=taxonomy["obligation_type"],
        applies_to=taxonomy["applies_to"],
        trigger_classes=taxonomy["trigger_class"],
        evidence_classes=[e for e in taxonomy["evidence_class"]],
    )


def _user_message(clause: Clause) -> str:
    a = clause.anchor
    return (
        f"Circular: {a.circular_no} ({a.circular_date})\n"
        f"Applies to intermediary: {a.intermediary}\n"
        f"Part {a.part} · Section {a.section_no} — {a.section_title}\n"
        f"Clause {a.clause_path} (page {a.page})\n\n"
        f"Clause text:\n\"\"\"\n{clause.text}\n\"\"\""
    )


class Extractor:
    def __init__(self, llm: LLM | None = None, *, judge_entailment: bool = True):
        self.llm = llm or LLM()
        self.taxonomy = load_yaml(TAXONOMY_PATH)
        self.thresholds = load_yaml(THRESHOLDS_PATH)
        self.system = render_system(self.taxonomy)
        self.tool = build_tool(self.taxonomy)
        # Without a judge every obligation fails closed to needs_review, which is
        # safe but makes the M2 groundedness gate unreachable.
        self.judge_entailment = judge_entailment

    def extract_clause(self, clause: Clause, document_text: str) -> list[Obligation]:
        """One clause -> zero or more gated obligations."""
        message, _usage = self.llm.call(
            "extract_obligations",
            system=self.system,
            user=_user_message(clause),
            tools=[self.tool],
            tool_choice={"type": "tool", "name": "submit_obligations"},
        )

        block = next(
            (b for b in message.content if getattr(b, "type", "") == "tool_use"), None
        )
        if block is None:
            return []

        out: list[Obligation] = []
        tau_high = float(self.thresholds["confidence"]["tau_high"])

        for raw in block.input.get("obligations", []):
            action = (raw.get("action_required") or "").strip()
            if not action:
                continue

            applies_to = raw.get("applies_to") or [clause.anchor.intermediary]

            # Only the model's own deadline phrase is used. Falling back to the
            # whole clause looks helpful and is wrong: a clause that creates three
            # duties and states one deadline would have that deadline stamped onto
            # all three. An obligation with no stated deadline must read as having
            # none rather than borrowing its neighbour's.
            deadline = normalise_deadline(raw.get("deadline_phrase") or "")

            ob = Obligation(
                obligation_id=obligation_id(
                    clause.anchor.intermediary,
                    raw["obligation_type"],
                    action,
                    applies_to,
                ),
                applies_to=applies_to,
                obligation_type=raw["obligation_type"],
                trigger={"class": raw["trigger_class"], "basis": raw.get("deadline_phrase")},
                deadline=deadline,
                action_required=action,
                evidence_artifact=raw.get("evidence_artifact"),
                parameters=raw.get("parameters") or {},
                consequence=raw.get("consequence"),
                criticality=raw["criticality"],
                # Provenance is copied from the clause we sent, never taken from
                # the model. A fabricated citation is not representable.
                source=clause.anchor.model_copy(deep=True),
                effective_date=clause.anchor.circular_date,
                rationale=raw.get("rationale"),
                confidence=float(raw.get("confidence", 0.0)),
                interpretation_trace=raw.get("source_sentence", ""),
            )
            entail = "neutral"
            if self.judge_entailment:
                start, end = ob.source.char_span
                entail, reason = judge(self.llm, ob, document_text[start:end])
                if reason:
                    ob.interpretation_trace = (
                        f"{ob.interpretation_trace}\n[entailment: {entail}] {reason}"
                    ).strip()
            evaluate(ob, document_text, entailment=entail, tau_high=tau_high)
            out.append(ob)

        return out

    def extract_many(
        self, clauses: list[Clause], document_text: str, *, stop_on_budget: bool = True
    ) -> list[Obligation]:
        from regspine.common.llm import BudgetExceeded

        results: list[Obligation] = []
        for clause in clauses:
            try:
                results.extend(self.extract_clause(clause, document_text))
            except BudgetExceeded:
                if stop_on_budget:
                    print(f"[budget] stopped after {len(results)} obligations")
                    break
                raise
        return results
