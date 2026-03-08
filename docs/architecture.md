# Architecture

## Overview

TruthCheckSG is a FastAPI application that verifies factual claims using web search and GPT-4.1. A claim comes in via HTTP, gets searched, scraped, and analysed, then the result streams back to the browser over SSE and is persisted to MongoDB for sharing.

## Request flow

```
Browser
  │
  ├─ POST /verify  (text + optional image)
  │       │
  │       ├─ [image] analyze_image() → OCR text / intent (ocr.py)
  │       ├─ Create task_id + asyncio.Queue
  │       └─ Spawn background task → run_pipeline()
  │
  └─ GET /stream/{task_id}  (Server-Sent Events)
          │
          ├─ event: progress  (steps 1-3)
          ├─ event: result    (verdict + sources)
          └─ event: error
```

### Pipeline (`pipeline.py`)

```
run_pipeline(claim, language, image_bytes?)
  │
  ├─ 1. parse_claim()        → validate claim, generate search query  (verifier.py / GPT-4.1)
  │
  ├─ 2. route_singstat?      → SingStat API for official SG statistics (singstat.py)
  │
  ├─ 3. brave_search()       → top URLs matching the search query      (search.py)
  │
  ├─ 4. fetch_all(urls)      → parallel scrape via Bright Data proxy   (scraper.py)
  │      └─ fallback: direct httpx.get() with Mozilla UA
  │
  └─ 5. verify_claim()       → GPT-4.1 structured output               (verifier.py)
          │
          └─ FactCheckResult {verdict, summary, explanation, sources}
```

After the pipeline completes, the result is written to MongoDB (`database.py`) and a `share_id` is returned so the result can be retrieved at `GET /share/{share_id}`.

## Component map

| File | Role |
|------|------|
| `main.py` | FastAPI app — endpoints, SSE stream, background tasks |
| `pipeline.py` | Orchestrator — sequences all steps, yields progress events |
| `verifier.py` | GPT-4.1 calls — `parse_claim`, `verify_claim`, `describe_image` |
| `ocr.py` | Image analysis — OCR text extraction + intent description |
| `scraper.py` | Web crawling — Bright Data proxy + trafilatura extraction |
| `search.py` | Brave Search API — returns top URLs for a query |
| `singstat.py` | Singapore Statistics API — routes stat-related claims to official data |
| `singstat_registry.py` | Curated table registry for faster SingStat matching |
| `tier.py` | Source classification — Government / News / Other |
| `database.py` | MongoDB (Motor) — store and retrieve results; in-memory fallback for tests |
| `config.py` | Settings — reads environment variables |
| `openai_client.py` | OpenAI client — round-robin key rotation across API keys |

## Data model

```
FactCheckResult
  verdict:     "true" | "likely_true" | "unverified" | "likely_false" | "false"
  summary:     str   (≤ 20 words)
  explanation: str   (3 bullet points)
  sources:     list[SourceResult]

SourceResult
  url:     str
  title:   str
  snippet: str
  tier:    "government" | "news" | "other"
```

## External services

| Service | Purpose | Fallback |
|---------|---------|---------|
| OpenAI GPT-4.1 | Claim parsing, verification, image description | None — required |
| Brave Search API | Web search | None — required |
| Bright Data unlocker | Proxy to bypass bot detection | Direct `httpx.get()` |
| MongoDB | Result persistence + image storage | In-memory dict (tests only) |
| SingStat API | Official Singapore statistics | Skipped (optional route) |

## Multimodal support

- **Image + text**: text is used as the claim; image bytes are passed to GPT-4o vision as additional context.
- **Image only**: OCR via `analyze_image()` extracts text to form the claim; a one-sentence description is captured for the share page.

## Frontend

The UI (`static/app.js`, `templates/index.html`) is a vanilla JS state machine with four states: `input → loading → result | error`. Progress is driven by the SSE stream. i18n JSON is injected server-side at render time; four languages are supported (EN, 中文, BM, தமிழ்). Past checks are stored in `localStorage`.

## Deployment

```
docker compose up -d   # starts MongoDB on port 27017
uv run python run_local.py  # FastAPI with hot-reload on :8001
```

Production runs in Docker (multi-stage build, Python 3.13, port 8000).
