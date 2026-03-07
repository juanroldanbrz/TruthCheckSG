import pytest
from unittest.mock import AsyncMock, patch

from fact_verifier.services import pipeline as pipeline_module


@pytest.mark.asyncio
async def test_pipeline_emits_progress_and_result_events():
    events = []

    with patch.object(pipeline_module, "parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch.object(pipeline_module, "brave_search", new_callable=AsyncMock) as mock_search, \
         patch.object(pipeline_module, "fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch.object(pipeline_module, "verify_claim", new_callable=AsyncMock) as mock_verify:
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

    with patch.object(pipeline_module, "parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch.object(pipeline_module, "brave_search", new_callable=AsyncMock) as mock_search, \
         patch.object(pipeline_module, "fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch.object(pipeline_module, "verify_claim", new_callable=AsyncMock) as mock_verify:
        mock_parse.return_value = {"is_relevant": True, "search_query": "CPF withdrawal age"}

        mock_search.return_value = [
            {"url": "https://www.moh.gov.sg/a", "title": "MOH", "snippet": "info"}
        ]
        mock_fetch.return_value = [
            {"url": "https://www.moh.gov.sg/a", "markdown": "Content here"}
        ]
        mock_verify.return_value = {
            "verdict": "true",
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

    with patch.object(pipeline_module, "parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch.object(pipeline_module, "brave_search", new_callable=AsyncMock) as mock_search, \
         patch.object(pipeline_module, "fetch_all", new_callable=AsyncMock) as mock_fetch:

        mock_parse.return_value = {"is_relevant": True, "search_query": "obscure claim"}
        mock_search.return_value = []
        mock_fetch.return_value = []

        from fact_verifier.services.pipeline import run_pipeline
        async for event in run_pipeline("obscure claim", "en"):
            events.append(event)

    assert any(e["type"] == "error" for e in events)
    assert not any(e["type"] == "result" for e in events)


@pytest.mark.asyncio
async def test_pipeline_falls_back_to_claim_when_search_query_returns_nothing():
    """When search_query returns no results but claim differs, pipeline retries with raw claim."""
    events = []

    with patch.object(pipeline_module, "parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch.object(pipeline_module, "brave_search", new_callable=AsyncMock) as mock_search, \
         patch.object(pipeline_module, "fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch.object(pipeline_module, "verify_claim", new_callable=AsyncMock) as mock_verify:

        mock_parse.return_value = {"is_relevant": True, "search_query": "very specific query different from claim"}
        mock_search.side_effect = [[], [{"url": "https://example.com", "title": "Example", "snippet": "info"}]]
        mock_fetch.return_value = [{"url": "https://example.com", "markdown": "Content"}]
        mock_verify.return_value = {"verdict": "false", "summary": "Not true.", "explanation": "Details.", "sources": []}

        from fact_verifier.services.pipeline import run_pipeline
        async for event in run_pipeline("some claim", "en"):
            events.append(event)

    assert any(e["type"] == "result" for e in events)
    assert not any(e["type"] == "error" for e in events)
    assert mock_search.call_count == 2


@pytest.mark.asyncio
async def test_pipeline_calls_singstat_for_router_approved_claims():
    events = []
    singstat_source = {
        "url": "https://tablebuilder.singstat.gov.sg/api/table/metadata/M810001",
        "title": "Indicators On Population, Annual",
        "tier": "government",
        "snippet": "SingStat reports Resident Population at 4,180,868 in 2024.",
        "markdown": "SingStat table: Indicators On Population, Annual",
        "provider": "singstat",
        "provider_label": "SingStat",
    }

    with patch.object(pipeline_module, "parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch.object(pipeline_module, "get_singstat_sources_for_claim", new_callable=AsyncMock) as mock_singstat, \
         patch.object(pipeline_module, "brave_search", new_callable=AsyncMock) as mock_search, \
         patch.object(pipeline_module, "fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch.object(pipeline_module, "verify_claim", new_callable=AsyncMock) as mock_verify:
        mock_parse.return_value = {"is_relevant": True, "search_query": "singapore resident population 2024"}
        mock_singstat.return_value = ([singstat_source], {"category": "demographics"})
        mock_search.return_value = []
        mock_fetch.return_value = []
        mock_verify.return_value = {
            "verdict": "true",
            "summary": "The claim matches SingStat data.",
            "explanation": "Details.",
            "sources": [singstat_source],
        }

        from fact_verifier.services.pipeline import run_pipeline
        async for event in run_pipeline("Singapore resident population was 4.18 million in 2024.", "en"):
            events.append(event)

    assert any(e["type"] == "result" for e in events)
    mock_singstat.assert_called_once()
    verify_sources = mock_verify.call_args.args[1]
    assert verify_sources[0]["provider"] == "singstat"


@pytest.mark.asyncio
async def test_pipeline_skips_singstat_when_router_rejects_claim():
    with patch.object(pipeline_module, "parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch.object(pipeline_module, "get_singstat_sources_for_claim", new_callable=AsyncMock) as mock_singstat, \
         patch.object(pipeline_module, "brave_search", new_callable=AsyncMock) as mock_search, \
         patch.object(pipeline_module, "fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch.object(pipeline_module, "verify_claim", new_callable=AsyncMock) as mock_verify:
        mock_parse.return_value = {"is_relevant": True, "search_query": "investment scam"}
        mock_singstat.return_value = ([], {"category": None})
        mock_search.return_value = [{"url": "https://www.police.gov.sg/a", "title": "SPF", "snippet": "alert"}]
        mock_fetch.return_value = [{"url": "https://www.police.gov.sg/a", "markdown": "Alert"}]
        mock_verify.return_value = {"verdict": "false", "summary": "Scam.", "explanation": "Details.", "sources": []}

        from fact_verifier.services.pipeline import run_pipeline
        async for _ in run_pipeline("Is this an investment scam?", "en"):
            pass

    assert mock_singstat.call_count == 1
    verify_sources = mock_verify.call_args.args[1]
    assert all(source.get("provider") != "singstat" for source in verify_sources)


@pytest.mark.asyncio
async def test_pipeline_preserves_singstat_metadata_in_result_sources():
    singstat_source = {
        "url": "https://tablebuilder.singstat.gov.sg/api/table/metadata/M213811",
        "title": "Percent Change In Consumer Price Index (CPI) Over Corresponding Period Of Previous Year, 2024 As Base Year, Annual",
        "tier": "government",
        "snippet": "SingStat reports All Items at 2.4 in 2024.",
        "markdown": "SingStat table: CPI annual change",
        "provider": "singstat",
        "provider_label": "SingStat",
    }

    with patch.object(pipeline_module, "parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch.object(pipeline_module, "get_singstat_sources_for_claim", new_callable=AsyncMock) as mock_singstat, \
         patch.object(pipeline_module, "brave_search", new_callable=AsyncMock) as mock_search, \
         patch.object(pipeline_module, "fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch.object(pipeline_module, "verify_claim", new_callable=AsyncMock) as mock_verify:
        mock_parse.return_value = {"is_relevant": True, "search_query": "singapore inflation cpi 2024"}
        mock_singstat.return_value = ([singstat_source], {"category": "prices_inflation"})
        mock_search.return_value = []
        mock_fetch.return_value = []
        mock_verify.return_value = {
            "verdict": "likely_true",
            "summary": "Inflation rose.",
            "explanation": "Details.",
            "sources": [singstat_source],
        }

        from fact_verifier.services.pipeline import run_pipeline
        events = [event async for event in run_pipeline("Singapore CPI rose in 2024.", "en")]

    result_event = next(event for event in events if event["type"] == "result")
    assert result_event["data"]["sources"][0]["provider"] == "singstat"
    assert result_event["data"]["sources"][0]["provider_label"] == "SingStat"


@pytest.mark.asyncio
async def test_pipeline_passes_image_to_parse_claim():
    """run_pipeline must pass image_bytes and image_content_type to parse_claim."""
    with patch.object(pipeline_module, "parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch.object(pipeline_module, "brave_search", new_callable=AsyncMock) as mock_search, \
         patch.object(pipeline_module, "fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch.object(pipeline_module, "verify_claim", new_callable=AsyncMock) as mock_verify:

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
    with patch.object(pipeline_module, "parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch.object(pipeline_module, "brave_search", new_callable=AsyncMock) as mock_search, \
         patch.object(pipeline_module, "fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch.object(pipeline_module, "verify_claim", new_callable=AsyncMock) as mock_verify:

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

    with patch.object(pipeline_module, "parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch.object(pipeline_module, "brave_search", new_callable=AsyncMock) as mock_search, \
         patch.object(pipeline_module, "fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch.object(pipeline_module, "verify_claim", new_callable=AsyncMock) as mock_verify:

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


@pytest.mark.asyncio
async def test_pipeline_uses_direct_link_pathway_for_url_submissions():
    direct_source = {
        "url": "https://www.cpf.gov.sg/article",
        "title": "CPF interest rates remain unchanged",
        "snippet": "CPF interest rates remain unchanged this quarter.",
        "markdown": "CPF Board said interest rates remain unchanged this quarter.",
        "tier": "government",
    }

    with patch.object(pipeline_module, "fetch_direct_source", new_callable=AsyncMock) as mock_direct_fetch, \
         patch.object(pipeline_module, "parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch.object(pipeline_module, "brave_search", new_callable=AsyncMock) as mock_search, \
         patch.object(pipeline_module, "fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch.object(pipeline_module, "get_singstat_sources_for_claim", new_callable=AsyncMock) as mock_singstat, \
         patch.object(pipeline_module, "verify_claim", new_callable=AsyncMock) as mock_verify:
        mock_direct_fetch.return_value = direct_source
        mock_parse.return_value = {"is_relevant": True, "search_query": "cpf interest rates singapore"}
        mock_search.return_value = []
        mock_fetch.return_value = []
        mock_verify.return_value = {"verdict": "true", "summary": "True.", "explanation": "Details.", "sources": []}

        from fact_verifier.services.pipeline import run_pipeline
        events = [event async for event in run_pipeline("https://www.cpf.gov.sg/article", "en")]

    assert any(event["type"] == "result" for event in events)
    mock_direct_fetch.assert_awaited_once_with("https://www.cpf.gov.sg/article")
    mock_singstat.assert_not_called()
    assert mock_verify.call_args.args[0] == "CPF interest rates remain unchanged"
    verify_sources = mock_verify.call_args.args[1]
    assert verify_sources[0]["url"] == "https://www.cpf.gov.sg/article"


@pytest.mark.asyncio
async def test_pipeline_falls_back_to_standard_flow_when_direct_fetch_fails():
    with patch.object(pipeline_module, "fetch_direct_source", new_callable=AsyncMock) as mock_direct_fetch, \
         patch.object(pipeline_module, "parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch.object(pipeline_module, "get_singstat_sources_for_claim", new_callable=AsyncMock) as mock_singstat, \
         patch.object(pipeline_module, "brave_search", new_callable=AsyncMock) as mock_search, \
         patch.object(pipeline_module, "fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch.object(pipeline_module, "verify_claim", new_callable=AsyncMock) as mock_verify:
        mock_direct_fetch.return_value = None
        mock_parse.return_value = {"is_relevant": True, "search_query": "cpf clarification"}
        mock_singstat.return_value = ([], {"category": None})
        mock_search.return_value = [{"url": "https://www.cpf.gov.sg/article", "title": "CPF", "snippet": "info"}]
        mock_fetch.return_value = [{"url": "https://www.cpf.gov.sg/article", "markdown": "Content"}]
        mock_verify.return_value = {"verdict": "true", "summary": "True.", "explanation": "Details.", "sources": []}

        from fact_verifier.services.pipeline import run_pipeline
        events = [event async for event in run_pipeline("https://www.cpf.gov.sg/article", "en")]

    assert any(event["type"] == "result" for event in events)
    mock_direct_fetch.assert_awaited_once_with("https://www.cpf.gov.sg/article")
    mock_singstat.assert_awaited_once()
    mock_parse.assert_awaited_once_with("https://www.cpf.gov.sg/article", "en", image_bytes=None, image_content_type=None)


@pytest.mark.asyncio
async def test_pipeline_dedupes_direct_link_against_search_results():
    direct_source = {
        "url": "https://www.cpf.gov.sg/article",
        "title": "CPF article",
        "snippet": "Direct article content.",
        "markdown": "Direct article content.",
        "tier": "government",
    }

    with patch.object(pipeline_module, "fetch_direct_source", new_callable=AsyncMock) as mock_direct_fetch, \
         patch.object(pipeline_module, "parse_claim", new_callable=AsyncMock) as mock_parse, \
         patch.object(pipeline_module, "brave_search", new_callable=AsyncMock) as mock_search, \
         patch.object(pipeline_module, "fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch.object(pipeline_module, "verify_claim", new_callable=AsyncMock) as mock_verify:
        mock_direct_fetch.return_value = direct_source
        mock_parse.return_value = {"is_relevant": True, "search_query": "cpf article"}
        mock_search.return_value = [{"url": "https://www.cpf.gov.sg/article", "title": "CPF article", "snippet": "Search snippet"}]
        mock_fetch.return_value = [{"url": "https://www.cpf.gov.sg/article", "markdown": "Fetched duplicate content"}]
        mock_verify.return_value = {"verdict": "true", "summary": "True.", "explanation": "Details.", "sources": []}

        from fact_verifier.services.pipeline import run_pipeline
        events = [event async for event in run_pipeline("https://www.cpf.gov.sg/article", "en")]

    assert any(event["type"] == "result" for event in events)
    verify_sources = mock_verify.call_args.args[1]
    assert len(verify_sources) == 1
    assert verify_sources[0]["url"] == "https://www.cpf.gov.sg/article"
