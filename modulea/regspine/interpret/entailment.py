"""Entailment judging for the groundedness gate (BuildSpec §4.4 step 3).

The gate's other three checks are lexical: they confirm the obligation *reuses*
the clause's words. Entailment is the one that asks whether the clause actually
*says* it — a well-worded restatement of something the clause does not require
passes keyterm matching and fails here.

Deliberately a separate model call with a narrow rubric rather than part of
extraction: the extractor has an incentive to justify its own output, and asking
the same call to both produce and validate defeats the purpose.
"""

from __future__ import annotations

from regspine.common.llm import LLM
from regspine.common.schemas import Obligation

SYSTEM = """You judge whether a regulatory clause entails a stated obligation.

You are given CLAUSE (verbatim regulatory text) and OBLIGATION (a duty someone
claims the clause creates). Decide:

- "entailed"     — the clause states this duty. A reader of the clause alone would
                   agree the duty exists, with this actor and this action.
- "neutral"      — the clause neither states nor contradicts it. Includes duties
                   that are plausible under SEBI practice but not in THIS clause,
                   and duties that change the actor or broaden the action.
- "contradicted" — the clause says something incompatible with it.

Be strict. "Neutral" is the correct answer whenever the clause does not carry the
duty on its own; do not use general knowledge of securities regulation to bridge a
gap. Judge only what the clause says.

Call `judge_entailment` exactly once."""

TOOL = {
    "name": "judge_entailment",
    "description": "Return the entailment relation between the clause and the obligation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "entailment": {
                "type": "string",
                "enum": ["entailed", "neutral", "contradicted"],
            },
            "reason": {"type": "string", "description": "One sentence."},
        },
        "required": ["entailment", "reason"],
    },
}


def judge(llm: LLM, obligation: Obligation, cited_text: str) -> tuple[str, str]:
    """Return (entailment, reason). Fails closed to 'neutral'."""
    if not cited_text.strip():
        return "neutral", "no cited text"

    user = (
        f"CLAUSE:\n\"\"\"\n{cited_text.strip()}\n\"\"\"\n\n"
        f"OBLIGATION:\n"
        f"- actor: {', '.join(obligation.applies_to)}\n"
        f"- action: {obligation.action_required}\n"
        f"- strength: {obligation.criticality}\n"
    )
    if obligation.deadline:
        user += f"- deadline: {obligation.deadline.model_dump(exclude_none=True)}\n"
    if obligation.evidence_artifact:
        user += f"- evidence: {obligation.evidence_artifact}\n"

    message, _ = llm.call("judge", system=SYSTEM, user=user, tools=[TOOL],
                          tool_choice={"type": "tool", "name": "judge_entailment"})
    block = next((b for b in message.content if getattr(b, "type", "") == "tool_use"), None)
    if block is None:
        return "neutral", "judge returned no verdict"
    return block.input.get("entailment", "neutral"), block.input.get("reason", "")
