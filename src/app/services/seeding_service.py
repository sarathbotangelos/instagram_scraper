import json
import time
import re
from datetime import datetime, timezone, UTC
from sqlalchemy.orm import Session
from src.app.core.db.models import User, PostsMetadata, PostMedia, UserLink
from src.app.core.logging_config import logger
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# --- Constants & Helpers from scripts ---

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{6,10}")
URL_REGEX = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

AGGREGATOR_DOMAINS = [
    "linktr.ee", "beacons.ai", "bio.site", "campsite.bio",
    "taplink.at", "linkpop.com", "hayko.tv", "solo.to", "shor.by",
]

CHUNK_SIZE = 10
SLEEP_SECONDS = 180

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
