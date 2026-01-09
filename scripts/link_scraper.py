import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.app.core.db.models import User, UserLink
from src.app.core.db.session import SessionLocal
from src.app.core.logging_config import logger

AGGREGATOR_DOMAINS = [
    "linktr.ee",
    "beacons.ai",
    "bio.site",
    "campsite.bio",
    "taplink.at",
    "linkpop.com",
    "hayko.tv",
    "solo.to",
    "shor.by",
]

# Regex to find URLs in text
URL_REGEX = re.compile(
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
)

def scrape_aggregator_links_sync(url: str) -> list[dict]:
    """
    Fetches an aggregator page (like Linktree) and extracts outbound links.
    """
    links = []
    domain = urlparse(url).netloc.lower().replace("www.", "")
    
    if domain not in AGGREGATOR_DOMAINS:
        return links

    logger.info(f"Scraping aggregator: {url}")
    
    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Linktree specific extraction
            if "linktr.ee" in domain:
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    # Filter out internal linktree links, socials, etc.
                    if any(x in href for x in ["linktr.ee", "instagram.com", "facebook.com", "twitter.com", "linkedin.com"]):
                        continue
                    
                    text = a.get_text(strip=True)
                    if href and text:
                        links.append({
                            "url": href,
                            "link_type": "aggregator_child",
                            "label": text
                        })
            else:
                # Generic fallback for other aggregators
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith("http") and domain not in href:
                        text = a.get_text(strip=True)
                        links.append({
                            "url": href,
                            "link_type": "external",
                            "label": text
                        })
                        
    except Exception as e:
        logger.error(f"Failed to scrape aggregator {url}: {e}")
        
    return links

def process_user_links(username: str):
    """
    Look up user by username, scan bio for links, and scrape any aggregators found.
    """
    db: Session = SessionLocal()
    
    # 1. Get user from DB
    user = db.query(User).filter(User.username == username).first()
    if not user:
        logger.error(f"User {username} not found in database. Seed the user first.")
        db.close()
        return

    # 2. Extract URLs from bio
    bio_urls = URL_REGEX.findall(user.bio_text or "")
    logger.info(f"Found {len(bio_urls)} potential links in bio for {username}")

    for url in bio_urls:
        # 3. Scrape if aggregator
        discovered = scrape_aggregator_links_sync(url)
        
        # 4. Save to UserLink table
        for link_data in discovered:
            # Check for existing link to avoid duplicates
            existing = db.query(UserLink).filter(
                UserLink.user_id == user.id,
                UserLink.url == link_data["url"]
            ).first()
            
            if not existing:
                new_link = UserLink(
                    user_id=user.id,
                    url=link_data["url"],
                    link_type=link_data["link_type"],
                    extracted_at=datetime.now(timezone.utc)
                )
                db.add(new_link)
                logger.info(f"Added link: {link_data['url']}")
    
    db.commit()
    db.close()
    logger.info(f"Finished processing links for {username}")

def main():
    import sys
    if len(sys.argv) != 2:
        print("usage: python -m scripts.link_scraper <username>")
        return
    
    username = sys.argv[1]
    process_user_links(username)

if __name__ == "__main__":
    main()
