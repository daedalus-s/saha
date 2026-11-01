import json
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.llm import LATEST_GEMINI_MODEL
from app.models import MEANING_LANGUAGES
from app.translate import resolve_meaning_language, translate_verses

# Frozen list shared with apps/mobile/src/utils/languages.ts.
FROZEN_MEANING_LANGUAGES = (
    ("en", "English", "latin"),
    ("hi", "Hindi", "devanagari"),
    ("ta", "Tamil", "tamil"),
    ("te", "Telugu", "telugu"),
    ("kn", "Kannada", "kannada"),
    ("ml", "Malayalam", "malayalam"),
    ("gu", "Gujarati", "gujarati"),
    ("bn", "Bengali", "bengali"),
)


def test_meaning_languages_match_frozen_list():
    assert MEANING_LANGUAGES == FROZEN_MEANING_LANGUAGES


def test_resolve_meaning_language_normalizes_case():
    assert resolve_meaning_language("TA") == ("ta", "Tamil", "tamil")


def test_resolve_meaning_language_rejects_unknown():
    with pytest.raises(ValueError, match="Unsupported meaning language"):
        resolve_meaning_language("fr")


async def test_translate_verses_asks_for_tamil(monkeypatch):
    payload = {
        "verses": [
            {"verse": "श्रीगुरु", "meaning": "குருவின் திருவடி"},
        ]
    }

    async def fake_completion(**kwargs):
        system = kwargs["messages"][0]["content"]
        user = kwargs["messages"][1]["content"]
        assert "Tamil" in system
        assert "Target language: Tamil (ta)" in user
        assert "temperature" not in kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )

    monkeypatch.setattr("litellm.acompletion", fake_completion)
    monkeypatch.setattr("app.translate.cache_get", lambda key: None)
    monkeypatch.setattr("app.translate.cache_set", lambda *args, **kwargs: None)

    result = await translate_verses(
        ["श्रीगुरु"],
        source_script="devanagari",
        target_language="ta",
        title="Hanuman Chalisa",
        settings=Settings(llm_model=LATEST_GEMINI_MODEL),
    )
    assert result.target_language == "ta"
    assert result.verses[0].meaning == "குருவின் திருவடி"


async def test_translate_verses_fills_missing_meaning_in_target_language(monkeypatch):
    async def fake_completion(**kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"verses": []})))]
        )

    monkeypatch.setattr("litellm.acompletion", fake_completion)
    monkeypatch.setattr("app.translate.cache_get", lambda key: None)
    monkeypatch.setattr("app.translate.cache_set", lambda *args, **kwargs: None)

    result = await translate_verses(
        ["verse"],
        source_script="devanagari",
        target_language="hi",
        settings=Settings(llm_model=LATEST_GEMINI_MODEL),
    )
    assert "अर्थ" in result.verses[0].meaning
