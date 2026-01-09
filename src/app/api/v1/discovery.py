from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from src.app.core.db.session import get_db
from src.app.services.orchestrator import run_discovery

router = APIRouter()

@router.post("/")
async def discover(prompt: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Triggers the LLM-driven discovery process in the background.
    """
    background_tasks.add_task(run_discovery, prompt, db)
    return {"message": f"Discovery process started for prompt: '{prompt}'"}
