import asyncio
from typing import AsyncGenerator
from fact_verifier.services.search import brave_search
from fact_verifier.services.scraper import fetch_all
from fact_verifier.services.verifier import verify_claim, parse_claim
from fact_verifier.services.tier import classify_tier


async def run_pipeline(
    claim: str,
    language: str = "en",
    image_bytes: bytes | None = None,
    image_content_type: str | None = None,
) -> AsyncGenerator[dict, None]:

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

    search_results = await brave_search(search_query)
    if not search_results:
        yield {"type": "error", "message": "error_generic"}
        return

    for r in search_results:
        r["tier"] = classify_tier(r["url"])

    yield {"type": "progress", "step": 2, "message": "step_2"}

    urls = [r["url"] for r in search_results]
    fetched = await fetch_all(urls)

    fetched_map = {f["url"]: f["markdown"] for f in fetched}
    for r in search_results:
        r["markdown"] = fetched_map.get(r["url"], "")

    sources_with_content = [r for r in search_results if r.get("markdown")]
    if not sources_with_content:
        sources_with_content = search_results

    yield {"type": "progress", "step": 3, "message": "step_3"}

    try:
        result = await verify_claim(claim, sources_with_content, language, image_bytes=image_bytes, image_content_type=image_content_type)
        yield {"type": "result", "data": result}
    except Exception:
        yield {"type": "error", "message": "error_generic"}
