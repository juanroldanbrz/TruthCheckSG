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
