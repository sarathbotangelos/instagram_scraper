
import sys
import os
from pathlib import Path

# Add the project root to sys.path to allow imports from src
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

try:
    from src.app.services.email_service import send_alert_email
    print("Successfully imported email_service.")
except ImportError as e:
    print(f"Error importing email_service: {e}")
    # This might happen if logging_config is missing or other dependencies are not met
    print("Check if all dependencies (like logging_config) are present.")
    sys.exit(1)

def main():
    print("Attempting to send test email...")
    try:
        # Using the hardcoded credentials in email_service.py for now
        result = send_alert_email(
            subject="Test Alert from Script",
            body="This is a manual test of the email service function.",
            error_details="No error, just verified via scripts/test_email.py"
        )
        if result:
            print("Email sent successfully!")
        else:
            print("Email returned False. Check logs for details.")
    except Exception as e:
        print(f"Exception during email send: {e}")

if __name__ == "__main__":
    main()
