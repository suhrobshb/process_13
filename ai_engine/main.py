"""
Main FastAPI application bootstrap.

This module is responsible for:
1. Creating the FastAPI app instance
2. Wiring CORS / middleware
3. Registering all API routers
4. Initialising long-running background services (TriggerEngine)
5. Providing a graceful shutdown via FastAPI lifespan

It now uses the modern `lifespan` interface instead of the deprecated
`@app.on_event("startup" | "shutdown")` decorators in order to silence the
FastAPI deprecation warnings visible during the test-suite run.
"""

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request, Response
from .routers import (
    task_router,
    workflow_router,
    execution_router,
)
from .routers.auth_router import router as auth_router
from .scenario_library import router as library_router

from .trigger_engine import TriggerEngine
from .database import create_db_and_tables

# --------------------------------------------------------------------------- #
# Structured / audit logging configuration
# --------------------------------------------------------------------------- #

import json
import logging
import time

# Configure root logger to emit JSON-structured logs so they can be parsed by
# Cloud Logging / ELK easily.  Only run once to avoid duplicate handlers when
# this module is re-imported by test runners.
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

def _json_log(event: str, **extra):
    """
    Helper that emits a single JSON-formatted log line.
    """
    logging.getLogger("ai_engine").info(json.dumps({"event": event, **extra}))

# --------------------------------------------------------------------------- #
# CORS configuration
# --------------------------------------------------------------------------- #

cors_config = {
    "allow_origins": ["*"],  # TODO: tighten this in production
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

# --------------------------------------------------------------------------- #
# Lifespan ‑ replaces the deprecated @app.on_event decorators
# --------------------------------------------------------------------------- #

trigger_engine = TriggerEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler.

    Starts the TriggerEngine in a background thread and guarantees a clean
    shutdown once the application stops.
    """

    # ----- Startup --------------------------------------------------------- #
    create_db_and_tables()

    thread = threading.Thread(target=trigger_engine.start, daemon=True)
    thread.start()

    try:
        # Instrument Prometheus metrics (lazy import to avoid hard-dep in tests)
        try:
            from prometheus_fastapi_instrumentator import Instrumentator

            Instrumentator().instrument(app).expose(app, include_in_schema=False)
            _json_log("metrics_enabled")
        except ModuleNotFoundError:
            _json_log("metrics_disabled")

        yield
    finally:
        # ----- Shutdown ---------------------------------------------------- #
        trigger_engine.stop()
        # Give the thread a moment to finish its current tick
        thread.join(timeout=1)


# --------------------------------------------------------------------------- #
# App instance
# --------------------------------------------------------------------------- #

app = FastAPI(
    title="HR Interview Automation",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    **cors_config,
)

# --------------------------------------------------------------------------- #
# Security headers & audit-logging middleware
# --------------------------------------------------------------------------- #

@app.middleware("http")
async def add_security_headers_and_audit(request: Request, call_next):
    """
    Middleware that:
    1. Adds common security headers to every response
    2. Emits an audit log entry for every request/response pair
    """
    start = time.time()
    response: Response = await call_next(request)

    # --- Security headers -------------------------------------------------- #
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Only set HSTS when running behind HTTPS (prod). For dev it's disabled.
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"

    # --- Audit log --------------------------------------------------------- #
    duration_ms = int((time.time() - start) * 1000)
    _json_log(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
        client_ip=request.client.host if request.client else None,
        # For privacy, we only log *whether* the header is present:
        authenticated=bool(request.headers.get("authorization")),
    )

    return response

# Include routers
# NOTE:
# Each individual router already declares its own functional prefix
# (e.g.  task_router → “/tasks”, workflow_router → “/workflows”, …).
# Adding another sub-prefix here produced duplicated paths such
# as “/api/workflows/workflows”.  We therefore only retain the common
# “/api” prefix at the application level.
app.include_router(task_router.router,     prefix="/api")
app.include_router(workflow_router.router, prefix="/api")
app.include_router(execution_router.router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(library_router, prefix="/api")

# --------------------------------------------------------------------------- #
# Misc utility endpoints
# --------------------------------------------------------------------------- #

@app.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    """Light-weight health-check used by Docker / k8s."""
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "HR Interview Automation API"} 