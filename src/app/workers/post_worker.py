from src.app.core.db.models import ScrapeJobSource
from sqlalchemy.exc import IntegrityError
from src.app.core.db.models import ScrapeJob, ScrapeJobStatus, ScrapeJobType
from sqlalchemy.orm import Session
from src.app.core.logging_config import logger


def enqueue_profile_job(username: str, db: Session):
    job = ScrapeJob(
        job_type=ScrapeJobType.PROFILE,
        entity_key=username,
        status=ScrapeJobStatus.PENDING,
        source=ScrapeJobSource.FOLLOWUP
    )
    try:
        db.add(job)
        logger.info(f"Enqueued profile job for username: {username}")
    except IntegrityError as e:
        logger.info(f"Profile job for username: {username} already exists")
        db.rollback() 
