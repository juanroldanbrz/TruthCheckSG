import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_analyze_image_returns_ocr_and_intent():
    mock_analysis = MagicMock()
    mock_analysis.ocr_text = "I am a real estate agent"
    mock_analysis.intent = "Promote a paid course to become a millionaire"

    mock_parsed = MagicMock()
    mock_parsed.choices = [MagicMock(message=MagicMock(parsed=mock_analysis))]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_parsed)

    with patch("fact_verifier.services.ocr.get_client", return_value=mock_client):
        from fact_verifier.services.ocr import analyze_image
        result = await analyze_image(b"fake-bytes", "image/jpeg")

    assert result is not None
    assert result.ocr_text == "I am a real estate agent"
    assert result.intent == "Promote a paid course to become a millionaire"


@pytest.mark.asyncio
async def test_analyze_image_returns_none_on_exception():
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(side_effect=Exception("API error"))

    with patch("fact_verifier.services.ocr.get_client", return_value=mock_client):
        from fact_verifier.services.ocr import analyze_image
        result = await analyze_image(b"fake-bytes", "image/jpeg")

    assert result is None