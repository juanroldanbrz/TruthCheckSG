# Claim Classification System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the `verified` verdict with `true` across the full stack, update verdict colors to the new spec, add a static per-verdict explanation sub-label under the badge, and update the LLM system prompt to use the new classification language.

**Architecture:** The verdict enum value changes from `verified` → `true` in the JSON schema passed to GPT-4o. All downstream rendering uses `t('verdict_' + data.verdict)` to look up i18n labels, so renaming the key there propagates automatically. A new `#verdict-explanation` element in the template is populated by a new set of i18n keys `verdict_<value>_explanation`.

**Tech Stack:** Python/FastAPI backend, OpenAI structured output, Jinja2 templates, vanilla JS, CSS custom properties.

---

### Task 1: Update unit tests to use the new verdict enum

**Files:**
- Modify: `tests/test_verifier.py:41`
- Modify: `tests/test_pipeline.py:55`

**Step 1: Update the verdict assertion in test_verifier.py**

In `tests/test_verifier.py` line 41, change:
```python
assert result["verdict"] in ("verified", "false", "unverified")
```
to:
```python
assert result["verdict"] in ("true", "likely_true", "false", "likely_false", "unverified")
```

**Step 2: Update the fixture verdict in test_pipeline.py**

In `tests/test_pipeline.py` line 55, change:
```python
"verdict": "verified",
```
to:
```python
"verdict": "true",
```

**Step 3: Run the unit tests — expect failures**

```bash
cd /Users/juanroldan/develop/fact-verifier
pytest tests/ --ignore=tests/e2e -v
```

Expected: `test_verify_returns_structured_result` fails because the mock returns `"false"` which IS in the new set — actually this test should still pass. The pipeline test using `"verified"` fixture may fail if there's a validation step. Confirm which tests fail before proceeding.

**Step 4: Commit**

```bash
git add tests/test_verifier.py tests/test_pipeline.py
git commit -m "test: update verdict enum from verified to true in unit tests"
```

---

### Task 2: Update verifier.py — enum and system prompt

**Files:**
- Modify: `src/fact_verifier/services/verifier.py:29`
- Modify: `src/fact_verifier/services/verifier.py:15-19`

**Step 1: Update the VERIFY_SCHEMA enum**

In `verifier.py` line 29, change:
```python
"verdict": {"type": "string", "enum": ["verified", "likely_true", "likely_false", "false", "unverified"]},
```
to:
```python
"verdict": {"type": "string", "enum": ["true", "likely_true", "likely_false", "false", "unverified"]},
```

**Step 2: Update SYSTEM_PROMPT to describe the new classification scale**

Replace the existing `SYSTEM_PROMPT` (lines 15-19):
```python
SYSTEM_PROMPT = """You are a fact-checking assistant for Singapore.
You will receive a claim and a list of sources with their content.
Respond ONLY in {language}.
Analyse the sources and produce a structured fact-check result.
Sort sources: government first, then news, then other."""
```
with:
```python
SYSTEM_PROMPT = """You are a fact-checking assistant for Singapore.
You will receive a claim and a list of sources with their content.
Respond ONLY in {language}.
Analyse the sources and produce a structured fact-check result.
Sort sources: government first, then news, then other.

Use the following five-tier verdict scale:
- true: The claim is correct. Reliable sources confirm this.
- likely_true: Mostly correct but small details may be unclear. Most evidence supports this claim.
- unverified: Not enough information to confirm or deny. Cannot determine if true or false yet.
- likely_false: Evidence suggests it is probably wrong. Most reliable sources say this is not correct.
- false: The claim is incorrect. Reliable sources show this claim is not true."""
```

**Step 3: Run unit tests — expect them to pass**

```bash
pytest tests/ --ignore=tests/e2e -v
```

Expected: all unit tests PASS.

**Step 4: Commit**

```bash
git add src/fact_verifier/services/verifier.py
git commit -m "feat: rename verdict enum from verified to true, update system prompt with five-tier scale"
```

