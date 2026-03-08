import pytest

pytest.importorskip("playwright", reason="playwright not installed")
from playwright.sync_api import Page


def _install_capture_spy(page: Page) -> None:
    """Install spy before page load using add_init_script.

    Sets __SV = 1 on the mock so the PostHog inline snippet (which checks
    window.posthog.__SV) skips overwriting window.posthog with its stub.
    """
    page.add_init_script("""
        window.__posthog_events__ = [];
        window.posthog = {
            __SV: 1,
            capture: function(event, props) {
                window.__posthog_events__.push({ event: event, props: props });
            },
            init: function() {},
        };
    """)


def test_claim_submitted_event_text_only(page: Page, live_server: str):
    _install_capture_spy(page)
    page.goto(live_server)
    page.fill("#claim-input", "The sky is green")
    page.click("#submit-btn")
    events = page.evaluate("window.__posthog_events__ || []")
    submitted = next((e for e in events if e["event"] == "claim_submitted"), None)
    assert submitted is not None, "claim_submitted event not fired"
    assert submitted["props"]["input_type"] == "text_only"
    assert submitted["props"]["claim_text"] == "The sky is green"
    assert submitted["props"]["language"] == "en"


def test_verification_completed_event(page: Page, live_server: str):
    _install_capture_spy(page)
    page.goto(live_server)
    page.fill("#claim-input", "The sky is blue")
    page.click("#submit-btn")
    page.wait_for_selector("#state-result:not([hidden])", timeout=90000)
    events = page.evaluate("window.__posthog_events__ || []")
    completed = next((e for e in events if e["event"] == "verification_completed"), None)
    assert completed is not None, "verification_completed event not fired"
    assert completed["props"]["verdict"] in ("true", "false", "misleading", "unverifiable", "opinion")
    assert isinstance(completed["props"]["duration_ms"], (int, float))
    assert completed["props"]["duration_ms"] > 0


def test_verification_failed_event_on_error(page: Page, live_server: str):
    """Mock fetch to return an error response, triggering the fetch-phase verification_failed event."""
    _install_capture_spy(page)
    page.goto(live_server)

    # Override fetch after page load to simulate a server error on /verify
    page.add_script_tag(content="""
        window.__original_fetch__ = window.fetch;
        window.fetch = async function(url, options) {
            if (url === '/verify') {
                return new Response(JSON.stringify({ error: 'simulated_server_error' }), {
                    status: 422,
                    headers: { 'Content-Type': 'application/json' },
                });
            }
            return window.__original_fetch__(url, options);
        };
    """)

    page.fill("#claim-input", "This claim will fail")
    page.click("#submit-btn")
    page.wait_for_selector("#state-error:not([hidden])", timeout=15000)
    events = page.evaluate("window.__posthog_events__ || []")
    failed = next((e for e in events if e["event"] == "verification_failed"), None)
    assert failed is not None, "verification_failed event not fired"
    assert failed["props"]["phase"] in ("fetch", "stream")
    assert "error_code" in failed["props"]
