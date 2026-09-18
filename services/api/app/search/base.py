from __future__ import annotations

from typing import Protocol

from app.models import SearchHit


class SearchProvider(Protocol):
    name: str

    async def search(self, query: str, count: int = 10) -> list[SearchHit]:
        ...
