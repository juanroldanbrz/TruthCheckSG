import pytest
from playwright.sync_api import Page
from tests.e2e.judge import llm_judge


def test_history_entry_appears_after_verification(page: Page, live_server):
    """After submitting a claim, the sidebar shows a history entry."""
    page.goto(live_server)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.fill("#claim-input", "Singapore is a city-state in Southeast Asia")
    page.click("#submit-btn")
    page.wait_for_selector(".verdict-badge", timeout=60000)

    entry = page.locator(".history-entry").first
    assert entry.is_visible(), "History entry should appear in sidebar after verification"
    claim_text = entry.locator(".history-entry-claim").inner_text()
    assert "Singapore" in claim_text


def test_history_persists_after_page_reload(page: Page, live_server):
    """History entry survives a full page reload."""
    page.goto(live_server)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.fill("#claim-input", "Singapore is a city-state in Southeast Asia")
    page.click("#submit-btn")
    page.wait_for_selector(".verdict-badge", timeout=60000)

    page.reload()
    page.wait_for_selector("#history-sidebar")
    assert page.locator(".history-entry").count() >= 1, "History should persist after reload"


def test_clicking_history_entry_shows_result(page: Page, live_server):
    """Clicking a history entry re-renders the result without resubmitting."""
    page.goto(live_server)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.fill("#claim-input", "The Merlion is a symbol of Singapore")
    page.click("#submit-btn")
    page.wait_for_selector(".verdict-badge", timeout=60000)

    # Go back to input state
    page.click("#reset-btn")
    page.wait_for_selector("#state-input:not([hidden])")

    # Click the history entry
    page.locator(".history-entry").first.click()
    page.wait_for_selector("#state-result:not([hidden])")

    verdict = page.inner_text(".verdict-badge")
    summary = page.inner_text("#result-summary")

    judgement = llm_judge(
        f"A fact-checking UI re-displayed a stored result with verdict '{verdict}' and summary: '{summary}'. "
        "Does this look like a valid fact-check result for 'The Merlion is a symbol of Singapore'?"
    )
    assert judgement.passed, judgement.reason


def test_clear_history_empties_sidebar(page: Page, live_server):
    """Clear all button removes all entries and shows empty state."""
    page.goto(live_server)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.fill("#claim-input", "Singapore is an island nation")
    page.click("#submit-btn")
    page.wait_for_selector(".verdict-badge", timeout=60000)

    page.click("#clear-history-btn")
    assert page.locator(".history-entry").count() == 0
    assert page.locator(".history-empty").is_visible()
