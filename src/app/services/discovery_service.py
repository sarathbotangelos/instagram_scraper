import json
import re
from openai import OpenAI
from apify_client import ApifyClient
from src.app.core.config import settings
from src.app.core.logging_config import logger
from src.app.services.seeding_service import run_full_seed_flow
from sqlalchemy.orm import Session

def generate_hashtags(prompt: str) -> list[str]:
    """
    Generates a list of relevant Instagram hashtags for a given prompt using DeepSeek LLM.
    """
    client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL
    )

    system_prompt = (
        "You are an Instagram marketing expert. "
        "Given a user request, generate a list of the 5-10 most relevant, high-traffic Instagram hashtags. "
        "Return the hashtags as a JSON array of strings, without the '#' symbol. "
        "Only return the JSON array, nothing else."
    )

    logger.info("Requesting hashtags from DeepSeek for prompt: %s", prompt)
    
    try:
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            extra_headers={
                "HTTP-Referer": "https://github.com/google-deepmind/antigravity",
                "X-Title": "Insta Scraper Photographers",
            }
        )

        content = response.choices[0].message.content
        json_match = re.search(r'\[.*\]|\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                data = []
        else:
            data = []

        if isinstance(data, dict):
            for key in ["hashtags", "tags", "results"]:
                if key in data and isinstance(data[key], list):
                    hashtags = data[key]
                    break
            else:
                for val in data.values():
                    if isinstance(val, list):
                        hashtags = val
                        break
                else:
                    hashtags = []
        elif isinstance(data, list):
            hashtags = data
        else:
            hashtags = []

        cleaned_hashtags = [re.sub(r'#', '', tag).strip() for tag in hashtags if tag]
        logger.info("Generated hashtags: %s", cleaned_hashtags)
        return cleaned_hashtags

    except Exception as e:
        logger.error("Failed to generate hashtags: %s", str(e))
        return []

def apify_fetch_hashtag_users(hashtag: str, limit: int = 50):
    client = ApifyClient(settings.APIFY_API_TOKEN)
    tag = hashtag.lstrip('#')
    run_input = {
        "hashtags": [tag],
        "resultsLimit": limit,
    }

    logger.info("Starting Apify Actor %s for hashtag #%s (limit=%d)", settings.APIFY_INSTAGRAM_ACTOR, tag, limit)
    
    try:
        run = client.actor(settings.APIFY_INSTAGRAM_ACTOR).call(run_input=run_input)
        usernames = set()
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            username = item.get("ownerUsername") or item.get("username")
            if username:
                usernames.add(username)
        return list(usernames)
    except Exception as e:
        logger.error("Apify fetch failed for #%s: %s", tag, str(e))
        return []

def run_discovery(prompt: str, db: Session):
    """
    Executes the full discovery flow: generate hashtags -> discover users -> seed users.
    """
    logger.info("Processing prompt: '%s'", prompt)
    hashtags = generate_hashtags(prompt)
    if not hashtags:
        logger.error("No hashtags generated for prompt.")
        return

    limit_per_tag = 20
    processed_users = set()

    for tag in hashtags:
        logger.info("Processing hashtag: #%s", tag)
        # usernames = apify_fetch_hashtag_users(tag, limit_per_tag)
        # for username in usernames:
        #     if username in processed_users:
        #         continue
        #     try:
        #         run_full_seed_flow(username, db)
        #         processed_users.add(username)
        #     except Exception as e:
        #         logger.error("Failed to seed user %s: %s", username, str(e))

    logger.info("LLM-driven discovery and seeding process complete.")
