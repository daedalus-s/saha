from app.search.expand import expand_queries, merge_hits
from app.models import SearchHit
from app.search.mock import MockSearchProvider
from app.search import search_sloka


def test_expand_queries_starts_with_the_raw_name():
    queries = expand_queries("Hanuman Chalisa")
    assert queries[0] == "Hanuman Chalisa"
    blob = " ".join(queries).lower()
    assert "hanuman chalisa" in blob
    assert "telugu" in blob
    assert "tamil" in blob
    assert "sanskrit" in blob


def test_merge_hits_dedupes_trailing_slash():
    a = SearchHit(url="https://example.org/x", title="A", snippet="", source_domain="example.org")
    b = SearchHit(url="https://example.org/x/", title="B", snippet="", source_domain="example.org")
    merged = merge_hits([[a], [b]], limit=10)
    assert len(merged) == 1


def test_merge_hits_respects_limit():
    batch = [
        SearchHit(url=f"https://example.org/{i}", title=str(i), snippet="", source_domain="example.org")
        for i in range(20)
    ]
    merged = merge_hits([batch], limit=5)
    assert len(merged) == 5


async def test_mock_search_returns_hits():
    result = await search_sloka("Hanuman Chalisa", provider=MockSearchProvider())
    assert result.hits
    assert result.expanded_queries


class _FailingProvider:
    name = "fail"

    async def search(self, query: str, count: int = 10):
        raise RuntimeError(f"provider down for {query}")


async def test_search_surfaces_provider_failures():
    try:
        await search_sloka("Hanuman Chalisa", provider=_FailingProvider())
    except RuntimeError as exc:
        assert "provider down" in str(exc)
    else:
        raise AssertionError("expected provider failure to raise")
