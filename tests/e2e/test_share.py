import pytest
from playwright.sync_api import Page, expect


def test_share_link_works(page: Page, live_server):
    """After verifying a claim, clicking the share button copies a URL.
    Navigating to that URL re-displays the same result without re-running the pipeline."""
    page.goto(live_server)

    page.fill("#claim-input", "The president of Singapore is donald trump")
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

    # Share container and URL input must be present with a valid share URL
    share_container = page.locator("#share-container")
    expect(share_container).to_be_visible()

    share_url_input = page.locator("#share-url")
    share_url = share_url_input.input_value()
    assert "/share/" in share_url, f"Expected a /share/<id> URL, got: {share_url!r}"

    # Click the share button — it copies the URL and changes its label briefly
    share_btn = page.locator("#share-btn")
    share_btn.click()
    # Button text should briefly change to the "copied" confirmation
    expect(share_btn).to_have_text("Copied!", timeout=3_000)

    # Capture the verdict and summary from the original result
    original_verdict = page.locator("#verdict-badge").inner_text()
    original_summary = page.locator("#result-summary").inner_text()

    # Navigate to the share URL in the same page
    page.goto(share_url)

    # The result state should load immediately (no pipeline call)
    expect(page.locator("#state-result")).to_be_visible(timeout=10_000)
    expect(page.locator("#verdict-badge")).to_be_visible()

    shared_verdict = page.locator("#verdict-badge").inner_text()
    shared_summary = page.locator("#result-summary").inner_text()

    assert shared_verdict.strip() == original_verdict.strip(), (
        f"Shared verdict {shared_verdict!r} does not match original {original_verdict!r}"
    )
    assert shared_summary.strip() == original_summary.strip(), (
        f"Shared summary does not match original"
    )
