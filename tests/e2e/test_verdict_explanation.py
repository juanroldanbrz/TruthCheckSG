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
