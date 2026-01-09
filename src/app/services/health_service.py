from sqlalchemy.orm import Session
from sqlalchemy import text
from src.app.core.logging_config import logger

def check_db_health(db: Session):
    """
    Verifies the database connection.
    """
    try:
        # Execute a simple query to check the connection
        db.execute(text("SELECT 1"))
        return {"status": "success", "message": "Database connection is healthy"}
    except Exception as e:
        logger.error("Database connection check failed: %s", str(e))
        return None
