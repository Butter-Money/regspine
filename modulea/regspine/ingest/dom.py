"""Ingestor orchestration: PDF -> SebiDom (BuildSpec §4.1).

Deterministic and idempotent. Page text is extracted once and cached on the
``Document`` so char offsets stay consistent between the TOC pass, segmentation
and the groundedness gate — a char_span is meaningless if two passes disagree
about where a page starts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pdfplumber

from regspine.common.hashing import dehyphenate, sha256_file
from regspine.common.schemas import (
    Block,
    CoverageGap,
    SectionIndexEntry,
)
from regspine.ingest.toc_repair import recover_text_rows
from regspine.ingest.skeleton import (
    Header,
    looks_like_toc_row,
    parse_header,
    parse_toc_rows,
)

RE_TOC_HEADING = re.compile(r"TABLE\s+OF\s+CONTENTS", re.I)
# Running headers/footers that must not leak into clause text or char offsets.
RE_RUNNING = re.compile(r"^\s*(?:Page\s+\d+\s+of\s+\d+|\d{1,4})\s*$")


@dataclass
class Page:
    number: int  # 1-based physical page
    text: str
    char_start: int  # offset into the document-wide text stream
    tables: list[list[list]] = field(default_factory=list)

    @property
    def char_end(self) -> int:
        return self.char_start + len(self.text)


@dataclass
class Document:
    path: str
    sha256: str
    pages: list[Page]
    header: Header
    gaps: list[CoverageGap] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "".join(p.text for p in self.pages)

    def page_of(self, char_offset: int) -> int:
        for p in self.pages:
            if p.char_start <= char_offset < p.char_end:
                return p.number
        return self.pages[-1].number if self.pages else 0

    def slice(self, span: tuple[int, int]) -> str:
        return self.full_text[span[0]: span[1]]


def _clean_page_text(raw: str) -> str:
    """Strip running headers/footers, de-hyphenate. Deterministic: same input,
    same output, so char offsets are reproducible."""
    lines = [ln for ln in (raw or "").split("\n")]
    kept = [ln for ln in lines if not RE_RUNNING.match(ln)]
    return dehyphenate("\n".join(kept)) + "\n"


def load_document(path: str) -> Document:
    """Extract every page once, building the document-wide char stream."""
    pages: list[Page] = []
    gaps: list[CoverageGap] = []
    offset = 0

    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            raw = page.extract_text() or ""
            if not raw.strip():
                # A page with no text layer is either blank or scanned; either way
                # deterministic parsing cannot see it, so it becomes LLM-eligible.
                gaps.append(
                    CoverageGap(page=i, reason="no_text", detail="empty text layer")
                )
            text = _clean_page_text(raw)
            tables = page.extract_tables() or []
            pages.append(Page(number=i, text=text, char_start=offset, tables=tables))
            offset += len(text)

    if not pages:
        raise ValueError(f"No pages extracted from {path}")

    front = "".join(p.text for p in pages[:3])
    header = parse_header(front)
    return Document(path=path, sha256=sha256_file(path), pages=pages, header=header, gaps=gaps)


def find_toc_pages(doc: Document, search_limit: int = 20) -> list[int]:
    """Locate the contiguous run of TOC pages: the page carrying the heading plus
    every following page that still yields TOC-shaped table rows."""
    start = None
    for p in doc.pages[:search_limit]:
        if RE_TOC_HEADING.search(p.text):
            start = p.number
            break
    if start is None:
        return []

    toc = [start]
    for p in doc.pages[start: start + search_limit]:
        rows = [r for t in p.tables for r in t]
        if rows and sum(looks_like_toc_row(r) for r in rows) >= max(2, len(rows) // 4):
            toc.append(p.number)
        else:
            break
    return toc


def _toc_page_hint(entries: list[SectionIndexEntry], toc_page: int, toc_pages: list[int]) -> int:
    """Best available page for a TOC row that carries no page number.

    Uses the largest start_page already seen on earlier TOC pages, so the row
    lands in the right block. This is a segmentation hint only — the row's real
    page is resolved later by finding its heading in the body.
    """
    seen_pages = [e.start_page for e in entries if e.start_page]
    return max(seen_pages) if seen_pages else 0


def build_section_index(doc: Document) -> tuple[list[SectionIndexEntry], list[CoverageGap]]:
    """TOC -> section index. The TOC is segmentation ground truth (§9)."""
    toc_pages = find_toc_pages(doc)
    if not toc_pages:
        return [], [
            CoverageGap(page=0, reason="unmatched_heading", detail="no TABLE OF CONTENTS found")
        ]

    rows: list[list] = []
    for n in toc_pages:
        for table in doc.pages[n - 1].tables:
            rows.extend(table)

    entries = parse_toc_rows(rows)
    gaps: list[CoverageGap] = []

    # The table detector silently drops TOC rows whose title wraps around the
    # number (see toc_repair). Recover them from the page text and merge, keyed
    # on (block, part, section_no) so a recovered row can never shadow a parsed
    # one. Block/part are inherited from the nearest preceding entry on the page.
    # Identity within the TOC is (block, section_no): body numbering runs
    # continuously across parts, and the annexure block restarts once. `part` is
    # inherited metadata, so including it here would let a recovered row that
    # guessed a different part masquerade as a new section.
    seen = {(e.block, e.section_no) for e in entries}
    annexure_start = min(
        (e.start_page for e in entries if e.block == "annexure"), default=None
    )

    for n in toc_pages:
        # Later TOC pages are the annexure block; use the page the row was found
        # on, not the row's own page number, which may be missing.
        for rec in recover_text_rows(doc.pages[n - 1].text):
            ref_page = rec.page or _toc_page_hint(entries, n, toc_pages)
            block: Block = (
                "annexure"
                if annexure_start is not None and ref_page >= annexure_start
                else "body"
            )
            if (block, rec.section_no) in seen:
                continue
            # Inherit the part from the nearest preceding section in the same block.
            prior = [
                e for e in entries if e.block == block and e.section_no < rec.section_no
            ]
            part = max(prior, key=lambda e: e.section_no).part if prior else None
            entry = SectionIndexEntry(
                block=block,
                part=part,
                section_no=rec.section_no,
                title=rec.title,
                start_page=rec.page or ref_page,
            )
            seen.add((block, rec.section_no))
            entries.append(entry)
            gaps.append(
                CoverageGap(
                    page=n,
                    reason="table_parse_failed",
                    detail=(
                        f"TOC row {rec.section_no} ({block}) recovered from text; "
                        + ("page inferred — absent from text layer"
                           if not rec.page else "table detector dropped the row")
                    ),
                )
            )

    entries.sort(key=lambda e: (e.block != "body", e.start_page, e.section_no))

    if not entries:
        gaps.append(
            CoverageGap(
                page=toc_pages[0],
                reason="table_parse_failed",
                detail=f"TOC pages {toc_pages} yielded no parseable rows",
            )
        )
    return entries, gaps


def summarise(entries: list[SectionIndexEntry]) -> dict:
    """Small helper used by the eval harness and the CLI report."""
    by_block: dict[Block, int] = {}
    parts: list[str] = []
    for e in entries:
        by_block[e.block] = by_block.get(e.block, 0) + 1
        if e.part and e.part not in parts:
            parts.append(e.part)
    keys = {e.key for e in entries}
    return {
        "entries": len(entries),
        "unique_keys": len(keys),
        "by_block": by_block,
        "parts": parts,
        "distinct_section_numbers": len({e.section_no for e in entries}),
    }
