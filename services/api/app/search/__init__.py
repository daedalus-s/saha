from __future__ import annotations

import asyncio
import logging

from app.config import Settings, get_settings
from app.models import SUPPORTED_SCRIPTS, SearchHit, SearchResponse
from app.search.base import SearchProvider
from app.search.brave import BraveSearchProvider
from app.search.expand import expand_queries, merge_hits
from app.search.google_cse import GoogleCseSearchProvider
from app.search.llm_lyrics import generate_lyrics
from app.search.mock import MockSearchProvider

logger = logging.getLogger(__name__)

_THROTTLED_PROVIDERS = {"brave", "google_cse", "google"}
_LYRICS_PROVIDERS = {"gemini", "llm"}
_HIT_LIMIT = 15


def build_provider(settings: Settings | None = None) -> SearchProvider:
    settings = settings or get_settings()
    name = (settings.search_provider or "mock").strip().lower()
    if name == "brave":
        return BraveSearchProvider(settings.brave_api_key or "")
    if name in ("google_cse", "google"):
        return GoogleCseSearchProvider(
            settings.google_cse_key or "",
            settings.google_cse_cx or "",
        )
    return MockSearchProvider()


async def _lyrics_search(query: str, script: str, settings: Settings) -> SearchResponse:
    version = await generate_lyrics(query, script, settings=settings)
    if version is None:
        return SearchResponse(hits=[], versions=[], expanded_queries=[query.strip()])
    hit = SearchHit(
        url=version.source_url,
        title=version.title,
        snippet="",
        source_domain=version.source_domain,
    )
    return SearchResponse(hits=[hit], versions=[version], expanded_queries=[query.strip()])


async def search_sloka(
    query: str,
    provider: SearchProvider | None = None,
    script: str = "devanagari",
    settings: Settings | None = None,
) -> SearchResponse:
    settings = settings or get_settings()
    provider_name = (settings.search_provider or "mock").strip().lower()
    if provider is None and provider_name in _LYRICS_PROVIDERS:
        script_key = script.strip().lower()
        if script_key not in SUPPORTED_SCRIPTS:
            raise ValueError(f"Unsupported script: {script}")
        return await _lyrics_search(query, script_key, settings)

    provider = provider or build_provider(settings)
    queries = expand_queries(query)
    batches: list[list[SearchHit]] = []
    errors: list[Exception] = []
    throttle = getattr(provider, "name", "") in _THROTTLED_PROVIDERS
    for index, expanded in enumerate(queries):
        if index and throttle:
            await asyncio.sleep(1.1)
        try:
            batches.append(await provider.search(expanded, count=8))
        except Exception as exc:
            errors.append(exc)
            logger.warning(
                "search provider %s failed for %r: %s",
                getattr(provider, "name", "unknown"),
                expanded,
                exc,
            )
        if len(merge_hits(batches, limit=_HIT_LIMIT)) >= _HIT_LIMIT:
            break
    if not batches and errors:
        raise errors[0]
    merged = merge_hits(batches, limit=_HIT_LIMIT)
    return SearchResponse(hits=merged, expanded_queries=queries)
