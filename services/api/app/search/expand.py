from __future__ import annotations

from urllib.parse import urlparse

from app.models import SearchHit

SCRIPT_QUERY_VARIANTS = (
    "sanskrit",
    "telugu",
    "tamil",
    "kannada",
    "malayalam",
    "gujarati",
    "bengali",
)


def expand_queries(name: str) -> list[str]:
    q = name.strip()
    queries = [
        q,
        f"{q} sloka mantra stotra",
        f"{q} lyrics",
        f"{q} ({' OR '.join(SCRIPT_QUERY_VARIANTS)})",
    ]
    seen: set[str] = set()
    out: list[str] = []
    for item in queries:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def domain_of(url: str) -> str:
    host = urlparse(url).hostname or ""
    return host.removeprefix("www.")


def merge_hits(batches: list[list[SearchHit]], limit: int = 15) -> list[SearchHit]:
    seen: set[str] = set()
    merged: list[SearchHit] = []
    for batch in batches:
        for hit in batch:
            key = hit.url.rstrip("/").lower()
            if key in seen:
                continue
            seen.add(key)
            if not hit.source_domain:
                hit.source_domain = domain_of(hit.url)
            merged.append(hit)
            if len(merged) >= limit:
                return merged
    return merged
