"""Shared LiteLLM options for lyrics, extract, and translation."""

from __future__ import annotations

# Stable Gemini Flash model. LiteLLM expects the provider prefix.
LATEST_GEMINI_MODEL = "gemini/gemini-3.8-flash"


def _model_name(model: str) -> str:
    return model.strip().lower().rsplit("/", 1)[-1]


def gemini_3_or_newer(model: str) -> bool:
    """True for Gemini 3+ ids such as gemini-3.8-flash or gemini-3-flash-preview."""
    name = _model_name(model)
    if not name.startswith("gemini-"):
        return False
    rest = name.removeprefix("gemini-")
    major = rest.split(".", 1)[0].split("-", 1)[0]
    return major.isdigit() and int(major) >= 3


def completion_kwargs(model: str, *, temperature: float | None = None) -> dict[str, object]:
    """Options safe for the configured model.

    Gemini 3.6+ ignores temperature, top_p, and top_k, and later models may reject
    them. Gemini 3.8 Flash also rejects thinking level "minimal"; "low" is the
    fastest supported level for name lookup and verse recall.
    """
    if gemini_3_or_newer(model):
        return {"reasoning_effort": "low"}
    if temperature is None:
        return {}
    return {"temperature": temperature}
