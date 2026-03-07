import pathlib
import pytest
from unittest.mock import AsyncMock, patch

from fact_verifier.services.ocr import ImageAnalysis

from tests.e2e.utils import collect_stream_events, make_result

IMAGE_PATH = pathlib.Path(__file__).parent / "fixtures" / "investment_scam.jpeg"
QUERY = "is this an investment scam?"


@pytest.mark.asyncio
async def test_investment_scam_backend_flow_preserves_query_and_image(app_client):
    captured = {}
    analysis = ImageAnalysis(
        ocr_text="Telegram chat promising high returns",
        intent="Convince the viewer to join a suspicious investment group",
    )
    image_bytes = IMAGE_PATH.read_bytes()

    async def fake_pipeline(claim, language, image_bytes=None, image_content_type=None):
        captured["claim"] = claim
        captured["language"] = language
        captured["image_bytes"] = image_bytes
        captured["image_content_type"] = image_content_type
        yield {"type": "progress", "step": 1, "message": "step_1"}
        yield {"type": "result", "data": make_result(summary="This looks like a likely investment scam.")}

    with (
        patch("fact_verifier.main.analyze_image", AsyncMock(return_value=analysis)),
        patch("fact_verifier.main.run_pipeline", side_effect=fake_pipeline),
        patch("fact_verifier.main.save_verification", AsyncMock(return_value="share-investment")),
    ):
        response = await app_client.post(
            "/verify",
            data={"text": QUERY, "language": "en"},
            files={"image": ("investment_scam.jpeg", image_bytes, "image/jpeg")},
        )
        task_id = response.json()["task_id"]
        events = await collect_stream_events(app_client, task_id)

    assert response.status_code == 200
    assert QUERY in captured["claim"]
    assert "Image text: Telegram chat promising high returns" in captured["claim"]
    assert "Image intent: Convince the viewer to join a suspicious investment group" in captured["claim"]
    assert captured["language"] == "en"
    assert captured["image_bytes"] == image_bytes
    assert captured["image_content_type"] == "image/jpeg"
    assert [event["event"] for event in events] == ["progress", "result"]
    assert events[-1]["data"]["share_id"] == "share-investment"
    assert events[-1]["data"]["has_image"] is True
