import sys
import os
from pathlib import Path

# Add project root to path so imports work
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.app.core.logging_config import logger
from src.app.core.config import settings

def test_logger():
    print("--- Testing Logger (from scripts folder) ---")
    logger.info("This is an INFO message for testing.")
    logger.warning("This is a WARNING message for testing.")
    logger.error("This is an ERROR message for testing.")
    
    log_file = settings.LOG_FILE
    if os.path.exists(log_file):
        print(f"Log file created at: {os.path.abspath(log_file)}")
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                print(f"Last line in log file: {lines[-1].strip()}")
            else:
                print("Log file is empty.")
    else:
        print(f"Error: Log file NOT found at {log_file}")

if __name__ == "__main__":
    test_logger()
