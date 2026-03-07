from urllib.parse import urlparse

GOV_DOMAINS = {".gov.sg"}
NEWS_DOMAINS = {
    "channelnewsasia.com",
    "cna.asia",
    "straitstimes.com",
    "todayonline.com",
    "mothership.sg",
    "zaobao.com.sg",
    "beritaharian.sg",
    "tamilmurasu.com.sg",
    "8world.com",
}


def classify_tier(url: str) -> str:
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        return "other"

    if any(hostname.endswith(d) for d in GOV_DOMAINS):
        return "government"
    if any(hostname.endswith(d) or hostname == d for d in NEWS_DOMAINS):
        return "news"
    return "other"
