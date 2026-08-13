# RegSpine Module A — Obligation Engine

Turns a SEBI master circular (PDF) into a **versioned, citation-anchored graph of
machine-actionable obligations**, and detects what changed between versions.

Module B (the interface auditor) lives at the repo root and ships as a static site.
Module A is this Python service. Built to `RegSpine_ModuleA_BuildSpec.md`.

**Status: M1 in progress.** The deterministic ingestor parses the SEBI skeleton and
the section index; segmentation to clauses, the interpreter, storage and
change-detection are not built yet.

## Run

```bash
cd modulea
/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest tests/ -q          # ~4 min: parses three 400-page PDFs
```

The four SEBI PDFs are **not committed** (17 MB of public documents). Put them in
`data/corpus/`; the tests name the exact files.

## Non-negotiables (spec §0) and where they live

| # | Rule | Enforced by |
|---|---|---|
| 1 | Provenance-first | `Anchor` is required on every `Clause`/`Obligation` |
| 2 | Deterministic ingestion, idempotent | `ingest/` is code-only; `test_section_index_is_idempotent` |
| 3 | Groundedness gate | `interpret/gate.py` *(not built)* |
| 4 | Bitemporal, versioned | `store/` *(not built)* |
| 5 | Every stage scoreable | `tests/test_ingest_toc.py`, `eval/` |
| 6 | LLM as a scalpel | only pages in the coverage manifest are LLM-eligible |

## What the corpus actually does

Written after parsing all four PDFs, because each of these broke a first attempt:

- **Section numbers are not unique.** Body sections run 1..92/94/98 continuously
  across Parts I–X, then an `Annexures` block **restarts at 1**. A flat
  `{section_no: ...}` index loses 42 of 133 rows in May-2024. Identity is
  `(block, section_no)`.
- **`extract_tables()` silently drops TOC rows.** Three shapes, all real: title
  wrapped around the number (May-2024 body 26, 52), a complete row the detector
  just misses (Aug-2024 body 24, 51, 74), and a row with no page number at all
  (annexure 30). Left unrepaired, recall caps at ~97.8%. `ingest/toc_repair.py`
  recovers all three from the text layer — deterministically, spending no tokens,
  because these are structural layout properties rather than anomalies.
- **Roman part numerals have holes.** May-2024 runs I–VII then IX, X. Part VIII
  (Default Related Provisions) appears only from Aug-2024.
- **The MVP slice renumbers.** "Settlement of Running Account of Client's Funds" is
  item **47** in May and Aug 2024 and item **48** in Jun 2025. Change-detection must
  never align on `section_no`; `obligation_id` is content-derived for this reason.
- **The version chain is derivable.** Each circular's preamble names the one it
  supersedes, so May→Aug→Jun-2025 is parsed, not configured.
- **Merchant Bankers is genuinely different.** Its TOC page yields *zero* tables,
  its preamble is arabic not roman, and it carries two dates (`Issued on` /
  `Last updated on`). It is the M6 generality test and is currently recorded as a
  coverage gap rather than silently passing.

## Gates met so far

| Gate | Target | Status |
|---|---|---|
| Section recall vs TOC | 100% | ✅ body + annexure contiguous on all 3 SB versions |
| Index key uniqueness | no collisions | ✅ |
| Idempotency | stable re-parse | ✅ |
| Header grammar, both circular families | parses | ✅ 4/4 documents |
| Groundedness | ≥ 99% | not built (M2) |
| Change-recall vs Annexure A | ≥ target | not built (M4) |

## Layout

```
config/     models.yaml · taxonomy.yaml · thresholds.yaml     (routing, vocab, thresholds)
prompts/    versioned Jinja templates, one per LLM job
regspine/
  common/     schemas.py (§2 contracts) · hashing.py (identity)
  ingest/     skeleton.py (SEBI grammar) · toc_repair.py · dom.py
  categorise/ interpret/ store/ changedet/ api/                (scaffolded)
eval/       fixtures + harness
tests/
```
