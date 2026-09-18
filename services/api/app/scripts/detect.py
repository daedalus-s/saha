"""Unicode-block script detection for Indic sloka text."""

from __future__ import annotations

import re
from collections import Counter

SCRIPT_RANGES: dict[str, tuple[int, int]] = {
    "devanagari": (0x0900, 0x097F),
    "bengali": (0x0980, 0x09FF),
    "gujarati": (0x0A80, 0x0AFF),
    "tamil": (0x0B80, 0x0BFF),
    "telugu": (0x0C00, 0x0C7F),
    "kannada": (0x0C80, 0x0CFF),
    "malayalam": (0x0D00, 0x0D7F),
}

IAST_RE = re.compile(
    r"[āĀīĪūŪṛṚṝṜḷḶḹḸṃṂḥḤṅṄñÑṭṬḍḌṇṆśŚṣṢēōṁ]",
)
ITRANS_HINT_RE = re.compile(r"\b(aa|ii|uu|RRi|chh|shh|~N|~n)\b")


def _script_for_char(ch: str) -> str | None:
    code = ord(ch)
    for name, (start, end) in SCRIPT_RANGES.items():
        if start <= code <= end:
            return name
    return None


def detect_script(text: str) -> str:
    """Return the dominant script key for `text`."""
    counts: Counter[str] = Counter()
    for ch in text:
        name = _script_for_char(ch)
        if name:
            counts[name] += 1
    if counts:
        return counts.most_common(1)[0][0]

    if IAST_RE.search(text):
        return "iast"
    if ITRANS_HINT_RE.search(text):
        return "itrans"
    return "latin"


def script_char_count(text: str, script: str) -> int:
    if script not in SCRIPT_RANGES:
        return 0
    start, end = SCRIPT_RANGES[script]
    return sum(1 for ch in text if start <= ord(ch) <= end)
