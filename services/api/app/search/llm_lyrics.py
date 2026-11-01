"""Ask an LLM (Gemini via LiteLLM) for sloka lyrics in a chosen script."""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

from app.cache import cache_get, cache_set
from app.config import Settings, get_settings
from app.extract.dedupe import version_fingerprint
from app.extract.llm_extract import dominant_script_for_verses
from app.llm import LATEST_GEMINI_MODEL, completion_kwargs
from app.llm_json import parse_json_payload
from app.models import SCRIPT_LABELS, SUPPORTED_SCRIPTS, LyricsContinueResponse, SlokaVersion
from app.scripts.detect import detect_script
from app.transliterate import romanize_name

LYRICS_SYSTEM = """You recall traditional Hindu sloka, mantra, chalisa, or stotra lyrics.
Return JSON only:
{"found": true, "title": "name of the work", "script": "devanagari", "verses": ["verse 1", "verse 2"]}
If you do not know the work, return {"found": false, "ambiguous": false, "title": "", "script": "latin", "verses": [], "suggestions": ["closest well-known name"]}.
Include "suggestions": a list of up to 5 traditional work names, and "ambiguous": true or false.
If one work clearly matches, set "ambiguous": false and "suggestions": [].
If the name is misspelled or unknown, set "found": false, "ambiguous": false, and put likely corrections in "suggestions".
If the name is too broad or fits several different works, set "found": false, "ambiguous": true, "verses": [], and list those works in "suggestions".
Write each suggestion as a name a person would search for, in the same script as the query when you can. Do not repeat the query. Do not invent modern compositions.
The name may be typed in Latin or in an Indic script, including Tamil.
A Tamil (or other Indic) spelling of a Sanskrit name is often approximate. Identify the
traditional work from the name as entered and from the romanized hint when one is given.
Do not treat that spelling as a different composition.
Write the lyrics in the requested script. One array entry per verse, couplet, or numbered line.
Return at most 80 verses. If the work continues after this response, set "done": false.
If this response includes the final verse, set "done": true.
When told to start at a verse number, begin there and do not repeat earlier verses.
Do not add translation, commentary, ritual instructions, or comparison of religions.
Do not invent a different composition. If unsure of a line, omit it rather than guessing wildly.
"""

_SLUG = re.compile(r"[^a-z0-9]+")
_SUGGESTION_LIMIT = 5
LYRICS_PAGE_SIZE = 80
MAX_LYRICS_VERSES = 4000

SUGGEST_SYSTEM = """You suggest traditional Hindu sloka, mantra, chalisa, or stotra names for a search that did not match.
Return JSON only: {"ambiguous": false, "suggestions": ["Name 1", "Name 2"]}
If the query is a misspelling or an unknown name, set "ambiguous" to false and suggest the closest well-known names.
If the query is too broad or matches several different works, set "ambiguous" to true and list those works.
Use the same script as the query when you can. Do not repeat the query. At most 5 names.
Do not invent modern compositions.
"""


class LyricsLookup:
    def __init__(
        self,
        version: SlokaVersion | None,
        suggestions: list[str],
        ambiguous: bool,
    ) -> None:
        self.version = version
        self.suggestions = suggestions
        self.ambiguous = ambiguous


def clean_suggestions(raw: object, query: str) -> list[str]:
    if not isinstance(raw, list):
        return []
    folded_query = query.casefold().strip()
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        text = " ".join(str(item).split())
        if not text or len(text) > 80:
            continue
        key = text.casefold()
        if key == folded_query or key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= _SUGGESTION_LIMIT:
            break
    return out


def _language_label(script: str) -> str:
    return SCRIPT_LABELS.get(script, script)


def lyrics_user_message(query: str, script_key: str) -> str:
    """Prompt that keeps a Tamil-script name, plus an IAST hint when it is reliable."""
    language = _language_label(script_key)
    entered = detect_script(query)
    entered_label = SCRIPT_LABELS.get(entered, entered)
    lines = [
        f"Give the lyrics of this traditional work in {language}.",
        f"Name as entered ({entered_label} script): {query}",
    ]
    roman = romanize_name(query, entered)
    if roman:
        lines.append(
            "Romanized hint (approximate; Tamil and some other scripts "
            f"do not distinguish every Sanskrit consonant): {roman}"
        )
    lines.append(
        f"Return at most {LYRICS_PAGE_SIZE} verses in {language}. "
        'If the work has more verses after these, set "done" to false.'
    )
    return "\n".join(lines)


def drop_verse_overlap(previous: list[str], incoming: list[str]) -> list[str]:
    """Drop a leading run of verses that repeats the previous page's ending."""
    if not previous or not incoming:
        return incoming
    limit = min(len(previous), len(incoming), 8)
    for size in range(limit, 0, -1):
        if previous[-size:] == incoming[:size]:
            return incoming[size:]
    return incoming


