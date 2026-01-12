from sqlalchemy.exc import IntegrityError
from src.app.core.db.models import ScrapeJob, ScrapeJobType, ScrapeJobSource
from src.app.core.db.session import SessionLocal
from src.app.core.db.models import ScrapeJobStatus

def enqueue_post_jobs(
    urls: set[str],
    source: ScrapeJobSource,
    db: SessionLocal,
) -> None:
    """
    Inserts POST jobs idempotently.
    One URL = one job.
    """

    for url in urls:
        job = ScrapeJob(
            job_type=ScrapeJobType.POST,
            entity_key=url,
            source=source,
            status=ScrapeJobStatus.PENDING,
        )
        try:
            db.add(job)
            db.commit()
        except IntegrityError:
            db.rollback()  # duplicate → expected
