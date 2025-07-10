import os
import yaml
import subprocess
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from ai_engine.database import create_db_and_tables
from ai_engine.routers import task_router, workflow_router, execution_router

# Import new routers
from missing_api_endpoints import (
    dashboard_router, 
    recording_router, 
    nlp_router, 
    analytics_router,
    system_router,
    websocket_router
)

# load environment variables from .env
load_dotenv()

# load configuration
with open("config/default.yaml", "r") as f:
    config = yaml.safe_load(f)

app = FastAPI(title="Process 13 - Enhanced AutoOps API", version="2.0.0")

# Add CORS middleware for frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/ping")
async def ping():
    return {"message": "pong"}

# Include existing routers
app.include_router(task_router.router, prefix="/api", tags=["tasks"])
app.include_router(workflow_router.router, prefix="/api", tags=["workflows"])
app.include_router(execution_router.router, prefix="/api", tags=["executions"])

# Include new enhanced routers
app.include_router(dashboard_router, tags=["dashboard"])
app.include_router(recording_router, tags=["recording"])
app.include_router(nlp_router, tags=["nlp"])
app.include_router(analytics_router, tags=["analytics"])
app.include_router(system_router, tags=["system"])
app.include_router(websocket_router, tags=["websocket"])

def run_database_migrations():
    """Run Alembic database migrations"""
    try:
        # Run Alembic migrations
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        logging.info("Database migrations completed successfully")
    except subprocess.CalledProcessError as e:
        logging.warning(f"Alembic migration failed: {e.stderr}")
        # Fallback to SQLModel table creation
        logging.info("Falling back to SQLModel table creation")
        create_db_and_tables()
    except FileNotFoundError:
        logging.warning("Alembic not found, using SQLModel table creation")
        create_db_and_tables()

@app.on_event("startup")
async def on_startup():
    """Run startup tasks including database migrations"""
    run_database_migrations()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config["server"]["host"],
        port=config["server"]["port"],
        reload=True
    )
