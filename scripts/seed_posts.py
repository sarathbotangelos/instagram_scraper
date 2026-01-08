import json
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from src.core.db.models import User, PostsMetadata, PostMedia
from src.core.db.session import SessionLocal
from scripts.instagram_fetch import get_profile
from src.core.logging_config import logger


CHUNK_SIZE = 10
SLEEP_SECONDS = 120  # 2 minutes


def seed_posts(username: str):
    db: Session = SessionLocal()

    user = db.query(User).filter(User.username == username).first()
    if not user:
        logger.error("User %s not found in database.", username)
        db.close()
        return

    existing_shortcodes = {
        row[0]
        for row in db.query(PostsMetadata.shortcode)
        .filter(PostsMetadata.posted_by == user.id)
        .all()
    }

    logger.info(
        "Starting sequential post seeding for %s (existing=%d)",
        username,
        len(existing_shortcodes),
    )

    total_seeded = 0
    chunk_seeded = 0

    # SINGLE PROFILE OBJECT (stateful iterator lives here)
    profile = get_profile(username)

    for post in profile.get_posts():
        if post.shortcode in existing_shortcodes:
            logger.info(
                "Reached already-seeded post %s. Stopping.",
                post.shortcode,
            )
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
            collaborators=json.dumps(
                [c.username for c in post.collaborators]
                if getattr(post, "collaborators", None)
                else []
            ),
            scraped_at=datetime.now(timezone.utc),
        )
        db.add(post_record)

        if post.typename == "GraphSidecar":
            for idx, node in enumerate(post.get_sidecar_nodes()):
                db.add(
                    PostMedia(
                        post_shortcode=post.shortcode,
                        media_url=node.video_url if node.is_video else node.display_url,
                        media_type="video" if node.is_video else "image",
                        media_index=idx,
                        tagged_users=json.dumps([]),
                        scraped_at=datetime.now(timezone.utc),
                    )
                )
        else:
            db.add(
                PostMedia(
                    post_shortcode=post.shortcode,
                    media_url=post.video_url if post.is_video else post.url,
                    media_type="video" if post.is_video else "image",
                    media_index=0,
                    tagged_users=json.dumps([]),
                    scraped_at=datetime.now(timezone.utc),
                )
            )

        existing_shortcodes.add(post.shortcode)
        total_seeded += 1
        chunk_seeded += 1

        if chunk_seeded >= CHUNK_SIZE:
            db.commit()
            logger.info(
                "Seeded %d posts (total=%d). Sleeping %d seconds.",
                chunk_seeded,
                total_seeded,
                SLEEP_SECONDS,
            )
            time.sleep(SLEEP_SECONDS)
            chunk_seeded = 0

    db.commit()
    db.close()

    logger.info(
        "Post seeding complete for %s. Total new posts: %d",
        username,
        total_seeded,
    )
