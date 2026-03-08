# TruthCheckSG

![TruthCheckSG](src/fact_verifier/static/logo.png)

[![Live](https://img.shields.io/badge/live-truthchecksg.org-brightgreen?style=flat-square)](https://truthchecksg.org/)
[![Tests](https://github.com/juanroldanbrz/TruthCheckSG/actions/workflows/e2e.yml/badge.svg)](https://github.com/juanroldanbrz/TruthCheckSG/actions/workflows/e2e.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue?style=flat-square)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Powered by GPT-4.1](https://img.shields.io/badge/powered%20by-GPT--4.1-412991?style=flat-square&logo=openai)](https://openai.com/)

A fact-checking web app for Singapore. Submit a claim in text or as a screenshot — the app searches the web, reads the sources, and returns a verdict with evidence. Results are stored in MongoDB and can be shared via a permanent link.

**Try it live at [truthchecksg.org](https://truthchecksg.org/)**

## How it works

1. **Relevancy check** — A GPT-4o call determines if the input is a verifiable factual claim and generates an optimised search query. Non-claims (recipes, questions, opinions) are rejected immediately.
2. **Search** — Brave Search API finds the top sources.
3. **Crawl** — Sources are fetched in parallel via Bright Data's unlocker proxy and extracted to plain text.
4. **Verify** — GPT-4o analyses the sources and returns a structured verdict: `true`, `likely_true`, `unverified`, `likely_false`, or `false`, with a summary, explanation, and ranked sources.
5. **Share** — Each result is stored in MongoDB and accessible via a permanent `/share/<id>` URL.

## Features

- Multilingual UI: English, 中文, Bahasa Melayu, தமிழ்
- Image upload with OCR (extract claims from screenshots)
- Server-Sent Events for real-time progress updates
- Source credibility tiers: Government → News → Other
- Shareable result links backed by MongoDB

## Stack

- **Backend:** FastAPI + SSE (Python 3.13)
- **AI:** OpenAI GPT-4.1 with structured output
- **Search:** Brave Search API
- **Crawling:** Bright Data unlocker (parallel)
- **Database:** MongoDB (Motor async driver)
- **Frontend:** Vanilla JS + Jinja2 templates

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Docker (for MongoDB)

### 1. Start MongoDB

```bash
docker compose up -d
```

### 2. Create the virtual environment and install dependencies

```bash
uv sync --dev
```

This creates a `.venv` folder and installs all dependencies (including dev tools).

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
BRAVE_API_KEY=your_brave_api_key
OPENAI_KEYS=your_openai_api_key          # comma-separated for round-robin rotation
BRIGHTDATA_API_KEY=your_brightdata_api_key
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=fact_verifier
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

# E2E tests
uv run pytest tests/e2e -m "not fact_checker" -v

# Fact-checker stage (driven by factscheck.csv)
uv run pytest -m fact_checker -v
```

### Adding fact-check scenarios

Edit `factscheck.csv` in the project root. Each row is a `query,result` pair:

```csv
query,result
Donald Trump is the president of Singapore,false
Singapore has a population of about 5.9 million,true
```

Valid verdicts: `true`, `likely_true`, `unverified`, `likely_false`, `false`.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
