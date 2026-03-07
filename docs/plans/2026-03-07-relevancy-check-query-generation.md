# Relevancy Check + LLM Query Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a single LLM call at pipeline start that rejects non-verifiable inputs and generates an optimised Brave search query.

**Architecture:** `parse_claim()` in `verifier.py` calls GPT-4o and returns `{ "is_relevant": bool, "search_query": str }`. `pipeline.py` calls it first — stops with `error_not_relevant` if irrelevant, otherwise passes `search_query` to Brave. All 4 i18n files get the new error key.

**Tech Stack:** OpenAI Python SDK (AsyncOpenAI, already in use), existing pipeline/verifier pattern.

---

### Task 1: Add `parse_claim()` to verifier.py

**Files:**
- Modify: `src/fact_verifier/services/verifier.py`
- Test: `tests/test_verifier.py`

**Step 1: Write the failing tests**

Add to `tests/test_verifier.py`:

```python
@pytest.mark.asyncio
async def test_parse_claim_relevant():
    from unittest.mock import AsyncMock, MagicMock, patch
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"is_relevant": true, "search_query": "Singapore president 2024"}'

    with patch("fact_verifier.services.verifier.client.chat.completions.create", new=AsyncMock(return_value=mock_response)):
        from fact_verifier.services.verifier import parse_claim
        result = await parse_claim("The president of Singapore is Donald Trump")

    assert result["is_relevant"] is True
    assert "search_query" in result
    assert len(result["search_query"]) > 0


@pytest.mark.asyncio
async def test_parse_claim_irrelevant():
    from unittest.mock import AsyncMock, MagicMock, patch
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"is_relevant": false, "search_query": ""}'

    with patch("fact_verifier.services.verifier.client.chat.completions.create", new=AsyncMock(return_value=mock_response)):
        from fact_verifier.services.verifier import parse_claim
        result = await parse_claim("How do I make pasta carbonara?")

    assert result["is_relevant"] is False
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_verifier.py::test_parse_claim_relevant tests/test_verifier.py::test_parse_claim_irrelevant -v
```
Expected: FAIL with `ImportError: cannot import name 'parse_claim'`

**Step 3: Add `parse_claim()` to verifier.py**

Add after the existing `client = AsyncOpenAI(...)` line and before `SYSTEM_PROMPT`:

```python
PARSE_CLAIM_PROMPT = """You are a pre-processing agent for a fact-checking system.

Given a user input, determine:
1. Whether it is a verifiable factual claim (a statement asserting something is true)
2. If yes, generate an optimised web search query to find evidence for or against it

NOT a verifiable claim: questions ("how do I..."), recipes, opinions, greetings, nonsense.
IS a verifiable claim: statements asserting facts ("X is Y", "X happened", "X costs Y").

Return ONLY valid JSON with this exact structure:
{
  "is_relevant": true | false,
  "search_query": "optimised search query string, or empty string if not relevant"
}"""


async def parse_claim(claim: str) -> dict:
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": PARSE_CLAIM_PROMPT},
            {"role": "user", "content": claim},
        ],
        max_tokens=200,
        temperature=0,
    )
    if not response.choices:
        raise ValueError("OpenAI returned empty choices list")
    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.split("```", 2)[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    return json.loads(content)
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_verifier.py::test_parse_claim_relevant tests/test_verifier.py::test_parse_claim_irrelevant -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/fact_verifier/services/verifier.py tests/test_verifier.py
git commit -m "feat: add parse_claim() for relevancy check and query generation"
```

---

### Task 2: Update pipeline.py to use `parse_claim()`

**Files:**
- Modify: `src/fact_verifier/services/pipeline.py`
- Test: `tests/test_pipeline.py`

**Step 1: Write the failing tests**

Check current `tests/test_pipeline.py` for existing patterns, then add:

```python
@pytest.mark.asyncio
async def test_pipeline_rejects_irrelevant_claim():
    from unittest.mock import AsyncMock, patch, MagicMock

    mock_parsed = {"is_relevant": False, "search_query": ""}

    with patch("fact_verifier.services.pipeline.parse_claim", new=AsyncMock(return_value=mock_parsed)):
        from fact_verifier.services.pipeline import run_pipeline
        events = []
        async for event in run_pipeline("How do I make pasta?"):
            events.append(event)

    assert any(e["type"] == "error" and e["message"] == "error_not_relevant" for e in events)


