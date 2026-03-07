# Claim Classification System — Design

**Date:** 2026-03-07
**Issue:** Improve Claim Classification System

## Overview

Replace the current five-tier verdict system (with `verified` as the top tier) with a cleaner confidence spectrum that uses plain-language labels, intuitive colors, and static per-verdict explanations shown in the UI.

## Verdict Scale

| Enum value    | Display label | Color        | Hex       |
|---------------|---------------|--------------|-----------|
| `true`        | TRUE          | Green        | #2E9E57   |
| `likely_true` | LIKELY TRUE   | Light Green  | #7BC67E   |
| `unverified`  | UNVERIFIED    | Grey         | #9CA3AF   |
| `likely_false`| LIKELY FALSE  | Orange       | #F59E0B   |
| `false`       | FALSE         | Red          | #EF2B2D   |

## Changes

### `verifier.py`
- Rename enum value `"verified"` → `"true"` in `VERIFY_SCHEMA`
- Update `SYSTEM_PROMPT` to describe the five-tier scale by name and meaning so the LLM reasons with the new classification language

### i18n (en, zh, ms, ta)
- Rename key `verdict_verified` → `verdict_true`; update display text to "TRUE" (and localised equivalents)
- Add 5 static explanation keys per language:
  - `verdict_true_explanation`
  - `verdict_likely_true_explanation`
  - `verdict_unverified_explanation`
  - `verdict_likely_false_explanation`
  - `verdict_false_explanation`

### `style.css`
- Rename `.verdict-verified` → `.verdict-true`
- Update all 5 verdict badge and card colors to the hex values above

### `templates/index.html`
- Add `<p id="verdict-explanation">` below `#verdict-badge`
- JS populates it from i18n on result render using the verdict value as a key

### Tests
- `test_verifier.py`, `test_pipeline.py`: update `"verified"` → `"true"` in fixture data and assertions
- `test_donald_trump_sg_president.py`: update `EXPECTED_VERDICT["en"]` from `"false"` (unchanged) and confirm `"true"` label where applicable
- Add new E2E test asserting the explanation sub-label is rendered and non-empty for a known verdict