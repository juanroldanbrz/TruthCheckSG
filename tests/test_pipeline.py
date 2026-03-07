import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_pipeline_emits_progress_and_result_events():
    events = []

    with patch("services.pipeline.brave_search", new_callable=AsyncMock) as mock_search, \
         patch("services.pipeline.fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch("services.pipeline.verify_claim", new_callable=AsyncMock) as mock_verify:

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

        from services.pipeline import run_pipeline
        async for event in run_pipeline("some claim", "en"):
            events.append(event)

    event_types = [e["type"] for e in events]
    assert "progress" in event_types
    assert "result" in event_types
    assert not any(e["type"] == "error" for e in events)


@pytest.mark.asyncio
async def test_pipeline_emits_three_progress_steps():
    events = []

    with patch("services.pipeline.brave_search", new_callable=AsyncMock) as mock_search, \
         patch("services.pipeline.fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch("services.pipeline.verify_claim", new_callable=AsyncMock) as mock_verify:

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

        from services.pipeline import run_pipeline
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

    with patch("services.pipeline.brave_search", new_callable=AsyncMock) as mock_search, \
         patch("services.pipeline.fetch_all", new_callable=AsyncMock) as mock_fetch:

        mock_search.return_value = []
        mock_fetch.return_value = []

        from services.pipeline import run_pipeline
        async for event in run_pipeline("obscure claim", "en"):
            events.append(event)

    assert any(e["type"] == "error" for e in events)
    assert not any(e["type"] == "result" for e in events)


@pytest.mark.asyncio
async def test_pipeline_emits_error_on_verify_exception():
    events = []

    with patch("services.pipeline.brave_search", new_callable=AsyncMock) as mock_search, \
         patch("services.pipeline.fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch("services.pipeline.verify_claim", new_callable=AsyncMock) as mock_verify:

        mock_search.return_value = [
            {"url": "https://www.moh.gov.sg/a", "title": "MOH", "snippet": "info"}
        ]
        mock_fetch.return_value = [
            {"url": "https://www.moh.gov.sg/a", "markdown": "Content"}
        ]
        mock_verify.side_effect = Exception("OpenAI API error")

        from services.pipeline import run_pipeline
        async for event in run_pipeline("some claim", "en"):
            events.append(event)

    assert any(e["type"] == "error" for e in events)
