import pytest
from unittest.mock import AsyncMock, patch

from tests.e2e.utils import collect_stream_events, make_result

CLAIM = "Donald Trump is the president of Singapore"


@pytest.mark.parametrize("lang", ["en", "zh", "ms", "ta"])
@pytest.mark.asyncio
async def test_donald_trump_sg_president_backend_flow(app_client, lang: str):
    calls = []

    async def fake_pipeline(claim, language, image_bytes=None, image_content_type=None):
        calls.append(
            {
                "claim": claim,
                "language": language,
                "image_bytes": image_bytes,
                "image_content_type": image_content_type,
            }
        )
        yield {"type": "progress", "step": 1, "message": "step_1"}
        yield {"type": "result", "data": make_result(summary="This claim is false.")}

    with (
        patch("fact_verifier.main.run_pipeline", side_effect=fake_pipeline),
        patch("fact_verifier.main.save_verification", AsyncMock(return_value=f"share-{lang}")),
    ):
        response = await app_client.post("/verify", data={"text": CLAIM, "language": lang})

        assert response.status_code == 200
        task_id = response.json()["task_id"]
        events = await collect_stream_events(app_client, task_id)

    assert calls == [
        {
            "claim": CLAIM,
            "language": lang,
            "image_bytes": None,
            "image_content_type": None,
        }
    ]
    assert [event["event"] for event in events] == ["progress", "result"]
    assert events[-1]["data"]["share_id"] == f"share-{lang}"
    assert events[-1]["data"]["claim"] == CLAIM
    assert events[-1]["data"]["data"]["verdict"] == "false"
