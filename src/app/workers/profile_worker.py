import instaloader
import time
import random
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.app.core.db.models import User, UserLink
from src.app.core.db.models import ScrapeJob, ScrapeJobStatus, ScrapeJobType, ScrapeJobSource
from src.app.workers.instagram_client import get_recent_post_urls
from src.app.core.logging_config import logger


# def process_profile_job(
#     job: ScrapeJob,
#     db: Session,
#     L: instaloader.Instaloader,
#     max_posts: int = 12,
# ) -> None:
#     """
#     PROFILE worker:
#     - enrich user
#     - extract bio links
#     - discover recent posts
#     - enqueue POST jobs
#     """

#     username = job.entity_key

#     # Load profile
#     profile = instaloader.Profile.from_username(L.context, username)

#     # Update user enrichment
#     user = db.query(User).filter_by(username=username).one()

#     user.display_name = profile.full_name
#     user.bio_text = profile.biography
#     user.followers_count = profile.followers
#     user.following_count = profile.followees
#     user.posts_count = profile.mediacount
#     user.is_verified = profile.is_verified

#     db.commit()

#     # Extract bio links
#     bio_links = set()

#     if profile.external_url:
#         bio_links.add(profile.external_url)

#     for url in bio_links:
#         link = UserLink(
#             user_id=user.id,
#             url=url,
#             link_type="website",
#         )
#         try:
#             db.add(link)
#             db.commit()
#         except IntegrityError:
#             db.rollback()  # duplicate

#     # Enumerate recent posts (bounded)
#     post_urls = get_recent_post_urls(
#         L,
#         username=username,
#         max_posts=max_posts,
#     )

#     # Enqueue POST jobs
#     for post_url in post_urls:
#         post_job = ScrapeJob(
#             job_type=ScrapeJobType.POST,
#             entity_key=post_url,
#             source=ScrapeJobSource.FOLLOWUP,
#             status=ScrapeJobStatus.PENDING,
#         )
#         try:
#             db.add(post_job)
#             db.commit()
#         except IntegrityError:
#             db.rollback()  # already exists


# new code 


import requests

def fetch_profile_webinfo(L, username: str) -> dict:
    session = L.context._session  # reuse authenticated cookies

    headers = {
        "User-Agent": L.context.user_agent,
        "X-IG-App-ID": "936619743392459",
        "Accept": "application/json",
        "Referer": f"https://www.instagram.com/{username}/",
    }

    resp = session.get(
        "https://www.instagram.com/api/v1/users/web_profile_info/",
        params={"username": username},
        headers=headers,
        timeout=15,
    )

    resp.raise_for_status()
    return resp.json()["data"]["user"]


def process_profile_job(
    job: ScrapeJob,
    db: Session,
    L: instaloader.Instaloader,
) -> None:
    username = job.entity_key
    profile_url = f"https://www.instagram.com/{username}"

    logger.info("Seeding profile %s", username)

    try:
        data = fetch_profile_webinfo(L, username)

        user = db.query(User).filter_by(username=username).first()
        if not user:
            user = User(username=username, profile_url=profile_url)
            db.add(user)
            db.flush()

        user.display_name = data.get("full_name")
        user.bio_text = data.get("biography")
        user.followers_count = data["edge_followed_by"]["count"]
        user.following_count = data["edge_follow"]["count"]
        user.posts_count = data["edge_owner_to_timeline_media"]["count"]
        user.is_verified = data.get("is_verified", False)
        user.is_private = data.get("is_private", False)
        user.profile_url = profile_url

        db.commit()
        logger.info("Profile %s enriched", username)

    except Exception as e:
        db.rollback()
        logger.error("Profile enrichment failed for %s: %s", username, e)
        raise



    # Enqueue POST jobs
    # for post_url in post_urls:
    #     try:
    #         db.add(
    #             ScrapeJob(
    #                 job_type=ScrapeJobType.POST,
    #                 entity_key=post_url,
    #                 source=ScrapeJobSource.FOLLOWUP,
    #                 status=ScrapeJobStatus.PENDING,
    #             )
    #         )
    #         db.commit()
    #     except IntegrityError:
    #         db.rollback()



if __name__ == "__main__":
    from src.app.core.db.session import SessionLocal
    from src.app.core.db.models import ScrapeJob, ScrapeJobStatus
    from src.app.instagram.client import get_instaloader
    from src.app.core.config import settings

    db = SessionLocal()

    job = (
        db.query(ScrapeJob)
        .filter(
            ScrapeJob.job_type == ScrapeJobType.PROFILE,
            ScrapeJob.status == ScrapeJobStatus.PENDING,
        )
        .first()
    )

    print(f"job is {job}")

    if not job:
        raise RuntimeError("No pending PROFILE jobs found")

    L = get_instaloader(settings.IG_USERNAME)  # must load saved session here

    process_profile_job(job, db, L)
