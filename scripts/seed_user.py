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
    
    logger.info("User fetched: %r", user)


    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Cache the username for later use
    FileCache.set("last_seeded_username", user.username)
    logger.info("Username %s cached in temporary store.", user.username)

    db.close()

    return user


