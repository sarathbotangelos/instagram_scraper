from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    # Base directory of the project
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # Database
    DATABASE_URL: str

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
