"""
Recording Analysis Router
=========================

This module provides the API endpoint for processing user recordings. It acts as
the primary entry point for the AI Learning Engine, taking raw event data from
the frontend and initiating the analysis process.

Key Responsibilities:
-   **Receive Recording Data**: An endpoint to accept a list of captured user
    events (clicks, keystrokes, etc.) and any user-provided business context.
-   **Initiate Background Analysis**: Uses FastAPI's `BackgroundTasks` to run
    the `AILearningEngine` without blocking the HTTP response. This provides an
    immediate acknowledgment to the user while the heavy processing occurs.
-   **Integrate with Real-time Streaming**: Connects the `AILearningEngine`'s
    output to the WebSocket router. As the engine generates new action steps,
    this router ensures they are broadcasted to the correct client in real-time.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel

from ai_engine.auth import get_current_active_user
from ai_engine.models.user import User
from ai_engine.ai_learning_engine import AILearningEngine
from ai_engine.routers.real_time_router import broadcast_event_to_frontend, manager as ws_manager

# Configure logging
logger = logging.getLogger(__name__)

# Define the router for recording operations
router = APIRouter(
    tags=["Recording & Analysis"],
)

# --- Pydantic Models for API Requests ---

class RecordingAnalysisRequest(BaseModel):
    """
    Defines the expected request body for analyzing a recording.
    """
    recording_data: List[Dict[str, Any]]
    business_context: Optional[str] = "No context provided."


# --- Background Analysis Task ---

def run_analysis_and_stream(
    client_id: str,
    task_id: int, # A task ID from the database to associate the workflow with
    recording_data: List[Dict[str, Any]],
    business_context: str
):
    """
    This function is executed as a background task. It runs the AILearningEngine
    and streams the results back to the client via WebSocket.
    """
    logger.info(f"Starting background analysis for client: {client_id}, task_id: {task_id}")

    # Define the callback function that the AILearningEngine will invoke
    # for each generated node.
    def sync_stream_callback(event_data: Dict[str, Any]):
        """
        A synchronous wrapper that calls the async broadcast function.
        This is necessary because the AILearningEngine is a synchronous class.
        """
        try:
            # Run the async broadcast function in a new event loop.
            # For production, a shared event loop managed by a separate thread
            # might be more efficient, but this is simpler and effective.
            asyncio.run(broadcast_event_to_frontend(task_id, event_data))
        except Exception as e:
            logger.error(f"Error in stream callback for task {task_id}: {e}", exc_info=True)

    try:
        # Instantiate the learning engine with the data and the callback
        learning_engine = AILearningEngine(
            recording_data=recording_data,
            business_context=business_context,
            stream_callback=sync_stream_callback
        )
        
        # This is a blocking, synchronous call that will invoke the callback
        # multiple times as it processes the data.
        final_workflow = learning_engine.analyze_and_generate_workflow()
        
        # After analysis is complete, send a final message to the client
        final_event = {
            "event": "analysis_complete",
            "task_id": task_id,
            "payload": final_workflow
        }
        asyncio.run(broadcast_event_to_frontend(task_id, final_event))
        
        logger.info(f"Analysis complete for task_id: {task_id}")

    except Exception as e:
        logger.error(f"Error during analysis for task_id {task_id}: {e}", exc_info=True)
        # Notify the client of the failure
        error_event = {
            "event": "analysis_failed",
            "task_id": task_id,
            "payload": {"error": str(e)}
        }
        asyncio.run(broadcast_event_to_frontend(task_id, error_event))


# --- API Endpoint to Trigger Analysis ---

@router.post("/recording/{task_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_recording(
    task_id: int,
    request: RecordingAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Receives raw recording data and triggers the AI analysis in the background.
    
    The results are streamed back to the client via the WebSocket connection
    established at `/ws/recording/{task_id}`.
    """
    if not request.recording_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="`recording_data` field cannot be empty."
        )

    # Check if a WebSocket client is actually listening for this task_id.
    # While not strictly required, it prevents starting analysis that no one is listening to.
    if task_id not in ws_manager.active_connections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active WebSocket listener for task_id: {task_id}. Please connect to the WebSocket first."
        )

    # Add the analysis task to run in the background.
    # The `client_id` can be used for logging or more complex session management if needed.
    # For now, we primarily use `task_id` to route messages.
    client_id = f"user_{current_user.id}_task_{task_id}"
    background_tasks.add_task(
        run_analysis_and_stream,
        client_id,
        task_id,
        request.recording_data,
        request.business_context
    )

    return {
        "status": "analysis_started",
        "message": f"AI analysis for task {task_id} has been initiated. Results will be streamed via WebSocket."
    }
