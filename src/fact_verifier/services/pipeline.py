import asyncio
from typing import AsyncGenerator
from urllib.parse import urlparse

from fact_verifier.config import settings
from fact_verifier.services.search import brave_search
from fact_verifier.services.scraper import fetch_all, fetch_direct_source
from fact_verifier.services.singstat import get_singstat_sources_for_claim
from fact_verifier.services.verifier import verify_claim, parse_claim
from fact_verifier.services.tier import classify_tier


def _dedupe_sources(sources: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for source in sources:
        key = source.get("url") or source.get("title") or repr(source)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source)
    return deduped


def _normalize_submitted_url(claim: str, *, image_bytes: bytes | None = None) -> str | None:
    if image_bytes:
        return None

    candidate = claim.strip()
    if not candidate or len(candidate.split()) != 1:
        return None
    if candidate.startswith("www."):
        candidate = f"https://{candidate}"

    try:
        parsed = urlparse(candidate)
    except Exception:
        return None

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return candidate


def _build_link_parse_input(source: dict) -> str:
    article_text = source.get("markdown", "")[:4000]
    title = source.get("title", "")
    url = source.get("url", "")
    return (
        "Fact-check the main factual assertions in this article.\n"
        f"Article URL: {url}\n"
        f"Article title: {title}\n"
        f"Article content:\n{article_text}"
    )


async def run_pipeline(
    claim: str,
    language: str = "en",
    image_bytes: bytes | None = None,
    image_content_type: str | None = None,
) -> AsyncGenerator[dict, None]:
    submitted_url = _normalize_submitted_url(claim, image_bytes=image_bytes)
    direct_source: dict | None = None
    direct_search_query: str | None = None
    direct_claim = claim

    if submitted_url:
        direct_source = await fetch_direct_source(submitted_url)
        if direct_source:
            direct_source["tier"] = classify_tier(direct_source["url"])
            direct_claim = direct_source.get("title") or submitted_url
            direct_search_query = direct_claim
            try:
                parsed_link = await parse_claim(_build_link_parse_input(direct_source), language)
                direct_search_query = parsed_link.get("search_query") or direct_search_query
            except Exception:
                pass

    if direct_source:
        yield {"type": "progress", "step": 1, "message": "step_1"}

        search_results = await brave_search(direct_search_query or direct_claim, count=settings.max_sources)
        for result in search_results:
            result["tier"] = classify_tier(result["url"])

        yield {"type": "progress", "step": 2, "message": "step_2"}

        urls = [result["url"] for result in search_results if result.get("url")]
        fetched = await fetch_all(urls) if urls else []
        fetched_map = {item["url"]: item["markdown"] for item in fetched}
        for result in search_results:
            result["markdown"] = fetched_map.get(result["url"], "")

        all_sources = _dedupe_sources([direct_source] + search_results)
        sources_with_content = [source for source in all_sources if source.get("markdown")]
        if not sources_with_content:
            sources_with_content = all_sources

        yield {"type": "progress", "step": 3, "message": "step_3"}

        try:
            result = await verify_claim(
                direct_claim,
                sources_with_content[: settings.max_sources],
                language,
                image_bytes=image_bytes,
                image_content_type=image_content_type,
            )
            yield {"type": "result", "data": result}
        except Exception:
            yield {"type": "error", "message": "error_generic"}
        return

    try:
        parsed = await parse_claim(claim, language, image_bytes=image_bytes, image_content_type=image_content_type)
    except Exception:
        yield {"type": "error", "message": "error_generic"}
        return

    if not parsed.get("is_relevant"):
        yield {"type": "error", "message": "error_not_relevant"}
        return

    search_query = parsed.get("search_query") or claim

    yield {"type": "progress", "step": 1, "message": "step_1"}

    singstat_sources: list[dict] = []
    try:
        singstat_sources, _ = await get_singstat_sources_for_claim(claim, search_query, language)
    except Exception:
        singstat_sources = []

    search_results = await brave_search(search_query, count=settings.max_sources)
    if not search_results and search_query != claim:
        search_results = await brave_search(claim, count=settings.max_sources)
    if not search_results and not singstat_sources:
        yield {"type": "error", "message": "error_generic"}
        return

    for r in search_results:
        r["tier"] = classify_tier(r["url"])

    yield {"type": "progress", "step": 2, "message": "step_2"}

    urls = [r["url"] for r in search_results if r.get("url")]
    fetched = await fetch_all(urls) if urls else []

    fetched_map = {f["url"]: f["markdown"] for f in fetched}
    for r in search_results:
        r["markdown"] = fetched_map.get(r["url"], "")

    all_sources = _dedupe_sources(singstat_sources + search_results)
    sources_with_content = [r for r in all_sources if r.get("markdown")]
    if not sources_with_content:
        sources_with_content = all_sources

    yield {"type": "progress", "step": 3, "message": "step_3"}

    try:
        result = await verify_claim(
            claim,
            sources_with_content[: settings.max_sources],
            language,
            image_bytes=image_bytes,
            image_content_type=image_content_type,
        )
        yield {"type": "result", "data": result}
    except Exception:
        yield {"type": "error", "message": "error_generic"}
