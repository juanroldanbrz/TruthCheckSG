import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fact_verifier.services.verifier import FactCheckResult, SourceResult, ClaimParseResult

MOCK_SOURCE = SourceResult(
    url="https://www.moh.gov.sg/advisory",
    title="MOH Advisory",
    tier="government",
    credibility_label="Official Government Source",
    stance="contradicts",
    snippet="No such policy has been announced.",
)

MOCK_FACT_CHECK = FactCheckResult(
    verdict="false",
    summary="This claim is not supported by official sources.",
    explanation="• Point 1\n• Point 2\n• Point 3",
    sources=[MOCK_SOURCE],
)

MOCK_SOURCES = [
    {
        "url": "https://www.moh.gov.sg/advisory",
        "title": "MOH Advisory",
        "tier": "government",
        "snippet": "No such policy has been announced.",
        "markdown": "The Ministry of Health has not announced any change to CPF withdrawal age.",
    }
]


def _make_parse_response(parsed):
    mock_response = MagicMock()
    mock_response.choices[0].message.parsed = parsed
    return mock_response


def _make_mock_client(parsed=None, *, side_effect=None):
    mock_client = MagicMock()
    mock_parse = AsyncMock(side_effect=side_effect)
    if side_effect is None:
        mock_parse.return_value = _make_parse_response(parsed)
    mock_client.beta.chat.completions.parse = mock_parse
    return mock_client, mock_parse


@pytest.mark.asyncio
async def test_verify_returns_structured_result():
    mock_client, _ = _make_mock_client(MOCK_FACT_CHECK)
    with patch("fact_verifier.services.verifier.get_client", return_value=mock_client):
        from fact_verifier.services.verifier import verify_claim
        result = await verify_claim("CPF age raised to 70", MOCK_SOURCES, "en")
        assert result["verdict"] in ("true", "likely_true", "false", "likely_false", "unverified")
        assert "summary" in result
        assert "explanation" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)


@pytest.mark.asyncio
async def test_verify_passes_language_to_prompt():
    mock_client, mock_parse = _make_mock_client(MOCK_FACT_CHECK)
    with patch("fact_verifier.services.verifier.get_client", return_value=mock_client):
        from fact_verifier.services.verifier import verify_claim
        await verify_claim("some claim", MOCK_SOURCES, "zh")
        call_args = mock_parse.call_args
        system_content = call_args.kwargs["messages"][0]["content"]
        assert "Simplified Chinese" in system_content


@pytest.mark.asyncio
async def test_verify_raises_when_parsed_is_none():
    mock_client, _ = _make_mock_client(None)
    with patch("fact_verifier.services.verifier.get_client", return_value=mock_client):
        from fact_verifier.services.verifier import verify_claim
        with pytest.raises(Exception):
            await verify_claim("some claim", MOCK_SOURCES, "en")


@pytest.mark.asyncio
async def test_parse_claim_with_image_sends_multimodal_message():
    """When image_bytes provided, parse_claim must send a list content (text + image_url)."""
    mock_parsed = ClaimParseResult(is_relevant=True, search_query="investment scam")

    mock_client, mock_parse = _make_mock_client(mock_parsed)
    with patch("fact_verifier.services.verifier.get_client", return_value=mock_client):
        from fact_verifier.services.verifier import parse_claim
        await parse_claim("is this an investment scam?", "en", image_bytes=b"fakebytes", image_content_type="image/jpeg")

        call_args = mock_parse.call_args
        user_message = call_args.kwargs["messages"][1]
        assert isinstance(user_message["content"], list), "User message content must be a list for multimodal input"
        content_types = [part["type"] for part in user_message["content"]]
        assert "image_url" in content_types, "Image URL part must be present in multimodal message"
        assert "text" in content_types, "Text part must be present in multimodal message"


@pytest.mark.asyncio
async def test_parse_claim_with_image_and_question_returns_relevant():
    """Image + question combo must be marked as relevant (not rejected as a bare question)."""
    mock_parsed = ClaimParseResult(is_relevant=True, search_query="investment scam Singapore Telegram")

    mock_client, _ = _make_mock_client(mock_parsed)
    with patch("fact_verifier.services.verifier.get_client", return_value=mock_client):
        from fact_verifier.services.verifier import parse_claim
        result = await parse_claim("is this an investment scam?", "en", image_bytes=b"fakebytes", image_content_type="image/jpeg")
        assert result["is_relevant"] is True


@pytest.mark.asyncio
async def test_verify_claim_with_image_sends_multimodal_message():
    """When image_bytes provided, verify_claim must include the image in the user message."""
    mock_client, mock_parse = _make_mock_client(MOCK_FACT_CHECK)
    with patch("fact_verifier.services.verifier.get_client", return_value=mock_client):
        from fact_verifier.services.verifier import verify_claim
        await verify_claim(
            "is this an investment scam?",
            MOCK_SOURCES,
            "en",
            image_bytes=b"fakebytes",
            image_content_type="image/jpeg",
        )

        call_args = mock_parse.call_args
        user_message = call_args.kwargs["messages"][1]
        assert isinstance(user_message["content"], list), "User message content must be a list for multimodal input"
        content_types = [part["type"] for part in user_message["content"]]
        assert "image_url" in content_types
