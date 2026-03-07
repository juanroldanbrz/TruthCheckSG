import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_extract_text_from_image_returns_string():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "CPF withdrawal age raised to 65"

    with patch("fact_verifier.services.ocr.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from fact_verifier.services.ocr import extract_text_from_image
        result = await extract_text_from_image(b"fake_image_bytes", "image/png")
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.asyncio
async def test_extract_text_returns_none_on_empty_response():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = ""

    with patch("fact_verifier.services.ocr.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from fact_verifier.services.ocr import extract_text_from_image
        result = await extract_text_from_image(b"fake_image_bytes", "image/png")
        assert result is None


@pytest.mark.asyncio
async def test_extract_text_returns_none_on_api_error():
    with patch("fact_verifier.services.ocr.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = Exception("API timeout")
        from fact_verifier.services.ocr import extract_text_from_image
        result = await extract_text_from_image(b"fake_image_bytes", "image/png")
        assert result is None
