import json
from sqlalchemy.orm import Session
from src.core.db.models import User, PostsMetadata, PostMedia
from src.core.db.session import SessionLocal
from scripts.instagram_fetch import fetch_posts
from src.core.logging_config import logger
from datetime import datetime, timezone

def seed_posts(username: str, count: int = 12):
    """
    Fetch posts for the given username and seed the database.
    """
    db: Session = SessionLocal()
    
    # 1. Get user from DB
    user = db.query(User).filter(User.username == username).first()
    if not user:
        logger.error(f"User {username} not found in database. Seed user first.")
        db.close()
        return

    logger.info(f"Fetching {count} posts for {username}...")
    posts_data = fetch_posts(username, count)
    
    seeded_count = 0
    for p_data in posts_data:
        # 2. Check for existing post
        existing_post = db.query(PostsMetadata).filter(PostsMetadata.shortcode == p_data["shortcode"]).first()
        if existing_post:
            logger.debug(f"Post {p_data['shortcode']} already exists. Skipping.")
            continue
            
        # 3. Create PostsMetadata
        post = PostsMetadata(
            shortcode=p_data["shortcode"],
            posted_by=user.id,
            posted_on=p_data["posted_on"].replace(tzinfo=timezone.utc),
            caption=p_data["caption"],
            likes_count=p_data["likes"],
            comments_count=p_data["comments"],
            views_count=p_data["views"],
            content_kind=p_data["content_kind"],
            is_container=p_data["is_container"],
            collaborators=json.dumps(p_data["collaborators"]),
            scraped_at=datetime.now(timezone.utc)
        )
        db.add(post)
        
        # 4. Create PostMedia
        for m_data in p_data["media"]:
            media = PostMedia(
                post_shortcode=post.shortcode,
                media_url=m_data["url"],
                media_type=m_data["type"],
                media_index=m_data["index"],
                tagged_users=json.dumps(m_data["tagged_users"]),
                scraped_at=datetime.now(timezone.utc)
            )
            db.add(media)
            
        seeded_count += 1
        
    db.commit()
    db.close()
    logger.info(f"Successfully seeded {seeded_count} new posts for {username}.")
