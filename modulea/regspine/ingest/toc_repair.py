"""Deterministic recovery of TOC rows that pdfplumber's table detector drops.

Why this exists: in every Stock-Broker version, a handful of TOC rows have a
title long enough to wrap, which puts the section number on its own text line.
``extract_tables()`` omits those rows entirely — not as an empty cell, as no row
at all. May-2024 loses body sections 26 and 52 and annexure rows 6 and 30 that
way, which caps section recall at ~97.8%.

Two shapes occur, both taken verbatim from the corpus:

    Applicability of Rule 8(1)(f) and 8(3)(f) of the Securities Contract
    26. 70                        <- number and page, title wrapped either side
    (Regulation) Rules, 1957

    Securities Trading through Wireless medium on Wireless Application 135
    52.                           <- number alone, page rode the title line
    Protocol (WAP) platform

This is a *structural* property of the layout, not an anomaly, so it is repaired
in code. Non-negotiable #2 keeps the LLM off the happy path; the coverage
manifest is for pages that genuinely defeat deterministic parsing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# "26. 70"  -> number + page, title wrapped around it
RE_NUM_PAGE = re.compile(r"^\s*(\d{1,3})\.\s+(\d{1,4})\s*$")
# "52."     -> number alone
RE_NUM_ONLY = re.compile(r"^\s*(\d{1,3})\.\s*$")
# "27. Mode of payment and delivery 71" -> a complete row, already handled by the table pass
RE_FULL_ROW = re.compile(r"^\s*(\d{1,3})\.\s+(\S.*?)\s+(\d{1,4})\s*$")
# Trailing page number on a wrapped title line
RE_TRAILING_PAGE = re.compile(r"^(.*?)\s+(\d{1,4})\s*$")
# Part headers and the annexure switch must not be swallowed into a title
RE_PART_LINE = re.compile(r"^\s*[IVXL]+\.\s+[A-Z][A-Z &,/\-\.']{3,}\s*$")
RE_ANNEXURES_LINE = re.compile(r"^\s*Annexures?\s*$", re.I)


@dataclass
class RecoveredRow:
    section_no: int
    title: str
    page: int
    source_line: int


def _is_boundary(line: str) -> bool:
    """A line that must never be absorbed into a wrapped title."""
    s = line.strip()
    if not s:
        return True
    return bool(
        RE_NUM_PAGE.match(s)
        or RE_NUM_ONLY.match(s)
        or RE_FULL_ROW.match(s)
        or RE_PART_LINE.match(s)
        or RE_ANNEXURES_LINE.match(s)
        or s.lower().startswith("s. no")
        or s.lower().startswith("table of contents")
    )


def recover_orphan_rows(page_text: str) -> list[RecoveredRow]:
    """Find TOC rows whose number sits on its own line, and rebuild title + page."""
    lines = page_text.split("\n")
    out: list[RecoveredRow] = []

    for i, line in enumerate(lines):
        s = line.strip()

        m_np = RE_NUM_PAGE.match(s)
        m_no = RE_NUM_ONLY.match(s) if not m_np else None
        if not (m_np or m_no):
            continue

        section_no = int((m_np or m_no).group(1))
        page = int(m_np.group(2)) if m_np else 0

        # Title fragment before the number line.
        before = ""
        j = i - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        if j >= 0 and not _is_boundary(lines[j]):
            before = lines[j].strip()
            if page == 0:
                # The page number rode the end of the title line ("... Application 135").
                if (mt := RE_TRAILING_PAGE.match(before)):
                    before, page = mt.group(1).strip(), int(mt.group(2))

        # Title fragment(s) after the number line, up to the next row.
        after: list[str] = []
        k = i + 1
        while k < len(lines) and not _is_boundary(lines[k]):
            after.append(lines[k].strip())
            k += 1

        title = " ".join(p for p in ([before] + after) if p).strip()
        title = re.sub(r"\s+", " ", title)

        # A recovered row without a title is not a row; leave it for the manifest.
        if title and page:
            out.append(RecoveredRow(section_no=section_no, title=title, page=page, source_line=i))

    return out


def recover_complete_rows(page_text: str) -> list[RecoveredRow]:
    """Recover TOC rows that are complete on one text line but absent from the
    table extraction.

    The table detector drops these too — Aug-2024 loses body sections 24, 51 and
    74, and Jun-2025 loses 55, each of which sits in the text as a perfectly
    ordinary ``"24. Collateral deposited by Clients with Brokers 69"``. Whether a
    row survives ``extract_tables()`` depends on ruling/whitespace geometry, not
    on the row's content, so the text layer is the more reliable source and the
    table pass is the one that needs backfilling.
    """
    out: list[RecoveredRow] = []
    for i, line in enumerate(page_text.split("\n")):
        s = line.strip()
        if not (m := RE_FULL_ROW.match(s)):
            continue
        title = re.sub(r"\s+", " ", m.group(2)).strip()
        # Guard against a wrapped title fragment that happens to end in a number.
        if not title or title[0].isdigit():
            continue
        out.append(
            RecoveredRow(
                section_no=int(m.group(1)),
                title=title,
                page=int(m.group(3)),
                source_line=i,
            )
        )
    return out


def recover_pageless_rows(page_text: str) -> list[RecoveredRow]:
    """Recover TOC rows that carry a title but no page number.

    May-2024 and Jun-2025 both render annexure row 30 as
    ``"30. Annexure-30 –Root Cause Analysis (RCA) Form"`` with the page number
    absent from the text layer entirely. The row is real, so dropping it would
    understate recall; instead it comes back with ``page=0`` and the caller
    infers a page and records a coverage gap. The TOC page is only ever a *hint* —
    body segmentation resolves the authoritative page by locating the heading —
    so an inferred hint never becomes an obligation's provenance.
    """
    out: list[RecoveredRow] = []
    for i, line in enumerate(page_text.split("\n")):
        s = line.strip()
        if RE_FULL_ROW.match(s) or RE_NUM_PAGE.match(s) or RE_NUM_ONLY.match(s):
            continue  # handled by the other passes
        if not (m := re.match(r"^\s*(\d{1,3})\.\s+(\S.*?)\s*$", s)):
            continue
        title = re.sub(r"\s+", " ", m.group(2)).strip()
        if not title or title[0].isdigit():
            continue
        out.append(
            RecoveredRow(section_no=int(m.group(1)), title=title, page=0, source_line=i)
        )
    return out


def recover_text_rows(page_text: str) -> list[RecoveredRow]:
    """Every TOC row visible in the text layer: wrapped, complete, or pageless."""
    return (
        recover_orphan_rows(page_text)
        + recover_complete_rows(page_text)
        + recover_pageless_rows(page_text)
    )
