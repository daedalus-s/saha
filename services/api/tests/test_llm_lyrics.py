import json

from app.config import Settings
from app.search.llm_lyrics import generate_lyrics, verses_from_freeform
from app.search import search_sloka
from app.models import SlokaVersion


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

        class Message:
            content = json.dumps(payload)

        class Choice:
            message = Message()

        class Response:
            choices = [Choice()]

        return Response()

    monkeypatch.setattr("app.search.llm_lyrics._complete", fake_complete)
    monkeypatch.setattr("app.search.llm_lyrics.cache_get", lambda key: None)
    monkeypatch.setattr("app.search.llm_lyrics.cache_set", lambda *args, **kwargs: None)

    settings = Settings(llm_model="gemini/gemini-2.0-flash", search_provider="gemini")
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

    async def fake_lyrics(name, script, settings=None):
        assert name == "Hanuman Chalisa"
        assert script == "devanagari"
        return version

    monkeypatch.setattr("app.search.generate_lyrics", fake_lyrics)
    settings = Settings(search_provider="gemini", llm_model="gemini/gemini-2.0-flash")
    result = await search_sloka("Hanuman Chalisa", script="devanagari", settings=settings)
    assert result.versions
    assert result.hits[0].url == version.source_url
