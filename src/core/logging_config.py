import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from src.core.config import settings

def setup_logging():
    # Ensure logs directory exists
    log_file_path = Path(settings.LOG_FILE)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Base configuration
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            # Rotating File Handler
            RotatingFileHandler(
                settings.LOG_FILE,
                maxBytes=settings.LOG_MAX_BYTES,
                backupCount=settings.LOG_BACKUP_COUNT,
                encoding="utf-8"
            ),
            # Console Handler
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized with level %s", settings.LOG_LEVEL)
    return logger

# Initialize logger
logger = setup_logging()
