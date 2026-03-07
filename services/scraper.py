import asyncio
import httpx
import trafilatura

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FactCheckerSG/1.0)"
}


async def fetch_as_markdown(url: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()
            html = response.text
        text = trafilatura.extract(html, include_links=False, include_tables=False)
        return text if text else None
    except Exception:
        return None


async def fetch_all(urls: list[str]) -> list[dict]:
    tasks = [fetch_as_markdown(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return [
        {"url": url, "markdown": md}
        for url, md in zip(urls, results)
        if md is not None
    ]
