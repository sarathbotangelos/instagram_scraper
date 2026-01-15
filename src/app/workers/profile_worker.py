
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.app.core.db.models import User, UserLink
from src.app.core.db.models import ScrapeJob, ScrapeJobStatus, ScrapeJobType, ScrapeJobSource
from src.app.workers.instagram_client import get_recent_post_urls
from src.app.core.logging_config import logger
import requests
from src.app.instagram.client import build_authenticated_session

def fetch_profile_webinfo(session: requests.Session, username: str) -> dict:
    resp = session.get(
        "https://www.instagram.com/api/v1/users/web_profile_info/",
        params={"username": username},
        headers={
            "Accept": "application/json",
            "X-IG-App-ID": "936619743392459",
            "Referer": f"https://www.instagram.com/{username}/",
        },
        timeout=(5, 10),
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"IG webinfo failed status={resp.status_code} body={resp.text[:200]}"
        )

    return resp.json()["data"]["user"]


def process_profile_job(
    job: ScrapeJob,
    db: Session,
) -> None:

    username = job.entity_key
    profile_url = f"https://www.instagram.com/{username}"

    logger.info("Seeding profile %s", username)

    session = build_authenticated_session()

    data = fetch_profile_webinfo(session, username)

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

    db = SessionLocal()

    while True:
        job = (
            db.query(ScrapeJob)
            .filter(
                ScrapeJob.job_type == ScrapeJobType.PROFILE,
                ScrapeJob.status == ScrapeJobStatus.PENDING,
            )
            .order_by(ScrapeJob.id.asc())
            .first()
        )

        if not job:
            logger.info("No pending PROFILE jobs left. Exiting.")
            break

        logger.info("Picked job id=%s username=%s", job.id, job.entity_key)

        job.status = ScrapeJobStatus.RUNNING
        db.commit()

        try:
            process_profile_job(job, db)
            job.status = ScrapeJobStatus.DONE
            db.commit()

        except Exception as e:
            job.status = ScrapeJobStatus.FAILED
            db.commit()
            logger.error(
                "Job id=%s username=%s failed: %s",
                job.id,
                job.entity_key,
                e,
            )

    db.close()
