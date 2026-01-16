
from src.app.core.logging_config import logger

from src.app.instagram.client import build_authenticated_session
from src.app.instagram.resolve_username import resolve_username
from src.app.workers.profile_worker import fetch_profile_webinfo
from src.app.workers.profile_worker import process_user_links
from src.app.workers.post_seed_worker import seed_posts_for_user
from src.app.core.db.models import ScrapeJobStatus,ScrapeJob
from src.app.core.db.models import User
from src.app.core.db.session import SessionLocal
from sqlalchemy.orm import Session
from src.app.services.extractors import extract_contacts




def process_scrape_job(job: ScrapeJob, db: Session) -> None:
    session = build_authenticated_session()

    try:
        # -------------------------
        # USER SEED PHASE
        # -------------------------
        job.status = ScrapeJobStatus.USER_SEED_RUNNING
        db.commit()

        username = resolve_username(job.entity_key)
        if not username:
            raise RuntimeError("Username resolution failed")

        profile_url = f"https://www.instagram.com/{username}"

        data = fetch_profile_webinfo(session, username)

        user = db.query(User).filter_by(username=username).first()
        if not user:
            user = User(username=username, profile_url=profile_url)
            db.add(user)
            db.flush()

        extracted = extract_contacts(data.get("biography", ""))

        user.display_name = data.get("full_name")
        user.bio_text = extracted["bio"]
        user.email = extracted["email"]
        user.phone_number = extracted["phone"]
        user.followers_count = data["edge_followed_by"]["count"]
        user.following_count = data["edge_follow"]["count"]
        user.posts_count = data["edge_owner_to_timeline_media"]["count"]
        user.is_verified = data.get("is_verified", False)

        db.commit()
        job.status = ScrapeJobStatus.USER_SEEDED
        db.commit()

        # enrichment must never fail job
        try:
            process_user_links(username, db)
        except Exception as e:
            logger.warning("Aggregator enrichment failed: %s", e)

        # -------------------------
        # POSTS SEED PHASE
        # -------------------------
        job.status = ScrapeJobStatus.POSTS_SEED_RUNNING
        db.commit()

        seed_posts_for_user(db, session, username)

        job.status = ScrapeJobStatus.POSTS_SEEDED
        db.commit()

        # -------------------------
        # DONE
        # -------------------------
        job.status = ScrapeJobStatus.SCRAPE_DONE
        db.commit()

    except RuntimeError as e:
        db.rollback()

        if "Session Dead" in str(e):
            job.status = ScrapeJobStatus.DEAD
        elif "rate" in str(e).lower():
            job.status = ScrapeJobStatus.RATE_LIMITED
        else:
            job.status = ScrapeJobStatus.FAILED

        job.last_error = str(e)
        db.commit()

    except Exception as e:
        db.rollback()
        job.status = ScrapeJobStatus.FAILED
        job.last_error = str(e)
        db.commit()
        raise
