"""M1 exit gate: the assembled SebiDom (BuildSpec §4.1, §9).

Idempotency is the load-bearing test here. Non-negotiable #2 says re-running the
ingestor must reproduce the DOM byte for byte; without that, a change ledger
built by diffing two ingests would report churn caused by the parser rather than
by SEBI.
"""

from __future__ import annotations

import pytest

from regspine.ingest.dom import ingest

CORPUS = {
    "may2024": "data/corpus/1716371484396.pdf",
    "aug2024": "data/corpus/1723438086672.pdf",
    "jun2025": "data/corpus/1750158789381.pdf",
    "merchant_bankers": "data/corpus/1784029390357.pdf",
}
ALL = list(CORPUS)


@pytest.fixture(scope="session")
def doms(ingest_cached) -> dict:
    return {name: ingest_cached(path) for name, path in CORPUS.items()}


@pytest.mark.parametrize("version", ALL)
def test_section_recall_is_total(doms, version):
    cov = doms[version].coverage
    assert cov.sections_expected > 0
    assert cov.sections_found == cov.sections_expected
    assert cov.section_recall == 1.0


@pytest.mark.parametrize("version", ALL)
def test_dom_hash_is_idempotent(doms, version):
    """Same file in, same hash out — and it must not drift with wall-clock time."""
    again = ingest(CORPUS[version])
    assert again.dom_hash == doms[version].dom_hash
    assert again.ingested_at != doms[version].ingested_at  # excluded from the hash


@pytest.mark.parametrize("version", ALL)
def test_documents_differ_from_each_other(doms, version):
    """A hash that is stable but identical everywhere would pass the test above
    and be useless."""
    others = [d.dom_hash for name, d in doms.items() if name != version]
    assert doms[version].dom_hash not in others


@pytest.mark.parametrize("version", ALL)
def test_llm_is_confined_to_the_coverage_manifest(doms, version):
    """Non-negotiable #6: only pages the deterministic parser could not handle are
    ever eligible for the LLM fallback."""
    cov = doms[version].coverage
    gap_pages = {g.page for g in cov.gaps}
    assert set(cov.llm_eligible_pages) <= gap_pages
    assert len(cov.llm_eligible_pages) < cov.total_pages / 2


def test_merchant_bankers_parses_despite_yielding_no_tables(doms):
    """The generality case. Its TOC page yields zero tables to pdfplumber, so it
    is carried entirely by the text-recovery pass — sections 1..10, contiguous,
    which is an independent check rather than a self-fulfilling one."""
    dom = doms["merchant_bankers"]
    assert dom.intermediary == "merchant_banker"
    nums = sorted(e.section_no for e in dom.section_index if e.block == "body")
    assert nums == list(range(1, 11))
    assert len(dom.clauses) > 100
    assert all(e.title and not e.title.endswith(".") for e in dom.section_index)


def test_only_aug2024_can_validate_change_detection(doms):
    """Restated at DOM level: the absence of a change list is recorded as a
    coverage gap, so downstream code sees it instead of assuming ground truth."""
    assert doms["aug2024"].annexure_a
    for version in ("may2024", "jun2025", "merchant_bankers"):
        dom = doms[version]
        assert not dom.annexure_a
        assert any("Annexure A" in g.detail for g in dom.coverage.gaps)
