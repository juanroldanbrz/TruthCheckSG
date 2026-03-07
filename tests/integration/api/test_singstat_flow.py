from unittest.mock import AsyncMock, patch

import pytest

from tests.e2e.utils import collect_stream_events


@pytest.mark.asyncio
async def test_verify_stream_includes_singstat_provider_metadata(app_client):
    singstat_source = {
        "url": "https://tablebuilder.singstat.gov.sg/api/table/metadata/M810001",
        "title": "Indicators On Population, Annual",
        "tier": "government",
        "snippet": "SingStat reports Resident Population at 4,180,868 in 2024.",
        "markdown": "SingStat table: Indicators On Population, Annual",
        "provider": "singstat",
        "provider_label": "SingStat",
    }

    with (
        patch("fact_verifier.services.pipeline.parse_claim", AsyncMock(return_value={"is_relevant": True, "search_query": "singapore resident population 2024"})),
        patch("fact_verifier.services.pipeline.get_singstat_sources_for_claim", AsyncMock(return_value=([singstat_source], {"category": "demographics"}))),
        patch("fact_verifier.services.pipeline.brave_search", AsyncMock(return_value=[])),
        patch("fact_verifier.services.pipeline.fetch_all", AsyncMock(return_value=[])),
        patch(
            "fact_verifier.services.pipeline.verify_claim",
            AsyncMock(
                return_value={
                    "verdict": "true",
                    "summary": "The claim matches SingStat data.",
                    "explanation": "• Official statistics support the claim\n• The 2024 figure matches the claim\n• SingStat is the authoritative source",
                    "sources": [
                        {
                            "url": singstat_source["url"],
                            "title": singstat_source["title"],
                            "tier": "government",
                            "credibility_label": "Official Government Source",
                            "stance": "supports",
                            "snippet": singstat_source["snippet"],
                            "provider": "singstat",
                            "provider_label": "SingStat",
                        }
                    ],
                }
            ),
        ),
        patch("fact_verifier.main.save_verification", AsyncMock(return_value="share-singstat")),
    ):
        response = await app_client.post("/verify", data={"text": "Singapore resident population was 4.18 million in 2024.", "language": "en"})
        task_id = response.json()["task_id"]
        events = await collect_stream_events(app_client, task_id)

    result_event = events[-1]["data"]
    assert result_event["share_id"] == "share-singstat"
    assert result_event["data"]["sources"][0]["provider"] == "singstat"
    assert result_event["data"]["sources"][0]["provider_label"] == "SingStat"
