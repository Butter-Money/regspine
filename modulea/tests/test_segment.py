"""M1 gate: body segmentation and anchor integrity (BuildSpec §4.1 steps 5, 7).

Provenance is non-negotiable #1, so the tests that matter most here are the dull
ones: every clause's char_span must resolve to the text it claims, and no section
may absorb text belonging to another.
"""

from __future__ import annotations

import pytest

from regspine.ingest.dom import build_section_index, find_toc_pages, load_document
from regspine.ingest.segment import TITLE_MATCH_THRESHOLD, locate_sections, split_clauses

CORPUS = {
    "may2024": "data/corpus/1716371484396.pdf",
    "aug2024": "data/corpus/1723438086672.pdf",
    "jun2025": "data/corpus/1750158789381.pdf",
}
VERSIONS = list(CORPUS)


@pytest.fixture(scope="session")
def segmented(load_cached) -> dict:
    out = {}
    for name, path in CORPUS.items():
        doc = load_cached(path)
        entries, _ = build_section_index(doc)
        toc = find_toc_pages(doc)
        body_start = doc.pages[toc[-1]].char_start if toc else 0
        full_text = doc.full_text
        spans, gaps = locate_sections(full_text, entries, body_start)
        clauses = []
        for span in spans:
            clauses.extend(
                split_clauses(
                    full_text,
                    span,
                    intermediary=doc.header.intermediary,
                    circular_no=doc.header.circular_no,
                    circular_date=doc.header.circular_date,
                    page_of=doc.page_of,
                )
            )
        out[name] = dict(
            doc=doc, entries=entries, spans=spans, gaps=gaps,
            clauses=clauses, full_text=full_text,
        )
    return out


@pytest.mark.parametrize("version", VERSIONS)
def test_every_body_section_is_located(segmented, version):
    s = segmented[version]
    body = [e for e in s["entries"] if e.block == "body"]
    assert len(s["spans"]) == len(body)
    assert all(sp.match_score >= TITLE_MATCH_THRESHOLD for sp in s["spans"])


@pytest.mark.parametrize("version", VERSIONS)
def test_sections_are_ordered_and_disjoint(segmented, version):
    """Overlapping spans would attribute one section's text to another, which
    would then be cited as provenance for an obligation that isn't there."""
    spans = segmented[version]["spans"]
    for a, b in zip(spans, spans[1:]):
        assert a.char_start < b.char_start
        assert a.char_end <= b.char_start
        assert a.char_start < a.char_end


@pytest.mark.parametrize("version", VERSIONS)
def test_body_stops_before_the_annexures(segmented, version):
    """The final body section must be bounded by the annexure block. Unbounded,
    it ran to end-of-file and swallowed ~356 annexure paragraphs in May-2024."""
    s = segmented[version]
    last = s["spans"][-1]
    assert last.char_end < len(s["full_text"])
    # A body section spanning a sixth of the document is the signature of that bug.
    assert (last.char_end - last.char_start) < len(s["full_text"]) / 6


@pytest.mark.parametrize("version", VERSIONS)
def test_every_anchor_resolves_to_its_text(segmented, version):
    """The groundedness gate reads clauses back through char_span, so a span that
    doesn't resolve is a citation that cannot be verified."""
    s = segmented[version]
    full_text = s["full_text"]
    for c in s["clauses"]:
        start, end = c.anchor.char_span
        assert 0 <= start < end <= len(full_text)
        assert full_text[start:end].strip() == c.text
        assert c.anchor.page >= 1


@pytest.mark.parametrize("version", VERSIONS)
def test_clause_ids_are_unique(segmented, version):
    clauses = segmented[version]["clauses"]
    assert len({c.clause_id for c in clauses}) == len(clauses)


@pytest.mark.parametrize("version", VERSIONS)
def test_clause_paths_are_well_formed(segmented, version):
    """clause_path is the human-facing half of a citation (spec: 'III.47.a.ii').

    It must identify the section unambiguously. Sections number their clauses
    inconsistently — "47.1" inside section 47, but "1.1" inside section 16 — so
    the path has to carry the section number regardless of which style is used.
    """
    for c in segmented[version]["clauses"]:
        path = c.anchor.clause_path
        assert path and path.startswith(f"{c.anchor.part}.")
        assert path.split(".")[1] == str(c.anchor.section_no), (
            f"{path} does not identify section {c.anchor.section_no}"
        )


@pytest.mark.parametrize("version", VERSIONS)
def test_clause_paths_are_unique(segmented, version):
    """Two clauses sharing a path means two obligations could cite the same
    address and mean different text."""
    paths = [c.anchor.clause_path for c in segmented[version]["clauses"]]
    dupes = {p for p in paths if paths.count(p) > 1}
    assert not dupes, f"duplicate clause paths: {sorted(dupes)[:8]}"


def test_mvp_slice_has_matching_structure_across_versions(segmented):
    """The running-account section must segment identically in all three versions,
    otherwise change-detection would report structural churn that isn't there."""
    shapes = {}
    for version in VERSIONS:
        s = segmented[version]
        span = next(sp for sp in s["spans"] if "running account" in sp.entry.title.lower())
        clauses = [c for c in s["clauses"] if c.anchor.section_no == span.section_no]
        assert clauses, f"{version}: no clauses for the MVP section"
        # Compare the sub-numbering, which is stable, not the section number, which isn't.
        suffixes = sorted(
            ".".join(c.anchor.clause_path.split(".")[2:]) for c in clauses
        )
        shapes[version] = suffixes

    assert shapes["may2024"] == shapes["aug2024"] == shapes["jun2025"]
    assert len(shapes["may2024"]) == 16
