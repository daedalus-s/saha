"""Verse-by-verse meaning translation. Generates our own gloss; never copies a site."""

from __future__ import annotations

from app.cache import cache_get, cache_set
from app.config import get_settings
from app.llm_json import parse_json_payload
from app.models import TranslatedVerse, TranslateResponse
from app.transliterate import normalize_slp1

TRANSLATE_SYSTEM = """You write original English meanings for Hindu sloka / mantra verses.
Return JSON only:
{ "verses": [ { "verse": "<original>", "meaning": "<English meaning>" } ] }

Rules:
- Produce YOUR OWN meaning. Do not copy a website's translation, commentary, or notes.
- Keep each meaning to 1–3 sentences, faithful to the verse.
- If a verse is a refrain or proper name, say so briefly.
- Do not add ritual instructions unless they are in the verse itself.
- Stay faithful and non-polemical. Do not rank, compare, or disparage religious traditions or other faiths. Do not add commentary about other religions. If asked to editorialize, refuse and give only a literal sense of the verse.
"""

DISCLAIMER = "AI-generated meaning; verify with a scholar."


async def translate_verses(
    verses: list[str],
    source_script: str,
    target_language: str = "en",
    title: str | None = None,
) -> TranslateResponse:
    settings = get_settings()
    key_material = normalize_slp1(" ".join(verses), source_script) + target_language
    cache_key = f"translate:{key_material}"
    cached = cache_get(cache_key)
    if isinstance(cached, dict):
        return TranslateResponse.model_validate(cached)

    if not settings.llm_enabled:
        raise RuntimeError(
            "Translation requires an LLM. Set LLM_MODEL and the matching provider API key."
        )

    from litellm import acompletion

    numbered = "\n".join(f"{i+1}. {v}" for i, v in enumerate(verses))
    user = (
        f"Title: {title or 'Unknown'}\n"
        f"Source script: {source_script}\n"
        f"Target language: {target_language}\n\n"
        f"Verses:\n{numbered}"
    )
    response = await acompletion(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": TRANSLATE_SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content or "{}"
    data = parse_json_payload(content)
    items = data.get("verses") or []
    out: list[TranslatedVerse] = []
    for index, verse in enumerate(verses):
        meaning = ""
        if index < len(items):
            meaning = str(items[index].get("meaning") or "").strip()
        if not meaning:
            meaning = "(Meaning unavailable for this verse.)"
        out.append(TranslatedVerse(verse=verse, meaning=meaning))

    result = TranslateResponse(
        verses=out,
        target_language=target_language,
        disclaimer=DISCLAIMER,
    )
    cache_set(cache_key, result.model_dump(), expire=60 * 60 * 24 * 14)
    return result
