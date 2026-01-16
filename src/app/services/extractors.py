# app/discovery/extractors.py

import re
import requests
from typing import Optional
from src.app.core.config import settings
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from src.app.core.db.models import User, UserLink
from src.app.core.logging_config import logger
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse



USERNAME_REGEX = re.compile(
    r'"owner":\{"id":"\d+","username":"([^"]+)"\}'
)


EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{6,10}")
URL_REGEX = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')



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


def extract_contacts(bio: str):
    emails = EMAIL_REGEX.findall(bio or "")
    phones = PHONE_REGEX.findall(bio or "")
    clean_bio = bio
    for e in emails:
        clean_bio = clean_bio.replace(e, "")
    for p in phones:
        clean_bio = clean_bio.replace(p, "")
    return {
        "email": emails[0] if emails else None,
        "phone": phones[0] if phones else None,
        "bio": clean_bio.strip(),
    }


def extract_collaborators(item: dict) -> list[str]:
    """
    Extract collaborator usernames from a feed item.
    Returns a deduplicated list of usernames.
    """
    usernames = set()

    for key in ("collaborators", "coauthor_producers", "coauthor_users"):
        users = item.get(key)
        if isinstance(users, list):
            for u in users:
                username = u.get("username")
                if username:
                    usernames.add(username)

    return list(usernames)



AGGREGATOR_DOMAINS = [
    "linktr.ee", "beacons.ai", "bio.site", "campsite.bio",
    "taplink.at", "linkpop.com", "hayko.tv", "solo.to", "shor.by",
]

CHUNK_SIZE = 10
SLEEP_SECONDS = 180



def scrape_aggregator_links_sync(url: str) -> list[dict]:
    links = []
    domain = urlparse(url).netloc.lower().replace("www.", "")
    if domain not in AGGREGATOR_DOMAINS:
        return links

    logger.info(f"Scraping aggregator: {url}")
    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = client.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            if "linktr.ee" in domain:
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if any(x in href for x in ["linktr.ee", "instagram.com", "facebook.com", "twitter.com", "linkedin.com"]):
                        continue
                    text = a.get_text(strip=True)
                    if href and text:
                        links.append({"url": href, "link_type": "aggregator_child", "label": text})
            else:
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith("http") and domain not in href:
                        text = a.get_text(strip=True)
                        links.append({"url": href, "link_type": "external", "label": text})
    except Exception as e:
        logger.error(f"Failed to scrape aggregator {url}: {e}")
    return links


def process_user_links(username: str, db: Session):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        logger.error(f"User {username} not found in database.")
        return

    bio_urls = URL_REGEX.findall(user.bio_text or "")
    for url in bio_urls:
        discovered = scrape_aggregator_links_sync(url)
        for link_data in discovered:
            existing = db.query(UserLink).filter(
                UserLink.user_id == user.id,
                UserLink.url == link_data["url"]
            ).first()
            if not existing:
                new_link = UserLink(
                    user_id=user.id,
                    url=link_data["url"],
                    link_type=link_data["link_type"],
                    extracted_at=datetime.now(UTC)
                )
                db.add(new_link)
    db.commit()




def extract_tagged_users(media: dict) -> list[str]:
    """
    Extract tagged usernames from a media item.
    """
    usernames = set()
    tags = media.get("usertags", {}).get("in", [])
    for t in tags:
        user = t.get("user")
        if user and user.get("username"):
            usernames.add(user["username"])
    return list(usernames)



def extract_media_items(item: dict) -> list[dict]:
    """
    Normalize post media (single or carousel) into a flat list.
    Each entry contains: url, type, subtype, index, tagged_users
    """
    media_items = []

    def pick_best_image(media):
        candidates = media.get("image_versions2", {}).get("candidates", [])
        return candidates[0]["url"] if candidates else None

    def pick_best_video(media):
        versions = media.get("video_versions", [])
        return versions[0]["url"] if versions else None

    # Carousel
    if item.get("media_type") == 8:
        for idx, media in enumerate(item.get("carousel_media", [])):
            media_type = "video" if media.get("media_type") == 2 else "image"
            url = (
                pick_best_video(media)
                if media_type == "video"
                else pick_best_image(media)
            )
            if not url:
                continue

            media_items.append({
                "media_url": url,
                "media_type": media_type,
                "media_subtype": media.get("media_type"),
                "media_index": idx,
                "tagged_users": extract_tagged_users(media),
            })

    # Single media
    else:
        media_type = "video" if item.get("media_type") == 2 else "image"
        url = (
            pick_best_video(item)
            if media_type == "video"
            else pick_best_image(item)
        )
        if url:
            media_items.append({
                "media_url": url,
                "media_type": media_type,
                "media_subtype": item.get("media_type"),
                "media_index": 0,
                "tagged_users": extract_tagged_users(item),
            })

    return media_items