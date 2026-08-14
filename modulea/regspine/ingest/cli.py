"""`make ingest` — run the deterministic pipeline over the corpus.

Also writes the eval fixtures (BuildSpec §9). The fixtures are derived from SEBI's
own TOC, Annexure A and Appendix, so they are ground truth rather than a snapshot
of what the parser happened to produce — with one deliberate exception noted in
``write_fixtures``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from regspine.ingest.dom import ingest

CORPUS_DIR = Path("data/corpus")
FIXTURES = Path("eval/fixtures")

# Stable slugs so fixtures are reviewable in a diff.
KNOWN = {
    "1716371484396.pdf": "stock_brokers_2024_05_22",
    "1723438086672.pdf": "stock_brokers_2024_08_09",
    "1750158789381.pdf": "stock_brokers_2025_06_17",
    "1784029390357.pdf": "merchant_bankers",
}


def slug_for(path: Path) -> str:
    return KNOWN.get(path.name, path.stem)


def write_fixtures(dom, slug: str) -> None:
    """Persist the three ground-truth blocks.

    toc_truth is the section index: SEBI's own contents page, which the
    segmentation gate scores against. annexureA_truth and appendix_truth are the
    change list and consolidated-circular list. Absent blocks are written as an
    explicit empty file rather than skipped, so "no Annexure A" is recorded as a
    fact about the document instead of looking like a missing fixture.
    """
    for name, payload in (
        ("toc_truth", [e.model_dump(mode="json") for e in dom.section_index]),
        ("annexureA_truth", [e.model_dump(mode="json") for e in dom.annexure_a]),
        ("appendix_truth", [e.model_dump(mode="json") for e in dom.appendix]),
    ):
        out = FIXTURES / name / f"{slug}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def report(dom, slug: str) -> None:
    c = dom.coverage
    print(f"\n{slug}")
    print(f"  {dom.circular_no}  {dom.circular_date}  ({dom.intermediary})")
    print(f"  pages {c.pages_parsed}/{c.total_pages}   dom_hash {dom.dom_hash[:16]}")
    print(
        f"  sections {c.sections_found}/{c.sections_expected}"
        f"  (recall {c.section_recall:.1%})   clauses {len(dom.clauses)}"
    )
    print(f"  annexure A {len(dom.annexure_a):>3} entries   appendix {len(dom.appendix):>3} entries")
    if c.gaps:
        print(f"  coverage gaps ({len(c.gaps)}):")
        for g in c.gaps[:6]:
            print(f"    p{g.page:<4} {g.reason:<20} {g.detail[:74]}")
        if len(c.gaps) > 6:
            print(f"    … {len(c.gaps) - 6} more")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ingest SEBI master circulars.")
    ap.add_argument("pdfs", nargs="*", help="PDF paths (default: the whole corpus)")
    ap.add_argument("--fixtures", action="store_true", help="write eval fixtures")
    args = ap.parse_args(argv)

    paths = [Path(p) for p in args.pdfs] or sorted(CORPUS_DIR.glob("*.pdf"))
    if not paths:
        print(f"No PDFs found in {CORPUS_DIR}/ — see modulea/README.md.", file=sys.stderr)
        return 1

    failures = 0
    for path in paths:
        slug = slug_for(path)
        try:
            dom = ingest(str(path))
        except Exception as exc:  # a document that cannot be parsed is a result too
            print(f"\n{slug}\n  FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
            failures += 1
            continue
        report(dom, slug)
        if args.fixtures:
            write_fixtures(dom, slug)
            print("  fixtures written")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
