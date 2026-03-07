import asyncio
import httpx
from fact_verifier.config import settings

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


def _parse_results(data: dict) -> list[dict]:
    results = data.get("web", {}).get("results", [])
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("description", "")}
        for r in results
    ]


async def brave_search(query: str, count: int = 10) -> list[dict]:
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": settings.brave_api_key,
    }
    params = {"q": query, "count": count}
    if settings.brave_goggles:
        params["goggles"] = settings.brave_goggles

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(BRAVE_SEARCH_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
        return _parse_results(data)
    except Exception:
        return []


async def brave_search_with_site_bias(query: str, count: int = 10, prefer_site: str = "") -> list[dict]:
    """Run search, optionally biasing results by running an extra query restricted to prefer_site and merging those first."""
    if not prefer_site or not prefer_site.strip():
        return await brave_search(query, count=count)

    # Fetch preferred-site results (e.g. site:gov.sg) and general results in parallel
    biased_query = f"{query} site:{prefer_site.strip()}"
    preferred_count = min(5, count)
    general_count = count

    preferred_task = asyncio.create_task(brave_search(biased_query, count=preferred_count))
    general_task = asyncio.create_task(brave_search(query, count=general_count))

    preferred, general = await asyncio.gather(preferred_task, general_task)
    seen = set()
    merged = []
    for r in preferred:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            merged.append(r)
    for r in general:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            merged.append(r)
        if len(merged) >= count:
            break
    return merged[:count]
