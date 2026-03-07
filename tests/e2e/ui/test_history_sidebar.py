from unittest.mock import AsyncMock, patch

import pytest

from tests.e2e.utils import collect_stream_events, make_pipeline, make_result


@pytest.mark.asyncio
async def test_stream_emits_progress_then_result(app_client):
    events = [
        {"type": "progress", "step": 1, "message": "step_1"},
        {"type": "progress", "step": 2, "message": "step_2"},
        {"type": "result", "data": make_result(summary="Singapore is a city-state in Southeast Asia.")},
    ]

    with (
        patch("fact_verifier.main.run_pipeline", make_pipeline(events)),
        patch("fact_verifier.main.save_verification", AsyncMock(return_value="share-123")),
    ):
        response = await app_client.post("/verify", data={"text": "Singapore is a city-state in Southeast Asia", "language": "en"})

        assert response.status_code == 200
        task_id = response.json()["task_id"]
        streamed_events = await collect_stream_events(app_client, task_id)

    assert [event["event"] for event in streamed_events] == ["progress", "progress", "result"]
    assert streamed_events[-1]["data"]["share_id"] == "share-123"
    assert streamed_events[-1]["data"]["claim"] == "Singapore is a city-state in Southeast Asia"
    assert streamed_events[-1]["data"]["has_image"] is False


@pytest.mark.asyncio
async def test_stream_cleans_up_task_queue_after_completion(app_client):
    from fact_verifier import main

    events = [{"type": "result", "data": make_result(summary="The Merlion is a symbol of Singapore.")}]

    with (
        patch("fact_verifier.main.run_pipeline", make_pipeline(events)),
        patch("fact_verifier.main.save_verification", AsyncMock(return_value="share-456")),
    ):
        response = await app_client.post("/verify", data={"text": "The Merlion is a symbol of Singapore", "language": "en"})

        task_id = response.json()["task_id"]
        assert task_id in main._task_queues

        streamed_events = await collect_stream_events(app_client, task_id)

    assert streamed_events[-1]["data"]["share_id"] == "share-456"
    assert task_id not in main._task_queues
    assert task_id not in main._task_timestamps
