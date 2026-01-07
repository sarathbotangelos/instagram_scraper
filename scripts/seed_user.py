from sqlalchemy.orm import Session
from src.core.db.models import User
from src.core.db.session import SessionLocal
from scripts.instagram_fetch import fetch_profile
from scripts.bio_extract import extract_contacts
from src.core.logging_config import logger
from datetime import datetime, timezone
from src.core.cache import FileCache


def seed_user(username: str):
    raw = fetch_profile(username)
    extracted = extract_contacts(raw["bio"])

    db: Session = SessionLocal()

    # 1. UPSERT logic: Check if user exists, else create
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
        user.scraped_at = datetime.now(timezone.utc)
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
            scraped_at=datetime.now(timezone.utc)
        )
        db.add(user)
    
    db.commit()
    db.refresh(user)
    
    # Cache the username and their specific post count for later use
    FileCache.set("last_seeded_username", user.username)
    FileCache.set(f"{user.username}_posts_count", user.posts_count)
    logger.info("User %s (posts: %s) cached in temporary store.", user.username, user.posts_count)

    db.close()

    return user
