import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_fetch_and_convert_returns_markdown():
    mock_response = MagicMock()
    mock_response.text = "<html><body><p>CPF is a retirement scheme.</p></body></html>"
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with (
        patch("fact_verifier.services.scraper.settings.brightdata_api_key", ""),
        patch("fact_verifier.services.scraper.trafilatura.extract", return_value="CPF is a retirement scheme."),
    ):
        from fact_verifier.services.scraper import fetch_as_markdown
        result = await fetch_as_markdown("https://www.cpf.gov.sg/article", mock_client)
        assert result is not None
        assert "CPF" in result


@pytest.mark.asyncio
async def test_fetch_returns_none_on_failure():
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=Exception("timeout"))

    with patch("fact_verifier.services.scraper.settings.brightdata_api_key", ""):
        from fact_verifier.services.scraper import fetch_as_markdown
        result = await fetch_as_markdown("https://bad-url.example.com", mock_client)
    assert result is None


@pytest.mark.asyncio
async def test_fetch_returns_none_when_trafilatura_extracts_nothing():
    mock_response = MagicMock()
    mock_response.text = "<html><body></body></html>"
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with (
        patch("fact_verifier.services.scraper.settings.brightdata_api_key", ""),
        patch("fact_verifier.services.scraper.trafilatura.extract", return_value=None),
    ):
        from fact_verifier.services.scraper import fetch_as_markdown
        result = await fetch_as_markdown("https://www.example.com/empty", mock_client)
        assert result is None


@pytest.mark.asyncio
async def test_fetch_all_returns_only_successful_results():
    async def mock_fetch(url, client):
        if "good" in url:
            return "Good content"
        return None

    with patch("fact_verifier.services.scraper.fetch_as_markdown", side_effect=mock_fetch):
        from fact_verifier.services.scraper import fetch_all
        results = await fetch_all(["https://good.com", "https://bad.com", "https://good2.com"])
        assert len(results) == 2
        assert all(r["markdown"] is not None for r in results)
        assert results[0]["url"] == "https://good.com"
