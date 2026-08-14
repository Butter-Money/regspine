"""Annexure A and Appendix parsers (BuildSpec §4.1 step 6).

These two blocks are not content — they are **ground truth**:

- **Annexure A ("List of Changes")** is SEBI's own statement of what changed in
  this version. §6.4 validates change-detection against it.
- **The Appendix ("List of Circulars/Communication")** is SEBI's own statement of
  which source circulars were consolidated. §9 scores provenance against it.

Availability is uneven, and callers must handle that rather than assume:
Annexure A is present **only in the Aug-2024 Stock-Broker circular**. May-2024,
Jun-2025 and Merchant Bankers carry no change list at all.
"""

from __future__ import annotations

import re

from regspine.common.schemas import AppendixEntry, ChangeEntry

RE_LIST_OF_CHANGES = re.compile(r"List of Changes", re.I)
RE_ANNEXURE_A = re.compile(r"^\s*Annexure\s*[-–—]?\s*A\s*$", re.M | re.I)
RE_APPENDIX_HEAD = re.compile(r"APPENDIX\s*[-–—]?\s*LIST OF CIRCULARS", re.I)

RE_CIRCULAR_ANY = re.compile(
    r"\b(?:SEBI/[A-Za-z0-9/\-_()]+|[A-Z]{2,}/\d[A-Za-z0-9/\-_()]*)\b"
)
RE_PARA_REF = re.compile(r"Para\s+([\d]+(?:\.[\d]+)*)", re.I)
RE_PAGE_REF = re.compile(r"page\s*no\.?\s*(\d{1,4})", re.I)
RE_SNO = re.compile(r"^\s*(\d{1,3})\.?\s*$")
RE_DATE_TAIL = re.compile(r"dated\s+([A-Z][a-z]+\s+\d{1,2},\s*\d{4})")


def _cell(row: list, i: int) -> str:
    if i >= len(row) or row[i] is None:
        return ""
    return re.sub(r"\s+", " ", str(row[i])).strip()


# ------------------------------------------------------------- Annexure A


def find_annexure_a(pages) -> int | None:
    """1-based physical page of the 'List of Changes', or None if absent.

    Requires *both* markers so the TOC's own reference to the annexure (page 8)
    is not mistaken for the annexure itself.
    """
    for i, page in enumerate(pages, start=1):
        if RE_LIST_OF_CHANGES.search(page.text) and RE_ANNEXURE_A.search(page.text):
            return i
    return None


def parse_annexure_a(pages, page_no: int) -> list[ChangeEntry]:
    """Parse the change list into structured entries.

    Columns are ``S. No. | Changes | Page and para number``. The third column
    routinely carries several references for one row, so they are collected as
    lists rather than a single anchor.
    """
    entries: list[ChangeEntry] = []
    rows: list[list] = []
    for table in pages[page_no - 1].tables:
        rows.extend(table)

    for row in rows:
        s_no_raw, changes, refs = _cell(row, 0), _cell(row, 1), _cell(row, 2)
        if not changes:
            continue
        if s_no_raw.lower().startswith("s. no") or changes.lower() == "changes":
            continue  # header row

        m_sno = RE_SNO.match(s_no_raw)
        m_circ = RE_CIRCULAR_ANY.search(changes)
        combined = f"{changes} {refs}"

        entries.append(
            ChangeEntry(
                s_no=int(m_sno.group(1)) if m_sno else None,
                description=changes,
                page_para_ref=refs or None,
                source_circular_no=m_circ.group(0) if m_circ else None,
                referenced_paras=sorted({m for m in RE_PARA_REF.findall(combined)}),
                referenced_pages=sorted({int(m) for m in RE_PAGE_REF.findall(combined)}),
            )
        )
    return entries


# --------------------------------------------------------------- Appendix


def find_appendix(pages) -> int | None:
    """1-based physical page where the Appendix begins, or None.

    Takes the *last* match: the heading also appears in the TOC near the front.
    """
    hits = [i for i, page in enumerate(pages, start=1) if RE_APPENDIX_HEAD.search(page.text)]
    return hits[-1] if hits else None


def parse_appendix(pages, start_page: int, max_pages: int = 40) -> list[AppendixEntry]:
    """Parse the consolidated-circulars list from ``start_page`` onwards.

    Columns are ``Sr. no | Circular/Notification No. and Date | Subject``. The
    table runs to the end of the document, so parsing simply continues while rows
    keep looking like appendix rows.
    """
    entries: list[AppendixEntry] = []
    for page in pages[start_page - 1: start_page - 1 + max_pages]:
        page_rows = [r for t in page.tables for r in t]
        if not page_rows:
            continue
        parsed_here = 0
        for row in page_rows:
            sr, circ, subject = _cell(row, 0), _cell(row, 1), _cell(row, 2)
            if not circ and not subject:
                continue
            if sr.lower().startswith("sr") or circ.lower().startswith("circular"):
                continue  # header row
            if not circ:
                continue
            m_sno = RE_SNO.match(sr)
            m_date = RE_DATE_TAIL.search(circ)
            entries.append(
                AppendixEntry(
                    s_no=int(m_sno.group(1)) if m_sno else None,
                    circular_no=circ,
                    circular_date=m_date.group(1) if m_date else None,
                    subject=subject,
                )
            )
            parsed_here += 1
        if parsed_here == 0 and entries:
            break  # ran past the end of the appendix table
    return entries
