from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.app.core.db.session import get_db
from src.app.services.health_service import check_db_health

router = APIRouter()

@router.get("/db")
async def db_health(db: Session = Depends(get_db)):
    """
    Verifies the database connection.
    """
    result = check_db_health(db)
    if not result:
        raise HTTPException(status_code=500, detail="Database connection failed")
    return result
