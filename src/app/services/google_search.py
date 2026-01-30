import requests
from typing import List
from src.app.core.config import settings
from src.app.core.logging_config import logger


def google_search_instagram_posts(query: str, limit: int = 30) -> List[str]:
    """
    Pagination-based Google search. Gets up to 100 results (API max is 100).
    """
    
    api_key = settings.GOOGLE_API_KEY
    cse_id = settings.GOOGLE_CSE_ID

    if not api_key or not cse_id:
        raise RuntimeError("Google Search API not configured")

    urls: list[str] = []
    limit = min(limit, 100)  # Google API max is 100
    
    calls_needed = (limit + 9) // 10
    
    for page in range(calls_needed):
        start_index = (page * 10) + 1
        
        params = {
            "key": api_key,
            "cx": cse_id,
            "q": f'site:instagram.com (inurl:/p/ OR inurl:/reel/) {query}',
            "start": start_index,
            "num": 10,
        }

        try:
            resp = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"Google API request failed at page {page}: {e}")
            break
        
        data = resp.json()
        items = data.get("items", [])
        
        if not items:
            break
        
        for item in items:
            link = item.get("link")
            if link and ("/p/" in link or "/reel/" in link):
                clean_url = link.split("?")[0]
                urls.append(clean_url)
                
                if len(urls) >= limit:
                    logger.info(f"Google search '{query}' returned {len(urls)} URLs")
                    return urls
    
    logger.info(f"Google search '{query}' returned {len(urls)} URLs (fewer than requested)")
    return urls