def clip_verse_page(
    verses: list[str],
    done: bool | None,
    offset: int,
) -> tuple[list[str], bool, int]:
    """Keep one page of verses and report whether another page should be requested."""
    start = max(0, offset)
    room = MAX_LYRICS_VERSES - start
    if room <= 0:
        return [], False, start
    if done is True:
        kept = verses[:room]
        return kept, False, start + len(kept)
    page = min(LYRICS_PAGE_SIZE, room)
    if done is False or len(verses) >= LYRICS_PAGE_SIZE:
        kept = verses[:page]
        has_more = bool(kept) and start + len(kept) < MAX_LYRICS_VERSES
        return kept, has_more, start + len(kept)
    kept = verses[:room]
    return kept, False, start + len(kept)


def _slug(name: str) -> str:
    hint = romanize_name(name) or name
    decomposed = unicodedata.normalize("NFKD", hint)
    ascii_text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    slug = _SLUG.sub("-", ascii_text.strip().lower()).strip("-")
    if slug:
        return slug[:80]
    return hashlib.sha256(name.strip().encode("utf-8")).hexdigest()[:12]


def _source_url(name: str, script: str) -> str:
    return f"saha://ai/gemini/{script}/{_slug(name)}"


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

    return await acompletion(
        model=model,
        messages=messages,
        **completion_kwargs(model, temperature=temperature),
    )


def _lookup_from_cache(cached: object) -> LyricsLookup | None:
    if not isinstance(cached, dict) or "suggestions" not in cached:
        return None
    raw_version = cached.get("version")
    version = SlokaVersion.model_validate(raw_version) if isinstance(raw_version, dict) else None
    suggestions = cached.get("suggestions")
    return LyricsLookup(
        version=version,
        suggestions=[str(item) for item in suggestions] if isinstance(suggestions, list) else [],
        ambiguous=bool(cached.get("ambiguous")),
    )


def _cache_lookup(cache_key: str, lookup: LyricsLookup) -> None:
    cache_set(
        cache_key,
        {
            "version": lookup.version.model_dump() if lookup.version else None,
            "suggestions": lookup.suggestions,
            "ambiguous": lookup.ambiguous,
        },
        expire=60 * 60 * 24 * 7,
    )


async def lookup_lyrics(
    name: str,
    script: str,
    settings: Settings | None = None,
) -> LyricsLookup:
    settings = settings or get_settings()
    script_key = script.strip().lower()
    if script_key not in SUPPORTED_SCRIPTS:
        raise ValueError(f"Unsupported script: {script}")
    if not settings.llm_enabled:
        raise RuntimeError(
            "Lyrics search requires an LLM. Set LLM_MODEL "
            f"(for example {LATEST_GEMINI_MODEL}) and GEMINI_API_KEY."
        )

    query = name.strip()
    cache_key = f"lyrics2:{script_key}:{query.casefold()}"
    cached_lookup = _lookup_from_cache(cache_get(cache_key))
    if cached_lookup is not None:
        return cached_lookup

    user = lyrics_user_message(query, script_key)
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
    parsed: dict | None = None
    try:
        parsed = parse_json_payload(content)
        verses = [str(v).strip() for v in parsed.get("verses") or [] if str(v).strip()]
        found = bool(parsed.get("found", bool(verses))) and bool(verses)
        title = (parsed.get("title") or query).strip() or query
        reported_script = str(parsed.get("script") or script_key).strip().lower()
    except (ValueError, TypeError):
        verses = verses_from_freeform(content)
        found = bool(verses)
        parsed = None

    suggestions = clean_suggestions(parsed.get("suggestions"), query) if parsed else []
    ambiguous = bool(parsed.get("ambiguous")) and bool(suggestions) if parsed else False

    if ambiguous or not found or not verses:
        lookup = LyricsLookup(version=None, suggestions=suggestions, ambiguous=ambiguous)
        _cache_lookup(cache_key, lookup)
        return lookup

    done = bool(parsed["done"]) if parsed is not None and "done" in parsed else None
    verses, has_more, next_offset = clip_verse_page(verses, done, 0)
    if not verses:
        lookup = LyricsLookup(version=None, suggestions=suggestions, ambiguous=ambiguous)
        _cache_lookup(cache_key, lookup)
        return lookup

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
        has_more=has_more,
        next_offset=next_offset,
    )
    lookup = LyricsLookup(version=version, suggestions=[], ambiguous=False)
    _cache_lookup(cache_key, lookup)
    return lookup


def _tail_lines(previous_tail: list[str]) -> list[str]:
    lines: list[str] = []
    for item in previous_tail[-2:]:
        text = " ".join(str(item).split())
        if text:
            lines.append(text[:400])
    return lines


