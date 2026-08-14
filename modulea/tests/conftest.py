"""Shared corpus parsing.

Parsing a 400-page circular takes ~40s, and four test modules all need the same
documents. Without a shared cache the suite re-parsed the corpus once per module
and took 13 minutes, which is too slow to be a useful CI gate.

The cached objects are treated as read-only by every test.
"""

from __future__ import annotations

import pytest

from regspine.ingest.dom import ingest, load_document

CORPUS = {
    "may2024": "data/corpus/1716371484396.pdf",
    "aug2024": "data/corpus/1723438086672.pdf",
    "jun2025": "data/corpus/1750158789381.pdf",
    "merchant_bankers": "data/corpus/1784029390357.pdf",
}
STOCK_BROKER_VERSIONS = ["may2024", "aug2024", "jun2025"]


@pytest.fixture(scope="session")
def load_cached():
    """Parse a PDF at most once per test session."""
    cache: dict[str, object] = {}

    def _load(path: str):
        if path not in cache:
            cache[path] = load_document(path)
        return cache[path]

    return _load


@pytest.fixture(scope="session")
def ingest_cached():
    """Run the full ingest at most once per PDF per session."""
    cache: dict[str, object] = {}

    def _ingest(path: str):
        if path not in cache:
            cache[path] = ingest(path)
        return cache[path]

    return _ingest
