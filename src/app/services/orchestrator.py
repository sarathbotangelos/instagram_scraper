from sqlalchemy.orm import Session
from src.app.services.llm import generate_search_queries
from src.app.services.google_search import google_search_instagram_posts
from src.app.services.extractors import extract_username_from_post
# from src.app.jobs.enqueue import enqueue_profile_jobs
# from src.app.jobs.enums import ScrapeJobSource
import logging

logger = logging.getLogger(__name__)


def run_discovery(prompt: str, db: Session) -> None:
    """
    Discovery = query generation + Google search + URL enqueue.
    No Instagram fetch. No username parsing.
    """

    logger.info("Discovery started for prompt: %s", prompt)

    queries = generate_search_queries(prompt)
    if not queries:
        logger.warning("No queries generated from prompt")
        return

    discovered_urls: set[str] = set()

    for query in queries:
        urls = google_search_instagram_posts(query, limit=20)
        for url in urls:
            # keep only posts/reels
            if "/p/" in url or "/reel/" in url:
                discovered_urls.add(url.split("?")[0])

    if not discovered_urls:
        logger.info("No post URLs discovered")
        return

    # enqueue_post_jobs(
    #     urls=discovered_urls,
    #     source=ScrapeJobSource.GOOGLE,
    #     db=db,
    # )

    logger.info("Discovered URLs: %s", discovered_urls)

    logger.info("Discovery finished. POST jobs enqueued: %d", len(discovered_urls))


def discover_usernames_from_queries(queries: list[str]) -> set[str]:
    """
    Runs Google search for each query and extracts unique Instagram usernames.
    Pure function. No DB access.
    """

    discovered: set[str] = set()

    for query in queries:
        post_urls = google_search_instagram_posts(query, limit=20)

        for post_url in post_urls:
            username = extract_username_from_post(post_url)
            if username:
                discovered.add(username)

    return discovered
