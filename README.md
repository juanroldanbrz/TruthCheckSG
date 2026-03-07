# TruthCheckSG

A fact-checking web app for Singapore. Submit a claim in text or as a screenshot — the app searches the web, reads the sources, and returns a verdict with evidence.

## How it works

1. **Relevancy check** — A GPT-4o call determines if the input is a verifiable factual claim and generates an optimised search query. Non-claims (recipes, questions, opinions) are rejected immediately.
2. **Search** — Brave Search API finds the top sources.
3. **Crawl** — Sources are fetched in parallel via Bright Data's unlocker proxy and extracted to plain text.
4. **Verify** — GPT-4o analyses the sources and returns a structured verdict: `verified`, `false`, or `unverified`, with a summary, explanation, and ranked sources.

## Features

- Multilingual UI: English, 中文, Bahasa Melayu, தமிழ்
- Image upload with OCR (extract claims from screenshots)
- Server-Sent Events for real-time progress updates
- Source credibility tiers: Government → News → Other

## Stack

- **Backend:** FastAPI + SSE (Python 3.14)
- **AI:** OpenAI GPT-4o with structured output
- **Search:** Brave Search API
- **Crawling:** Bright Data unlocker (parallel)
- **Frontend:** Vanilla JS + Jinja2 templates

## Setup

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)

### 1. Create the virtual environment and install dependencies

```bash
uv sync --dev
```

This creates a `.venv` folder and installs all dependencies (including dev tools).

### 2. Install Playwright browsers (for e2e tests)

```bash
uv run playwright install chromium
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
BRAVE_API_KEY=your_brave_api_key
OPENAI_API_KEY=your_openai_api_key
BRIGHTDATA_API_KEY=your_brightdata_api_key
```

### 4. Run the server

```bash
uv run python run_local.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

> The server runs with hot-reload enabled. Any changes to source files will restart it automatically.

## Tests

```bash
# Unit tests
uv run pytest tests/ --ignore=tests/e2e -v

# E2E tests (requires running app + valid API keys)
uv run pytest tests/e2e/ -v
```
