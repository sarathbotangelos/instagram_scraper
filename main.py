import sys
from scripts.seed_user import seed_user
from scripts.seed_posts import seed_posts
from scripts.link_scraper import process_user_links
from scripts.discover_accounts import discover_users_by_hashtags, seed_discovered_users
from scripts.llm_utils import generate_hashtags
from src.core.cache import FileCache
from src.core.logging_config import logger

def main():
    if len(sys.argv) < 2:
        # Default behavior: run discovery for wedding photographers if no argument
        prompt = "find kerala wedding photographers"
    else:
        prompt = sys.argv[1]

    if prompt.startswith("@"):
        # Handle specific username seeding if prompt starts with @
        username = prompt.lstrip("@")
        logger.info("Starting direct seed for username=%s", username)
        seed_user(username)
        process_user_links(username)
        seed_posts(username)
        logger.info("Direct seed completed for username=%s", username)
        return

    # LLM-driven flow
    logger.info("Processing prompt: '%s'", prompt)
    
    # 1. Generate hashtags
    hashtags = generate_hashtags(prompt)
    if not hashtags:
        logger.error("No hashtags generated for prompt. Exiting.")
        return

    # 2. Discover users for these hashtags
    # Using a smaller limit per tag since we have multiple tags
    limit_per_tag = 20
    logger.info("Discovering users for hashtags: %s (limit=%d per tag)", hashtags, limit_per_tag)
    hashtag_map = discover_users_by_hashtags(hashtags, limit_per_tag)

    # 3. Seed discovered users
    seed_discovered_users(hashtag_map)
    
    logger.info("LLM-driven discovery and seeding process complete.")

if __name__ == "__main__":
    main()
