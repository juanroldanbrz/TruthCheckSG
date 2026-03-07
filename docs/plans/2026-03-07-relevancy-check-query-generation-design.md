# Design: Relevancy Check + LLM Query Generation

## Problem

The pipeline currently passes the raw user input directly to Brave Search. This has two issues:
1. Non-verifiable inputs (questions, recipes, opinions) are processed unnecessarily
2. The search query is unoptimised — a raw claim is rarely the best search query

## Solution

A single LLM call at the start of the pipeline that checks relevancy and generates an optimised search query simultaneously.

## Architecture

### New function: `parse_claim(claim) -> dict`

Location: `src/fact_verifier/services/verifier.py`

Calls GPT-4o with a system prompt that:
- Determines if the input is a verifiable factual claim
- Generates an optimised Brave search query if relevant
- Returns: `{ "is_relevant": bool, "search_query": str }`

### Pipeline changes

`src/fact_verifier/services/pipeline.py`:

1. Call `parse_claim(claim)` before any progress events
2. If `is_relevant` is `False` → yield `{"type": "error", "message": "error_not_relevant"}` and return
3. If `is_relevant` is `True` → use `search_query` (not raw claim) in `brave_search()`
4. Existing 3-step progress flow and result handling unchanged

### i18n changes

Add `"error_not_relevant"` key to all 4 language files (en, zh, ms, ta).

## Out of Scope (Next Iteration)

- Proxy for web crawling
- Parallel source fetching
