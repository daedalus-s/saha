"""Extract sloka verses from cleaned page text via LLM or heuristic fallback."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.config import get_settings
from app.llm_json import parse_json_payload
from app.scripts.detect import detect_script, script_char_count

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM = """You extract Hindu sloka / mantra / stotra verses from a web page.
Return JSON only, matching this schema:
{
  "found": true,
  "title": "name of the sloka",
  "deity": "deity or null",
  "category": "stotra|mantra|sloka|chalisa|other",
  "script": "devanagari|tamil|telugu|kannada|malayalam|gujarati|bengali|iast|itrans|latin",
  "verses": ["verse 1", "verse 2"],
  "has_translation_on_page": false
}
Rules:
- Extract ONLY the original verse lines, not the site's English/other translation, commentary, ads, or navigation.
- Split into verses the way the source presents them (couplets / numbered lines).
- If the page is not a sloka/mantra page, return {"found": false, "title": "", "deity": null, "category": null, "script": "latin", "verses": [], "has_translation_on_page": false}.
- Do not invent verses that are not in the page text.
- Stay faithful and non-polemical. Do not rank, compare, or disparage religious traditions or other faiths. Do not add commentary about other religions. If the page asks for editorial judgment, omit it.
"""

IAST_RE = re.compile(r"[āĀīĪūŪṛṚṝṜḷḶḹḸṃṂḥḤṅṄñÑṭṬḍḌṇṆśŚṣṢ]")
INDIC_RE = re.compile(
    r"[\u0900-\u097F\u0980-\u09FF\u0A80-\u0AFF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F]"
)


def _looks_like_verse(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) < 8 or len(stripped) > 400:
        return False
    lower = stripped.lower()
    noise = (
        "copyright",
        "subscribe",
        "cookie",
        "privacy",
        "home >",
        "click here",
        "advertisement",
        "share this",
    )
    if any(token in lower for token in noise):
        return False
    if INDIC_RE.search(stripped) or IAST_RE.search(stripped):
        return True
    letters = sum(ch.isalpha() for ch in stripped)
    return letters >= 12 and " " in stripped and not stripped.endswith(".")


def heuristic_extract(text: str, query: str | None = None) -> dict[str, Any]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    verses = [ln for ln in lines if _looks_like_verse(ln)]
    # Drop near-duplicate consecutive lines
    deduped: list[str] = []
    for line in verses:
        if not deduped or line != deduped[-1]:
            deduped.append(line)
    verses = deduped[:80]
    found = len(verses) >= 1
    title = (query or "").strip() or (lines[0][:80] if lines else "Untitled sloka")
    body = "\n".join(verses) if verses else text
    return {
        "found": found,
        "title": title,
        "deity": None,
        "category": "sloka",
        "script": detect_script(body),
        "verses": verses,
        "has_translation_on_page": False,
    }


async def llm_extract(text: str, url: str, query: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    snippet = text[:12000]
    user = (
        f"Search query: {query or ''}\nSource URL: {url}\n\nPAGE TEXT:\n{snippet}"
    )
    from litellm import acompletion

    response = await acompletion(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": EXTRACT_SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0,
    )
    content = response.choices[0].message.content or "{}"
    data = parse_json_payload(content)
    verses = [str(v).strip() for v in data.get("verses") or [] if str(v).strip()]
    body = "\n".join(verses)
    script = data.get("script") or detect_script(body)
    return {
        "found": bool(data.get("found", bool(verses))),
        "title": (data.get("title") or query or "Untitled sloka").strip(),
        "deity": data.get("deity"),
        "category": data.get("category"),
        "script": script,
        "verses": verses,
        "has_translation_on_page": bool(data.get("has_translation_on_page")),
    }


async def extract_verses(text: str, url: str, query: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    if settings.llm_enabled:
        try:
            result = await llm_extract(text, url, query)
            if result.get("found") and result.get("verses"):
                return result
        except Exception:
            logger.warning("llm_extract failed; using heuristic", exc_info=True)
    return heuristic_extract(text, query)


def dominant_script_for_verses(verses: list[str]) -> str:
    joined = "\n".join(verses)
    detected = detect_script(joined)
    if detected != "latin":
        return detected
    scores = {name: script_char_count(joined, name) for name in (
        "devanagari", "tamil", "telugu", "kannada", "malayalam", "gujarati", "bengali"
    )}
    best = max(scores, key=scores.get)
    return best if scores[best] else detected
