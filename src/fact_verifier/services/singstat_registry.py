from __future__ import annotations

from typing import Literal, TypedDict

SingStatCategory = Literal[
    "demographics",
    "prices_inflation",
    "labor_market",
    "housing_property_supply",
    "macro_indicators",
    "education_social_indicators",
]


class SingStatSeriesConfig(TypedDict):
    key: str
    label: str
    series_nos: list[str]
    aggregate: Literal["first", "sum"]
    keywords: list[str]


class SingStatRegistryEntry(TypedDict):
    category: SingStatCategory
    resource_id: str
    title: str
    frequency: str
    public_url: str
    claim_keywords: list[str]
    series_options: list[SingStatSeriesConfig]


SINGSTAT_REGISTRY: list[SingStatRegistryEntry] = [
    {
        "category": "demographics",
        "resource_id": "M810001",
        "title": "Indicators On Population, Annual",
        "frequency": "Annual",
        "public_url": "https://tablebuilder.singstat.gov.sg/api/table/metadata/M810001",
        "claim_keywords": ["population", "resident population", "citizen population", "demographic"],
        "series_options": [
            {
                "key": "resident_population",
                "label": "Resident Population",
                "series_nos": ["2"],
                "aggregate": "first",
                "keywords": ["resident population", "population", "residents"],
            },
            {
                "key": "total_population",
                "label": "Total Population",
                "series_nos": ["1"],
                "aggregate": "first",
                "keywords": ["total population", "population"],
            },
        ],
    },
    {
        "category": "prices_inflation",
        "resource_id": "M213811",
        "title": "Percent Change In Consumer Price Index (CPI) Over Corresponding Period Of Previous Year, 2024 As Base Year, Annual",
        "frequency": "Annual",
        "public_url": "https://tablebuilder.singstat.gov.sg/api/table/metadata/M213811",
        "claim_keywords": ["inflation", "cpi", "consumer price index", "prices"],
        "series_options": [
            {
                "key": "headline_cpi_change",
                "label": "All Items",
                "series_nos": ["1"],
                "aggregate": "first",
                "keywords": ["inflation", "cpi", "consumer price index", "all items", "prices"],
            },
        ],
    },
    {
        "category": "labor_market",
        "resource_id": "M182332",
        "title": "Unemployment Rate Aged 15 Years And Over, End June, Annual, Seasonally Adjusted",
        "frequency": "Annual",
        "public_url": "https://tablebuilder.singstat.gov.sg/api/table/metadata/M182332",
        "claim_keywords": ["unemployment", "jobless", "labor market", "employment rate"],
        "series_options": [
            {
                "key": "resident_unemployment_rate",
                "label": "Resident Unemployment Rate, (SA)",
                "series_nos": ["5"],
                "aggregate": "first",
                "keywords": ["resident unemployment", "unemployment rate", "jobless rate", "labor market"],
            },
            {
                "key": "total_unemployment_rate",
                "label": "Total Unemployment Rate, (SA)",
                "series_nos": ["4"],
                "aggregate": "first",
                "keywords": ["total unemployment", "unemployment rate"],
            },
        ],
    },
    {
        "category": "housing_property_supply",
        "resource_id": "M400391",
        "title": "Supply Of Private Residential Properties In The Pipeline By Development Status (End Of Period), Quarterly",
        "frequency": "Quarterly",
        "public_url": "https://tablebuilder.singstat.gov.sg/api/table/metadata/M400391",
        "claim_keywords": ["housing", "property supply", "pipeline", "private residential", "residential properties"],
        "series_options": [
            {
                "key": "total_private_residential_pipeline",
                "label": "Total Private Residential Properties In The Pipeline",
                "series_nos": ["1", "2"],
                "aggregate": "sum",
                "keywords": ["private residential", "property pipeline", "housing supply", "residential properties", "pipeline"],
            },
            {
                "key": "non_landed_pipeline",
                "label": "Total Non-Landed Properties",
                "series_nos": ["2"],
                "aggregate": "first",
                "keywords": ["non-landed", "condo", "apartments", "private residential"],
            },
        ],
    },
    {
        "category": "macro_indicators",
        "resource_id": "M014911",
        "title": "Expenditure On Gross Domestic Product In Chained (2015) Dollars, Annual",
        "frequency": "Annual",
        "public_url": "https://tablebuilder.singstat.gov.sg/api/table/metadata/M014911",
        "claim_keywords": ["gdp", "gross domestic product", "economy", "economic growth", "macro"],
        "series_options": [
            {
                "key": "gdp_chained_dollars",
                "label": "GDP In Chained (2015) Dollars",
                "series_nos": ["1"],
                "aggregate": "first",
                "keywords": ["gdp", "gross domestic product", "economy", "economic growth"],
            },
        ],
    },
    {
        "category": "education_social_indicators",
        "resource_id": "M850251",
        "title": "Enrolment In Educational Institutions, Annual",
        "frequency": "Annual",
        "public_url": "https://tablebuilder.singstat.gov.sg/api/table/metadata/M850251",
        "claim_keywords": ["education", "students", "enrolment", "literacy", "schools", "social indicators"],
        "series_options": [
            {
                "key": "total_education_enrolment",
                "label": "Total Enrolment In Educational Institutions",
                "series_nos": ["1"],
                "aggregate": "first",
                "keywords": ["enrolment", "students", "education", "schools"],
            },
            {
                "key": "university_enrolment",
                "label": "Enrolment In Universities",
                "series_nos": ["1.8"],
                "aggregate": "first",
                "keywords": ["university", "higher education", "students"],
            },
        ],
    },
]

