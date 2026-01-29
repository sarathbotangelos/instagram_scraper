import json
import re
from openai import OpenAI
from src.app.core.config import settings
from src.app.core.logging_config import logger



def generate_search_queries(prompt: str) -> list[str]:
    client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )

    system_prompt = (
        "You generate search queries for Google.\n"
        "Return ONLY a JSON array of strings.\n"
        "No explanation."
    )

    try:
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content
        logger.info("LLM raw output: %r", content)

        if not content or not content.strip():
            logger.warning("LLM returned empty content")
            return []

        # STEP 1: try strict JSON parse first
        try:
            parsed = json.loads(content)
            logger.info("Strict JSON parse succeeded")

        except json.JSONDecodeError as e:
            logger.warning("Strict JSON parse failed: %s", e)

            # STEP 2: fallback regex extraction
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if not json_match:
                logger.error("No JSON array found in LLM output")
                return []

            try:
                parsed = json.loads(json_match.group())
                logger.info("Regex JSON extraction succeeded")
            except Exception as e:
                logger.error("Regex JSON parse failed: %s", e)
                return []

        # STEP 3: type validation
        if not isinstance(parsed, list):
            logger.error("Parsed JSON is not a list: %s", type(parsed))
            return []

        # STEP 4: element validation
        final_queries = []
        for i, q in enumerate(parsed):
            if isinstance(q, str) and q.strip():
                final_queries.append(q.strip())
            else:
                logger.warning(
                    "Invalid query at index %d: %r (type=%s)",
                    i, q, type(q)
                )

        if not final_queries:
            logger.warning("Parsed list contained no valid string queries")
            return []

        logger.info(
            "Query generation successful: %d queries",
            len(final_queries)
        )

        return final_queries

    except Exception as e:
        logger.exception("LLM query generation crashed")
        return []
