# Fact Verifier SG — Development Guidelines

## PR Requirements

**All tests must pass before a PR can be merged.** Run the full test suite (unit + E2E) and confirm everything is green before opening or updating a PR.

## E2E Testing with Playwright

**Every feature MUST have a Playwright E2E test.** No exceptions.

### Rules

1. **Always write an E2E test for every feature.** The test must actually interact with the UI — click buttons, fill forms, observe rendered results.

2. **Always verify success or failure in the UI.** Do not just check HTTP status codes or API responses. Assert on what the user sees in the browser.

3. **Use LLM-as-a-judge when the assertion requires understanding rendered content.** For example: verifying that a verdict summary makes sense, that a result page looks correct, or that an error message is appropriate. Use the OpenAI client with structured output for this.

4. **Always use structured output** when calling an LLM in tests. Define a Pydantic model for the response and pass it via `response_format`.

### Test Location

Place E2E tests in `tests/e2e/`. Unit tests stay in `tests/`.

### LLM-as-a-Judge Pattern

Use this pattern when asserting on UI content that requires semantic understanding:

```python
from pydantic import BaseModel
from openai import OpenAI

class UIJudgement(BaseModel):
    passed: bool
    reason: str

def llm_judge(prompt: str) -> UIJudgement:
    client = OpenAI()
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format=UIJudgement,
    )
    return response.choices[0].message.parsed
```

### E2E Test Example

```python
from playwright.sync_api import Page
from tests.e2e.judge import llm_judge

def test_verify_claim_shows_verdict(page: Page):
    page.goto("http://localhost:8000")
    page.fill("#claim-input", "CPF withdrawal age raised to 70")
    page.click("#submit-btn")
    page.wait_for_selector(".verdict-badge", timeout=60000)

    verdict_text = page.inner_text(".verdict-badge")
    summary_text = page.inner_text(".result-summary")

    judgement = llm_judge(
        f"A fact-checking UI returned verdict '{verdict_text}' and summary: '{summary_text}'. "
        "Does this look like a valid, coherent fact-check result for the claim 'CPF withdrawal age raised to 70'?"
    )
    assert judgement.passed, judgement.reason
```

### Structured Output Everywhere

Use structured output (Pydantic + `response_format`) for **all** LLM calls in both application code and tests. Never parse raw JSON strings manually when a structured model can be used instead.

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
