from sqlalchemy.orm import Session
from src.core.db.models import User
from src.core.db.session import SessionLocal
from scripts.instagram_fetch import fetch_profile
from scripts.bio_extract import extract_contacts
from src.core.logging_config import logger

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
    )

    logger.info(f"User fetched: {user}")

    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()

    return user


def main():
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m scripts.seed_user <instagram_username>")

    username = sys.argv[1]
    logger.info("Starting seed for username=%s", username)

    user = seed_user(username)
    logger.info("Seed completed for username=%s", user.username)


if __name__ == "__main__":
    main()
