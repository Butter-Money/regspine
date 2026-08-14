"""The groundedness gate (BuildSpec §4.4) — the anti-hallucination core.

An obligation is only stored if its own cited span supports it. Three of the four
checks are pure code and cost nothing; only entailment needs a model, and it is
only consulted for candidates that have already passed the cheap checks.

The same function is reused verbatim as an eval metric (§9), which is the point:
the thing that admits an obligation is the thing that scores it.
"""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from regspine.common.hashing import normalise_text
from regspine.common.schemas import Groundedness, Obligation

# Deontic modality (§4.2). Binding language creates a duty; advisory language does not.
BINDING = re.compile(
    r"\b(shall|must|is\s+required\s+to|are\s+required\s+to|shall\s+not|"
    r"is\s+mandatory|shall\s+ensure|has\s+to|have\s+to)\b",
    re.I,
)
ADVISORY = re.compile(
    r"\b(may|should|is\s+encouraged|are\s+encouraged|is\s+advised|are\s+advised|"
    r"is\s+desirable|can)\b",
    re.I,
)

# Tokens too generic to evidence that an action came from a clause.
_STOPWORDS = {
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "for", "by", "with",
    "shall", "must", "be", "is", "are", "as", "at", "from", "that", "this",
    "any", "all", "such", "within", "their", "its", "may", "not",
}

KEYTERM_FUZZ_THRESHOLD = 82
KEYTERM_COVERAGE = 0.55


def _salient(text: str) -> list[str]:
    words = re.findall(r"[a-z]{3,}", normalise_text(text))
    return [w for w in words if w not in _STOPWORDS]


def check_span(obligation: Obligation, document_text: str) -> bool:
    """The citation must resolve to non-empty text inside the document."""
    start, end = obligation.source.char_span
    if not (0 <= start < end <= len(document_text)):
        return False
    return bool(document_text[start:end].strip())


def check_keyterms(obligation: Obligation, cited_text: str) -> bool:
    """Salient words of the action must actually appear in the cited clause.

    Fuzzy per-token rather than exact, because the model legitimately inflects
    ("settles" for "settle") and SEBI hyphenates inconsistently. A model that
    invented an obligation from its own knowledge of SEBI practice fails here,
    which is the case this check exists for.
    """
    needles = _salient(obligation.action_required)
    if not needles:
        return False
    haystack_words = set(_salient(cited_text))
    if not haystack_words:
        return False

    hits = 0
    for term in needles:
        if term in haystack_words:
            hits += 1
            continue
        if any(fuzz.ratio(term, w) >= KEYTERM_FUZZ_THRESHOLD for w in haystack_words):
            hits += 1
    return (hits / len(needles)) >= KEYTERM_COVERAGE


def check_modality(obligation: Obligation, cited_text: str) -> bool:
    """The obligation's strength must match the clause's language.

    An advisory "may" recorded as binding is the failure that turns a suggestion
    into a compliance requirement, so the mismatch is treated as a gate failure
    rather than a rounding error.
    """
    binding = bool(BINDING.search(cited_text))
    advisory = bool(ADVISORY.search(cited_text))
    if obligation.criticality == "binding":
        return binding
    # Advisory is acceptable when the clause is advisory, or when both appear and
    # the model chose the weaker reading.
    return advisory or not binding


def score(g: Groundedness) -> float:
    """Weighted, with entailment dominant: the other three are necessary but a
    clause can satisfy all of them and still not entail the obligation."""
    entail = {"entailed": 1.0, "neutral": 0.35, "contradicted": 0.0}[g.entailment]
    return round(
        0.20 * g.span_ok + 0.20 * g.keyterm_ok + 0.15 * g.modality_ok + 0.45 * entail, 4
    )


def evaluate(
    obligation: Obligation,
    document_text: str,
    *,
    entailment: str = "neutral",
    tau_high: float = 0.80,
) -> Groundedness:
    """Run the gate and set ``review_status`` on the obligation in place.

    ``entailment`` is supplied by the caller (NLI or LLM judge) so this function
    stays pure and testable. Callers that skip it get "neutral", which cannot
    reach auto-acceptance — failing closed.
    """
    start, end = obligation.source.char_span
    cited_text = document_text[start:end] if check_span(obligation, document_text) else ""

    g = Groundedness(
        span_ok=bool(cited_text),
        keyterm_ok=check_keyterms(obligation, cited_text) if cited_text else False,
        entailment=entailment,  # type: ignore[arg-type]
        modality_ok=check_modality(obligation, cited_text) if cited_text else False,
    )
    g.score = score(g)

    if g.entailment == "contradicted" or not g.span_ok:
        obligation.review_status = "rejected"
    elif (
        g.span_ok
        and g.keyterm_ok
        and g.modality_ok
        and g.entailment == "entailed"
        and obligation.confidence >= tau_high
    ):
        obligation.review_status = "auto_accepted"
    else:
        obligation.review_status = "needs_review"

    obligation.groundedness = g
    return g
