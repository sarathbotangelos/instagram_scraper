import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, UTC


from src.app.core.logging_config import logger

# ===================== EMAIL CONFIGURATION =====================
from src.app.core.config import settings

# ===================== EMAIL CONFIGURATION =====================
# Configuration is now loaded from src.app.core.config.settings
# ================================================================



def send_alert_email(subject: str, body: str, error_details: str = None) -> bool:
    """
    Send email alert when session dies or critical error occurs.
    
    Args:
        subject: Email subject line
        body: Main email body message
        error_details: Optional detailed error information
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = f"[Instagram Scraper Alert] {subject}"
        message["From"] = settings.EMAIL_SENDER
        message["To"] = settings.EMAIL_RECIPIENT
        
        # Create HTML email body
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="background-color: white; padding: 20px; border-radius: 5px; border-left: 4px solid #ff4444;">
                    <h2 style="color: #ff4444; margin-top: 0;">⚠️ Instagram Scraper Alert</h2>
                    <p><strong>Subject:</strong> {subject}</p>
                    <p><strong>Time:</strong> {timestamp}</p>
                    <hr>
                    <p><strong>Details:</strong></p>
                    <p>{body}</p>
        """
        
        if error_details:
            html_body += f"""
                    <hr>
                    <p><strong>Error Details:</strong></p>
                    <pre style="background-color: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto;">
{error_details}
                    </pre>
            """
        
        html_body += """
                    <hr>
                    <p style="color: #888; font-size: 12px;">
                        This is an automated alert from your Instagram scraper worker.
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Attach HTML to message
        message.attach(MIMEText(html_body, "html"))
        
        # Send email
        with smtplib.SMTP(settings.EMAIL_SERVER, settings.EMAIL_PORT) as server:
            server.starttls()  # Secure connection
            server.login(settings.EMAIL_SENDER, settings.EMAIL_PASSWORD)
            server.sendmail(settings.EMAIL_SENDER, settings.EMAIL_RECIPIENT, message.as_string())
        
        logger.info(f"Alert email sent successfully to {settings.EMAIL_RECIPIENT}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")
        return False