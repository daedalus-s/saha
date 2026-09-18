from __future__ import annotations

from app.models import SearchHit


class MockSearchProvider:
    """Deterministic provider for local development and tests."""

    name = "mock"

    async def search(self, query: str, count: int = 10) -> list[SearchHit]:
        q = query.strip() or "sloka"
        return [
            SearchHit(
                url="https://example.org/vignanam/hanuman-chalisa-devanagari",
                title=f"{q} — Devanagari",
                snippet="Hanuman Chalisa in Devanagari script with verses.",
                source_domain="example.org",
            ),
            SearchHit(
                url="https://example.org/stotranidhi/hanuman-chalisa-telugu",
                title=f"{q} — Telugu",
                snippet="Hanuman Chalisa in Telugu script.",
                source_domain="example.org",
            ),
            SearchHit(
                url="https://example.org/greenmesg/hanuman-chalisa-tamil",
                title=f"{q} — Tamil",
                snippet="Hanuman Chalisa in Tamil script.",
                source_domain="example.org",
            ),
        ][:count]
