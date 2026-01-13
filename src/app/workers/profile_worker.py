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

def process_profile_job(
    job: ScrapeJob,
    db: Session,
    L: instaloader.Instaloader,
    max_posts: int = 12,
) -> None:
    username = job.entity_key

    # HARD THROTTLE — TEMPORARY
    # time.sleep(random.uniform(60, 90))

    print(f"trying to seed a user {username}")


    # Load profile (AUTHENTICATED)
    profile = instaloader.Profile.from_username(L.context, username)

    # construct profile url 
    profile_url = f"https://www.instagram.com/{username}"

    # Update user enrichment
    try:
        user = db.query(User).filter_by(username=username).first()
        if not user:
            logger.info("User %s not found, creating new record", username)
            user = User(username=username, profile_url=profile_url)
            db.add(user)
            db.flush()

        user.display_name = profile.full_name
        user.bio_text = profile.biography
        user.followers_count = profile.followers
        user.following_count = profile.followees
        user.posts_count = profile.mediacount
        user.is_verified = profile.is_verified
        user.profile_url = profile_url

        db.commit()
        logger.info("Successfully updated/created user %s", username)
    except Exception as e:
        db.rollback()
        logger.error("Failed to update/create user %s: %s", username, e)
        raise

    # Extract bio links
    # if profile.external_url:
    #     try:
    #         db.add(
    #             UserLink(
    #                 user_id=user.id,
    #                 url=profile.external_url,
    #                 link_type="website",
    #             )
    #         )
    #     except IntegrityError:
    #         db.rollback()

    # Enumerate recent posts
    post_urls = get_recent_post_urls(
        L,
        username=username,
        max_posts=user.posts_count,
    )

    # log each of the post urls
    for post_url in post_urls:
        logger.info("Recent post URL: %s", post_url)




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
