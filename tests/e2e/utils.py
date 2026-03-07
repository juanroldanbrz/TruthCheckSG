from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable

from httpx import AsyncClient


def make_result(
    *,
    verdict: str = "false",
    summary: str = "This claim is not supported.",
    explanation: str = "• Point 1\n• Point 2\n• Point 3",
    sources: list[dict] | None = None,
) -> dict:
    return {
        "verdict": verdict,
        "summary": summary,
        "explanation": explanation,
        "sources": sources or [],
    }


def make_pipeline(events: Iterable[dict]):
    async def _pipeline(*args, **kwargs) -> AsyncIterator[dict]:
        for event in events:
            yield event

    return _pipeline


def parse_sse_events(payload: str) -> list[dict]:
    events: list[dict] = []
    event_name: str | None = None
    data_lines: list[str] = []

    for line in payload.splitlines():
        if line.startswith("event: "):
            event_name = line.removeprefix("event: ")
        elif line.startswith("data: "):
            data_lines.append(line.removeprefix("data: "))
        elif line == "" and event_name is not None:
            raw_data = "\n".join(data_lines)
            events.append({"event": event_name, "data": json.loads(raw_data)})
            event_name = None
            data_lines = []

    if event_name is not None:
        raw_data = "\n".join(data_lines)
        events.append({"event": event_name, "data": json.loads(raw_data)})

    return events


async def collect_stream_events(client: AsyncClient, task_id: str) -> list[dict]:
    response = await client.get(f"/stream/{task_id}")
    assert response.status_code == 200
    return parse_sse_events(response.text)
