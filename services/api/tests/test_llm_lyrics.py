import json
from types import SimpleNamespace

from app.config import Settings
from app.llm import LATEST_GEMINI_MODEL
from app.models import SlokaVersion
from app.search import search_sloka
from app.search.llm_lyrics import (
    LYRICS_PAGE_SIZE,
    MAX_LYRICS_VERSES,
    LyricsLookup,
    clean_suggestions,
    clip_verse_page,
    continue_lyrics,
    drop_verse_overlap,
    generate_lyrics,
    lookup_lyrics,
    lyrics_user_message,
    verses_from_freeform,
)


def test_verses_from_freeform_skips_fences():
    raw = "```json\n{\n}\n```\nश्रीगुरु चरन सरोज रज\nनिज मनु मुकुरु सुधारि"
    verses = verses_from_freeform(raw)
    assert "श्रीगुरु चरन सरोज रज" in verses
    assert "निज मनु मुकुरु सुधारि" in verses


async def test_generate_lyrics_parses_json(monkeypatch):
    payload = {
        "found": True,
        "title": "Hanuman Chalisa",
        "script": "devanagari",
        "verses": ["श्रीगुरु चरन सरोज रज", "निज मनु मुकुरु सुधारि"],
    }

    async def fake_complete(model, messages, temperature):
        assert "Hanuman Chalisa" in messages[1]["content"]
        assert "Devanagari" in messages[1]["content"]

        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )

    monkeypatch.setattr("app.search.llm_lyrics._complete", fake_complete)
    monkeypatch.setattr("app.search.llm_lyrics.cache_get", lambda key: None)
    monkeypatch.setattr("app.search.llm_lyrics.cache_set", lambda *args, **kwargs: None)

    settings = Settings(llm_model=LATEST_GEMINI_MODEL, search_provider="gemini")
    version = await generate_lyrics("Hanuman Chalisa", "devanagari", settings=settings)
    assert version is not None
    assert version.ai_generated
    assert version.verses[0].startswith("श्रीगुरु")
    assert version.source_url.startswith("saha://ai/gemini/")


async def test_search_sloka_gemini_returns_version(monkeypatch):
    version = SlokaVersion(
        title="Hanuman Chalisa",
        script="devanagari",
        verses=["दोहा"],
        source_url="saha://ai/gemini/devanagari/hanuman-chalisa",
        source_domain="AI-generated",
        fingerprint="abc",
        normalized="doha",
        ai_generated=True,
    )

    async def fake_lookup(name, script, settings=None):
        assert name == "Hanuman Chalisa"
        assert script == "devanagari"
        return LyricsLookup(version=version, suggestions=[], ambiguous=False)

    monkeypatch.setattr("app.search.lookup_lyrics", fake_lookup)
    settings = Settings(search_provider="gemini", llm_model=LATEST_GEMINI_MODEL)
    result = await search_sloka("Hanuman Chalisa", script="devanagari", settings=settings)
    assert result.versions
    assert result.hits[0].url == version.source_url


def test_lyrics_prompt_keeps_tamil_name():
    name = "ஹனுமான் சாலிசா"
    message = lyrics_user_message(name, "devanagari")
    assert name in message
    assert "Tamil script" in message
    assert "Devanagari" in message
    assert "Romanized hint" not in message


def test_lyrics_prompt_adds_iast_hint_for_devanagari_name():
    name = "हनुमान चालीसा"
    message = lyrics_user_message(name, "tamil")
    assert name in message
    assert "Devanagari script" in message
    assert "Tamil" in message
    assert "Romanized hint" in message
    assert "hanum" in message.casefold()


async def test_generate_lyrics_from_tamil_name(monkeypatch):
    name = "ஹனுமான் சாலிசா"
    payload = {
        "found": True,
        "title": "Hanuman Chalisa",
        "script": "devanagari",
        "verses": ["श्रीगुरु चरन सरोज रज"],
    }

    async def fake_complete(model, messages, temperature):
        assert model == LATEST_GEMINI_MODEL
        assert name in messages[1]["content"]
        assert "Tamil script" in messages[1]["content"]

        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )

    monkeypatch.setattr("app.search.llm_lyrics._complete", fake_complete)
    monkeypatch.setattr("app.search.llm_lyrics.cache_get", lambda key: None)
    monkeypatch.setattr("app.search.llm_lyrics.cache_set", lambda *args, **kwargs: None)

    settings = Settings(llm_model=LATEST_GEMINI_MODEL, search_provider="gemini")
    version = await generate_lyrics(name, "devanagari", settings=settings)
    assert version is not None
    assert version.verses[0].startswith("श्रीगुरु")
    assert version.source_url.startswith("saha://ai/gemini/devanagari/")
    assert not version.source_url.endswith("/sloka")


def test_short_page_is_complete_when_done_is_omitted():
    kept, has_more, next_offset = clip_verse_page(["one", "two"], None, 0)
    assert kept == ["one", "two"]
    assert has_more is False
    assert next_offset == 2


def test_full_page_requests_another_when_not_done():
    verses = [f"line {index}" for index in range(LYRICS_PAGE_SIZE)]
    kept, has_more, next_offset = clip_verse_page(verses, False, 0)
    assert len(kept) == LYRICS_PAGE_SIZE
    assert has_more is True
    assert next_offset == LYRICS_PAGE_SIZE


