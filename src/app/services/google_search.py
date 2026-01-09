import requests
from typing import List
from src.app.core.config import settings


def google_search_instagram_posts(query: str, limit: int = 20) -> List[str]:
    """
    Runs a Google search and returns Instagram post/reel URLs.
    Discovery-only. No scraping logic.
    """

    api_key = settings.GOOGLE_API_KEY
    cse_id = settings.GOOGLE_CSE_ID

    if not api_key or not cse_id:
        raise RuntimeError("Google Search API not configured")

    params = {
        "key": api_key,
        "cx": cse_id,
        "q": f'site:instagram.com (inurl:/p/ OR inurl:/reel/) {query}',
        "num": min(limit, 10),  # Google API hard limit = 10 per call
    }

    resp = requests.get(
        "https://www.googleapis.com/customsearch/v1",
        params=params,
        timeout=10,
    )
    resp.raise_for_status()

    data = resp.json()
    items = data.get("items", [])

    urls: list[str] = []

    for item in items:
        link = item.get("link")
        if not link:
            continue

        if "/p/" in link or "/reel/" in link:
            urls.append(link.split("?")[0])

    return urls
