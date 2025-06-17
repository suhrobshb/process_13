from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import task_router, workflow_router, execution_router
from .trigger_engine import TriggerEngine
from .database import engine, create_db_and_tables
import threading

app = FastAPI(title="HR Interview Automation")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(task_router.router, prefix="/api/tasks")
app.include_router(workflow_router.router, prefix="/api/workflows")
app.include_router(execution_router.router, prefix="/api/executions")

# Initialize trigger engine
trigger_engine = TriggerEngine()

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()
    # Start trigger engine in background thread
    threading.Thread(target=trigger_engine.start, daemon=True).start()

@app.on_event("shutdown")
async def shutdown_event():
    trigger_engine.stop()

@app.get("/")
async def root():
    return {"message": "HR Interview Automation API"} 