async def continue_lyrics(
    name: str,
    script: str,
    offset: int,
    title: str | None = None,
    previous_tail: list[str] | None = None,
    settings: Settings | None = None,
) -> LyricsContinueResponse:
    """Fetch the next page of a long work. Offset is the 0-based index to start at."""
    settings = settings or get_settings()
    script_key = script.strip().lower()
    if script_key not in SUPPORTED_SCRIPTS:
        raise ValueError(f"Unsupported script: {script}")
    if offset < 0 or offset > MAX_LYRICS_VERSES:
        raise ValueError(f"Verse offset must be between 0 and {MAX_LYRICS_VERSES}")
    query = name.strip()
    if offset >= MAX_LYRICS_VERSES:
        return LyricsContinueResponse(verses=[], has_more=False, next_offset=offset, title=title or query)
    if not settings.llm_enabled:
        raise RuntimeError(
            "Lyrics search requires an LLM. Set LLM_MODEL "
            f"(for example {LATEST_GEMINI_MODEL}) and GEMINI_API_KEY."
        )

    cache_key = f"lyrics2:{script_key}:{query.casefold()}:from:{offset}"
    cached = cache_get(cache_key)
    if isinstance(cached, dict) and "verses" in cached:
        return LyricsContinueResponse.model_validate(cached)

    tail = _tail_lines(previous_tail or [])
    language = _language_label(script_key)
    work = (title or query).strip() or query
    tail_block = "\n".join(f"- {line}" for line in tail) or "(none)"
    user = (
        f"Continue the lyrics of {work} in {language}.\n"
        f"Start at verse {offset + 1}. Return at most {LYRICS_PAGE_SIZE} verses.\n"
        "Do not repeat these previous lines:\n"
        f"{tail_block}\n"
        'If more verses remain after this page, set "done" to false. '
        'If this page ends the work, set "done" to true.'
    )
    response = await _complete(
        settings.llm_model,
        [
            {"role": "system", "content": LYRICS_SYSTEM},
            {"role": "user", "content": user},
        ],
        0.2,
    )
    content = response.choices[0].message.content or ""
    raw_verses: list[str] = []
    done: bool | None = None
    page_title = work
    try:
        parsed = parse_json_payload(content)
        raw_verses = [str(v).strip() for v in parsed.get("verses") or [] if str(v).strip()]
        page_title = (parsed.get("title") or work).strip() or work
        done = bool(parsed["done"]) if "done" in parsed else None
    except (ValueError, TypeError):
        raw_verses = verses_from_freeform(content)
        done = None

    incoming = drop_verse_overlap(tail, raw_verses)
    if not incoming:
        result = LyricsContinueResponse(verses=[], has_more=False, next_offset=offset, title=page_title)
        cache_set(cache_key, result.model_dump(), expire=60 * 60 * 24 * 7)
        return result
    kept, has_more, next_offset = clip_verse_page(incoming, done, offset)
    result = LyricsContinueResponse(
        verses=kept,
        has_more=has_more,
        next_offset=next_offset,
        title=page_title,
    )
    cache_set(cache_key, result.model_dump(), expire=60 * 60 * 24 * 7)
    return result


async def generate_lyrics(
    name: str,
    script: str,
    settings: Settings | None = None,
) -> SlokaVersion | None:
    return (await lookup_lyrics(name, script, settings=settings)).version


async def suggest_search_terms(
    query: str,
    settings: Settings | None = None,
) -> tuple[list[str], bool]:
    """Names to offer when a web search returns nothing."""
    settings = settings or get_settings()
    if not settings.llm_enabled:
        return [], False
    text = query.strip()
    cache_key = f"suggest:{text.casefold()}"
    cached_lookup = _lookup_from_cache(cache_get(cache_key))
    if cached_lookup is not None:
        return cached_lookup.suggestions, cached_lookup.ambiguous

    suggestions: list[str] = []
    ambiguous = False
    try:
        response = await _complete(
            settings.llm_model,
            [
                {"role": "system", "content": SUGGEST_SYSTEM},
                {"role": "user", "content": f"Search query: {text}"},
            ],
            0.2,
        )
        content = response.choices[0].message.content or ""
        data = parse_json_payload(content)
        suggestions = clean_suggestions(data.get("suggestions"), text)
        ambiguous = bool(data.get("ambiguous")) and bool(suggestions)
    except Exception:
        logger.warning("did-you-mean suggestions failed for %r", text, exc_info=True)
        suggestions = []
        ambiguous = False
    lookup = LyricsLookup(version=None, suggestions=suggestions, ambiguous=ambiguous)
    _cache_lookup(cache_key, lookup)
    return suggestions, ambiguous
