"""Deadline normalisation (BuildSpec §4.3 step 3) — pure code, no tokens.

"within 3 working days of quarter-end" -> Deadline(offset=3, unit=working_day,
relative_to=quarter_end).

Deliberately deterministic. A deadline is the field most likely to be quietly
wrong in a model's output and the one most consequential when it is, so the model
is asked for the *phrase* and the structure is derived here, where it can be
tested exhaustively.
"""

from __future__ import annotations

import re
from datetime import datetime

from regspine.common.schemas import Deadline

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "fifteen": 15, "thirty": 30,
}

# "within 3 working days", "not later than fifteen days", "within T+1 day"
RE_OFFSET = re.compile(
    r"\b(?:within|not\s+later\s+than|no\s+later\s+than|latest\s+by|upto|up\s+to)\s+"
    r"(?P<num>\d+|" + "|".join(_NUMBER_WORDS) + r")\s*"
    r"(?P<unit>working\s+days?|business\s+days?|calendar\s+days?|days?|weeks?|months?|quarters?)",
    re.I,
)
RE_T_PLUS = re.compile(r"\bT\s*\+\s*(?P<num>\d+)\s*(?P<unit>working\s+day|day)?s?\b", re.I)
RE_FIXED_DATE = re.compile(
    r"\b(?:on\s+or\s+before|by)\s+([A-Z][a-z]+\s+\d{1,2},\s*\d{4})\b"
)

# What the offset is measured from.
_RELATIVE_TO = [
    (re.compile(r"\bquarter[\s\-]?end|end\s+of\s+(?:the\s+)?quarter\b", re.I), "quarter_end"),
    (re.compile(r"\bmonth[\s\-]?end|end\s+of\s+(?:the\s+)?month\b", re.I), "month_end"),
    (re.compile(r"\bfinancial\s+year|end\s+of\s+(?:the\s+)?year\b", re.I), "financial_year_end"),
    (re.compile(r"\bend\s+of\s+(?:the\s+)?day|EOD\b", re.I), "end_of_day"),
    (re.compile(r"\bdate\s+of\s+receipt|on\s+receipt\b", re.I), "receipt"),
    (re.compile(r"\btrade\s+date|trading\s+day\b", re.I), "trade_date"),
]

# Bare periodicity, where the obligation recurs rather than having an offset.
_PERIODIC = [
    (re.compile(r"\bquarterly\b", re.I), "quarter"),
    (re.compile(r"\bmonthly\b", re.I), "month"),
    (re.compile(r"\bannual(?:ly)?\b|\byearly\b", re.I), "year"),
    (re.compile(r"\bdaily\b", re.I), "day"),
    (re.compile(r"\bweekly\b", re.I), "week"),
]

_UNIT_MAP = {
    "working day": "working_day", "working days": "working_day",
    "business day": "working_day", "business days": "working_day",
    "calendar day": "day", "calendar days": "day",
    "day": "day", "days": "day",
    "week": "day", "weeks": "day",  # normalised to days below
    "month": "month", "months": "month",
    "quarter": "quarter", "quarters": "quarter",
}


def _to_int(raw: str) -> int | None:
    raw = raw.strip().lower()
    if raw.isdigit():
        return int(raw)
    return _NUMBER_WORDS.get(raw)


def _relative_to(text: str) -> str | None:
    for pattern, label in _RELATIVE_TO:
        if pattern.search(text):
            return label
    return None


def normalise_deadline(text: str) -> Deadline | None:
    """Parse a deadline out of clause text. Returns None when there isn't one —
    which is the common case and must not be confused with 'no deadline found'
    meaning 'immediately'."""
    if not text:
        return None

    if (m := RE_FIXED_DATE.search(text)):
        try:
            return Deadline(
                fixed_date=datetime.strptime(m.group(1), "%B %d, %Y").date(),
                relative_to="fixed_date",
            )
        except ValueError:
            pass

    if (m := RE_OFFSET.search(text)):
        num = _to_int(m.group("num"))
        unit_raw = re.sub(r"\s+", " ", m.group("unit").strip().lower())
        unit = _UNIT_MAP.get(unit_raw)
        if num is not None and unit:
            if unit_raw.startswith("week"):
                num, unit = num * 7, "day"
            return Deadline(offset=num, unit=unit, relative_to=_relative_to(text))

    if (m := RE_T_PLUS.search(text)):
        num = _to_int(m.group("num"))
        if num is not None:
            unit = "working_day" if (m.group("unit") or "").lower().startswith("working") else "day"
            return Deadline(offset=num, unit=unit, relative_to="trade_date")

    for pattern, unit in _PERIODIC:
        if pattern.search(text):
            # Recurring with no explicit offset: the period is the deadline.
            return Deadline(offset=None, unit=unit, relative_to=_relative_to(text) or "period_end")

    return None
