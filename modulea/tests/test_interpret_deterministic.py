"""Deterministic halves of the interpreter: deadlines and the gate (§4.3, §4.4).

No API calls — these are the parts deliberately kept out of the model's hands, so
they must be provable without one. Phrases are taken from the corpus wherever
possible rather than invented.
"""

from __future__ import annotations

from datetime import date

import pytest

from regspine.common.schemas import Anchor, Groundedness, Obligation
from regspine.interpret.deadlines import normalise_deadline
from regspine.interpret.gate import (
    check_keyterms,
    check_modality,
    check_span,
    evaluate,
    score,
)

# --------------------------------------------------------------- deadlines


@pytest.mark.parametrize(
    "text,offset,unit,relative_to",
    [
        ("shall settle within 3 working days of quarter-end", 3, "working_day", "quarter_end"),
        ("not later than fifteen days from the date of receipt", 15, "day", "receipt"),
        ("shall report within 7 days", 7, "day", None),
        ("within 2 months of the end of the month", 2, "month", "month_end"),
        ("shall be completed within 1 week", 7, "day", None),
        ("pay-in obligation of T+1 day", 1, "day", "trade_date"),
    ],
)
def test_offsets_are_normalised(text, offset, unit, relative_to):
    d = normalise_deadline(text)
    assert d is not None, text
    assert (d.offset, d.unit, d.relative_to) == (offset, unit, relative_to)


def test_bare_periodicity_has_no_offset():
    """The running-account clause says settlement happens "on quarterly and monthly
    basis" with no offset — a recurrence, not a countdown."""
    d = normalise_deadline(
        "shall settle the running accounts at the choice of the clients on "
        "quarterly and monthly basis, on the dates stipulated by the Stock Exchanges."
    )
    assert d is not None
    assert d.offset is None
    assert d.unit == "quarter"


def test_fixed_date():
    d = normalise_deadline("shall comply on or before March 31, 2025")
    assert d is not None and d.fixed_date == date(2025, 3, 31)


def test_no_deadline_returns_none():
    """Absence must be distinguishable from 'immediately'."""
    assert normalise_deadline("The TM shall maintain records of client instructions.") is None
    assert normalise_deadline("") is None


# -------------------------------------------------------------------- gate

CLAUSE = (
    "47.1.1 The TM, after considering the End of the Day (EOD) obligation of funds "
    "across all the Exchanges, shall settle the running accounts at the choice of "
    "the clients on quarterly and monthly basis, on the dates stipulated by the "
    "Stock Exchanges."
)
DOC = "prefix " + CLAUSE + " suffix"
SPAN = (7, 7 + len(CLAUSE))


def make_obligation(**kw) -> Obligation:
    defaults = dict(
        obligation_id="OB-TEST",
        obligation_type="conduct",
        action_required="settle the running accounts of clients on a quarterly and monthly basis",
        criticality="binding",
        confidence=0.9,
        effective_date=date(2024, 5, 22),
        source=Anchor(
            circular_no="SEBI/TEST/1",
            circular_date=date(2024, 5, 22),
            intermediary="stock_broker",
            page=122,
            char_span=SPAN,
        ),
    )
    defaults.update(kw)
    return Obligation(**defaults)


def test_span_must_resolve():
    assert check_span(make_obligation(), DOC)
    bad = make_obligation()
    bad.source.char_span = (10_000, 10_050)
    assert not check_span(bad, DOC)


def test_keyterms_accept_a_faithful_action():
    assert check_keyterms(make_obligation(), CLAUSE)


def test_keyterms_reject_an_invented_action():
    """The case the gate exists for: a plausible SEBI-sounding duty that the cited
    clause simply does not contain."""
    invented = make_obligation(
        action_required="maintain a cyber security incident response plan and report breaches to CERT-In"
    )
    assert not check_keyterms(invented, CLAUSE)


def test_modality_rejects_binding_read_of_advisory_text():
    advisory_text = "The TM may consider settling the running account more frequently."
    assert not check_modality(make_obligation(criticality="binding"), advisory_text)
    assert check_modality(make_obligation(criticality="advisory"), advisory_text)


def test_modality_accepts_binding_read_of_shall():
    assert check_modality(make_obligation(criticality="binding"), CLAUSE)


def test_auto_accept_requires_everything_including_entailment():
    ob = make_obligation()
    g = evaluate(ob, DOC, entailment="entailed")
    assert g.span_ok and g.keyterm_ok and g.modality_ok
    assert ob.review_status == "auto_accepted"
    assert g.score > 0.9


def test_missing_entailment_fails_closed():
    """A caller that skips the judge must not get an auto-accepted obligation."""
    ob = make_obligation()
    evaluate(ob, DOC)  # entailment defaults to neutral
    assert ob.review_status == "needs_review"


def test_contradiction_is_rejected_outright():
    ob = make_obligation()
    evaluate(ob, DOC, entailment="contradicted")
    assert ob.review_status == "rejected"


def test_low_confidence_goes_to_review_even_when_grounded():
    ob = make_obligation(confidence=0.4)
    evaluate(ob, DOC, entailment="entailed")
    assert ob.review_status == "needs_review"


def test_unresolvable_span_is_rejected():
    ob = make_obligation()
    ob.source.char_span = (99_000, 99_100)
    evaluate(ob, DOC, entailment="entailed")
    assert ob.review_status == "rejected"


def test_score_is_dominated_by_entailment():
    everything_but_entailment = Groundedness(
        span_ok=True, keyterm_ok=True, modality_ok=True, entailment="neutral"
    )
    assert score(everything_but_entailment) < 0.8
