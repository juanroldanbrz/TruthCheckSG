import asyncio
import re
from html import unescape

import httpx
try:
    import trafilatura
except Exception:
    class _TrafilaturaFallback:
        @staticmethod
        def extract(*args, **kwargs):
            return None

    trafilatura = _TrafilaturaFallback()

from fact_verifier.config import settings

BRIGHTDATA_URL = "https://api.brightdata.com/request"


def _extract_text(html: str) -> str | None:
    extracted = trafilatura.extract(html, include_links=False, include_tables=False)
    if extracted:
        return extracted

    # Lightweight fallback so local tests can run without trafilatura installed.
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _extract_title(html: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = unescape(re.sub(r"\s+", " ", match.group(1))).strip()
    return title or None


def _build_excerpt(text: str, limit: int = 240) -> str:
    excerpt = re.sub(r"\s+", " ", text).strip()
    if len(excerpt) <= limit:
        return excerpt
    return excerpt[: limit - 3].rstrip() + "..."


async def fetch_url_source(url: str, client: httpx.AsyncClient) -> dict | None:
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
            resolved_url = url
        else:
            response = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; FactCheckerSG/1.0)"},
                timeout=10,
                follow_redirects=True,
            )
            resolved_url = str(response.url)
        response.raise_for_status()
        html = response.text
        text = _extract_text(html)
        if not text:
            return None

        return {
            "requested_url": url,
            "url": url,
            "resolved_url": resolved_url,
            "title": _extract_title(html) or resolved_url,
            "markdown": text,
            "snippet": _build_excerpt(text),
        }
    except Exception:
        return None


async def fetch_direct_source(url: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        return await fetch_url_source(url, client)


async def fetch_as_markdown(url: str, client: httpx.AsyncClient) -> str | None:
    result = await fetch_url_source(url, client)
    return result["markdown"] if result else None


async def fetch_all(urls: list[str]) -> list[dict]:
    async with httpx.AsyncClient() as client:
        tasks = [fetch_as_markdown(url, client) for url in urls]
        results = await asyncio.gather(*tasks)
    return [
        {"url": url, "markdown": md}
        for url, md in zip(urls, results)
        if md is not None
    ]
