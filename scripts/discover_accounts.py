import sys
from apify_client import ApifyClient
from src.app.core.config import settings
from src.app.core.logging_config import logger
from scripts.seed_user import seed_user
from scripts.seed_posts import seed_posts
from scripts.link_scraper import process_user_links

def apify_fetch_hashtag_users(hashtag: str, limit: int = 50):
    """
    Fetches Instagram usernames from Apify for a given hashtag.
    """
    client = ApifyClient(settings.APIFY_API_TOKEN)
    
    # Clean the hashtag (Apify Actor expects no '#' prefix)
    tag = hashtag.lstrip('#')

    # Actor input configuration
    run_input = {
        "hashtags": [tag],
        "resultsLimit": limit,
    }

    logger.info("Starting Apify Actor %s for hashtag #%s (limit=%d)", settings.APIFY_INSTAGRAM_ACTOR, tag, limit)
    
    try:
        # Run the Actor and wait for it to finish
        run = client.actor(settings.APIFY_INSTAGRAM_ACTOR).call(run_input=run_input)

        usernames = set()
        logger.info("Fetching results from Apify dataset %s", run["defaultDatasetId"])
        
        # Fetch results from the run's dataset
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            username = item.get("ownerUsername") or item.get("username")
            if username:
                usernames.add(username)

        logger.info("Discovered %d unique usernames for hashtag #%s", len(usernames), tag)
        return list(usernames)
    except Exception as e:
        logger.error("Apify fetch failed for #%s: %s", tag, str(e))
        return []

def discover_users_by_hashtags(hashtags: list[str], limit_per_tag: int = 50) -> dict[str, list[str]]:
    """
    Runs discovery for multiple hashtags and returns a mapping of {hashtag: [usernames]}.
    """
    hashtag_to_users = {}
    for tag in hashtags:
        usernames = apify_fetch_hashtag_users(tag, limit_per_tag)
        hashtag_to_users[tag] = usernames

    logger.info("Discovered users for hashtags: %s", hashtag_to_users)    
    return hashtag_to_users

def seed_discovered_users(hashtag_map: dict[str, list[str]]):
    """
    Seeds users from the hashtag mapping into the database.
    """
    total_users = sum(len(users) for users in hashtag_map.values())
    processed_users = set()
    
    logger.info("Starting seeding for %d discovered users from %d hashtags", total_users, len(hashtag_map))

    for tag, usernames in hashtag_map.items():
        logger.info("Processing users for hashtag #%s", tag)
        for username in usernames:
            if username in processed_users:
                logger.info("User %s already processed in this run, skipping duplicate.", username)
                continue
                
            try:
                logger.info("Seeding user: %s", username)
                seed_user(username)
                
                logger.info("Processing user links for %s...", username)
                process_user_links(username) 
                
                logger.info("Seeding posts for %s...", username)
                seed_posts(username)
                
                processed_users.add(username)
            except Exception as e:
                logger.error("Failed to seed user %s: %s", username, str(e))

def discover_and_seed_by_hashtag(hashtag: str, limit: int = 50):
    """
    Backward compatibility wrapper for discovering and seeding a single hashtag.
    """
    mapping = discover_users_by_hashtags([hashtag], limit)
    seed_discovered_users(mapping)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.discover_accounts <hashtag> [limit]")
        sys.exit(1)

    tag = sys.argv[1]
    limit_val = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    discover_and_seed_by_hashtag(tag, limit_val)
