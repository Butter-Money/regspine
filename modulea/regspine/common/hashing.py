"""Stable identity + normalisation (BuildSpec §5 identity, non-negotiable #2).

Everything here must be deterministic across runs and machines: the idempotency
gate compares ``dom_hash`` between two ingests of the same file, and change
detection relies on ``obligation_id`` being stable when a clause is *renumbered*
but not reworded — which the corpus actually does (TOC item 47 in the May-2024
and Aug-2024 Stock-Broker circulars becomes item 48 in Jun-2025).

That is why neither identity function takes a page or a section number.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

# Curly quotes, en/em dashes and non-breaking spaces all appear in the corpus and
# are not stable across pdfplumber versions or between the same text quoted in an
# annexure vs the body. Fold them before hashing.
_PUNCT_FOLD = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "−": "-",
    " ": " ", " ": " ", "​": "",
}

_WS = re.compile(r"\s+")
_SOFT_HYPHEN = re.compile(r"(\w)-\s*\n\s*(\w)")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x1f")  # unit separator, so ("a","bc") != ("ab","c")
    return h.hexdigest()


def dehyphenate(text: str) -> str:
    """Join words broken across a line by a hyphen — a pdfplumber artifact, not
    content. Applied before normalisation so hashes ignore line wrapping."""
    return _SOFT_HYPHEN.sub(r"\1\2", text)


def normalise_text(text: str) -> str:
    """Canonical form for hashing and fuzzy comparison. Case-folded, punctuation
    unified, whitespace collapsed. Never store this — it is for identity only."""
    text = unicodedata.normalize("NFKC", dehyphenate(text))
    for src, dst in _PUNCT_FOLD.items():
        text = text.replace(src, dst)
    return _WS.sub(" ", text).strip().casefold()


def clause_id(intermediary: str, section_no: int | None, clause_path: str | None, text: str) -> str:
    """§5: sha256(intermediary|section_no|clause_path|normalised_text).

    Includes section_no because a clause *is* positioned within a version; the
    cross-version join is done by obligation_id, not clause_id.
    """
    return sha256_text(
        intermediary,
        "" if section_no is None else str(section_no),
        clause_path or "",
        normalise_text(text),
    )


def action_signature(action_required: str) -> str:
    """A reworded-but-equivalent action should hash the same; a materially changed
    one should not. Strip the parts SEBI routinely rewords without changing the
    duty — deadlines and amounts move, the verb+object usually doesn't."""
    s = normalise_text(action_required)
    s = re.sub(r"\b(?:within|not later than|on or before)\b.*?(?=[,.;]|$)", "", s)
    s = re.sub(r"\b\d+(?:\.\d+)?\b", "#", s)  # digits -> placeholder
    s = re.sub(r"\b(?:rs\.?|inr|crore|lakh)\b", "", s)
    return _WS.sub(" ", s).strip()


def obligation_id(
    intermediary: str, obligation_type: str, action: str, applies_to: list[str]
) -> str:
    """§5: sha256(intermediary|obligation_type|action_signature|applies_to).

    Deliberately free of section_no, page and circular_no so the same duty keeps
    one identity across versions and the change ledger can align on it.
    """
    return sha256_text(
        intermediary,
        obligation_type,
        action_signature(action),
        "|".join(sorted(applies_to)),
    )


def dom_hash(payload: str) -> str:
    """Hash of the DOM's canonical JSON. Idempotency gate: re-ingesting the same
    PDF must reproduce this exactly."""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
