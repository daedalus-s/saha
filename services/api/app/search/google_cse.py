from __future__ import annotations

import httpx

from app.models import SearchHit
from app.search.expand import domain_of


class GoogleCseSearchProvider:
    name = "google_cse"
    endpoint = "https://www.googleapis.com/customsearch/v1"

    def __init__(
        self,
        api_key: str,
        cx: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key or not cx:
            raise ValueError("GOOGLE_CSE_KEY and GOOGLE_CSE_CX are required")
        self.api_key = api_key
        self.cx = cx
        self._client = client

    async def search(self, query: str, count: int = 10) -> list[SearchHit]:
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": min(count, 10),
        }
        if self._client is not None:
            response = await self._client.get(self.endpoint, params=params)
            response.raise_for_status()
            data = response.json()
        else:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(self.endpoint, params=params)
                response.raise_for_status()
                data = response.json()

        hits: list[SearchHit] = []
        for item in data.get("items", []):
            url = item.get("link") or ""
            if not url:
                continue
            hits.append(
                SearchHit(
                    url=url,
                    title=item.get("title") or url,
                    snippet=item.get("snippet") or "",
                    source_domain=domain_of(url),
                )
            )
        return hits
