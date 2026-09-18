from __future__ import annotations

from pathlib import Path
from typing import Any

from diskcache import Cache

from app.config import get_settings

_cache: Cache | None = None


def get_cache() -> Cache:
    global _cache
    if _cache is None:
        path = Path(get_settings().cache_dir)
        path.mkdir(parents=True, exist_ok=True)
        _cache = Cache(str(path))
    return _cache


def cache_get(key: str) -> Any | None:
    return get_cache().get(key)


def cache_set(key: str, value: Any, expire: int | None = 60 * 60 * 24 * 7) -> None:
    get_cache().set(key, value, expire=expire)
