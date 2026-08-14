"""Body segmentation: section index -> located sections -> clauses (BuildSpec §4.1 steps 5, 7).

Deterministic. This is where provenance stops being a schema field and becomes
checkable: every clause carries an absolute ``char_span`` into the document text,
so the groundedness gate (§4.4) can later re-read exactly what a citation claims.

Sections are located by *finding their heading in the body*, not by trusting the
TOC's page number. Two reasons: the printed page numbers in the TOC do not equal
physical PDF page indices (there is front matter before page 1), and one recovered
TOC row has no page number at all. Matching heading text and requiring monotonic
progress through the document is both more accurate and independently checkable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from regspine.common.hashing import clause_id, normalise_text
from regspine.common.schemas import Anchor, Clause, CoverageGap, SectionIndexEntry

# A heading candidate: a line starting with the section number and a title.
def _heading_re(n: int) -> re.Pattern:
    return re.compile(rf"^[ \t]*{n}\.[ \t]+(\S[^\n]*)", re.MULTILINE)


# Clause markers, ordered most- to least-specific. Order matters twice over:
# "dotted" must precede everything (it is the primary SEBI structure), and
# "roman" must precede "alpha" or "(i)" would be read as the letter i.
#
# The dotted form is what the corpus actually uses — 47.1, 47.1.1, 47.2 — and
# Jun-2025 renders it with a trailing dot (48.1.) where May-2024 does not, so the
# trailing dot is optional. Requiring whitespace immediately after the digits
# (an earlier attempt) silently produced zero clauses for the entire Jun-2025
# document while appearing to succeed.
CLAUSE_MARKERS: list[tuple[str, re.Pattern]] = [
    ("dotted", re.compile(r"^[ \t]*(?P<m>\d{1,3}(?:\.\d{1,3})+)\.?[ \t]+", re.MULTILINE)),
    ("roman", re.compile(r"^[ \t]*\((?P<m>[ivxlcd]+)\)[ \t]+", re.MULTILINE | re.I)),
    ("alpha", re.compile(r"^[ \t]*\((?P<m>[a-z])\)[ \t]+", re.MULTILINE)),
    ("alpha_paren", re.compile(r"^[ \t]*(?P<m>[a-z])\)[ \t]+", re.MULTILINE)),
]

# Similarity below which a heading candidate is not accepted as the section.
TITLE_MATCH_THRESHOLD = 72.0


@dataclass
class SectionSpan:
    entry: SectionIndexEntry
    char_start: int
    char_end: int
    heading: str
    match_score: float

    @property
    def section_no(self) -> int:
        return self.entry.section_no


def _score(candidate_title: str, toc_title: str) -> float:
    """How well a body heading matches its TOC row.

    ``partial_ratio`` because the TOC cell often truncates or rewraps the title
    while the body carries it in full (or vice versa).
    """
    return fuzz.partial_ratio(normalise_text(candidate_title), normalise_text(toc_title))


def locate_sections(
    full_text: str, entries: list[SectionIndexEntry], body_start: int = 0
) -> tuple[list[SectionSpan], list[CoverageGap]]:
    """Find each body section's heading, in order, moving only forwards.

    Monotonicity is the safeguard: a numbered list item inside section 40 cannot
    be mistaken for the heading of section 12, because 12 was already placed.
    """
    body = [e for e in entries if e.block == "body"]
    body.sort(key=lambda e: e.section_no)

    spans: list[SectionSpan] = []
    gaps: list[CoverageGap] = []
    cursor = body_start

    for entry in body:
        best: tuple[float, int, str] | None = None
        for m in _heading_re(entry.section_no).finditer(full_text, cursor):
            score = _score(m.group(1), entry.title)
            if best is None or score > best[0]:
                best = (score, m.start(), m.group(1).strip())
            if score >= 95:  # good enough; take the earliest strong match
                break

        if best is None or best[0] < TITLE_MATCH_THRESHOLD:
            gaps.append(
                CoverageGap(
                    page=entry.start_page,
                    reason="unmatched_heading",
                    detail=(
                        f"section {entry.section_no} '{entry.title[:60]}' not located in body"
                        + (f" (best score {best[0]:.0f})" if best else " (no candidate)")
                    ),
                )
            )
            continue

        score, start, heading = best
        spans.append(
            SectionSpan(entry=entry, char_start=start, char_end=len(full_text),
                        heading=heading, match_score=score)
        )
        cursor = start + 1

    # A section runs until the next one begins.
    for a, b in zip(spans, spans[1:]):
        a.char_end = b.char_start

    # The last body section must stop where the annexure block starts — the body
    # does not run to the end of the file. Without this bound the final section
    # absorbs every annexure (303,969 chars, pages 294-402, in May-2024) and its
    # clauses are attributed to a section they do not belong to.
    if spans:
        annexure_start = locate_annexure_start(full_text, entries, after=spans[-1].char_start)
        if annexure_start is not None:
            spans[-1].char_end = annexure_start
        else:
            gaps.append(
                CoverageGap(
                    page=spans[-1].entry.start_page,
                    reason="orphan_span",
                    detail=(
                        "annexure block start not located; last body section is bounded "
                        "by end-of-document and may absorb annexure text"
                    ),
                )
            )

    return spans, gaps


# "Annexure-1", "Annexure - 1", "ANNEXURE 1" at the start of a line.
def _annexure_heading_re(label: str) -> re.Pattern:
    return re.compile(rf"^[ \t]*{label}\s*[-–—]?\s*1\b", re.MULTILINE | re.I)


def locate_annexure_start(
    full_text: str, entries: list[SectionIndexEntry], *, after: int
) -> int | None:
    """Character offset where the annexure block begins, or None.

    Anchored to the first annexure row in the section index rather than to a page
    number, since printed page numbers are not physical page indices and one
    recovered row has no page number at all.
    """
    first = min(
        (e for e in entries if e.block == "annexure"),
        key=lambda e: e.section_no,
        default=None,
    )
    if first is None:
        return None

    # Prefer the exact title from the index; fall back to the generic word.
    lead = first.title.split("-")[0].strip() or "Annexure"
    for pattern in (_annexure_heading_re(re.escape(lead.rstrip("1234567890 -"))),
                    _annexure_heading_re("Annexure")):
        if (m := pattern.search(full_text, after)):
            return m.start()
    return None


# Words that follow a clause number when it is being *cited* rather than opened.
# A clause opens with its own provision ("The TM shall..."); a citation is
# followed by a linking word.
_REFERENCE_WORDS = {"above", "below", "to", "and", "or", "thereof", "herein", "hereof", "read"}


def _is_cross_reference(text: str, match: re.Match) -> bool:
    """True when a numbered marker is a citation inside prose, not a new clause.

    SEBI prose cites its own clauses constantly ("...as specified in 15.5.2
    below."). When such a citation wraps onto a new line it looks exactly like a
    clause opening, producing two different texts that claim the same address.

    The discriminator is the word that follows. An earlier attempt also required
    the previous line to end a sentence, on the theory that clauses start fresh —
    but that dropped 259 genuine clauses to remove 11 citations, because plenty of
    real clauses follow a line with no terminator (the section heading, for one).
    Under-segmenting is the worse failure: a missing clause is an obligation that
    never gets extracted at all.
    """
    tail = text[match.end(): match.end() + 24].strip().lower()
    first_word = re.split(r"[^a-z]+", tail, maxsplit=1)[0] if tail else ""
    return first_word in _REFERENCE_WORDS


def _marker_positions(text: str) -> list[tuple[int, str, str]]:
    """All clause markers in a section body, as (offset, kind, marker)."""
    found: list[tuple[int, str, str]] = []
    claimed: set[int] = set()
    for kind, pattern in CLAUSE_MARKERS:
        for m in pattern.finditer(text):
            if m.start() in claimed:
                continue  # a more specific marker already owns this position
            if kind == "dotted" and _is_cross_reference(text, m):
                continue
            claimed.add(m.start())
            found.append((m.start(), kind, m.group("m")))
    found.sort(key=lambda t: t[0])
    return found


# Depth for the paren-style markers, which nest *under* the nearest dotted clause.
_SUB_DEPTH = {"alpha": 1, "alpha_paren": 1, "roman": 2}


def split_clauses(
    full_text: str,
    span: SectionSpan,
    *,
    intermediary: str,
    circular_no: str,
    circular_date,
    page_of,
) -> list[Clause]:
    """Split one located section into clauses with hierarchical ``clause_path``.

    A section with no internal markers is itself one clause — that is the common
    case for short sections and must not be dropped.
    """
    # Skip the heading line itself: it is the section's title, not a clause.
    heading_end = full_text.find("\n", span.char_start)
    body_start = (
        heading_end + 1 if heading_end != -1 and heading_end < span.char_end else span.char_start
    )
    section_text = full_text[body_start: span.char_end]
    markers = _marker_positions(section_text)

    part = span.entry.part
    base = f"{part}.{span.section_no}" if part else str(span.section_no)

    def mk(local_start: int, local_end: int, path: str) -> Clause | None:
        abs_start = body_start + local_start
        abs_end = body_start + local_end
        text = full_text[abs_start:abs_end].strip()
        if len(text) < 3:
            return None
        anchor = Anchor(
            circular_no=circular_no,
            circular_date=circular_date,
            intermediary=intermediary,
            block="body",
            part=part,
            section_no=span.section_no,
            section_title=span.entry.title,
            clause_path=path,
            page=page_of(abs_start),
            char_span=(abs_start, abs_end),
        )
        return Clause(
            clause_id=clause_id(intermediary, span.section_no, path, text),
            anchor=anchor,
            text=text,
            node_type="clause",
            parent_section_no=span.section_no,
        )

    clauses: list[Clause] = []
    used_paths: dict[str, int] = {}

    def unique(path: str) -> str:
        """Keep clause_path unique within a section.

        A flattened table can repeat a marker — Part VII's default-handling
        timeline has three rows all opening "a)" — and two clauses sharing an
        address means two obligations could cite the same place and mean
        different text. The suffix is honest about what it is: the nth occurrence
        at that address. ``char_span`` remains the authoritative provenance.
        Proper table handling (node_type="table", spec §4.1 step 6) supersedes
        this once tables.py lands.
        """
        n = used_paths.get(path, 0) + 1
        used_paths[path] = n
        return path if n == 1 else f"{path}#{n}"

    if not markers:
        if (c := mk(0, len(section_text), unique(base))):
            clauses.append(c)
        return clauses

    # Text between the heading and the first marker is the section's lead-in.
    if markers[0][0] > 0:
        if (c := mk(0, markers[0][0], unique(base))):
            clauses.append(c)

    # A dotted marker carries its own absolute path ("47.1.1"), so it replaces the
    # current position outright. Paren markers nest beneath whatever dotted clause
    # is currently open.
    dotted_path = base
    sub_stack: list[str] = []

    for i, (pos, kind, marker) in enumerate(markers):
        end = markers[i + 1][0] if i + 1 < len(markers) else len(section_text)

        if kind == "dotted":
            # Two numbering conventions coexist in the corpus. Most sections
            # prefix the section number ("47.1" inside section 47), but some
            # number locally ("1.1" inside section 16). Treating the latter as
            # absolute yields "II.1.1", which is indistinguishable from a clause
            # of section 1 — an ambiguous citation, which provenance cannot have.
            head = marker.split(".")[0]
            absolute = head == str(span.section_no)
            dotted_path = (
                (f"{part}.{marker}" if part else marker) if absolute else f"{base}.{marker}"
            )
            sub_stack = []
            path = dotted_path
        else:
            depth = _SUB_DEPTH[kind]
            sub_stack = sub_stack[: depth - 1]
            while len(sub_stack) < depth - 1:
                sub_stack.append("_")
            sub_stack.append(marker.lower())
            path = ".".join([dotted_path, *sub_stack])

        if (c := mk(pos, end, unique(path))):
            clauses.append(c)

    return clauses
