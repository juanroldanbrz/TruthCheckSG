from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_share_page_renders_saved_result(app_client):
    share_id = "share-abc"
    saved_doc = {
        "share_id": share_id,
        "claim": "The president of Singapore is Donald Trump",
        "result": {
            "verdict": "false",
            "summary": "This claim is false.",
            "explanation": "• Point 1\n• Point 2\n• Point 3",
            "sources": [],
        },
        "image_bytes": None,
    }

    with patch("fact_verifier.main.get_verification", AsyncMock(return_value=saved_doc)):
        response = await app_client.get(f"/share/{share_id}")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "The president of Singapore is Donald Trump" in response.text
    assert "This claim is false." in response.text


@pytest.mark.asyncio
async def test_share_image_returns_saved_binary(app_client):
    image_bytes = b"fake-image"

    with patch("fact_verifier.main.get_verification_image", AsyncMock(return_value=(image_bytes, "image/jpeg"))):
        response = await app_client.get("/share/share-abc/image")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == image_bytes
