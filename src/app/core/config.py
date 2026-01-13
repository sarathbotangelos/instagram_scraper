from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    # Base directory of the project
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # Database
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_NAME: str

    # Apify
    APIFY_API_TOKEN: str
    APIFY_INSTAGRAM_ACTOR: str = "apify/instagram-hashtag-scraper"
    APIFY_BASE_URL: str = "https://api.apify.com/v2"

    # DeepSeek / OpenRouter
    DEEPSEEK_API_KEY: str
    DEEPSEEK_BASE_URL: str = "https://openrouter.ai/api/v1"
    DEEPSEEK_MODEL: str = "deepseek/deepseek-r1-0528:free"

    # Google
    GOOGLE_API_KEY : str
    GOOGLE_CSE_ID : str

    # Instagram
    IG_USERNAME : str
    IG_PASSWORD : str

    # User Agent
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "sys_logs/app.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
