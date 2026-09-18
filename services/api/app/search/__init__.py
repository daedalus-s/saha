from __future__ import annotations

import asyncio

from app.config import Settings, get_settings
from app.models import SearchHit, SearchResponse
from app.search.base import SearchProvider
from app.search.brave import BraveSearchProvider
from app.search.expand import expand_queries, merge_hits
from app.search.google_cse import GoogleCseSearchProvider
from app.search.mock import MockSearchProvider


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


async def search_sloka(query: str, provider: SearchProvider | None = None) -> SearchResponse:
    provider = provider or build_provider()
    queries = expand_queries(query)
    results = await asyncio.gather(
        *(provider.search(expanded, count=8) for expanded in queries),
        return_exceptions=True,
    )
    batches: list[list[SearchHit]] = []
    for item in results:
        if isinstance(item, BaseException):
            continue
        batches.append(item)
    merged = merge_hits(batches, limit=15)
    return SearchResponse(hits=merged, expanded_queries=queries)
