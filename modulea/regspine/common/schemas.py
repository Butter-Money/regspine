"""Canonical data contracts — the spine of Module A (BuildSpec §2).

Every stage's output is one of these types, so each stage is serialisable,
diffable and testable in isolation. Three additions to the spec's §2 list, each
forced by the actual structure of the corpus rather than invented:

- ``Anchor.block`` — SEBI circulars carry four addressable regions (preamble,
  body, annexure, appendix) and the annexure block *restarts its numbering at 1*.
  Without the block, a section number is ambiguous: in the May-2024 Stock-Broker
  circular there are 133 numbered TOC rows for only 91 distinct numbers.
- ``SectionIndexEntry`` — keyed on (block, part, section_no) for the same reason.
  A flat ``{section_no: ...}`` map silently drops 42 of those rows, which would
  let the "section recall = 100%" gate pass while under-counting.
- ``CoverageManifest`` — §4.1 step 8 names it and §4.1's LLM fallback is defined
  entirely in terms of it, so it needs to be a typed artifact: it is the list of
  pages the LLM is *permitted* to see.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

# Which addressable region of the circular a node lives in. The body is the
# operative text; annexures and appendix carry their own numbering.
Block = Literal["preamble", "body", "annexure", "appendix", "toc"]

NodeType = Literal["clause", "table", "list_item", "annexure_entry", "appendix_entry"]

ReviewStatus = Literal["auto_accepted", "needs_review", "human_verified", "rejected"]

Criticality = Literal["binding", "advisory"]


class Anchor(BaseModel):
    """Provenance. Non-negotiable #1: no obligation exists without one of these."""

    circular_no: str
    circular_date: date
    intermediary: str

    block: Block = "body"
    # Roman part label, e.g. "III". NOT contiguous: the May-2024 Stock-Broker
    # circular runs I-VII then IX, X — Part VIII only appears from Aug-2024.
    part: str | None = None
    section_no: int | None = None
    section_title: str | None = None
    clause_path: str | None = None  # e.g. "III.47.a.ii"

    page: int  # 1-based, as printed in the TOC
    char_span: tuple[int, int]

    def cite(self) -> str:
        """Human-readable citation, used in traces and the copilot's answers."""
        bits = [self.circular_no]
        if self.part:
            bits.append(f"Part {self.part}")
        if self.section_no is not None:
            bits.append(f"s.{self.section_no}")
        if self.clause_path:
            bits.append(self.clause_path)
        bits.append(f"p.{self.page}")
        return " · ".join(bits)


class SectionIndexEntry(BaseModel):
    """One row of the TOC. The TOC is segmentation ground truth (§9)."""

    block: Block
    part: str | None
    section_no: int
    title: str
    start_page: int

    @property
    def key(self) -> tuple[str, str | None, int]:
        return (self.block, self.part, self.section_no)


class Clause(BaseModel):
    """Ingestor output; the operative unit for categorise + interpret."""

    clause_id: str  # sha256, see store/identity.py
    anchor: Anchor
    text: str
    node_type: NodeType = "clause"
    parent_section_no: int | None = None
    defined_terms: list[str] = Field(default_factory=list)


class CategoryTags(BaseModel):
    applies_to: list[str] = Field(default_factory=list)
    obligation_type: str
    trigger_class: Literal["periodic", "event_driven", "one_time", "conditional"]
    criticality: Criticality
    evidence_class: str | None = None
    confidence: float = 0.0
    inherited: dict = Field(default_factory=dict)


class Deadline(BaseModel):
    offset: int | None = None
    unit: Literal["day", "working_day", "month", "quarter"] | None = None
    relative_to: str | None = None  # quarter_end | event | fixed_date
    fixed_date: date | None = None


class Groundedness(BaseModel):
    """Output of the anti-hallucination gate (§4.4). Reused verbatim as an eval metric."""

    span_ok: bool = False
    keyterm_ok: bool = False
    entailment: Literal["entailed", "neutral", "contradicted"] = "neutral"
    modality_ok: bool = False
    score: float = 0.0


class Obligation(BaseModel):
    obligation_id: str  # stable across versions so diffs align (§5 identity)
    applies_to: list[str] = Field(default_factory=list)
    obligation_type: str
    trigger: dict = Field(default_factory=dict)  # {class, basis}
    deadline: Deadline | None = None
    action_required: str
    evidence_artifact: str | None = None
    parameters: dict = Field(default_factory=dict)
    consequence: str | None = None
    criticality: Criticality
    defined_terms_used: list[str] = Field(default_factory=list)

    source: Anchor  # required — the citation
    effective_date: date
    supersedes: str | None = None  # obligation_id@circular_no
    rationale: str | None = None
    confidence: float = 0.0
    groundedness: Groundedness = Field(default_factory=Groundedness)
    interpretation_trace: str = ""
    review_status: ReviewStatus = "needs_review"


class CoverageGap(BaseModel):
    """A page or section the deterministic parser could not confidently segment."""

    page: int
    reason: Literal[
        "no_text", "scanned", "unmatched_heading", "table_parse_failed", "orphan_span"
    ]
    detail: str = ""


class CoverageManifest(BaseModel):
    """What parsed and what didn't. Gates the LLM: only pages listed here may be
    sent to ``prompts/page_repair.j2`` (§4.1). Everything else costs zero tokens."""

    document_sha256: str
    total_pages: int
    pages_parsed: int
    sections_expected: int  # from the TOC
    sections_found: int
    gaps: list[CoverageGap] = Field(default_factory=list)

    @property
    def section_recall(self) -> float:
        if self.sections_expected == 0:
            return 0.0
        return self.sections_found / self.sections_expected

    @property
    def llm_eligible_pages(self) -> list[int]:
        return sorted({g.page for g in self.gaps})


class ChangeEntry(BaseModel):
    """One row of Annexure A ("List of Changes") — change-detection ground truth (§6.4).

    Present in only one document of the corpus (the Aug-2024 Stock-Broker
    circular); May-2024, Jun-2025 and Merchant Bankers carry no change list.
    """

    s_no: int | None = None
    description: str
    page_para_ref: str | None = None
    source_circular_no: str | None = None
    referenced_pages: list[int] = Field(default_factory=list)
    # Dotted paragraph paths as SEBI writes them — "41.9", "15.8.1.1" — which
    # line up with Anchor.clause_path, not with section numbers. Strings, not
    # ints: "41.9" is an address, not a quantity.
    referenced_paras: list[str] = Field(default_factory=list)


class AppendixEntry(BaseModel):
    """One row of the Appendix (list of circulars) — provenance ground truth (§9)."""

    s_no: int | None = None
    circular_no: str
    circular_date: str | None = None
    subject: str
    status: str | None = None


class SebiDom(BaseModel):
    """The deterministic ingestor's headline artifact. ``dom_hash`` must be
    byte-stable across re-runs — non-negotiable #2 (idempotency)."""

    document_sha256: str
    dom_hash: str
    circular_no: str
    circular_date: date
    intermediary: str
    doc_type: str = "master_circular"
    supersedes_circular_no: str | None = None
    total_pages: int

    section_index: list[SectionIndexEntry] = Field(default_factory=list)
    clauses: list[Clause] = Field(default_factory=list)
    annexure_a: list[ChangeEntry] = Field(default_factory=list)
    appendix: list[AppendixEntry] = Field(default_factory=list)
    coverage: CoverageManifest | None = None

    ingested_at: datetime | None = None
