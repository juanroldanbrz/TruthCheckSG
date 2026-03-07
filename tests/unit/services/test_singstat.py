import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from fact_verifier.services.singstat import (
    SingStatRouteDecision,
    build_singstat_source,
    fetch_singstat_metadata,
    fetch_singstat_tabledata,
    get_singstat_sources_for_claim,
    route_singstat_claim,
    search_singstat_tables,
)
from fact_verifier.services.singstat_registry import SINGSTAT_REGISTRY

FIXTURE_DIR = Path(__file__).parents[2] / "fixtures" / "singstat"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _make_mock_client(parsed):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.parsed = parsed
    mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.mark.asyncio
async def test_route_singstat_claim_returns_model_decision():
    decision = SingStatRouteDecision(
        should_use_singstat=True,
        category="demographics",
        reason="Official population data should come from SingStat.",
        suggested_keywords=["resident population"],
    )

    with patch("fact_verifier.services.singstat.get_client", return_value=_make_mock_client(decision)):
        result = await route_singstat_claim("Singapore resident population was 4.18 million in 2024.", "singapore resident population 2024")

    assert result.should_use_singstat is True
    assert result.category == "demographics"
    assert result.suggested_keywords == ["resident population"]


@pytest.mark.asyncio
async def test_route_singstat_claim_rejects_non_statistical_claim():
    decision = SingStatRouteDecision(
        should_use_singstat=False,
        category=None,
        reason="This is not a structured statistics claim.",
        suggested_keywords=[],
    )

    with patch("fact_verifier.services.singstat.get_client", return_value=_make_mock_client(decision)):
        result = await route_singstat_claim("A new scam is spreading on Telegram.", "telegram scam singapore")

    assert result.should_use_singstat is False
    assert result.category is None


@pytest.mark.asyncio
async def test_search_singstat_tables_returns_resource_results():
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value=load_fixture("resourceid_population.json"))
    mock_response.raise_for_status = MagicMock()

    with patch("fact_verifier.services.singstat.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await search_singstat_tables("population")

    assert result["Data"]["records"][0]["id"] == "M810001"


@pytest.mark.asyncio
async def test_fetch_singstat_metadata_returns_metadata_payload():
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value=load_fixture("metadata_population.json"))
    mock_response.raise_for_status = MagicMock()

    with patch("fact_verifier.services.singstat.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await fetch_singstat_metadata("M810001")

    assert result["Data"]["records"]["title"] == "Indicators On Population, Annual"


@pytest.mark.asyncio
async def test_fetch_singstat_tabledata_returns_series_rows():
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value=load_fixture("tabledata_population.json"))
    mock_response.raise_for_status = MagicMock()

    with patch("fact_verifier.services.singstat.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await fetch_singstat_tabledata("M810001", seriesNoORrowNo=["2"], sortBy="key desc", limit=2)

    assert result["Data"]["row"][0]["seriesNo"] == "2"


@pytest.mark.asyncio
async def test_search_singstat_tables_raises_on_http_error():
    with patch("fact_verifier.services.singstat.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))
        mock_client_class.return_value = mock_client

        with pytest.raises(httpx.ReadTimeout):
            await search_singstat_tables("population")


@pytest.mark.asyncio
async def test_fetch_singstat_metadata_raises_on_malformed_json():
    mock_response = MagicMock()
    mock_response.json = MagicMock(side_effect=ValueError("bad json"))
    mock_response.raise_for_status = MagicMock()

    with patch("fact_verifier.services.singstat.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with pytest.raises(ValueError):
            await fetch_singstat_metadata("M810001")


def test_build_singstat_source_uses_claim_year_and_provider_metadata():
    entry = next(item for item in SINGSTAT_REGISTRY if item["category"] == "demographics")
    selection = entry["series_options"][0]
    source = build_singstat_source(
        entry,
        type("Selection", (), {"label": selection["label"], "series_nos": selection["series_nos"], "aggregate": selection["aggregate"]})(),
        load_fixture("metadata_population.json"),
        load_fixture("tabledata_population.json"),
        "Singapore resident population was 4.18 million in 2024.",
    )

    assert source is not None
    assert source["provider"] == "singstat"
    assert source["provider_label"] == "SingStat"
    assert source["period"] == "2024"
    assert source["value"] == "4,180,868"


def test_build_singstat_source_aggregates_housing_series():
    entry = next(item for item in SINGSTAT_REGISTRY if item["category"] == "housing_property_supply")
    selection = entry["series_options"][0]
    source = build_singstat_source(
        entry,
        type("Selection", (), {"label": selection["label"], "series_nos": selection["series_nos"], "aggregate": selection["aggregate"]})(),
        load_fixture("metadata_population.json"),
        load_fixture("tabledata_housing_supply.json"),
        "Private residential properties in the pipeline increased in 2025.",
    )

    assert source is not None
    assert source["period"] == "2025 4Q"
    assert source["value"] == "48,680"


def test_build_singstat_source_returns_none_for_empty_data():
    entry = next(item for item in SINGSTAT_REGISTRY if item["category"] == "demographics")
    selection = entry["series_options"][0]
    source = build_singstat_source(
        entry,
        type("Selection", (), {"label": selection["label"], "series_nos": selection["series_nos"], "aggregate": selection["aggregate"]})(),
        load_fixture("metadata_population.json"),
        load_fixture("tabledata_empty.json"),
        "Singapore resident population was 4.18 million in 2024.",
    )

    assert source is None


def test_build_singstat_source_returns_none_when_latest_value_is_missing():
    entry = next(item for item in SINGSTAT_REGISTRY if item["category"] == "education_social_indicators")
    selection = entry["series_options"][0]
    source = build_singstat_source(
        entry,
        type("Selection", (), {"label": selection["label"], "series_nos": selection["series_nos"], "aggregate": selection["aggregate"]})(),
        load_fixture("metadata_population.json"),
        load_fixture("tabledata_missing_latest_value.json"),
        "Enrolment in educational institutions increased in 2025.",
    )

    assert source is None


@pytest.mark.asyncio
async def test_get_singstat_sources_for_claim_returns_normalized_source():
    decision = SingStatRouteDecision(
        should_use_singstat=True,
        category="prices_inflation",
        reason="Inflation claims should use SingStat CPI data.",
        suggested_keywords=["inflation", "cpi"],
    )

    with (
        patch("fact_verifier.services.singstat.route_singstat_claim", AsyncMock(return_value=decision)),
        patch("fact_verifier.services.singstat.fetch_singstat_metadata", AsyncMock(return_value=load_fixture("metadata_population.json"))),
        patch("fact_verifier.services.singstat.fetch_singstat_tabledata", AsyncMock(return_value=load_fixture("tabledata_cpi.json"))),
    ):
        sources, returned_decision = await get_singstat_sources_for_claim(
            "Singapore CPI rose in 2024.",
            "singapore inflation cpi 2024",
        )

    assert returned_decision.category == "prices_inflation"
    assert len(sources) == 1
    assert sources[0]["provider"] == "singstat"
    assert sources[0]["tier"] == "government"
    assert sources[0]["period"] == "2024"
