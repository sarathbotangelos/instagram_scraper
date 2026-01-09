from fastapi import FastAPI
from src.app.api.v1.discovery import router as discovery_router
from src.app.api.v1.health import router as health_router

app = FastAPI(title="Instagram Scrapper API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Welcome to Instagram Scrapper API", "status": "running"}

# Include API routers
app.include_router(discovery_router, prefix="/api/v1/discovery", tags=["discovery"])
app.include_router(health_router, prefix="/api/v1/health", tags=["health"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
