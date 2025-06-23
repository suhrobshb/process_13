import os
import yaml
from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from ai_engine.database import create_db_and_tables
from ai_engine.routers import task_router, workflow_router, execution_router

# load environment variables from .env
load_dotenv()

# load configuration
with open("config/default.yaml", "r") as f:
    config = yaml.safe_load(f)

app = FastAPI(title="AutoOps API")

# Add CORS middleware to allow requests from the dashboard UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/ping")
async def ping():
    return {"message": "pong"}

# Include routers
app.include_router(task_router.router, prefix="/api")
app.include_router(workflow_router.router, prefix="/api")
app.include_router(execution_router.router, prefix="/api")

@app.on_event("startup")
async def on_startup():
    create_db_and_tables()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config["server"]["host"],
        port=config["server"]["port"],
        reload=True
    )
