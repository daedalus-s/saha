from __future__ import annotations

from urllib.parse import urlparse

from app.cache import cache_get, cache_set
from app.extract.clean import clean_html
from app.extract.dedupe import version_fingerprint
from app.extract.fetch import FetchError, fetch_url
from app.extract.llm_extract import dominant_script_for_verses, extract_verses
from app.extract.mock_pages import mock_extract
from app.models import ExtractResponse, SlokaVersion


async def extract_from_url(url: str, query: str | None = None) -> ExtractResponse:
    mocked = mock_extract(url)
    if mocked is not None:
        return mocked

    cache_key = f"extract:{url}"
    cached = cache_get(cache_key)
    if isinstance(cached, dict):
        return ExtractResponse.model_validate(cached)

    try:
        html = await fetch_url(url)
    except FetchError as exc:
        result = ExtractResponse(version=None, error=str(exc))
        cache_set(cache_key, result.model_dump(), expire=60 * 15)
        return result

    text = clean_html(html, url=url)
    if not text:
        result = ExtractResponse(version=None, error="No textual content found on the page")
        cache_set(cache_key, result.model_dump(), expire=60 * 30)
        return result

    data = await extract_verses(text, url=url, query=query)
    verses = [v for v in data.get("verses") or [] if v.strip()]
    if not data.get("found") or not verses:
        result = ExtractResponse(version=None, error="No sloka verses found on this page")
        cache_set(cache_key, result.model_dump(), expire=60 * 30)
        return result

    script = data.get("script") or dominant_script_for_verses(verses)
    digest, normalized = version_fingerprint(verses, script)
    domain = urlparse(url).hostname or ""
    domain = domain.removeprefix("www.")
    version = SlokaVersion(
        title=(data.get("title") or query or "Untitled sloka").strip(),
        script=script,
        verses=verses,
        source_url=url,
        source_domain=domain,
        fingerprint=digest,
        normalized=normalized,
        deity=data.get("deity"),
        category=data.get("category"),
    )
    result = ExtractResponse(version=version, error=None)
    cache_set(cache_key, result.model_dump(), expire=60 * 60 * 24)
    return result
