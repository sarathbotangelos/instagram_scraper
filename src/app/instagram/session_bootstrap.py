import instaloader
from src.app.core.config import settings
from src.app.core.logging_config import logger

def create_session():
    L = instaloader.Instaloader()

    try:
        L.login(settings.IG_USERNAME, settings.IG_PASSWORD)
        L.save_session_to_file(
            filename=f"/sessions/{settings.IG_USERNAME}.session"
        )

        logger.info("Session created successfully")

    except Exception as e:
        logger.error("Failed to create session: %s", e)


if __name__ == "__main__":
    create_session()