---

### Task 3: Update i18n files — rename key and add explanation strings

**Files:**
- Modify: `src/fact_verifier/i18n/en.json`
- Modify: `src/fact_verifier/i18n/zh.json`
- Modify: `src/fact_verifier/i18n/ms.json`
- Modify: `src/fact_verifier/i18n/ta.json`

**Step 1: Update en.json**

Remove the key `"verdict_verified"` and replace with `"verdict_true"`. Add five explanation keys after the verdict labels:

```json
{
  "app_title": "Singapore Fact Checker",
  "app_subtitle": "Submit a claim or screenshot to verify its accuracy",
  "input_placeholder": "Type or paste a claim here...",
  "upload_label": "Or upload a screenshot",
  "submit_button": "Check Fact",
  "checking_message": "This may take 20-30 seconds, please wait.",
  "step_1": "Searching sources...",
  "step_2": "Reading articles...",
  "step_3": "Analysing facts...",
  "verdict_true": "TRUE",
  "verdict_likely_true": "LIKELY TRUE",
  "verdict_likely_false": "LIKELY FALSE",
  "verdict_false": "FALSE",
  "verdict_unverified": "UNVERIFIED",
  "verdict_true_explanation": "Reliable sources confirm this is correct.",
  "verdict_likely_true_explanation": "Most evidence supports this claim.",
  "verdict_unverified_explanation": "We cannot confirm if this is true or false yet.",
  "verdict_likely_false_explanation": "Most reliable sources say this is not correct.",
  "verdict_false_explanation": "Reliable sources show this claim is not true.",
  "sources_title": "Sources checked",
  "tier_government": "Government",
  "tier_news": "News",
  "tier_other": "Other",
  "stance_supports": "Supports",
  "stance_contradicts": "Contradicts",
  "stance_neutral": "Neutral",
  "reset_button": "Check another fact",
  "error_empty": "Please enter a claim or upload an image.",
  "error_generic": "Something went wrong. Please try again.",
  "error_no_text": "Could not extract text from image. Please try again.",
  "error_not_relevant": "This doesn't appear to be a verifiable factual claim. Please enter a statement you'd like fact-checked.",
  "limited_sources": "Limited sources found.",
  "share_button": "Copy share link",
  "share_copied": "Copied!"
}
```

**Step 2: Update zh.json**

Remove `"verdict_verified": "已核实"`, replace with `"verdict_true": "正确"`. Add explanation keys:

```json
"verdict_true": "正确",
"verdict_likely_true": "可能属实",
"verdict_likely_false": "可能错误",
"verdict_false": "错误",
"verdict_unverified": "无法核实",
"verdict_true_explanation": "可靠来源证实此说法正确。",
"verdict_likely_true_explanation": "大多数证据支持此说法。",
"verdict_unverified_explanation": "目前无法确认此说法的真实性。",
"verdict_likely_false_explanation": "大多数可靠来源认为此说法不正确。",
"verdict_false_explanation": "可靠来源表明此说法不实。",
```

**Step 3: Update ms.json**

Remove `"verdict_verified": "DISAHKAN"`, replace with `"verdict_true": "BENAR"`. Add explanation keys:

```json
"verdict_true": "BENAR",
"verdict_likely_true": "MUNGKIN BENAR",
"verdict_likely_false": "MUNGKIN PALSU",
"verdict_false": "PALSU",
"verdict_unverified": "TIDAK DAPAT DISAHKAN",
"verdict_true_explanation": "Sumber yang boleh dipercayai mengesahkan ini adalah benar.",
"verdict_likely_true_explanation": "Kebanyakan bukti menyokong dakwaan ini.",
"verdict_unverified_explanation": "Kami tidak dapat mengesahkan sama ada ini benar atau salah buat masa ini.",
"verdict_likely_false_explanation": "Kebanyakan sumber yang boleh dipercayai mengatakan ini tidak betul.",
"verdict_false_explanation": "Sumber yang boleh dipercayai menunjukkan dakwaan ini tidak benar.",
```

