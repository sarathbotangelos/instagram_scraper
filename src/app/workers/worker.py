import time
import logging
import re
import requests
from sqlalchemy.orm import Session

import instaloader

from src.app.core.db.session import SessionLocal
from src.app.core.config import settings
from src.app.core.db.models import ScrapeJob,ScrapeJobStatus, ScrapeJobType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # seconds



def fetch_next_job(db: Session) -> ScrapeJob | None:
    return (
        db.query(ScrapeJob)
        .filter(
            ScrapeJob.status == ScrapeJobStatus.PENDING,
            ScrapeJob.job_type == ScrapeJobType.POST,
        )
        .order_by(ScrapeJob.created_at)
        .with_for_update(skip_locked=True)
        .first()
    )


L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    download_comments=False,
    save_metadata=False,
)

def extract_username_from_post(post_url: str) -> str | None:
    shortcode = post_url.rstrip("/").split("/")[-1]

    post = instaloader.Post.from_shortcode(L.context, shortcode)
    return post.owner_username



def run_worker():
    logger.info("Worker started")

    while True:
        db = SessionLocal()
        job: ScrapeJob | None = None

        try:
            job = fetch_next_job(db)

            if not job:
                db.close()
                time.sleep(POLL_INTERVAL)
                continue

            logger.info("Picked job id=%s url=%s", job.id, job.entity_key)

            # mark RUNNING
            job.status = ScrapeJobStatus.RUNNING
            db.commit()

            # --- risky section ---
            username = extract_username_from_post(job.entity_key)

            logger.info(
                "Job id=%s extracted username=%s",
                job.id,
                username,
            )

            # mark DONE
            job.status = ScrapeJobStatus.DONE
            db.commit()

        except Exception as e:
            db.rollback()

            if job:
                job.status = ScrapeJobStatus.FAILED
                job.last_error = str(e)
                db.commit()

            logger.exception("Worker error")

        finally:
            db.close()


if __name__ == "__main__":
    run_worker()
