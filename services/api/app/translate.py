"""Verse-by-verse meaning translation. Generates our own gloss; never copies a site."""

from __future__ import annotations

from app.cache import cache_get, cache_set
from app.config import Settings, get_settings
from app.llm import completion_kwargs
from app.llm_json import parse_json_payload
from app.models import MEANING_LANGUAGES, SCRIPT_LABELS, TranslatedVerse, TranslateResponse
from app.transliterate import normalize_slp1

DISCLAIMER = "AI-generated meaning; verify with a scholar."

_UNAVAILABLE = {
    "en": "(Meaning unavailable for this verse.)",
    "hi": "(इस पंक्ति का अर्थ उपलब्ध नहीं है।)",
    "ta": "(இந்த வரிக்குப் பொருள் கிடைக்கவில்லை.)",
    "te": "(ఈ పాదానికి అర్థం అందుబాటులో లేదు.)",
    "kn": "(ಈ ಸಾಲಿನ ಅರ್ಥ ಲಭ್ಯವಿಲ್ಲ.)",
    "ml": "(ഈ വരിയുടെ അർത്ഥം ലഭ്യമല്ല.)",
    "gu": "(આ પંક્તિનો અર્થ ઉપલબ્ધ નથી.)",
    "bn": "(এই পঙক্তির অর্থ পাওয়া যায়নি।)",
}


def resolve_meaning_language(code: str) -> tuple[str, str, str]:
    key = code.strip().lower()
    for item in MEANING_LANGUAGES:
        if item[0] == key:
            return item
    supported = ", ".join(item[0] for item in MEANING_LANGUAGES)
    raise ValueError(f"Unsupported meaning language: {code}. Supported: {supported}")


def translate_system(language_name: str, script_label: str) -> str:
    return f"""You write original meanings for Hindu sloka / mantra verses.
Return JSON only:
{{ "verses": [ {{ "verse": "<original verse, unchanged>", "meaning": "<meaning in {language_name}>" }} ] }}

Rules:
- Write every meaning in {language_name}, using the {script_label} script. Do not mix in another language.
- Produce YOUR OWN meaning. Do not copy a website's translation, commentary, or notes.
- Keep each meaning to 1–3 sentences, faithful to the verse.
- If a verse is a refrain or proper name, say so briefly in {language_name}.
- Do not add ritual instructions unless they are in the verse itself.
- Stay faithful and non-polemical. Do not rank, compare, or disparage religious traditions or other faiths. Do not add commentary about other religions. If asked to editorialize, refuse and give only a literal sense of the verse.
"""


async def translate_verses(
    verses: list[str],
    source_script: str,
    target_language: str = "en",
    title: str | None = None,
    settings: Settings | None = None,
) -> TranslateResponse:
    code, language_name, script_key = resolve_meaning_language(target_language)
    settings = settings or get_settings()
    key_material = normalize_slp1(" ".join(verses), source_script) + code
    cache_key = f"translate:{key_material}"
    cached = cache_get(cache_key)
    if isinstance(cached, dict):
        return TranslateResponse.model_validate(cached)

    if not settings.llm_enabled:
        raise RuntimeError(
            "Translation requires an LLM. Set LLM_MODEL and the matching provider API key."
        )

    from litellm import acompletion

    script_label = SCRIPT_LABELS.get(script_key, script_key)
    numbered = "\n".join(f"{i+1}. {v}" for i, v in enumerate(verses))
    user = (
        f"Title: {title or 'Unknown'}\n"
        f"Source script: {source_script}\n"
        f"Target language: {language_name} ({code})\n"
        f"Write the meaning in the {script_label} script.\n\n"
        f"Verses:\n{numbered}"
    )
    response = await acompletion(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": translate_system(language_name, script_label)},
            {"role": "user", "content": user},
        ],
        **completion_kwargs(settings.llm_model, temperature=0.2),
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
            meaning = _UNAVAILABLE[code]
        out.append(TranslatedVerse(verse=verse, meaning=meaning))

    result = TranslateResponse(
        verses=out,
        target_language=code,
        disclaimer=DISCLAIMER,
    )
    cache_set(cache_key, result.model_dump(), expire=60 * 60 * 24 * 14)
    return result
