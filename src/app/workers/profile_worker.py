import instaloader
from sqlalchemy.orm import Session
from src.app.core.db.models import User, UserLink
from src.app.core.db.models import ScrapeJob,ScrapeJobStatus, ScrapeJobType, ScrapeJobSource
from src.app.workers.instagram_client import get_recent_post_urls
from sqlalchemy.exc import IntegrityError


def process_profile_job(
    job: ScrapeJob,
    db: Session,
    L: instaloader.Instaloader,
    max_posts: int = 12,
) -> None:
    """
    PROFILE worker:
    - enrich user
    - extract bio links
    - discover recent posts
    - enqueue POST jobs
    """

    username = job.entity_key

    # Load profile
    profile = instaloader.Profile.from_username(L.context, username)

    # Update user enrichment
    user = db.query(User).filter_by(username=username).one()

    user.display_name = profile.full_name
    user.bio_text = profile.biography
    user.followers_count = profile.followers
    user.following_count = profile.followees
    user.posts_count = profile.mediacount
    user.is_verified = profile.is_verified

    db.commit()

    # Extract bio links
    bio_links = set()

    if profile.external_url:
        bio_links.add(profile.external_url)

    for url in bio_links:
        link = UserLink(
            user_id=user.id,
            url=url,
            link_type="website",
        )
        try:
            db.add(link)
            db.commit()
        except IntegrityError:
            db.rollback()  # duplicate

    # Enumerate recent posts (bounded)
    post_urls = get_recent_post_urls(
        L,
        username=username,
        max_posts=max_posts,
    )

    # Enqueue POST jobs
    for post_url in post_urls:
        post_job = ScrapeJob(
            job_type=ScrapeJobType.POST,
            entity_key=post_url,
            source=ScrapeJobSource.FOLLOWUP,
            status=ScrapeJobStatus.PENDING,
        )
        try:
            db.add(post_job)
            db.commit()
        except IntegrityError:
            db.rollback()  # already exists