**Step 4: Update ta.json**

Remove `"verdict_verified": "சரிபார்க்கப்பட்டது"`, replace with `"verdict_true": "உண்மை"`. Add explanation keys:

```json
"verdict_true": "உண்மை",
"verdict_likely_true": "பெரும்பாலும் உண்மை",
"verdict_likely_false": "பெரும்பாலும் தவறு",
"verdict_false": "தவறானது",
"verdict_unverified": "சரிபார்க்க முடியவில்லை",
"verdict_true_explanation": "நம்பகமான ஆதாரங்கள் இது சரி என்று உறுதிப்படுத்துகின்றன.",
"verdict_likely_true_explanation": "பெரும்பாலான சான்றுகள் இந்தக் கூற்றை ஆதரிக்கின்றன.",
"verdict_unverified_explanation": "இது உண்மையா தவறா என்று இப்போது உறுதிப்படுத்த முடியவில்லை.",
"verdict_likely_false_explanation": "பெரும்பாலான நம்பகமான ஆதாரங்கள் இது சரியில்லை என்கின்றன.",
"verdict_false_explanation": "நம்பகமான ஆதாரங்கள் இந்தக் கூற்று உண்மையில்லை என்று காட்டுகின்றன.",
```

**Step 5: Commit**

```bash
git add src/fact_verifier/i18n/
git commit -m "feat: update i18n — rename verdict_verified to verdict_true, add per-verdict explanation strings"
```

---

### Task 4: Update CSS — rename class and update verdict colors

**Files:**
- Modify: `src/fact_verifier/static/style.css:258-278`

**Step 1: Replace verdict-card and verdict-badge rules**

Replace lines 258–278 in `style.css`:

```css
.verdict-card:has(.verdict-verified)     { border-left-color: var(--green);  background: #f0fdf4; }
.verdict-card:has(.verdict-likely_true)  { border-left-color: #65a30d;       background: #f7fee7; }
.verdict-card:has(.verdict-likely_false) { border-left-color: #ea580c;       background: #fff7ed; }
.verdict-card:has(.verdict-false)        { border-left-color: var(--red);    background: #fff5f5; }
.verdict-card:has(.verdict-unverified)   { border-left-color: var(--yellow); background: #fefce8; }
...
.verdict-verified     { background: #dcfce7; color: var(--green); }
.verdict-likely_true  { background: #ecfccb; color: #65a30d; }
.verdict-likely_false { background: #ffedd5; color: #ea580c; }
.verdict-false        { background: #fee2e2; color: var(--red); }
.verdict-unverified   { background: #fef9c3; color: var(--yellow); }
```

with:

```css
.verdict-card:has(.verdict-true)         { border-left-color: #2E9E57; background: #f0fdf4; }
.verdict-card:has(.verdict-likely_true)  { border-left-color: #7BC67E; background: #f7fee7; }
.verdict-card:has(.verdict-likely_false) { border-left-color: #F59E0B; background: #fff7ed; }
.verdict-card:has(.verdict-false)        { border-left-color: #EF2B2D; background: #fff5f5; }
.verdict-card:has(.verdict-unverified)   { border-left-color: #9CA3AF; background: #f9fafb; }

.verdict-true         { background: #dcfce7; color: #2E9E57; }
.verdict-likely_true  { background: #ecfccb; color: #7BC67E; }
.verdict-likely_false { background: #ffedd5; color: #F59E0B; }
.verdict-false        { background: #fee2e2; color: #EF2B2D; }
.verdict-unverified   { background: #f3f4f6; color: #9CA3AF; }
```

**Step 2: Commit**

```bash
git add src/fact_verifier/static/style.css
git commit -m "feat: update verdict badge and card colors to new five-tier classification spec"
```

---

### Task 5: Add verdict explanation element to template and wire up JS

