# app/discovery/extractors.py

import re
import requests
from typing import Optional
from src.app.core.config import settings


USERNAME_REGEX = re.compile(
    r'"owner":\{"id":"\d+","username":"([^"]+)"\}'
)


def extract_username_from_post(post_url: str) -> Optional[str]:
    """
    Fetches an Instagram post page and extracts the creator username.
    Lightweight. No JS. No scrolling.
    """

    headers = {
        "User-Agent": settings.USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        resp = requests.get(
            post_url,
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None

    match = USERNAME_REGEX.search(resp.text)
    if match:
        return match.group(1)

    return None
