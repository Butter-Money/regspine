"""Ground-truth parsers: Annexure A and the Appendix (BuildSpec §4.1 step 6, §9).

These blocks are what the eval harness scores against, so the most important
assertion here is the uncomfortable one: **Annexure A exists in only one of the
four documents.** The spec treats "validated against Annexure A" as the headline
proof for change-detection (§6.4, §10 M4), and that is only available for the
May-2024 -> Aug-2024 transition. Pinning it as a test stops the limitation being
quietly forgotten and rediscovered at M4.
"""

from __future__ import annotations

import pytest

from regspine.ingest.annexure import (
    find_annexure_a,
    find_appendix,
    parse_annexure_a,
    parse_appendix,
)
from regspine.ingest.dom import load_document

CORPUS = {
    "may2024": "data/corpus/1716371484396.pdf",
    "aug2024": "data/corpus/1723438086672.pdf",
    "jun2025": "data/corpus/1750158789381.pdf",
    "merchant_bankers": "data/corpus/1784029390357.pdf",
}


@pytest.fixture(scope="session")
def docs(load_cached) -> dict:
    return {name: load_cached(path) for name, path in CORPUS.items()}


def test_annexure_a_exists_only_in_aug2024(docs):
    """Change-detection ground truth is available for exactly one transition."""
    present = {name: find_annexure_a(doc.pages) is not None for name, doc in docs.items()}
    assert present == {
        "may2024": False,
        "aug2024": True,
        "jun2025": False,
        "merchant_bankers": False,
    }


def test_annexure_a_parses_to_structured_changes(docs):
    doc = docs["aug2024"]
    page = find_annexure_a(doc.pages)
    entries = parse_annexure_a(doc.pages, page)

    assert len(entries) == 5
    # Every row must be attributable to somewhere in the document, otherwise it
    # cannot be used to score a change-set.
    assert all(e.description for e in entries)
    assert sum(len(e.referenced_paras) or len(e.referenced_pages) for e in entries) >= 5

    paras = {p for e in entries for p in e.referenced_paras}
    assert {"41.9", "50", "94", "51.3.6"} <= paras


def test_annexure_a_does_not_cover_the_mvp_slice(docs):
    """The only change list SEBI provides says nothing about the running-account
    section, so the MVP demo slice cannot be validated against it. Asserted so the
    demo narrative and the eval fixture stay honestly separate."""
    doc = docs["aug2024"]
    entries = parse_annexure_a(doc.pages, find_annexure_a(doc.pages))
    paras = {p.split(".")[0] for e in entries for p in e.referenced_paras}
    assert "47" not in paras
    assert not any("running account" in e.description.lower() for e in entries)


@pytest.mark.parametrize("version", ["may2024", "aug2024", "jun2025"])
def test_appendix_parses_on_every_stock_broker_version(docs, version):
    doc = docs[version]
    page = find_appendix(doc.pages)
    assert page is not None
    entries = parse_appendix(doc.pages, page)
    assert len(entries) > 100
    assert all(e.circular_no for e in entries)
    assert sum(1 for e in entries if e.circular_date) > len(entries) * 0.8


def test_appendix_grows_as_circulars_are_consolidated(docs):
    """Each version consolidates more source circulars than the last — a cheap
    sanity check that the parser is tracking the document, not a fixed table."""
    counts = {
        v: len(parse_appendix(docs[v].pages, find_appendix(docs[v].pages)))
        for v in ("may2024", "aug2024", "jun2025")
    }
    assert counts["may2024"] < counts["aug2024"] < counts["jun2025"]


def test_merchant_bankers_has_neither_block(docs):
    """The generality case: M6 cannot rely on either ground-truth block."""
    doc = docs["merchant_bankers"]
    assert find_annexure_a(doc.pages) is None
    assert find_appendix(doc.pages) is None
