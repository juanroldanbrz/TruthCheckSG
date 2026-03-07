import pathlib
import pytest
from playwright.sync_api import Page, expect
from pydantic import BaseModel
from openai import OpenAI

RESOURCES_DIR = pathlib.Path(__file__).parent.parent.parent / "resources"
IMAGE_PATH = RESOURCES_DIR / "investment_scam.jpeg"
QUERY = "is this an investment scam?"


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


def test_investment_scam_image_with_query_returns_result(page: Page, live_server: str):
    page.goto(live_server)
    expect(page.locator("#state-input")).to_be_visible()

    page.fill("#claim-input", QUERY)

    page.locator("#upload-area").click()
    page.locator("#image-input").set_input_files(str(IMAGE_PATH))

    page.click("#submit-btn")

    expect(page.locator("#state-loading")).to_be_visible()

    page.wait_for_selector(
        "#state-result:not([hidden]), #state-error:not([hidden])",
        timeout=120_000,
    )

    if page.locator("#state-error").is_visible():
        error_text = page.locator("#error-message").inner_text()
        pytest.fail(f"Pipeline returned an error instead of a result: {error_text!r}")

    expect(page.locator("#state-result")).to_be_visible()

    verdict_text = page.locator("#verdict-badge").inner_text()
    summary_text = page.locator("#result-summary").inner_text()

    assert verdict_text.strip(), "Verdict badge must not be empty"
    assert summary_text.strip(), "Result summary must not be empty"

    judgement = llm_judge(
        f"A fact-checking UI was given a screenshot of a Telegram investment group chat "
        f"and the question '{QUERY}'. It returned verdict '{verdict_text}' and summary: '{summary_text}'. "
        f"Does the verdict and summary reflect a coherent analysis of this investment group? "
        f"Pass if the summary addresses scam-related concerns (red flags, warnings, or uncertainty about legitimacy), "
        f"regardless of whether the verdict is 'false', 'unverified', or similar. "
        f"Fail only if the output is an error message, completely off-topic, or contains no scam analysis."
    )
    assert judgement.passed, judgement.reason
