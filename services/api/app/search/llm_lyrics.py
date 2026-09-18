"""Ask an LLM (Gemini via LiteLLM) for sloka lyrics in a chosen script."""

from __future__ import annotations

import re

from app.cache import cache_get, cache_set
from app.config import Settings, get_settings
from app.extract.dedupe import version_fingerprint
from app.extract.llm_extract import dominant_script_for_verses
from app.llm_json import parse_json_payload
from app.models import SCRIPT_LABELS, SUPPORTED_SCRIPTS, SlokaVersion

LYRICS_SYSTEM = """You recall traditional Hindu sloka, mantra, chalisa, or stotra lyrics.
Return JSON only:
{"found": true, "title": "name of the work", "script": "devanagari", "verses": ["verse 1", "verse 2"]}
If you do not know the work, return {"found": false, "title": "", "script": "latin", "verses": []}.
Write the lyrics in the requested script. One array entry per verse, couplet, or numbered line.
Do not add translation, commentary, ritual instructions, or comparison of religions.
Do not invent a different composition. If unsure of a line, omit it rather than guessing wildly.
"""

_SLUG = re.compile(r"[^a-z0-9]+")


def _language_label(script: str) -> str:
    return SCRIPT_LABELS.get(script, script)


def _source_url(name: str, script: str) -> str:
    slug = _SLUG.sub("-", name.strip().lower()).strip("-") or "sloka"
    return f"saha://ai/gemini/{script}/{slug}"


def verses_from_freeform(raw: str) -> list[str]:
    lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip().strip("`")
        if not stripped or stripped.startswith("```"):
            continue
        if stripped.lower() in {"json", "{", "}"}:
            continue
        lines.append(stripped)
    return lines[:120]


async def _complete(model: str, messages: list[dict[str, str]], temperature: float):
    from litellm import acompletion

    return await acompletion(model=model, messages=messages, temperature=temperature)


async def generate_lyrics(
    name: str,
    script: str,
    settings: Settings | None = None,
) -> SlokaVersion | None:
    settings = settings or get_settings()
    script_key = script.strip().lower()
    if script_key not in SUPPORTED_SCRIPTS:
        raise ValueError(f"Unsupported script: {script}")
    if not settings.llm_enabled:
        raise RuntimeError(
            "Lyrics search requires an LLM. Set LLM_MODEL (for example gemini/gemini-2.0-flash) "
            "and GEMINI_API_KEY."
        )

    query = name.strip()
    cache_key = f"lyrics:{script_key}:{query.casefold()}"
    cached = cache_get(cache_key)
    if isinstance(cached, dict):
        return SlokaVersion.model_validate(cached)

    language = _language_label(script_key)
    user = f"Gemini, please give me the lyrics of {query} in {language}."
    response = await _complete(
        settings.llm_model,
        [
            {"role": "system", "content": LYRICS_SYSTEM},
            {"role": "user", "content": user},
        ],
        0.2,
    )
    content = response.choices[0].message.content or ""
    verses: list[str] = []
    title = query
    found = False
    reported_script = script_key
    try:
        data = parse_json_payload(content)
        verses = [str(v).strip() for v in data.get("verses") or [] if str(v).strip()]
        found = bool(data.get("found", bool(verses))) and bool(verses)
        title = (data.get("title") or query).strip() or query
        reported_script = str(data.get("script") or script_key).strip().lower()
    except (ValueError, TypeError):
        verses = verses_from_freeform(content)
        found = bool(verses)

    if not found or not verses:
        return None

    if reported_script not in SUPPORTED_SCRIPTS:
        reported_script = dominant_script_for_verses(verses)
    digest, normalized = version_fingerprint(verses, reported_script)
    version = SlokaVersion(
        title=title,
        script=reported_script,
        verses=verses,
        source_url=_source_url(query, script_key),
        source_domain="AI-generated",
        fingerprint=digest,
        normalized=normalized,
        ai_generated=True,
    )
    cache_set(cache_key, version.model_dump(), expire=60 * 60 * 24 * 7)
    return version
