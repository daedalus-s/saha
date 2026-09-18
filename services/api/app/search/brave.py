from __future__ import annotations

import httpx

from app.models import SearchHit
from app.search.expand import domain_of


class BraveSearchProvider:
    name = "brave"
    endpoint = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        if not api_key:
            raise ValueError("BRAVE_API_KEY is required for the Brave search provider")
        self.api_key = api_key
        self._client = client

    async def search(self, query: str, count: int = 10) -> list[SearchHit]:
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        params = {"q": query, "count": min(count, 20)}
        if self._client is not None:
            response = await self._client.get(self.endpoint, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
        else:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(self.endpoint, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

        hits: list[SearchHit] = []
        for item in data.get("web", {}).get("results", []):
            url = item.get("url") or ""
            if not url:
                continue
            hits.append(
                SearchHit(
                    url=url,
                    title=item.get("title") or url,
                    snippet=item.get("description") or "",
                    source_domain=domain_of(url),
                )
            )
        return hits
