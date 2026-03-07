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

    with patch("services.verifier.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from services.verifier import verify_claim
        result = await verify_claim("CPF age raised to 70", MOCK_SOURCES, "en")
        assert result["verdict"] in ("verified", "false", "unverified")
        assert "summary" in result
        assert "explanation" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)


@pytest.mark.asyncio
async def test_verify_passes_language_to_prompt():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = MOCK_GPT_RESPONSE

    with patch("services.verifier.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from services.verifier import verify_claim
        await verify_claim("some claim", MOCK_SOURCES, "zh")
        call_args = mock_create.call_args
        system_content = call_args.kwargs["messages"][0]["content"]
        assert "Simplified Chinese" in system_content


@pytest.mark.asyncio
async def test_verify_raises_on_invalid_json():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "not valid json"

    with patch("services.verifier.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from services.verifier import verify_claim
        with pytest.raises(Exception):
            await verify_claim("some claim", MOCK_SOURCES, "en")
