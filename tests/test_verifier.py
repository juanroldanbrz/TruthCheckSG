import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

MOCK_SOURCES = [
    {
        "url": "https://www.moh.gov.sg/advisory",
        "title": "MOH Advisory",
        "tier": "government",
        "snippet": "No such policy has been announced.",
        "markdown": "The Ministry of Health has not announced any change to CPF withdrawal age.",
    }
]

MOCK_GPT_RESPONSE = json.dumps({
    "verdict": "false",
    "summary": "This claim is not supported by official sources.",
    "explanation": "The Ministry of Health has not announced any such policy change.",
    "sources": [
        {
            "url": "https://www.moh.gov.sg/advisory",
            "title": "MOH Advisory",
            "tier": "government",
            "credibility_label": "Official Government Source",
            "stance": "contradicts",
            "snippet": "No such policy has been announced.",
        }
    ],
})


@pytest.mark.asyncio
async def test_verify_returns_structured_result():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = MOCK_GPT_RESPONSE

    with patch("fact_verifier.services.verifier.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from fact_verifier.services.verifier import verify_claim
        result = await verify_claim("CPF age raised to 70", MOCK_SOURCES, "en")
        assert result["verdict"] in ("true", "likely_true", "false", "likely_false", "unverified")
        assert "summary" in result
        assert "explanation" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)


@pytest.mark.asyncio
async def test_verify_passes_language_to_prompt():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = MOCK_GPT_RESPONSE

    with patch("fact_verifier.services.verifier.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from fact_verifier.services.verifier import verify_claim
        await verify_claim("some claim", MOCK_SOURCES, "zh")
        call_args = mock_create.call_args
        system_content = call_args.kwargs["messages"][0]["content"]
        assert "Simplified Chinese" in system_content


@pytest.mark.asyncio
async def test_verify_raises_on_invalid_json():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "not valid json"

    with patch("fact_verifier.services.verifier.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from fact_verifier.services.verifier import verify_claim
        with pytest.raises(Exception):
            await verify_claim("some claim", MOCK_SOURCES, "en")


@pytest.mark.asyncio
async def test_verify_handles_markdown_fenced_json():
    fenced_response = f"```json\n{MOCK_GPT_RESPONSE}\n```"
    mock_response = MagicMock()
    mock_response.choices[0].message.content = fenced_response

    with patch("fact_verifier.services.verifier.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from fact_verifier.services.verifier import verify_claim
        result = await verify_claim("CPF age raised to 70", MOCK_SOURCES, "en")
        assert result["verdict"] == "false"
        assert "summary" in result


@pytest.mark.asyncio
async def test_parse_claim_with_image_sends_multimodal_message():
    """When image_bytes provided, parse_claim must send a list content (text + image_url)."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({"is_relevant": True, "search_query": "investment scam"})

    with patch("fact_verifier.services.verifier.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from fact_verifier.services.verifier import parse_claim
        await parse_claim("is this an investment scam?", "en", image_bytes=b"fakebytes", image_content_type="image/jpeg")

        call_args = mock_create.call_args
        user_message = call_args.kwargs["messages"][1]
        assert isinstance(user_message["content"], list), "User message content must be a list for multimodal input"
        content_types = [part["type"] for part in user_message["content"]]
        assert "image_url" in content_types, "Image URL part must be present in multimodal message"
        assert "text" in content_types, "Text part must be present in multimodal message"


@pytest.mark.asyncio
async def test_parse_claim_with_image_and_question_returns_relevant():
    """Image + question combo must be marked as relevant (not rejected as a bare question)."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({"is_relevant": True, "search_query": "investment scam Singapore Telegram"})

    with patch("fact_verifier.services.verifier.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from fact_verifier.services.verifier import parse_claim
        result = await parse_claim("is this an investment scam?", "en", image_bytes=b"fakebytes", image_content_type="image/jpeg")
        assert result["is_relevant"] is True


@pytest.mark.asyncio
async def test_verify_claim_with_image_sends_multimodal_message():
    """When image_bytes provided, verify_claim must include the image in the user message."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = MOCK_GPT_RESPONSE

    with patch("fact_verifier.services.verifier.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from fact_verifier.services.verifier import verify_claim
        await verify_claim(
            "is this an investment scam?",
            MOCK_SOURCES,
            "en",
            image_bytes=b"fakebytes",
            image_content_type="image/jpeg",
        )

        call_args = mock_create.call_args
        user_message = call_args.kwargs["messages"][1]
        assert isinstance(user_message["content"], list), "User message content must be a list for multimodal input"
        content_types = [part["type"] for part in user_message["content"]]
        assert "image_url" in content_types
