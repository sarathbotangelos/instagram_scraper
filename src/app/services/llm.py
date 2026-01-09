import json
import re
from openai import OpenAI
from src.app.core.config import settings
from src.app.core.logging_config import logger



def generate_search_queries(prompt: str) -> list[str]:
    """
    Generates Google-search-optimized queries (hashtags + phrases)
    for Instagram discovery.
    """

    client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )

    system_prompt = (
        "You generate search queries for Google.\n"
        "Given a user request, return 5–10 search queries suitable for Google Search "
        "to find Instagram posts and profiles.\n"
        "Include a mix of:\n"
        "- natural language phrases\n"
        "- hashtags (with #)\n\n"
        "Return ONLY a JSON array of strings. No explanation."
    )

    try:
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if not json_match:
            return []

        queries = json.loads(json_match.group())
        final_queries = [q.strip() for q in queries if isinstance(q, str) and q.strip()]
        
        logger.info("Generated search queries: %s", final_queries)
        return final_queries

    except Exception as e:
        logger.error(f"Failed to generate search queries, {e}")
        return []
