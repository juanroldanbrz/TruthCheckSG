import asyncio
import httpx
import trafilatura

from fact_verifier.config import settings

BRIGHTDATA_URL = "https://api.brightdata.com/request"


async def fetch_as_markdown(url: str, client: httpx.AsyncClient) -> str | None:
    try:
        if settings.brightdata_api_key:
            response = await client.post(
                BRIGHTDATA_URL,
                json={"zone": "unblocker", "url": url, "format": "raw"},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.brightdata_api_key}",
                },
                timeout=30,
            )
        else:
            response = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; FactCheckerSG/1.0)"},
                timeout=10,
                follow_redirects=True,
            )
        response.raise_for_status()
        html = response.text
        text = trafilatura.extract(html, include_links=False, include_tables=False)
        return text if text else None
    except Exception:
        return None


async def fetch_all(urls: list[str]) -> list[dict]:
    async with httpx.AsyncClient() as client:
        tasks = [fetch_as_markdown(url, client) for url in urls]
        results = await asyncio.gather(*tasks)
    return [
        {"url": url, "markdown": md}
        for url, md in zip(urls, results)
        if md is not None
    ]
