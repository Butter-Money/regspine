"""M1 gate: segmentation vs the TOC (BuildSpec §9).

The TOC is SEBI's own segmentation ground truth, so these tests are scored
against the documents themselves rather than against hand-written expectations.

The load is slow (400-page PDFs), so documents are parsed once per session.
"""

from __future__ import annotations

import pytest

from regspine.ingest.dom import build_section_index, load_document

CORPUS = {
    "may2024": ("data/corpus/1716371484396.pdf", "SEBI/HO/MIRSD/MIRSD-PoD-1/P/CIR/2024/53"),
    "aug2024": ("data/corpus/1723438086672.pdf", "SEBI/HO/MIRSD/MIRSD-PoD-1/P/CIR/2024/110"),
    "jun2025": ("data/corpus/1750158789381.pdf", "SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/90"),
}

STOCK_BROKER_VERSIONS = list(CORPUS)


@pytest.fixture(scope="session")
def parsed() -> dict:
    out = {}
    for name, (path, _) in CORPUS.items():
        doc = load_document(path)
        entries, gaps = build_section_index(doc)
        out[name] = (doc, entries, gaps)
    return out


@pytest.mark.parametrize("version", STOCK_BROKER_VERSIONS)
def test_header_grammar(parsed, version):
    doc, _, _ = parsed[version]
    assert doc.header.circular_no == CORPUS[version][1]
    assert doc.header.intermediary == "stock_broker"


def test_supersedes_chain_is_derived_not_assumed(parsed):
    """Each version names the one it replaces, so the chain is deterministic."""
    may, aug, jun = (parsed[v][0].header for v in STOCK_BROKER_VERSIONS)
    assert aug.supersedes_date == may.circular_date
    assert jun.supersedes_date == aug.circular_date


@pytest.mark.parametrize("version", STOCK_BROKER_VERSIONS)
@pytest.mark.parametrize("block", ["body", "annexure"])
def test_section_recall_is_contiguous(parsed, version, block):
    """The recall gate. SEBI numbers sections 1..N with no holes, so any missing
    number is a parse failure — this is what caught extract_tables() silently
    dropping rows whose titles wrap."""
    _, entries, _ = parsed[version]
    nums = sorted(e.section_no for e in entries if e.block == block)
    assert nums, f"no {block} sections parsed for {version}"
    assert nums[0] == 1
    expected = list(range(1, nums[-1] + 1))
    assert nums == expected, f"{version}/{block} missing {sorted(set(expected) - set(nums))}"


@pytest.mark.parametrize("version", STOCK_BROKER_VERSIONS)
def test_index_keys_are_unique(parsed, version):
    """(block, section_no) must be collision-free. A flat {section_no: ...} map
    loses 42 of 133 rows in May-2024 because the annexure block restarts at 1."""
    _, entries, _ = parsed[version]
    keys = [(e.block, e.section_no) for e in entries]
    assert len(keys) == len(set(keys))


def test_mvp_slice_renumbers_across_versions(parsed):
    """'Settlement of Running Account' is item 47 in May and Aug 2024 and item 48
    in Jun 2025. Change-detection must therefore never align on section_no —
    doing so would report the MVP slice as superseded+added instead of modified.
    """
    found = {}
    for version in STOCK_BROKER_VERSIONS:
        _, entries, _ = parsed[version]
        hits = [e for e in entries if "running account" in e.title.lower()]
        assert len(hits) == 1, f"{version}: expected exactly one match, got {len(hits)}"
        found[version] = hits[0]

    assert found["may2024"].section_no == 47
    assert found["aug2024"].section_no == 47
    assert found["jun2025"].section_no == 48
    assert {e.part for e in found.values()} == {"III"}


@pytest.mark.parametrize("version", STOCK_BROKER_VERSIONS)
def test_parts_are_recorded_even_though_not_contiguous(parsed, version):
    """May-2024 runs I-VII then IX, X — Part VIII only exists from Aug-2024.
    The parser must not assume roman numerals are gap-free."""
    _, entries, _ = parsed[version]
    parts = {e.part for e in entries if e.block == "body" and e.part}
    assert {"I", "II", "III"} <= parts
    if version == "may2024":
        assert "VIII" not in parts
    else:
        assert "VIII" in parts


@pytest.mark.parametrize("version", STOCK_BROKER_VERSIONS)
def test_section_index_is_idempotent(parsed, version):
    """Non-negotiable #2: re-parsing the same file yields an identical index."""
    path = CORPUS[version][0]
    entries_a = [e.model_dump() for e in build_section_index(load_document(path))[0]]
    _, entries_b, _ = parsed[version]
    assert entries_a == [e.model_dump() for e in entries_b]
