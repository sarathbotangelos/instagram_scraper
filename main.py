from scripts.seed_user import seed_user
from scripts.link_scraper import process_user_links
from scripts.seed_posts import seed_posts
from src.core.cache import FileCache
from src.core.logging_config import logger


def main():
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("usage: python main.py <instagram_username>")

    username = sys.argv[1]
    logger.info("Starting seed for username=%s", username)

    user = seed_user(username)
    logger.info("Seed completed for username=%s", user.username)

    # Retrieve username from cache
    cached_username = FileCache.get("last_seeded_username")
    
    if cached_username:
        # Retrieve the specific post count for this user
        cached_posts_count = FileCache.get(f"{cached_username}_posts_count") or 12
        
        logger.info("Retrieved username from cache: %s. Starting link processing...", cached_username)
        process_user_links(cached_username)
        
        logger.info("Starting post seeding for %s (count=%s)...", cached_username, cached_posts_count)
        seed_posts(cached_username, count=cached_posts_count)
    else:
        logger.warning("No username found in cache. Skipping link processing.")


if __name__ == "__main__":
    main()
