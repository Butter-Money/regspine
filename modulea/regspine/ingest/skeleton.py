"""Deterministic SEBI grammar: header, block detection, TOC (BuildSpec §4.1 steps 1-4).

Code only — non-negotiable #2. Zero tokens are spent here; the LLM never sees a
well-formed page. Everything in this module was written against the four corpus
PDFs and each regex family below is present in at least one of them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from regspine.common.schemas import Block, SectionIndexEntry

# --- circular number: two families, both real in the corpus -------------------
# Stock Brokers:    SEBI/HO/MIRSD/MIRSD-PoD-1/P/CIR/2024/53
# Merchant Bankers: HO/49/14/15(3)2026-CFD-POD1/I/16178/2026
RE_CIRCULAR_SEBI = re.compile(r"\bSEBI/HO/[A-Za-z0-9/\-_]+?/P/CIR/\d{4}/\d+\b")
RE_CIRCULAR_CFD = re.compile(r"\bHO/\d+/\d+/\d+\(\d+\)\d{4}-[A-Za-z0-9\-]+/[A-Za-z]/\d+/\d{4}\b")

RE_DATE = re.compile(r"\b([A-Z][a-z]{2,8})\s+(\d{1,2}),\s*(\d{4})\b")
RE_ISSUED_ON = re.compile(r"Issued\s+on\s*:\s*" + RE_DATE.pattern, re.I)
RE_LAST_UPDATED = re.compile(r"Last\s+updated\s+on\s*:\s*" + RE_DATE.pattern, re.I)
RE_SUBJECT = re.compile(r"Subject\s*:\s*Master\s+Circular\s+for\s+(.+)", re.I)
# "SEBI had issued Master Circular dated May 22, 2024" — the version this supersedes.
RE_SUPERSEDES = re.compile(r"Master\s+Circular\s+dated\s+" + RE_DATE.pattern, re.I)

# --- TOC row shapes ----------------------------------------------------------
# Part header row, full width: "III. DEALINGS WITH CLIENT". Roman numerals are
# NOT contiguous — May-2024 runs I-VII then IX, X with no Part VIII.
RE_PART = re.compile(r"^\s*([IVXL]+)\.\s+([A-Z][A-Z &,/\-\.']{3,})\s*$")
RE_SECTION_NO = re.compile(r"^\s*(\d{1,3})\.?\s*$")
RE_PAGE_NO = re.compile(r"^\s*(\d{1,4})\s*$")
# The row that switches the TOC into the annexure block, where numbering RESTARTS.
RE_ANNEXURE_BLOCK = re.compile(r"^\s*Annexures?\s*$", re.I)

INTERMEDIARY_SLUGS = {
    "stock brokers": "stock_broker",
    "merchant bankers": "merchant_banker",
}


@dataclass
class Header:
    circular_no: str
    circular_date: date
    intermediary: str
    intermediary_label: str
    supersedes_date: date | None = None
    issued_on: date | None = None


def _mk_date(m: re.Match, group_offset: int = 0) -> date:
    month, day, year = m.group(1 + group_offset), m.group(2 + group_offset), m.group(3 + group_offset)
    return datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date()


def slug_intermediary(label: str) -> str:
    low = label.lower()
    for key, slug in INTERMEDIARY_SLUGS.items():
        if key in low:
            return slug
    # Fall back to a slug rather than guessing wrong; the coverage manifest will
    # surface it and taxonomy.yaml can be extended.
    return re.sub(r"[^a-z0-9]+", "_", low).strip("_")[:40]


def parse_header(first_pages_text: str) -> Header:
    """Parse the fixed SEBI front matter. Raises if the document is not a master
    circular in either known family — better to fail loudly than to ingest junk."""
    m_no = RE_CIRCULAR_SEBI.search(first_pages_text) or RE_CIRCULAR_CFD.search(first_pages_text)
    if not m_no:
        raise ValueError("No SEBI circular number found in either known family.")

    m_subj = RE_SUBJECT.search(first_pages_text)
    if not m_subj:
        raise ValueError("No 'Subject: Master Circular for ...' line found.")
    label = m_subj.group(1).strip().rstrip(".")

    # Date. The Merchant-Bankers circular carries two ("Issued on" and "Last
    # updated on"); the *version* date is the later one, which is what change
    # detection must order by.
    issued = last_upd = None
    if (m := RE_ISSUED_ON.search(first_pages_text)):
        issued = _mk_date(m)
    if (m := RE_LAST_UPDATED.search(first_pages_text)):
        last_upd = _mk_date(m)

    if last_upd:
        circ_date = last_upd
    elif issued:
        circ_date = issued
    else:
        # Stock-Broker family: the date sits on the same line as the circular no.
        tail = first_pages_text[m_no.end(): m_no.end() + 120]
        m_d = RE_DATE.search(tail) or RE_DATE.search(first_pages_text)
        if not m_d:
            raise ValueError("No circular date found.")
        circ_date = _mk_date(m_d)

    supersedes = None
    for m in RE_SUPERSEDES.finditer(first_pages_text):
        d = _mk_date(m)
        if d < circ_date:  # the preamble also names the current one
            supersedes = d if supersedes is None or d > supersedes else supersedes

    return Header(
        circular_no=m_no.group(0),
        circular_date=circ_date,
        intermediary=slug_intermediary(label),
        intermediary_label=label,
        supersedes_date=supersedes,
        issued_on=issued,
    )


# ---------------------------------------------------------------- TOC parsing


# TOC entries are typeset with dot leaders ("Deployment of Funds .......... 6"),
# which are decoration, not title. They must be stripped before the title is used
# for heading matching or stored as section_title.
RE_DOT_LEADER = re.compile(r"[.\u2026]{3,}\s*\d*\s*$")


def clean_title(raw: str) -> str:
    title = re.sub(r"\s+", " ", raw or "").strip()
    title = RE_DOT_LEADER.sub("", title).strip()
    return title.strip(" .\u2026-")


def _cell(row: list, i: int) -> str:
    if i >= len(row) or row[i] is None:
        return ""
    return re.sub(r"\s+", " ", str(row[i])).strip()


def parse_toc_rows(rows: list[list]) -> list[SectionIndexEntry]:
    """Turn raw 3-column TOC table rows into the section index.

    The index is keyed on (block, part, section_no) rather than section_no alone.
    In the body, numbering runs continuously across Parts I-X; the ``Annexures``
    row then restarts it at 1. A flat map loses 42 of 133 rows in May-2024.
    """
    entries: list[SectionIndexEntry] = []
    block: Block = "body"
    part: str | None = None

    for row in rows:
        c0, c1, c2 = _cell(row, 0), _cell(row, 1), _cell(row, 2)
        if not c0 and not c1:
            continue

        # Header row of the table itself.
        if c0.lower().startswith("s. no") or c1.lower() == "subject":
            continue

        # "Annexures" — numbering restarts from here.
        if RE_ANNEXURE_BLOCK.match(c0) or (not c1 and RE_ANNEXURE_BLOCK.match(c1 or c0)):
            block, part = "annexure", None
            continue

        # Part header. Sometimes carries its own page number in col 2.
        if (m := RE_PART.match(c0)):
            part = m.group(1)
            continue
        # Some rows put the part header in the subject column instead.
        if not c0 and (m := RE_PART.match(c1)):
            part = m.group(1)
            continue

        # Numbered section row.
        if (m := RE_SECTION_NO.match(c0)) and c1:
            page = int(c2) if RE_PAGE_NO.match(c2) else 0
            entries.append(
                SectionIndexEntry(
                    block=block,
                    part=part,
                    section_no=int(m.group(1)),
                    title=clean_title(c1),
                    start_page=page,
                )
            )

    return entries


def looks_like_toc_row(row: list) -> bool:
    c0, c1 = _cell(row, 0), _cell(row, 1)
    return bool(RE_SECTION_NO.match(c0) and c1) or bool(RE_PART.match(c0)) or bool(
        RE_ANNEXURE_BLOCK.match(c0)
    )
