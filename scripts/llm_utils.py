from openai import OpenAI
from src.core.config import settings
from src.core.logging_config import logger
import json
import re

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
                "HTTP-Referer": "https://github.com/google-deepmind/antigravity", # Optional, for OpenRouter ranking
                "X-Title": "Insta Scraper Photographers", # Optional, for OpenRouter ranking
            }
        )

        content = response.choices[0].message.content
        logger.debug("LLM response content: %s", content)
        
        # Try to find JSON in the content (handles cases with markdown code blocks)
        json_match = re.search(r'\[.*\]|\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                data = []
        else:
            data = []

        # Handle cases where LLM might return {"hashtags": [...]} or just [...]
        if isinstance(data, dict):
            # Try to find a list in the dictionary
            for key in ["hashtags", "tags", "results"]:
                if key in data and isinstance(data[key], list):
                    hashtags = data[key]
                    break
            else:
                # If no known key, take the first list found
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

        # Clean hashtags: remove # and whitespace
        cleaned_hashtags = [re.sub(r'#', '', tag).strip() for tag in hashtags if tag]
        
        logger.info("Generated hashtags: %s", cleaned_hashtags)
        return cleaned_hashtags

    except Exception as e:
        logger.error("Failed to generate hashtags: %s", str(e))
        return []

if __name__ == "__main__":
    # Test
    import sys
    test_prompt = sys.argv[1] if len(sys.argv) > 1 else "kerala wedding photographers"
    tags = generate_hashtags(test_prompt)
    print(f"Hashtags for '{test_prompt}': {tags}")
