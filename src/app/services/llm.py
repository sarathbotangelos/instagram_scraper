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

    SYSTEM_PROMPT = (
        "You generate Google search queries.\n"
        "Output plain text only.\n"
        "One query per line.\n"
        "Do NOT use JSON.\n"
        "Do NOT use Markdown.\n"
        "Do NOT use code blocks.\n"
        "Never return empty output."
    )

    def call_llm(user_prompt: str) -> str:
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            temperature=0,
            max_tokens=256,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        msg = response.choices[0].message
        return (msg.content or "").strip()

    try:
        # ---------- FIRST ATTEMPT ----------
        content = call_llm(prompt)
        logger.info("LLM raw output: %r", content)

        # ---------- HARD CONTRACT VALIDATION ----------
        if not content:
            raise ValueError("LLM returned empty content")

        forbidden_tokens = ("```", "{", "}", "[", "]", "json")
        if any(tok in content.lower() for tok in forbidden_tokens):
            raise ValueError("LLM violated output contract")

        queries = [line.strip() for line in content.splitlines() if line.strip()]

        if not queries:
            raise ValueError("No valid queries after parsing")

        logger.info("Query generation successful: %d queries", len(queries))
        return queries

    except Exception as first_error:
        logger.warning("Primary LLM call failed: %s", first_error)

        # ---------- SINGLE DETERMINISTIC RETRY ----------
        retry_prompt = (
            "Generate 5 Google search queries.\n"
            "Kerala wedding photographers."
        )

        try:
            content = call_llm(retry_prompt)
            logger.info("LLM retry output: %r", content)

            if not content:
                raise ValueError("Retry returned empty content")

            forbidden_tokens = ("```", "{", "}", "[", "]", "json")
            if any(tok in content.lower() for tok in forbidden_tokens):
                raise ValueError("Retry violated output contract")

            queries = [line.strip() for line in content.splitlines() if line.strip()]

            if not queries:
                raise ValueError("Retry produced no valid queries")

            logger.info(
                "Query generation successful after retry: %d queries",
                len(queries),
            )
            return queries

        except Exception:
            logger.exception("LLM query generation failed after retry")
            return []
