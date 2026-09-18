"""Deterministic Indic transliteration via sanscript. No LLM."""

from __future__ import annotations

import hashlib
import re

from indic_transliteration import sanscript

from app.scripts.detect import detect_script

SCHEME_BY_SCRIPT: dict[str, str] = {
    "devanagari": sanscript.DEVANAGARI,
    "tamil": sanscript.TAMIL,
    "telugu": sanscript.TELUGU,
    "kannada": sanscript.KANNADA,
    "malayalam": sanscript.MALAYALAM,
    "gujarati": sanscript.GUJARATI,
    "bengali": sanscript.BENGALI,
    "iast": sanscript.IAST,
    "itrans": sanscript.ITRANS,
    "latin": sanscript.IAST,
    "slp1": sanscript.SLP1,
}

# Tamil cannot represent every Sanskrit consonant; superscript numerals
# keep those distinctions (k¹, g², …) instead of collapsing them.
_TAMIL_SUPERSCRIPT_ALIASES = ("tamil_superscripted", "TAMIL_SUPERSCRIPTED")


def resolve_scheme(script: str) -> str:
    key = script.lower().strip()
    if key not in SCHEME_BY_SCRIPT:
        raise ValueError(f"Unsupported script: {script}")
    return SCHEME_BY_SCRIPT[key]


def _tamil_target_scheme() -> str:
    schemes = getattr(sanscript, "SCHEMES", {})
    for alias in _TAMIL_SUPERSCRIPT_ALIASES:
        if alias in schemes:
            return alias
        if alias.lower() in schemes:
            return alias.lower()
    if hasattr(sanscript, "TAMIL_SUPERSCRIPTED"):
        return sanscript.TAMIL_SUPERSCRIPTED
    return sanscript.TAMIL


def transliterate_text(text: str, source_script: str, target_script: str) -> str:
    if not text.strip():
        return text
    src = resolve_scheme(source_script)
    tgt_key = target_script.lower().strip()
    if tgt_key == "tamil":
        tgt = _tamil_target_scheme()
    else:
        tgt = resolve_scheme(target_script)
    if src == tgt:
        return text
    return sanscript.transliterate(text, src, tgt)


def transliterate_verses(
    verses: list[str], source_script: str, target_script: str
) -> list[str]:
    from app.cache import cache_get, cache_set

    digest, _ = fingerprint(verses, source_script)
    cache_key = f"xlit:{digest}:{source_script}:{target_script}"
    cached = cache_get(cache_key)
    if isinstance(cached, list):
        return cached
    out = [transliterate_text(v, source_script, target_script) for v in verses]
    cache_set(cache_key, out, expire=60 * 60 * 24 * 30)
    return out


_NON_SLP1 = re.compile(r"[^A-Za-z0-9]+")


def to_slp1(text: str, source_script: str | None = None) -> str:
    script = source_script or detect_script(text)
    if script == "latin":
        script = "iast"
    try:
        return transliterate_text(text, script, "slp1")
    except Exception:
        return text


def normalize_slp1(text: str, source_script: str | None = None) -> str:
    slp1 = to_slp1(text, source_script)
    return _NON_SLP1.sub("", slp1).lower()


def fingerprint(verses: list[str], source_script: str | None = None) -> tuple[str, str]:
    joined = " ".join(verses)
    normalized = normalize_slp1(joined, source_script)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return digest, normalized
