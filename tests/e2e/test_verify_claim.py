import pytest
from playwright.sync_api import Page, expect


def test_verify_false_claim(page: Page, live_server):
    page.goto(live_server)

    # Input state is visible
    expect(page.locator("#state-input")).to_be_visible()

    # Fill in the claim
    page.fill("#claim-input", "The president of Singapore is donald trump")

    # Submit the form
    page.click("#submit-btn")

    # Loading state should appear
    expect(page.locator("#state-loading")).to_be_visible()

    # Wait for either result or error state (pipeline makes real AI calls, allow up to 90s)
    page.wait_for_selector(
        "#state-result:not([hidden]), #state-error:not([hidden])",
        timeout=90_000,
    )

    # Assert result state — not error
    error_visible = page.locator("#state-error").is_visible()
    if error_visible:
        error_text = page.locator("#error-message").inner_text()
        pytest.fail(f"Pipeline returned an error state: {error_text!r}")

    expect(page.locator("#state-result")).to_be_visible()

    # Verify key result elements are populated
    expect(page.locator("#verdict-badge")).to_be_visible()
    expect(page.locator("#result-summary")).to_be_visible()

    verdict = page.locator("#verdict-badge").inner_text()
    assert verdict.strip(), "Verdict badge should have text"

    summary = page.locator("#result-summary").inner_text()
    assert summary.strip(), "Result summary should have text"
