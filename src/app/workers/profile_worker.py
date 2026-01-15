
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.app.core.db.models import User
from src.app.core.db.models import ScrapeJob, ScrapeJobStatus, ScrapeJobType, ScrapeJobSource
from src.app.core.logging_config import logger
import requests
from src.app.instagram.client import build_authenticated_session
from src.app.services.seeding_service import extract_contacts, process_user_links


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
        db.flush()  # ensures user.id exists

    user.display_name = data.get("full_name")

    bio_text = data.get("biography", "")
    extracted = extract_contacts(bio_text)

    user.bio_text = extracted["bio"]
    user.email = extracted["email"]
    user.phone_number = extracted["phone"]

    user.followers_count = data["edge_followed_by"]["count"]
    user.following_count = data["edge_follow"]["count"]
    user.posts_count = data["edge_owner_to_timeline_media"]["count"]
    user.is_verified = data.get("is_verified", False)
    user.profile_url = profile_url

    # persist profile state first
    db.commit()

    # enrichment phase: must never fail the profile job
    try:
        process_user_links(username, db)
    except Exception as e:
        logger.warning(
            "Aggregator expansion failed for username=%s: %s",
            username,
            e,
        )




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