@pytest.mark.asyncio
async def test_pipeline_uses_generated_search_query():
    from unittest.mock import AsyncMock, patch, MagicMock

    mock_parsed = {"is_relevant": True, "search_query": "Singapore president 2024"}
    mock_search = AsyncMock(return_value=[])  # empty results → error_generic, but query was used

    with patch("fact_verifier.services.pipeline.parse_claim", new=AsyncMock(return_value=mock_parsed)), \
         patch("fact_verifier.services.pipeline.brave_search", mock_search):
        from fact_verifier.services.pipeline import run_pipeline
        async for _ in run_pipeline("The president of Singapore is Donald Trump"):
            pass

    mock_search.assert_called_once_with("Singapore president 2024")
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_pipeline.py::test_pipeline_rejects_irrelevant_claim tests/test_pipeline.py::test_pipeline_uses_generated_search_query -v
```
Expected: FAIL

**Step 3: Update pipeline.py**

Replace the content of `src/fact_verifier/services/pipeline.py`:

```python
import asyncio
from typing import AsyncGenerator
from fact_verifier.services.search import brave_search
from fact_verifier.services.scraper import fetch_all
from fact_verifier.services.verifier import verify_claim, parse_claim
from fact_verifier.services.tier import classify_tier


async def run_pipeline(
    claim: str, language: str = "en"
) -> AsyncGenerator[dict, None]:

    try:
        parsed = await parse_claim(claim)
    except Exception:
        yield {"type": "error", "message": "error_generic"}
        return

    if not parsed.get("is_relevant"):
        yield {"type": "error", "message": "error_not_relevant"}
        return

    search_query = parsed.get("search_query") or claim

    yield {"type": "progress", "step": 1, "message": "step_1"}

    search_results = await brave_search(search_query)
    if not search_results:
        yield {"type": "error", "message": "error_generic"}
        return

    for r in search_results:
        r["tier"] = classify_tier(r["url"])

    yield {"type": "progress", "step": 2, "message": "step_2"}

    urls = [r["url"] for r in search_results]
    fetched = await fetch_all(urls)

    fetched_map = {f["url"]: f["markdown"] for f in fetched}
    for r in search_results:
        r["markdown"] = fetched_map.get(r["url"], "")

    sources_with_content = [r for r in search_results if r.get("markdown")]
    if not sources_with_content:
        sources_with_content = search_results

    yield {"type": "progress", "step": 3, "message": "step_3"}

    try:
        result = await verify_claim(claim, sources_with_content, language)
        yield {"type": "result", "data": result}
    except Exception:
        yield {"type": "error", "message": "error_generic"}
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_pipeline.py -v
```
Expected: all PASS

**Step 5: Commit**

```bash
git add src/fact_verifier/services/pipeline.py tests/test_pipeline.py
git commit -m "feat: use parse_claim in pipeline for relevancy gate and query optimisation"
```

---

### Task 3: Add `error_not_relevant` to all i18n files

**Files:**
- Modify: `src/fact_verifier/i18n/en.json`
- Modify: `src/fact_verifier/i18n/zh.json`
- Modify: `src/fact_verifier/i18n/ms.json`
- Modify: `src/fact_verifier/i18n/ta.json`

**Step 1: Add the key to each file**

`en.json` — add after `"error_no_text"`:
```json
"error_not_relevant": "This doesn't appear to be a verifiable factual claim. Please enter a statement you'd like fact-checked."
```

`zh.json`:
```json
"error_not_relevant": "这似乎不是一个可核实的事实声明。请输入您想核查的陈述。"
```

`ms.json`:
```json
"error_not_relevant": "Ini nampaknya bukan dakwaan fakta yang boleh disahkan. Sila masukkan pernyataan yang ingin anda semak."
```

`ta.json`:
```json
"error_not_relevant": "இது சரிபார்க்கக்கூடிய உண்மையான கூற்றாகத் தெரியவில்லை. நீங்கள் சரிபார்க்க விரும்பும் ஒரு கூற்றை உள்ளிடவும்."
```

**Step 2: Verify JSON is valid**

```bash
uv run python -c "
import json, pathlib
for lang in ('en', 'zh', 'ms', 'ta'):
    p = pathlib.Path(f'src/fact_verifier/i18n/{lang}.json')
    data = json.loads(p.read_text())
    assert 'error_not_relevant' in data, f'Missing in {lang}'
    print(f'{lang}: ok')
"
```
Expected: all 4 print `ok`

**Step 3: Commit**

```bash
git add src/fact_verifier/i18n/
git commit -m "feat: add error_not_relevant i18n key to all languages"
```

---

### Task 4: Update e2e test to verify successful result

**Files:**
- Modify: `tests/e2e/test_verify_claim.py`

**Step 1: Run the e2e test to confirm it now passes end-to-end**

```bash
uv run pytest tests/e2e/ -v --no-header -s
```
Expected: PASS — the claim "The president of Singapore is donald trump" is relevant, gets an optimised query, Brave returns results, LLM produces a verdict.

If it fails, check:
- `.env` has valid `BRAVE_API_KEY` and `OPENAI_API_KEY`
- Run `uv run python -c "from fact_verifier.config import settings; print(bool(settings.brave_api_key))"` to confirm keys load

**Step 2: Commit**

```bash
git add tests/e2e/
git commit -m "test: e2e test now asserts successful result from full pipeline"
```
