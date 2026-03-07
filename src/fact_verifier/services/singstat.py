from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx
from openai import RateLimitError
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from fact_verifier.config import settings
from fact_verifier.openai_client import get_client
from fact_verifier.services.singstat_registry import SINGSTAT_REGISTRY, SingStatCategory

BASE_API_URL = "https://tablebuilder.singstat.gov.sg/api/table"

_retry_on_rate_limit = retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)

_ROUTER_SKIP_TERMS = (
    "scam",
    "telegram",
    "whatsapp",
    "image text:",
    "image intent:",
    "donald trump",
    "president of singapore",
    "hoax",
    "rumour",
    "rumor",
    "fake news",
)

_ROUTER_HINT_TERMS = (
    "singapore",
    "population",
    "resident",
    "inflation",
    "cpi",
    "consumer price index",
    "unemployment",
    "employment",
    "labor",
    "labour",
    "housing",
    "property",
    "residential",
    "supply",
    "gdp",
    "gross domestic product",
    "education",
    "enrolment",
    "enrollment",
    "students",
    "literacy",
)

_CATEGORY_LABELS: dict[SingStatCategory, str] = {
    "demographics": "demographics",
    "prices_inflation": "prices/inflation",
    "labor_market": "labor market",
    "housing_property_supply": "housing/property supply",
    "macro_indicators": "macro indicators",
    "education_social_indicators": "education/social indicators",
}


class SingStatRouteDecision(BaseModel):
    should_use_singstat: bool
    category: SingStatCategory | None = None
    reason: str
    suggested_keywords: list[str] = []


@dataclass(frozen=True)
class SeriesSelection:
    label: str
    series_nos: list[str]
    aggregate: str


def _singstat_headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "User-Agent": settings.singstat_user_agent,
    }


def _extract_years(text: str) -> list[str]:
    return re.findall(r"\b(19\d{2}|20\d{2})\b", text)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _should_skip_router(claim: str) -> bool:
    lowered = _clean_text(claim)
    return any(term in lowered for term in _ROUTER_SKIP_TERMS)


def _should_consider_singstat(claim: str, search_query: str) -> bool:
    combined = _clean_text(f"{claim} {search_query}")
    if _should_skip_router(combined):
        return False
    if any(term in combined for term in _ROUTER_HINT_TERMS):
        return True
    return bool(re.search(r"\b\d+(?:\.\d+)?%?\b", combined))


async def _get_json(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=settings.singstat_timeout, headers=_singstat_headers()) as client:
        response = await client.get(f"{BASE_API_URL}{path}", params=params)
        response.raise_for_status()
        return response.json()


async def search_singstat_tables(keyword: str, search_option: str = "all") -> dict[str, Any]:
    return await _get_json("/resourceid", {"keyword": keyword, "searchOption": search_option})


async def fetch_singstat_metadata(resource_id: str) -> dict[str, Any]:
    return await _get_json(f"/metadata/{resource_id}")


async def fetch_singstat_tabledata(resource_id: str, **params: Any) -> dict[str, Any]:
    if "seriesNoORrowNo" in params and isinstance(params["seriesNoORrowNo"], list):
        params["seriesNoORrowNo"] = ",".join(params["seriesNoORrowNo"])
    return await _get_json(f"/tabledata/{resource_id}", params)


@_retry_on_rate_limit
async def route_singstat_claim(claim: str, search_query: str, language: str = "en") -> SingStatRouteDecision:
    if not _should_consider_singstat(claim, search_query):
        return SingStatRouteDecision(
            should_use_singstat=False,
            reason="Claim does not look like a Singapore statistics question.",
            suggested_keywords=[],
        )

    allowed = ", ".join(f'"{key}" ({label})' for key, label in _CATEGORY_LABELS.items())
    response = await get_client().beta.chat.completions.parse(
        model=settings.openai_small_model or settings.openai_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You decide whether a Singapore fact-check claim should query the official SingStat statistics API. "
                    "Only approve claims that are primarily about measurable official statistics, rates, counts, indices, "
                    "or time-series indicators for Singapore. Reject scams, rumours, personalities, breaking news, "
                    "policy opinions, causation claims, or anything that is not directly answerable with SingStat data. "
                    f"Allowed categories: {allowed}. "
                    "Return concise suggested_keywords that could help locate the right dataset."
                ),
            },
            {
                "role": "user",
                "content": f"Claim: {claim}\nSearch query: {search_query}\nLanguage: {language}",
            },
        ],
        response_format=SingStatRouteDecision,
        max_completion_tokens=250,
    )
    if not response.choices:
        raise ValueError("OpenAI returned empty choices list")
    return response.choices[0].message.parsed