**Files:**
- Modify: `src/fact_verifier/templates/index.html:88-92`
- Modify: `src/fact_verifier/static/app.js:214-220`

**Step 1: Add the explanation element in index.html**

In `index.html`, inside `.verdict-card` (after `id="verdict-badge"`, before `id="result-summary"`), add:

```html
<div class="verdict-card">
  <div id="verdict-badge" class="verdict-badge"></div>
  <p id="verdict-explanation" class="verdict-explanation"></p>
  <p id="result-summary" class="result-summary"></p>
  <p id="result-explanation" class="result-explanation"></p>
</div>
```

**Step 2: Add CSS for the new element in style.css**

After the `.verdict-unverified` rule (around line 278), add:

```css
.verdict-explanation {
  font-size: 13px;
  font-style: italic;
  color: var(--muted);
  margin-bottom: 12px;
}
```

**Step 3: Populate the explanation in renderResult in app.js**

In `app.js`, after line 217 (`badge.classList.add('verdict-' + data.verdict);`), add:

```js
document.getElementById('verdict-explanation').textContent = t('verdict_' + data.verdict + '_explanation');
```

The full updated block in `renderResult` (lines 214–220) should look like:

```js
const badge = document.getElementById('verdict-badge');
badge.className = 'verdict-badge';
badge.textContent = t('verdict_' + data.verdict);
badge.classList.add('verdict-' + data.verdict);
document.getElementById('verdict-explanation').textContent = t('verdict_' + data.verdict + '_explanation');

document.getElementById('result-summary').textContent = data.summary || '';
```

**Step 4: Commit**

```bash
git add src/fact_verifier/templates/index.html src/fact_verifier/static/app.js src/fact_verifier/static/style.css
git commit -m "feat: add verdict explanation sub-label below verdict badge"
```

---

### Task 6: Add E2E test for verdict explanation sub-label

**Files:**
- Create: `tests/e2e/test_verdict_explanation.py`

**Step 1: Write the failing test**

```python
# tests/e2e/test_verdict_explanation.py
from playwright.sync_api import Page, expect


def test_verdict_explanation_is_shown(page: Page, live_server: str):
    """After a fact-check completes, the verdict explanation sub-label must be visible and non-empty."""
    page.goto(live_server)
    expect(page.locator("#state-input")).to_be_visible()

    page.fill("#claim-input", "Donald Trump is the president of Singapore")
    page.click("#submit-btn")

    page.wait_for_selector(
        "#state-result:not([hidden]), #state-error:not([hidden])",
        timeout=90_000,
    )

    if page.locator("#state-error").is_visible():
        error_text = page.locator("#error-message").inner_text()
        raise AssertionError(f"Pipeline returned an error: {error_text!r}")

    expect(page.locator("#state-result")).to_be_visible()

    explanation = page.locator("#verdict-explanation").inner_text().strip()
    assert explanation, "Verdict explanation sub-label must not be empty"
    assert len(explanation) > 5, f"Verdict explanation too short: {explanation!r}"
```

**Step 2: Run the test against the live server**

```bash
pytest tests/e2e/test_verdict_explanation.py -v
```

Expected: PASS (explanation element is rendered with the i18n string for the verdict returned).

**Step 3: Commit**

```bash
git add tests/e2e/test_verdict_explanation.py
git commit -m "test: add E2E test for verdict explanation sub-label"
```

---

### Task 7: Run the full test suite and verify

**Step 1: Run unit tests**

```bash
pytest tests/ --ignore=tests/e2e -v
```

Expected: all PASS.

**Step 2: Run E2E tests (requires live server)**

```bash
pytest tests/e2e/ -v
```

Expected: all PASS including the new `test_verdict_explanation_is_shown`.

**Step 3: Confirm no references to the old `verdict_verified` key remain**

```bash
grep -r "verdict_verified\|verdict-verified\|\"verified\"" src/ tests/
```

Expected: no matches.
