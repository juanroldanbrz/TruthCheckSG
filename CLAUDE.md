# Fact Verifier SG — Development Guidelines

## PR Requirements

**All tests must pass before a PR can be merged.** Run the full test suite (unit + E2E) and confirm everything is green before opening or updating a PR.

## E2E Testing Through The Backend

**E2E tests should exercise the backend flow directly.** Prefer hitting FastAPI endpoints with `httpx.AsyncClient` and `ASGITransport` instead of browser automation.

### Rules

1. **Write E2E tests around backend flows.** Cover the real request sequence such as `/verify`, `/stream/{task_id}`, `/share/{share_id}`, and `/share/{share_id}/image`.

2. **Assert on backend outputs, not browser rendering.** Check JSON payloads, SSE event streams, returned HTML, and binary responses.

3. **Prefer deterministic assertions.** Mock external dependencies when needed and assert on exact backend behavior rather than using an LLM-as-a-judge.

4. **Only use browser automation for explicitly UI-specific work.** If a feature truly requires DOM behavior, get approval first before introducing Playwright-style coverage.

### Test Location

Place E2E tests in `tests/e2e/`. Keep unit tests in `tests/unit/` and app-level integration tests in `tests/integration/`.

### Backend E2E Pattern

Use this pattern for backend flows:

```python
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_verify_claim_streams_result():
    from fact_verifier.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        verify_response = await client.post("/verify", data={"text": "CPF withdrawal age raised to 70", "language": "en"})
        assert verify_response.status_code == 200
        task_id = verify_response.json()["task_id"]

        stream_response = await client.get(f"/stream/{task_id}")
        assert stream_response.status_code == 200
        assert "event: result" in stream_response.text
```

## Cleanup

**Always remove unused code.** No exceptions.

After every change, delete:
- Imports that are no longer referenced
- Variables, parameters, or fields that are never read
- Functions or classes with no callers
- Dead branches (`if False`, unreachable `else`, etc.)
- Commented-out code
- Files that no longer serve a purpose

Do not leave unused code "just in case". If it is not used, delete it.
