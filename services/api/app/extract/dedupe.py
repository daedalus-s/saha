"""Near-duplicate checks of sloka versions via SLP1 + rapidfuzz.

Production grouping of extract hits is done on the client
(`apps/mobile/src/utils/groupVersions.ts`) because search is two-phase.
"""

from __future__ import annotations

from rapidfuzz import fuzz

from app.transliterate import fingerprint, normalize_slp1

DEFAULT_THRESHOLD = 85


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return float(fuzz.ratio(a, b))


def are_duplicates(
    verses_a: list[str],
    verses_b: list[str],
    script_a: str | None = None,
    script_b: str | None = None,
    threshold: int = DEFAULT_THRESHOLD,
) -> bool:
    norm_a = normalize_slp1(" ".join(verses_a), script_a)
    norm_b = normalize_slp1(" ".join(verses_b), script_b)
    return similarity(norm_a, norm_b) >= threshold


def version_fingerprint(verses: list[str], script: str) -> tuple[str, str]:
    return fingerprint(verses, script)
