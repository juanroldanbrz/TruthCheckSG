from unittest.mock import AsyncMock, patch

import pytest

from tests.e2e.utils import collect_stream_events, make_pipeline, make_result


@pytest.mark.asyncio
async def test_verdict_explanation_is_present_in_result_event(app_client):
    result = make_result(explanation="• Official sources disagree\n• No evidence supports it\n• The claim is false")

    with (
        patch("fact_verifier.main.run_pipeline", make_pipeline([{"type": "result", "data": result}])),
        patch("fact_verifier.main.save_verification", AsyncMock(return_value="share-explained")),
    ):
        response = await app_client.post("/verify", data={"text": "Donald Trump is the president of Singapore", "language": "en"})
        task_id = response.json()["task_id"]
        events = await collect_stream_events(app_client, task_id)

    explanation = events[-1]["data"]["data"]["explanation"].strip()
    assert explanation
    assert explanation.count("• ") == 3
