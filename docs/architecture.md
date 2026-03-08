# Architecture

## Overview

TruthCheckSG is a FastAPI application that verifies factual claims using web search and GPT-4.1. A claim comes in via HTTP, gets searched, scraped, and analysed, then the result streams back to the browser over SSE and is persisted to MongoDB for sharing.

## Request flow

```mermaid
sequenceDiagram
    participant Browser
    participant API as FastAPI (main.py)
    participant BG as Background Task
    participant Pipeline as pipeline.py

    Browser->>API: POST /verify (text + optional image)
    API->>API: OCR image if present (ocr.py)
    API->>API: Create task_id + asyncio.Queue
    API->>BG: Spawn background task
    API-->>Browser: 200 { task_id }

    Browser->>API: GET /stream/{task_id} (SSE)

    BG->>Pipeline: run_pipeline(claim, language, image?)
    Pipeline-->>BG: event: progress (step 1)
    BG-->>Browser: SSE progress
    Pipeline-->>BG: event: progress (step 2)
    BG-->>Browser: SSE progress
    Pipeline-->>BG: event: progress (step 3)
    BG-->>Browser: SSE progress

    Pipeline-->>BG: event: result (FactCheckResult)
    BG->>API: Save to MongoDB → share_id
    BG-->>Browser: SSE result
```

## Pipeline

```mermaid
flowchart TD
    A([claim + language + image?]) --> B[parse_claim\nverifier.py / GPT-4.1]
    B -->|not a verifiable claim| C([yield error: not_relevant])
    B -->|valid claim + search query| D{Stats claim?}
    D -->|yes| E[get_singstat_sources\nsingstat.py]
    D -->|no| F[brave_search\nsearch.py]
    E --> F
    F --> G[fetch_all urls\nscraper.py\nparallel]
    G -->|Bright Data proxy| H[extracted markdown]
    G -->|fallback| I[direct httpx.get]
    H --> J[verify_claim\nverifier.py / GPT-4.1]
    I --> J
    J --> K([yield result: FactCheckResult])
```

After the pipeline completes the result is written to MongoDB (`database.py`) and a `share_id` is returned so the result can be retrieved at `GET /share/{share_id}`.

## Component map

```mermaid
graph LR
    subgraph API Layer
        main[main.py\nendpoints + SSE]
    end

    subgraph Orchestration
        pipeline[pipeline.py\norchestrator]
    end

    subgraph AI
        verifier[verifier.py\nparse_claim\nverify_claim\ndescribe_image]
        ocr[ocr.py\nanalyze_image]
    end

    subgraph Data Sources
        search[search.py\nBrave Search]
        scraper[scraper.py\nweb crawling]
        singstat[singstat.py\nSingStat API]
    end

    subgraph Storage
        db[database.py\nMongoDB / memory]
    end

    subgraph Utilities
        tier[tier.py\nsource tier]
        config[config.py\nsettings]
        oai[openai_client.py\nkey rotation]
    end

    main --> pipeline
    main --> ocr
    main --> db
    pipeline --> verifier
    pipeline --> search
    pipeline --> scraper
    pipeline --> singstat
    verifier --> oai
    ocr --> oai
    scraper --> tier
    singstat --> verifier
```

## Data model

```mermaid
classDiagram
    class FactCheckResult {
        verdict: true | likely_true | unverified | likely_false | false
        summary: str
        explanation: str
        sources: list[SourceResult]
    }

    class SourceResult {
        url: str
        title: str
        snippet: str
        tier: government | news | other
    }

    FactCheckResult "1" --> "many" SourceResult
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

- **Image + text**: text is used as the claim; image bytes are passed to GPT-4.1 vision as additional context.
- **Image only**: OCR via `analyze_image()` extracts text to form the claim; a one-sentence description is captured for the share page.

## Frontend

The UI (`static/app.js`, `templates/index.html`) is a vanilla JS state machine with four states: `input → loading → result | error`. Progress is driven by the SSE stream. i18n JSON is injected server-side at render time; four languages are supported (EN, 中文, BM, தமிழ்). Past checks are stored in `localStorage`.

## Deployment

```bash
docker compose up -d        # starts MongoDB on port 27017
uv run python run_local.py  # FastAPI with hot-reload on :8001
```

Production runs in Docker (multi-stage build, Python 3.13, port 8000).
