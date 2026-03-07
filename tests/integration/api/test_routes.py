import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_home_returns_200():
    from fact_verifier.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_verify_text_returns_task_id():
    from fact_verifier.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/verify", data={"text": "CPF age raised to 70", "language": "en"})
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert len(data["task_id"]) > 0


@pytest.mark.asyncio
async def test_verify_empty_text_returns_422():
    from fact_verifier.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/verify", data={"text": "", "language": "en"})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_stream_unknown_task_returns_404():
    from fact_verifier.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/stream/nonexistent-task-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_verify_image_with_text_preserves_text_query():
    """When both image and text are submitted, the text query must NOT be discarded."""
    import asyncio
    from fact_verifier.main import app
    from fact_verifier.services.ocr import ImageAnalysis

    async def fake_pipeline(*args, **kwargs):
        return
        yield  # make it an async generator

    fake_analysis = ImageAnalysis(ocr_text="some text", intent="some intent")
    with (
        patch("fact_verifier.main.analyze_image", AsyncMock(return_value=fake_analysis)),
        patch("fact_verifier.main.run_pipeline", side_effect=fake_pipeline) as mock_pipeline,
    ):
        fake_image = b"\xff\xd8\xff"  # minimal JPEG header
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/verify",
                files={"image": ("scam.jpg", fake_image, "image/jpeg")},
                data={"text": "is this an investment scam?", "language": "en"},
            )

        assert response.status_code == 200
        # Let the background task run
        await asyncio.sleep(0.1)
        call_args = mock_pipeline.call_args
        assert call_args is not None, "run_pipeline was never called"
        claim_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("claim")
        assert "is this an investment scam?" in claim_arg, f"Expected text query to be preserved, got: {claim_arg!r}"


@pytest.mark.asyncio
async def test_verify_image_with_text_passes_image_bytes_to_pipeline():
    """Image bytes must be forwarded to run_pipeline when image is uploaded."""
    import asyncio
    from fact_verifier.main import app
    from fact_verifier.services.ocr import ImageAnalysis

    async def fake_pipeline(*args, **kwargs):
        return
        yield

    fake_analysis = ImageAnalysis(ocr_text="some text", intent="some intent")
    with (
        patch("fact_verifier.main.analyze_image", AsyncMock(return_value=fake_analysis)),
        patch("fact_verifier.main.run_pipeline", side_effect=fake_pipeline) as mock_pipeline,
    ):
        fake_image = b"\xff\xd8\xff"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/verify",
                files={"image": ("scam.jpg", fake_image, "image/jpeg")},
                data={"text": "is this an investment scam?", "language": "en"},
            )

        await asyncio.sleep(0.1)
        assert mock_pipeline.call_args is not None, "run_pipeline was never called"
        call_kwargs = mock_pipeline.call_args.kwargs
        assert call_kwargs.get("image_bytes") == fake_image
        assert call_kwargs.get("image_content_type") == "image/jpeg"


@pytest.mark.asyncio
async def test_verify_link_submission_uses_direct_link_pathway():
    import asyncio
    from fact_verifier.main import app

    direct_source = {
        "url": "https://www.cpf.gov.sg/article",
        "title": "CPF interest rates remain unchanged",
        "snippet": "CPF interest rates remain unchanged this quarter.",
        "markdown": "CPF Board said interest rates remain unchanged this quarter.",
        "tier": "government",
    }
    verify_result = {
        "verdict": "true",
        "summary": "The article matches official guidance.",
        "explanation": "• Point 1\n• Point 2\n• Point 3",
        "sources": [
            {
                "url": direct_source["url"],
                "title": direct_source["title"],
                "tier": "government",
                "credibility_label": "Official source",
                "stance": "supports",
                "snippet": "CPF Board said interest rates remain unchanged this quarter.",
            }
        ],
    }

    with (
        patch("fact_verifier.services.pipeline.fetch_direct_source", AsyncMock(return_value=direct_source)) as mock_direct_fetch,
        patch("fact_verifier.services.pipeline.parse_claim", AsyncMock(return_value={"is_relevant": True, "search_query": "cpf interest rates singapore"})),
        patch("fact_verifier.services.pipeline.brave_search", AsyncMock(return_value=[])),
        patch("fact_verifier.services.pipeline.fetch_all", AsyncMock(return_value=[])),
        patch("fact_verifier.services.pipeline.get_singstat_sources_for_claim", AsyncMock(return_value=([], {"category": None}))) as mock_singstat,
        patch("fact_verifier.services.pipeline.verify_claim", AsyncMock(return_value=verify_result)),
        patch("fact_verifier.main.save_verification", AsyncMock(return_value="share-123")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/verify", data={"text": "https://www.cpf.gov.sg/article", "language": "en"})
            assert response.status_code == 200
            task_id = response.json()["task_id"]

            await asyncio.sleep(0.05)
            stream_response = await client.get(f"/stream/{task_id}")

    assert stream_response.status_code == 200
    assert "event: result" in stream_response.text
    assert '"share_id": "share-123"' in stream_response.text
    mock_direct_fetch.assert_awaited_once_with("https://www.cpf.gov.sg/article")
    mock_singstat.assert_not_called()
