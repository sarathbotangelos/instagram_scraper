import requests

def google_search_instagram_posts(query: str, limit: int = 20) -> list[str]:
    """
    Returns Instagram post URLs from Google Search.
    """
    api_key = settings.GOOGLE_API_KEY
    cse_id = settings.GOOGLE_CSE_ID

    params = {
        "key": api_key,
        "cx": cse_id,
        "q": f'site:instagram.com (inurl:/p/ OR inurl:/reel/) {query}',
        "num": min(limit, 10),
    }

    resp = requests.get("https://www.googleapis.com/customsearch/v1", params=params)
    resp.raise_for_status()

    data = resp.json()
    items = data.get("items", [])

    urls: list[str] = []
    for item in items:
        link = item.get("link")
        if link and "instagram.com" in link:
            urls.append(link)

    return urls
