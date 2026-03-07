# Fact Verifier — Design Document
**Date:** 2026-03-07
**Target:** Singapore general public (medium-age users)
**Stack:** FastAPI + Jinja2 (bundled FE), no database

---

## Overview

A web app where users submit a text claim or a screenshot (social media post, WhatsApp message, article) and receive a structured fact-check verdict, sourced from Singapore-relevant references, ranked by trustworthiness. The UI supports all four official Singapore languages: English, Simplified Chinese, Malay, and Tamil.

---

## Architecture

```
[Browser]
   │  POST /verify (text or image + language)
   ▼
[FastAPI]
   ├── If image → GPT-4o Vision → extract text
   ├── Spawn asyncio background task (task_id)
   └── Return task_id immediately

[Browser] → GET /stream/{task_id} (SSE)
   │
   ▼
[Background Task]
   ├── Step 1: Query Brave Search (top 10 results)
   ├── Step 2: Fetch each URL → trafilatura → markdown (async, parallel)
   ├── Step 3: Send claim + sources + markdown to ChatGPT
   │          (system prompt: verdict, summary, source ranking, chosen language)
   └── Step 4: Stream result back via SSE → browser renders verdict

[Jinja2 Frontend] — single HTML page, vanilla JS for SSE + language switching
```

**Key decisions:**
- No database — task state held in-memory per session, discarded after result delivered
- All URL fetching done in parallel with `asyncio.gather` for speed
- Language passed as parameter — ChatGPT responds entirely in chosen language
- Single Jinja2 template, no JS framework needed

---

## File Structure

```
fact-verifier/
├── main.py                  # FastAPI app, routes
├── config.py                # Settings from .env (API keys, trusted domains)
├── .env                     # BRAVE_API_KEY, OPENAI_API_KEY
├── requirements.txt
│
├── services/
│   ├── ocr.py               # GPT-4o Vision → extract text from image
│   ├── search.py            # Brave Search → top 10 results
│   ├── scraper.py           # Fetch URLs → trafilatura → markdown (async)
│   ├── verifier.py          # ChatGPT call → verdict + sources + summary
│   └── pipeline.py          # Orchestrates the full flow, emits SSE steps
│
├── templates/
│   └── index.html           # Jinja2 template (full UI)
│
├── static/
│   ├── style.css            # Simple, clean CSS — large text, high contrast
│   └── app.js               # SSE client, language switcher, progress UI
│
└── i18n/
    ├── en.json              # English strings
    ├── zh.json              # Simplified Chinese
    ├── ms.json              # Malay
    └── ta.json              # Tamil
```

---

## Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serve the main Jinja2 page |
| POST | `/verify` | Accept `text` or `image` + `language`, return `task_id` |
| GET | `/stream/{task_id}` | SSE endpoint — streams progress events + final result |

---

## Data Flow & SSE Events

```json
// Progress events (step-by-step)
event: progress
data: {"step": 1, "message": "Searching sources..."}

event: progress
data: {"step": 2, "message": "Reading articles..."}

event: progress
data: {"step": 3, "message": "Analysing facts..."}

// Final result event
event: result
data: {
  "verdict": "false",
  "summary": "Short 2-3 sentence summary...",
  "explanation": "Longer paragraph...",
  "sources": [
    {
      "url": "https://www.moh.gov.sg/...",
      "title": "MOH Advisory on...",
      "tier": "government",
      "credibility_label": "Official Government Source",
      "stance": "contradicts",
      "snippet": "..."
    }
  ]
}

// Error event
event: error
data: {"message": "Could not retrieve enough sources. Please try again."}
```

**Verdict values:** `"verified"` | `"false"` | `"unverified"`
**Stance values:** `"supports"` | `"contradicts"` | `"neutral"`

### Source Tier Logic

Applied before sending to ChatGPT:
- Domains matching `*.gov.sg` → `tier: "government"` (always shown first)
- Known SG news domains (CNA, Straits Times, TODAY, Mothership, etc.) → `tier: "news"` (shown second)
- Everything else → ChatGPT assigns credibility label dynamically

---

## UI / UX

Single page, three states:

### State 1 — Input
- Language switcher top-right: EN | 中文 | BM | தமிழ்
- Large headline (translated)
- Big text area for typing a claim
- Image upload (drag & drop / tap) — PNG, JPG, WEBP
- Large "Check Fact" button
- Font 18px+, high contrast, minimal clutter

### State 2 — Loading
- Step-by-step animated indicator:
  ```
  Searching sources...      [done]
  Reading articles...       [in progress]
  Analysing facts...        [pending]
  ```
- Friendly message: estimated wait time

### State 3 — Result
- Large verdict badge: VERIFIED / FALSE / UNVERIFIED (with colour coding)
- Short summary (bold, 2-3 sentences)
- Explanation paragraph
- Source cards ranked by tier, each showing:
  - Tier badge (Government / News / Other)
  - Title + URL
  - Stance tag (Supports / Contradicts / Neutral)
  - Short snippet
- "Check another fact" button to reset

All text (verdict, summary, explanation, labels) rendered in the user's chosen language via ChatGPT.

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| Image with no readable text | GPT-4o returns empty → user-facing error in chosen language |
| Brave Search returns < 3 results | Proceed with available results, note "Limited sources found" |
| URL fetch fails (timeout/blocked) | Skip that URL silently, continue with remaining |
| ChatGPT API error | SSE `error` event → friendly translated message |
| Missing API keys | App startup fails with clear terminal error |
| Request takes > 90s | SSE `error` event → timeout message |
| Empty input submitted | Frontend validation — no server call made |

---

## Environment Variables

```env
BRAVE_API_KEY=...
OPENAI_API_KEY=...
```

---

## Deployment (Phase 1)

Local machine only — `uvicorn main:app --reload`
