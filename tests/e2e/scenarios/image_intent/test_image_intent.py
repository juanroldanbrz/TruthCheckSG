from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from fact_verifier.services.ocr import ImageAnalysis

from tests.e2e.utils import collect_stream_events, make_result

IMAGE_PATH = Path(__file__).parent / "fixtures" / "facebook_1.jpeg"


@pytest.mark.asyncio
async def test_image_only_backend_flow_includes_image_context(app_client):
    captured = {}
    analysis = ImageAnalysis(ocr_text="Visible Facebook post text", intent="Promote an investment scam")
    image_bytes = IMAGE_PATH.read_bytes()

    async def fake_pipeline(claim, language, image_bytes=None, image_content_type=None):
        captured["claim"] = claim
        captured["language"] = language
        captured["image_bytes"] = image_bytes
        captured["image_content_type"] = image_content_type
        yield {"type": "result", "data": make_result(summary="The uploaded image shows scam red flags.")}

    with (
        patch("fact_verifier.main.analyze_image", AsyncMock(return_value=analysis)),
        patch("fact_verifier.main.describe_image", AsyncMock(return_value="A Facebook post promoting an investment scheme.")),
        patch("fact_verifier.main.run_pipeline", side_effect=fake_pipeline),
        patch("fact_verifier.main.save_verification", AsyncMock(return_value="share-image-only")),
    ):
        response = await app_client.post(
            "/verify",
            data={"text": "", "language": "en"},
            files={"image": ("facebook_1.jpeg", image_bytes, "image/jpeg")},
        )
        task_id = response.json()["task_id"]
        events = await collect_stream_events(app_client, task_id)

    assert response.status_code == 200
    assert "Image text: Visible Facebook post text" in captured["claim"]
    assert "Image intent: Promote an investment scam" in captured["claim"]
    assert captured["language"] == "en"
    assert captured["image_bytes"] == image_bytes
    assert captured["image_content_type"] == "image/jpeg"
    assert events[-1]["data"]["has_image"] is True
    assert events[-1]["data"]["image_description"] == "A Facebook post promoting an investment scheme."
    assert events[-1]["data"]["share_id"] == "share-image-only"
