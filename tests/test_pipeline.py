import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_pipeline_emits_progress_and_result_events():
    events = []

    with patch("fact_verifier.services.pipeline.parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch("fact_verifier.services.pipeline.brave_search", new_callable=AsyncMock) as mock_search, \
         patch("fact_verifier.services.pipeline.fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch("fact_verifier.services.pipeline.verify_claim", new_callable=AsyncMock) as mock_verify:
        mock_parse.return_value = {"is_relevant": True, "search_query": "CPF withdrawal age"}

        mock_search.return_value = [
            {"url": "https://www.moh.gov.sg/a", "title": "MOH", "snippet": "info"}
        ]
        mock_fetch.return_value = [
            {"url": "https://www.moh.gov.sg/a", "markdown": "Content here"}
        ]
        mock_verify.return_value = {
            "verdict": "false",
            "summary": "Not true.",
            "explanation": "Details.",
            "sources": [],
        }

        from fact_verifier.services.pipeline import run_pipeline
        async for event in run_pipeline("some claim", "en"):
            events.append(event)

    event_types = [e["type"] for e in events]
    assert "progress" in event_types
    assert "result" in event_types
    assert not any(e["type"] == "error" for e in events)


@pytest.mark.asyncio
async def test_pipeline_emits_three_progress_steps():
    events = []

    with patch("fact_verifier.services.pipeline.parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch("fact_verifier.services.pipeline.brave_search", new_callable=AsyncMock) as mock_search, \
         patch("fact_verifier.services.pipeline.fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch("fact_verifier.services.pipeline.verify_claim", new_callable=AsyncMock) as mock_verify:
        mock_parse.return_value = {"is_relevant": True, "search_query": "CPF withdrawal age"}

        mock_search.return_value = [
            {"url": "https://www.moh.gov.sg/a", "title": "MOH", "snippet": "info"}
        ]
        mock_fetch.return_value = [
            {"url": "https://www.moh.gov.sg/a", "markdown": "Content here"}
        ]
        mock_verify.return_value = {
            "verdict": "verified",
            "summary": "True.",
            "explanation": "Details.",
            "sources": [],
        }

        from fact_verifier.services.pipeline import run_pipeline
        async for event in run_pipeline("some claim", "en"):
            events.append(event)

    progress_events = [e for e in events if e["type"] == "progress"]
    steps = [e["step"] for e in progress_events]
    assert 1 in steps
    assert 2 in steps
    assert 3 in steps


@pytest.mark.asyncio
async def test_pipeline_emits_error_on_no_search_results():
    events = []

    with patch("fact_verifier.services.pipeline.parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch("fact_verifier.services.pipeline.brave_search", new_callable=AsyncMock) as mock_search, \
         patch("fact_verifier.services.pipeline.fetch_all", new_callable=AsyncMock) as mock_fetch:

        mock_parse.return_value = {"is_relevant": True, "search_query": "obscure claim"}
        mock_search.return_value = []
        mock_fetch.return_value = []

        from fact_verifier.services.pipeline import run_pipeline
        async for event in run_pipeline("obscure claim", "en"):
            events.append(event)

    assert any(e["type"] == "error" for e in events)
    assert not any(e["type"] == "result" for e in events)


@pytest.mark.asyncio
async def test_pipeline_passes_image_to_parse_claim():
    """run_pipeline must pass image_bytes and image_content_type to parse_claim."""
    with patch("fact_verifier.services.pipeline.parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch("fact_verifier.services.pipeline.brave_search", new_callable=AsyncMock) as mock_search, \
         patch("fact_verifier.services.pipeline.fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch("fact_verifier.services.pipeline.verify_claim", new_callable=AsyncMock) as mock_verify:

        mock_parse.return_value = {"is_relevant": True, "search_query": "investment scam"}
        mock_search.return_value = [{"url": "https://www.police.gov.sg/a", "title": "SPF", "snippet": "scam alert"}]
        mock_fetch.return_value = [{"url": "https://www.police.gov.sg/a", "markdown": "Investment scam alert."}]
        mock_verify.return_value = {"verdict": "false", "summary": "Scam.", "explanation": "Details.", "sources": []}

        from fact_verifier.services.pipeline import run_pipeline
        async for _ in run_pipeline("is this an investment scam?", "en", image_bytes=b"fakeimg", image_content_type="image/jpeg"):
            pass

        mock_parse.assert_called_once_with("is this an investment scam?", "en", image_bytes=b"fakeimg", image_content_type="image/jpeg")


@pytest.mark.asyncio
async def test_pipeline_passes_image_to_verify_claim():
    """run_pipeline must pass image_bytes and image_content_type to verify_claim."""
    with patch("fact_verifier.services.pipeline.parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch("fact_verifier.services.pipeline.brave_search", new_callable=AsyncMock) as mock_search, \
         patch("fact_verifier.services.pipeline.fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch("fact_verifier.services.pipeline.verify_claim", new_callable=AsyncMock) as mock_verify:

        mock_parse.return_value = {"is_relevant": True, "search_query": "investment scam"}
        mock_search.return_value = [{"url": "https://www.police.gov.sg/a", "title": "SPF", "snippet": "scam alert"}]
        mock_fetch.return_value = [{"url": "https://www.police.gov.sg/a", "markdown": "Investment scam alert."}]
        mock_verify.return_value = {"verdict": "false", "summary": "Scam.", "explanation": "Details.", "sources": []}

        from fact_verifier.services.pipeline import run_pipeline
        async for _ in run_pipeline("is this an investment scam?", "en", image_bytes=b"fakeimg", image_content_type="image/jpeg"):
            pass

        call_kwargs = mock_verify.call_args.kwargs
        assert call_kwargs.get("image_bytes") == b"fakeimg"
        assert call_kwargs.get("image_content_type") == "image/jpeg"


@pytest.mark.asyncio
async def test_pipeline_emits_error_on_verify_exception():
    events = []

    with patch("fact_verifier.services.pipeline.parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch("fact_verifier.services.pipeline.brave_search", new_callable=AsyncMock) as mock_search, \
         patch("fact_verifier.services.pipeline.fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch("fact_verifier.services.pipeline.verify_claim", new_callable=AsyncMock) as mock_verify:

        mock_parse.return_value = {"is_relevant": True, "search_query": "some claim"}
        mock_search.return_value = [
            {"url": "https://www.moh.gov.sg/a", "title": "MOH", "snippet": "info"}
        ]
        mock_fetch.return_value = [
            {"url": "https://www.moh.gov.sg/a", "markdown": "Content"}
        ]
        mock_verify.side_effect = Exception("OpenAI API error")

        from fact_verifier.services.pipeline import run_pipeline
        async for event in run_pipeline("some claim", "en"):
            events.append(event)

    assert any(e["type"] == "error" for e in events)
