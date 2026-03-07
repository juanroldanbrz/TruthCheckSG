import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_fetch_and_convert_returns_markdown():
    mock_response = MagicMock()
    mock_response.text = "<html><body><p>CPF is a retirement scheme.</p></body></html>"
    mock_response.raise_for_status = MagicMock()

    with patch("services.scraper.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch("services.scraper.trafilatura.extract", return_value="CPF is a retirement scheme."):
            from services.scraper import fetch_as_markdown
            result = await fetch_as_markdown("https://www.cpf.gov.sg/article")
            assert result is not None
            assert "CPF" in result


@pytest.mark.asyncio
async def test_fetch_returns_none_on_failure():
    with patch("services.scraper.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=Exception("timeout"))
        mock_client_class.return_value = mock_client

        from services.scraper import fetch_as_markdown
        result = await fetch_as_markdown("https://bad-url.example.com")
        assert result is None


@pytest.mark.asyncio
async def test_fetch_returns_none_when_trafilatura_extracts_nothing():
    mock_response = MagicMock()
    mock_response.text = "<html><body></body></html>"
    mock_response.raise_for_status = MagicMock()

    with patch("services.scraper.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch("services.scraper.trafilatura.extract", return_value=None):
            from services.scraper import fetch_as_markdown
            result = await fetch_as_markdown("https://www.example.com/empty")
            assert result is None


@pytest.mark.asyncio
async def test_fetch_all_returns_only_successful_results():
    async def mock_fetch(url):
        if "good" in url:
            return "Good content"
        return None

    with patch("services.scraper.fetch_as_markdown", side_effect=mock_fetch):
        from services.scraper import fetch_all
        results = await fetch_all(["https://good.com", "https://bad.com", "https://good2.com"])
        assert len(results) == 2
        assert all(r["markdown"] is not None for r in results)
        assert results[0]["url"] == "https://good.com"