def _tokenise(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", _clean_text(text)))


def _score_terms(haystack: str, terms: list[str]) -> int:
    lowered = _clean_text(haystack)
    return sum(1 for term in terms if term in lowered)


def _pick_registry_entry(category: SingStatCategory, claim: str, search_query: str, suggested_keywords: list[str]) -> dict[str, Any] | None:
    combined = f"{claim} {search_query} {' '.join(suggested_keywords)}"
    entries = [entry for entry in SINGSTAT_REGISTRY if entry["category"] == category]
    if not entries:
        return None
    return max(entries, key=lambda entry: _score_terms(combined, entry["claim_keywords"]))


def _pick_series(entry: dict[str, Any], claim: str, search_query: str, suggested_keywords: list[str]) -> SeriesSelection:
    combined = f"{claim} {search_query} {' '.join(suggested_keywords)}"
    series = max(entry["series_options"], key=lambda option: _score_terms(combined, option["keywords"]))
    return SeriesSelection(
        label=series["label"],
        series_nos=list(series["series_nos"]),
        aggregate=series["aggregate"],
    )


def _parse_numeric(value: Any) -> float | None:
    if value in (None, "", "na", "NA", "N.A.", ".."):
        return None
    try:
        return float(str(value).replace(",", ""))
    except Exception:
        return None


def _format_value(value: float | None) -> str:
    if value is None:
        return "N/A"
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.1f}".rstrip("0").rstrip(".")


def _pick_period_value(columns: list[dict[str, Any]], target_years: list[str]) -> tuple[str | None, float | None, float | None]:
    if not columns:
        return None, None, None

    for target_year in target_years:
        matching = [column for column in columns if str(column.get("key", "")).startswith(target_year)]
        if matching:
            current = matching[0]
            previous = matching[1] if len(matching) > 1 else None
            return (
                str(current.get("key")),
                _parse_numeric(current.get("value")),
                _parse_numeric(previous.get("value")) if previous else None,
            )

    current = columns[0]
    previous = columns[1] if len(columns) > 1 else None
    return (
        str(current.get("key")),
        _parse_numeric(current.get("value")),
        _parse_numeric(previous.get("value")) if previous else None,
    )


def _aggregate_rows(rows: list[dict[str, Any]], target_years: list[str], aggregate: str) -> tuple[str | None, float | None, float | None]:
    if not rows:
        return None, None, None
    if aggregate == "first" or len(rows) == 1:
        return _pick_period_value(rows[0].get("columns", []), target_years)

    current_period: str | None = None
    current_total = 0.0
    previous_total = 0.0
    found_current = False
    found_previous = False

    for row in rows:
        period, current, previous = _pick_period_value(row.get("columns", []), target_years)
        if period:
            current_period = period
        if current is not None:
            current_total += current
            found_current = True
        if previous is not None:
            previous_total += previous
            found_previous = True

    return (
        current_period,
        current_total if found_current else None,
        previous_total if found_previous else None,
    )


def build_singstat_source(
    entry: dict[str, Any],
    selection: SeriesSelection,
    metadata: dict[str, Any],
    tabledata: dict[str, Any],
    claim: str,
) -> dict[str, Any] | None:
    target_years = _extract_years(claim)
    rows = tabledata.get("Data", {}).get("row", [])
    if not rows:
        return None

    period, current_value, previous_value = _aggregate_rows(rows, target_years, selection.aggregate)
    if period is None or current_value is None:
        return None

    unit = rows[0].get("uoM") or ""
    comparison_text = ""
    if previous_value is not None:
        delta = current_value - previous_value
        direction = "higher than" if delta > 0 else "lower than" if delta < 0 else "the same as"
        comparison_text = f" This is {direction} the previous comparable value of {_format_value(previous_value)}."

    snippet = (
        f"SingStat reports {selection.label} at {_format_value(current_value)} in {period}."
        f"{comparison_text}"
    )
    markdown_lines = [
        f"SingStat table: {entry['title']}",
        f"Series: {selection.label}",
        f"Relevant period: {period}",
        f"Value: {_format_value(current_value)} {unit}".strip(),
    ]
    if previous_value is not None:
        markdown_lines.append(f"Previous comparable value: {_format_value(previous_value)} {unit}".strip())
    data_source = metadata.get("Data", {}).get("records", {}).get("dataSource")
    if data_source:
        markdown_lines.append(f"Source agency: {data_source}")

    return {
        "url": entry["public_url"],
        "title": entry["title"],
        "snippet": snippet,
        "tier": "government",
        "markdown": "\n".join(markdown_lines),
        "provider": "singstat",
        "provider_label": "SingStat",
        "resource_id": entry["resource_id"],
        "series_no": ",".join(selection.series_nos),
        "period": period,
        "value": _format_value(current_value),
    }


async def get_singstat_sources_for_claim(claim: str, search_query: str, language: str = "en") -> tuple[list[dict[str, Any]], SingStatRouteDecision]:
    decision = await route_singstat_claim(claim, search_query, language)
    if not decision.should_use_singstat or not decision.category:
        return [], decision

    entry = _pick_registry_entry(decision.category, claim, search_query, decision.suggested_keywords)
    if not entry:
        return [], decision

    selection = _pick_series(entry, claim, search_query, decision.suggested_keywords)
    metadata = await fetch_singstat_metadata(entry["resource_id"])
    tabledata = await fetch_singstat_tabledata(
        entry["resource_id"],
        seriesNoORrowNo=selection.series_nos,
        sortBy="key desc",
        limit=4,
    )
    source = build_singstat_source(entry, selection, metadata, tabledata, claim)
    if not source:
        return [], decision

    return [source], decision

