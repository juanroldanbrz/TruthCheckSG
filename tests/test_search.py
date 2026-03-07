import pytest
from unittest.mock import AsyncMock, patch, MagicMock

MOCK_BRAVE_RESPONSE = {
    "web": {
        "results": [
            {"title": "MOH Advisory", "url": "https://www.moh.gov.sg/advisory", "description": "Official MOH info"},
            {"title": "CNA Article", "url": "https://www.channelnewsasia.com/article", "description": "CNA coverage"},
        ]
    }
}


@pytest.mark.asyncio
async def test_search_returns_list_of_results():
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value=MOCK_BRAVE_RESPONSE)
    mock_response.raise_for_status = MagicMock()

    with patch("fact_verifier.services.search.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        from fact_verifier.services.search import brave_search
        results = await brave_search("CPF withdrawal age")
        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["url"] == "https://www.moh.gov.sg/advisory"
        assert "title" in results[0]
        assert "snippet" in results[0]


@pytest.mark.asyncio
async def test_search_returns_empty_list_on_no_results():
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value={"web": {"results": []}})
    mock_response.raise_for_status = MagicMock()

    with patch("fact_verifier.services.search.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        from fact_verifier.services.search import brave_search
        results = await brave_search("nonexistent claim")
        assert results == []


@pytest.mark.asyncio
async def test_search_returns_empty_list_on_http_error():
    with patch("fact_verifier.services.search.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=Exception("HTTP error"))
        mock_client_class.return_value = mock_client

        from fact_verifier.services.search import brave_search
        results = await brave_search("some claim")
        assert results == []


@pytest.mark.asyncio
async def test_search_with_site_bias_merges_preferred_first():
    """When prefer_site is set, results from site: query appear first, then general, deduplicated."""
    from fact_verifier.services.search import brave_search_with_site_bias

    gov_result = {"title": "MOH", "url": "https://www.moh.gov.sg/page", "snippet": "Government info"}
    general_results = [
        {"title": "CNA", "url": "https://channelnewsasia.com/a", "snippet": "News"},
        {"title": "Other", "url": "https://other.com/b", "snippet": "Other"},
    ]

    async def mock_brave_search(query: str, count: int = 10):
        if "site:gov.sg" in query:
            return [gov_result]
        return general_results

    with patch("fact_verifier.services.search.brave_search", new_callable=AsyncMock, side_effect=mock_brave_search):
        results = await brave_search_with_site_bias("CPF age", count=10, prefer_site="gov.sg")
    assert len(results) == 3
    assert results[0]["url"] == "https://www.moh.gov.sg/page"
    assert results[1]["url"] == "https://channelnewsasia.com/a"
    assert results[2]["url"] == "https://other.com/b"


@pytest.mark.asyncio
async def test_search_with_site_bias_empty_prefer_site_calls_brave_search_once():
    """When prefer_site is empty, brave_search_with_site_bias delegates to brave_search once."""
    with patch("fact_verifier.services.search.brave_search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [{"title": "X", "url": "https://x.com", "snippet": "S"}]
        from fact_verifier.services.search import brave_search_with_site_bias
        results = await brave_search_with_site_bias("claim", count=5, prefer_site="")
    mock_search.assert_called_once_with("claim", count=5)
    assert len(results) == 1
    assert results[0]["url"] == "https://x.com"