def test_pages_stop_at_four_thousand_verses():
    kept, has_more, next_offset = clip_verse_page(["last"], False, MAX_LYRICS_VERSES - 1)
    assert kept == ["last"]
    assert has_more is False
    assert next_offset == MAX_LYRICS_VERSES


def test_drop_verse_overlap_removes_repeated_tail():
    incoming = drop_verse_overlap(["alpha", "beta"], ["beta", "gamma"])
    assert incoming == ["gamma"]


def test_clean_suggestions_drops_query_and_duplicates():
    names = clean_suggestions(
        ["Hanuman Chalisa", "hanuman chalisa", "  Hanuman Ashtak  ", "", "Hanuman Chalisa"],
        "Hanuman Chalisa",
    )
    assert names == ["Hanuman Ashtak"]


async def test_lookup_lyrics_suggests_when_missing(monkeypatch):
    payload = {
        "found": False,
        "ambiguous": False,
        "title": "",
        "script": "latin",
        "verses": [],
        "suggestions": ["Hanuman Chalisa", "Hanuman Ashtak"],
    }

    async def fake_complete(model, messages, temperature):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )

    monkeypatch.setattr("app.search.llm_lyrics._complete", fake_complete)
    monkeypatch.setattr("app.search.llm_lyrics.cache_get", lambda key: None)
    monkeypatch.setattr("app.search.llm_lyrics.cache_set", lambda *args, **kwargs: None)

    settings = Settings(llm_model=LATEST_GEMINI_MODEL, search_provider="gemini")
    lookup = await lookup_lyrics("hanuman chalisaa", "devanagari", settings=settings)
    assert lookup.version is None
    assert lookup.suggestions == ["Hanuman Chalisa", "Hanuman Ashtak"]
    assert lookup.ambiguous is False


async def test_lookup_lyrics_ambiguous_does_not_return_verses(monkeypatch):
    payload = {
        "found": True,
        "ambiguous": True,
        "title": "Hanuman",
        "script": "devanagari",
        "verses": ["a guessed verse"],
        "suggestions": ["Hanuman Chalisa", "Bajrang Baan"],
    }

    async def fake_complete(model, messages, temperature):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )

    monkeypatch.setattr("app.search.llm_lyrics._complete", fake_complete)
    monkeypatch.setattr("app.search.llm_lyrics.cache_get", lambda key: None)
    monkeypatch.setattr("app.search.llm_lyrics.cache_set", lambda *args, **kwargs: None)

    settings = Settings(llm_model=LATEST_GEMINI_MODEL, search_provider="gemini")
    lookup = await lookup_lyrics("Hanuman", "devanagari", settings=settings)
    assert lookup.version is None
    assert lookup.ambiguous is True
    assert lookup.suggestions == ["Hanuman Chalisa", "Bajrang Baan"]


async def test_continue_lyrics_drops_repeated_tail(monkeypatch):
    payload = {
        "found": True,
        "done": False,
        "title": "Ramayana",
        "script": "devanagari",
        "verses": ["beta", "gamma"],
    }

    async def fake_complete(model, messages, temperature):
        assert "Start at verse 3" in messages[1]["content"]
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )

    monkeypatch.setattr("app.search.llm_lyrics._complete", fake_complete)
    monkeypatch.setattr("app.search.llm_lyrics.cache_get", lambda key: None)
    monkeypatch.setattr("app.search.llm_lyrics.cache_set", lambda *args, **kwargs: None)

    settings = Settings(llm_model=LATEST_GEMINI_MODEL, search_provider="gemini")
    page = await continue_lyrics(
        "Ramayana",
        "devanagari",
        2,
        title="Ramayana",
        previous_tail=["alpha", "beta"],
        settings=settings,
    )
    assert page.verses == ["gamma"]
    assert page.has_more is True
    assert page.next_offset == 3


async def test_lookup_marks_long_first_page_incomplete(monkeypatch):
    payload = {
        "found": True,
        "done": False,
        "title": "Ramayana",
        "script": "devanagari",
        "verses": [f"line {index}" for index in range(LYRICS_PAGE_SIZE + 5)],
    }

    async def fake_complete(model, messages, temperature):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )

    monkeypatch.setattr("app.search.llm_lyrics._complete", fake_complete)
    monkeypatch.setattr("app.search.llm_lyrics.cache_get", lambda key: None)
    monkeypatch.setattr("app.search.llm_lyrics.cache_set", lambda *args, **kwargs: None)

    settings = Settings(llm_model=LATEST_GEMINI_MODEL, search_provider="gemini")
    version = await generate_lyrics("Ramayana", "devanagari", settings=settings)
    assert version is not None
    assert len(version.verses) == LYRICS_PAGE_SIZE
    assert version.has_more is True
    assert version.next_offset == LYRICS_PAGE_SIZE


async def test_search_sloka_returns_suggestions(monkeypatch):
    async def fake_lookup(name, script, settings=None):
        return LyricsLookup(
            version=None,
            suggestions=["Hanuman Chalisa"],
            ambiguous=True,
        )

    monkeypatch.setattr("app.search.lookup_lyrics", fake_lookup)
    settings = Settings(search_provider="gemini", llm_model=LATEST_GEMINI_MODEL)
    result = await search_sloka("Hanuman", script="devanagari", settings=settings)
    assert result.versions == []
    assert result.suggestions == ["Hanuman Chalisa"]
    assert result.ambiguous is True
