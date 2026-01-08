import sys
from apify_client import ApifyClient
from src.core.config import settings
from src.core.logging_config import logger
from scripts.seed_user import seed_user
from scripts.seed_posts import seed_posts
from scripts.link_scraper import process_user_links

def apify_fetch_hashtag_users(hashtag: str, limit: int = 50):
    """
    Fetches Instagram usernames from Apify for a given hashtag.
    """
    client = ApifyClient(settings.APIFY_API_TOKEN)

    # Actor input configuration
    # Note: These parameters depend on the specific Apify Actor used.
    # 'apify/instagram-hashtag-scraper' usually takes 'hashtags' and 'resultsLimit'
    run_input = {
        "hashtags": [hashtag],
        "resultsLimit": limit,
    }

    logger.info("Starting Apify Actor %s for hashtag #%s (limit=%d)", settings.APIFY_INSTAGRAM_ACTOR, hashtag, limit)
    
    # Run the Actor and wait for it to finish
    run = client.actor(settings.APIFY_INSTAGRAM_ACTOR).call(run_input=run_input)

    usernames = set()
    logger.info("Fetching results from Apify dataset %s", run["defaultDatasetId"])
    
    # Fetch results from the run's dataset
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        # The exact field name depends on the Actor's output schema.
        # Often it's 'ownerUsername' or 'username' under a post object.
        username = item.get("ownerUsername") or item.get("username")
        if username:
            usernames.add(username)

    logger.info("Discovered %d unique usernames for hashtag #%s", len(usernames), hashtag)
    return list(usernames)

def discover_and_seed_by_hashtag(hashtag: str, limit: int = 50):
    """
    Discovers accounts by hashtag and seeds them into the database.
    """
    usernames = apify_fetch_hashtag_users(hashtag, limit)

    for username in usernames:
        try:
            logger.info("Seeding discovered user: %s", username)
            seed_user(username)
            # call process userlinks
            logger.info("Processing user links for %s...", username)
            process_user_links(username) 
            # seed the posts
            logger.info("Seeding posts for %s...", username)
            seed_posts(username)
        except Exception as e:
            logger.error("Failed to seed user %s: %s", username, str(e))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.discover_accounts <hashtag> [limit]")
        sys.exit(1)

    tag = sys.argv[1].lstrip('#')
    limit_val = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    discover_and_seed_by_hashtag(tag, limit_val)
