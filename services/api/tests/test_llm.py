from app.llm import LATEST_GEMINI_MODEL, completion_kwargs, gemini_3_or_newer


def test_latest_gemini_model_is_3_8_flash():
    assert LATEST_GEMINI_MODEL == "gemini/gemini-3.8-flash"
    assert gemini_3_or_newer(LATEST_GEMINI_MODEL)


def test_gemini_3_omits_temperature_and_uses_low_thinking():
    options = completion_kwargs(LATEST_GEMINI_MODEL, temperature=0.2)
    assert options == {"reasoning_effort": "low"}
    assert "temperature" not in options


def test_older_gemini_keeps_temperature():
    options = completion_kwargs("gemini/gemini-2.0-flash", temperature=0.2)
    assert options == {"temperature": 0.2}
