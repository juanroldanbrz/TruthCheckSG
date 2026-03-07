import io
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from fact_verifier.services.ocr import ImageAnalysis


def make_analysis(ocr_text="Agent text", intent="Sell a course"):
    return ImageAnalysis(ocr_text=ocr_text, intent=intent)


async def aiter(items):
    for item in items:
        yield item


@pytest.mark.asyncio
async def test_image_only_builds_claim_with_explicit_labels():
    import asyncio
    analysis = make_analysis("I am a real estate agent", "Sell a millionaire course")

    captured = {}

    async def fake_pipeline(claim, language, image_bytes=None, image_content_type=None):
        captured["claim"] = claim
        captured["image_bytes"] = image_bytes
        return
        yield  # make it an async generator

    with (
        patch("fact_verifier.main.analyze_image", AsyncMock(return_value=analysis)),
        patch("fact_verifier.main.run_pipeline", fake_pipeline),
        patch("fact_verifier.main.describe_image", AsyncMock(return_value="an agent photo")),
    ):
        from fact_verifier.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/verify",
                data={"text": "", "language": "en"},
                files={"image": ("test.jpg", io.BytesIO(b"fake"), "image/jpeg")},
            )
        await asyncio.sleep(0.2)

    assert response.status_code == 200
    assert "Image text:" in captured["claim"]
    assert "Image intent:" in captured["claim"]
    assert captured["image_bytes"] is not None  # image must reach pipeline


@pytest.mark.asyncio
async def test_image_plus_text_appends_image_context():
    import asyncio
    analysis = make_analysis("Free money scheme", "Scam to collect personal data")

    captured = {}

    async def fake_pipeline(claim, language, image_bytes=None, image_content_type=None):
        captured["claim"] = claim
        return
        yield

    with (
        patch("fact_verifier.main.analyze_image", AsyncMock(return_value=analysis)),
        patch("fact_verifier.main.run_pipeline", fake_pipeline),
    ):
        from fact_verifier.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/verify",
                data={"text": "Is this a scam?", "language": "en"},
                files={"image": ("test.jpg", io.BytesIO(b"fake"), "image/jpeg")},
            )
        await asyncio.sleep(0.1)

    assert response.status_code == 200
    assert "Is this a scam?" in captured["claim"]
    assert "Image text:" in captured["claim"]
    assert "Image intent:" in captured["claim"]