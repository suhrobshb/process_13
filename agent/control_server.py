import os
import threading
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# local import – recorder that captures multi-monitor events
# use full package path so it works when launched from repo root
from agent.recorder.multi_monitor_capture import MultiMonitorCapture
# upload helper
from agent.uploader import upload_recording

app = FastAPI(
    title="AutoOps Agent Control",
    docs_url=None,
    redoc_url=None,
)

# --- CORS (allow dashboard running on localhost:3000) ---
app.add_middleware(
    CORSMiddleware,
    # Allow any origin so that local `file:///...` pages or other tools can
    # interact with the control API without CORS errors during development.
    allow_origins=["*"],
    # POST for real request, OPTIONS for browser pre-flight
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Single recorder instance for this process
OUTPUT_DIR = os.getenv("AGENT_OUTPUT_DIR", "recordings/localhost")
recorder = MultiMonitorCapture(output_dir=OUTPUT_DIR, fps=2)

@app.post("/start")
def start_recording():
    """Begin screen / event capture in a background thread."""
    if getattr(recorder, "_running", False):
        raise HTTPException(400, "Already recording")

    threading.Thread(target=recorder.start, daemon=True).start()
    return {"status": "recording_started"}


# Expose both POST and GET for convenience/testing from browser address bar
@app.get("/start")
def start_recording_get():
    """GET wrapper for /start (calls the same logic)."""
    return start_recording()


@app.post("/stop")
def stop_recording(auto_upload: bool = True):
    """Stop capture and return output directory."""
    if not getattr(recorder, "_running", False):
        raise HTTPException(400, "Not recording right now")

    recorder.stop()
    # auto-upload
    upload_result = None
    if auto_upload:
        upload_url = os.getenv("TASK_UPLOAD_URL", "http://localhost:8000/api/tasks/upload")
        try:
            upload_recording(recorder.output_dir, upload_url)
            upload_result = "uploaded"
        except Exception as exc:  # pylint: disable=broad-except
            # Log the error but do not fail the stop endpoint
            upload_result = f"upload_failed: {exc}"

    return {
        "status": "recording_stopped",
        "output_dir": recorder.output_dir,
        "upload_status": upload_result,
    }


@app.get("/stop")
def stop_recording_get(auto_upload: bool = True):
    """GET wrapper for /stop (calls the same logic)."""
    return stop_recording(auto_upload=auto_upload)
