import pytest
from playwright.sync_api import Page, expect


CLAIM = "Donald trump is the president of Singapore"


def test_verify_false_claim(page: Page, live_server):
    page.goto(live_server)

    expect(page.locator("#state-input")).to_be_visible()

    page.fill("#claim-input", CLAIM)
    page.click("#submit-btn")

    expect(page.locator("#state-loading")).to_be_visible()

    page.wait_for_selector(
        "#state-result:not([hidden]), #state-error:not([hidden])",
        timeout=90_000,
    )

    error_visible = page.locator("#state-error").is_visible()
    if error_visible:
        error_text = page.locator("#error-message").inner_text()
        pytest.fail(f"Pipeline returned an error state: {error_text!r}")

    expect(page.locator("#state-result")).to_be_visible()

    # Original claim is displayed in the result
    claim_text = page.locator("#result-claim").inner_text()
    assert claim_text.strip() == CLAIM, f"Expected claim {CLAIM!r}, got {claim_text!r}"

    # Verdict must be FALSE — Donald Trump is not the president of Singapore
    expect(page.locator("#verdict-badge")).to_be_visible()
    verdict = page.locator("#verdict-badge").inner_text().strip().lower()
    assert verdict == "false", f"Expected verdict 'false', got {verdict!r}"

    summary = page.locator("#result-summary").inner_text()
    assert summary.strip(), "Result summary should have text"
