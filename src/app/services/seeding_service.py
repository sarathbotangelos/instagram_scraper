import json
import time
import re
from datetime import datetime, timezone, UTC
from sqlalchemy.orm import Session
from src.app.core.db.models import User, PostsMetadata, PostMedia, UserLink
from src.app.core.logging_config import logger
from src.app.core.instagram_loader import get_loader
import instaloader
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

def get_insta_profile(username: str):
    L = get_loader()
    return instaloader.Profile.from_username(L.context, username)

def fetch_profile_data(username: str):
    profile = get_insta_profile(username)
    return {
        "username": profile.username,
        "full_name": profile.full_name,
        "bio": profile.biography,
        "followers": profile.followers,
        "following": profile.followees,
        "posts": profile.mediacount,
        "is_private": profile.is_private,
        "is_verified": profile.is_verified,
        "profile_pic_url": profile.profile_pic_url,
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

# --- Main Service Functions ---

def seed_user(username: str, db: Session):
    raw = fetch_profile_data(username)
    extracted = extract_contacts(raw["bio"])

    user = db.query(User).filter(User.username == raw["username"]).first()
    if user:
        logger.info("User %s already exists. Updating record...", user.username)
        user.display_name = raw["full_name"]
        user.bio_text = extracted["bio"]
        user.email = extracted["email"]
        user.phone_number = extracted["phone"]
        user.followers_count = raw["followers"]
        user.following_count = raw["following"]
        user.posts_count = raw["posts"]
        user.is_verified = raw["is_verified"]
        user.scraped_at = datetime.now(UTC)
    else:
        logger.info("Creating new user record for %s...", raw["username"])
        user = User(
            username=raw["username"],
            display_name=raw["full_name"],
            bio_text=extracted["bio"],
            email=extracted["email"],
            profile_url=f"https://www.instagram.com/{raw['username']}/",
            phone_number=extracted["phone"],
            followers_count=raw["followers"],
            following_count=raw["following"],
            posts_count=raw["posts"],
            is_verified=raw["is_verified"],
            scraped_at=datetime.now(UTC)
        )
        db.add(user)
    db.commit()
    db.refresh(user)
    return user

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

def seed_posts(username: str, db: Session):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return

    existing_shortcodes = {row[0] for row in db.query(PostsMetadata.shortcode).filter(PostsMetadata.posted_by == user.id).all()}
    total_seeded = 0
    chunk_seeded = 0
    profile = get_insta_profile(username)

    for post in profile.get_posts():
        if post.shortcode in existing_shortcodes:
            break

        post_record = PostsMetadata(
            shortcode=post.shortcode,
            posted_by=user.id,
            posted_on=post.date_utc.replace(tzinfo=timezone.utc),
            caption=post.caption,
            likes_count=post.likes,
            comments_count=post.comments,
            views_count=post.video_view_count if post.is_video else 0,
            content_kind="reel" if post.is_video else "post",
            is_container=post.typename == "GraphSidecar",
            collaborators=json.dumps([c.username for c in post.collaborators] if getattr(post, "collaborators", None) else []),
            scraped_at=datetime.now(UTC),
        )
        db.add(post_record)

        if post.typename == "GraphSidecar":
            for idx, node in enumerate(post.get_sidecar_nodes()):
                db.add(PostMedia(
                    post_shortcode=post.shortcode,
                    media_url=node.video_url if node.is_video else node.display_url,
                    media_type="video" if node.is_video else "image",
                    media_index=idx,
                    tagged_users=json.dumps([]),
                    scraped_at=datetime.now(UTC),
                ))
        else:
            db.add(PostMedia(
                post_shortcode=post.shortcode,
                media_url=post.video_url if post.is_video else post.url,
                media_type="video" if post.is_video else "image",
                media_index=0,
                tagged_users=json.dumps([]),
                scraped_at=datetime.now(UTC),
            ))

        total_seeded += 1
        chunk_seeded += 1
        if chunk_seeded >= CHUNK_SIZE:
            db.commit()
            time.sleep(SLEEP_SECONDS)
            chunk_seeded = 0

    db.commit()

def run_full_seed_flow(username: str, db: Session):
    """
    Executes the seeding flow for a specific user: seed profile -> process links -> seed posts.
    """
    logger.info("Starting direct seed for username=%s", username)
    seed_user(username, db)
    process_user_links(username, db)
    seed_posts(username, db)
    logger.info("Direct seed completed for username=%s", username)
