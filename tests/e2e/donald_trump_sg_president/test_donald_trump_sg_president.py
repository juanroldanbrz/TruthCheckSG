import pytest
from playwright.sync_api import Page, expect

CLAIM = "Donald Trump is the president of Singapore"

# Expected localised verdict text per language
EXPECTED_VERDICT = {
    "en": "false",
    "zh": "错误",
    "ms": "palsu",
    "ta": "தவறானது",
}


@pytest.mark.parametrize("lang", ["en", "zh", "ms", "ta"])
def test_donald_trump_sg_president(page: Page, live_server: str, lang: str):
    page.goto(live_server)

    expect(page.locator("#state-input")).to_be_visible()

    # Switch language and verify the UI button becomes active
    lang_btn = page.locator(f"[data-lang='{lang}']")
    lang_btn.click()
    expect(lang_btn).to_have_class("lang-btn active")

    page.fill("#claim-input", CLAIM)
    page.click("#submit-btn")

    expect(page.locator("#state-loading")).to_be_visible()

    page.wait_for_selector(
        "#state-result:not([hidden]), #state-error:not([hidden])",
        timeout=90_000,
    )

    if page.locator("#state-error").is_visible():
        error_text = page.locator("#error-message").inner_text()
        pytest.fail(f"[{lang}] Pipeline returned an error: {error_text!r}")

    expect(page.locator("#state-result")).to_be_visible()

    # Original claim is shown in the result
    claim_text = page.locator("#result-claim").inner_text()
    assert claim_text.strip() == CLAIM, f"[{lang}] Expected claim {CLAIM!r}, got {claim_text!r}"

    # Verdict must match the expected localised text for this language
    verdict = page.locator("#verdict-badge").inner_text().strip().lower()
    expected = EXPECTED_VERDICT[lang].lower()
    assert verdict == expected, f"[{lang}] Expected verdict {expected!r}, got {verdict!r}"

    summary = page.locator("#result-summary").inner_text()
    assert summary.strip(), f"[{lang}] Result summary should not be empty"
