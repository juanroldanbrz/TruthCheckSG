import csv
from pathlib import Path

import pytest

from tests.e2e.utils import collect_stream_events

_CSV_PATH = Path(__file__).parents[3] / "factscheck.csv"


def _load_fact_scenarios() -> list[tuple[str, str]]:
    with _CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [(row["query"], row["result"]) for row in reader]


@pytest.mark.fact_checker
@pytest.mark.parametrize("query,expected_verdict", _load_fact_scenarios())
@pytest.mark.asyncio
async def test_fact_check(app_client, query: str, expected_verdict: str):
    response = await app_client.post("/verify", data={"text": query, "language": "en"})
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    events = await collect_stream_events(app_client, task_id)

    result_event = events[-1]
    assert result_event["event"] == "result"
    assert result_event["data"]["claim"] == query
    assert result_event["data"]["data"]["verdict"] == expected_verdict
