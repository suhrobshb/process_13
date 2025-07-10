"""
WebSocket Router for Real-time Communication
============================================

This module provides the real-time communication layer for the AI Engine,
enabling a live, interactive user experience during the recording and analysis
process.

Key Features:
-   **Connection Management**: A robust manager for handling multiple concurrent
    WebSocket clients, ensuring each user receives their own data stream.
-   **Real-time Event Streaming**: Establishes a WebSocket endpoint that the
    frontend can connect to for receiving live updates.
-   **Action Box Generation Broadcasting**: Integrates with the AILearningEngine
    to stream AI-generated action step boxes to the UI as they are created,
    providing immediate feedback to the user during the analysis phase.

This router is essential for creating the "live AI" feeling of the platform,
where the user can see the system thinking and building the workflow in real-time.
"""

import asyncio
import logging
from typing import Dict, List, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks

from ai_engine.ai_learning_engine import AILearningEngine

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["websockets"])


# --- Connection Manager ---

class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        logger.info("ConnectionManager initialized.")

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accepts a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client connected: {client_id}. Total clients: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        """Disconnects a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client disconnected: {client_id}. Total clients: {len(self.active_connections)}")

    async def broadcast_json(self, data: Dict[str, Any], client_id: str):
        """Sends a JSON message to a specific client."""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(data)
                logger.debug(f"Broadcasted to client {client_id}: {data.get('type')}")
            except WebSocketDisconnect:
                self.disconnect(client_id)
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {e}")
                self.disconnect(client_id)


# Instantiate the manager
manager = ConnectionManager()


# --- WebSocket Endpoint ---

@router.websocket("/ws/recording/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    The main WebSocket endpoint for real-time recording and analysis updates.
    """
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Keep the connection alive. The server will push data.
            # We can also handle incoming messages from the client here if needed.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"Unhandled error in WebSocket for client {client_id}: {e}")
        manager.disconnect(client_id)


# --- Analysis Task ---

def run_analysis_and_stream(
    client_id: str,
    recording_data: List[Dict[str, Any]],
    business_context: str
):
    """
    A background task that runs the AI Learning Engine and streams results.
    """
    logger.info(f"Starting background analysis for client: {client_id}")

    # Define the callback function to be used by the learning engine
    async def stream_callback(node_data: Dict[str, Any]):
        await manager.broadcast_json({
            "type": "NEW_WORKFLOW_NODE",
            "payload": node_data
        }, client_id)

    # The stream_callback needs to be called within an async context.
    # We create a wrapper that can be called from the sync AILearningEngine.
    def sync_stream_callback(node_data: Dict[str, Any]):
        # asyncio.run_coroutine_threadsafe is ideal for calling async code
        # from a synchronous thread, but for simplicity in this context,
        # we can create a new event loop for each callback.
        # In a more complex app, a shared event loop and thread would be better.
        asyncio.run(stream_callback(node_data))

    try:
        # Instantiate the learning engine with the callback
        learning_engine = AILearningEngine(
            recording_data=recording_data,
            business_context=business_context,
            stream_callback=sync_stream_callback
        )
        
        # Run the analysis (this is a synchronous call)
        final_workflow = learning_engine.analyze_and_generate_workflow()
        
        # Send a final message indicating completion
        asyncio.run(manager.broadcast_json({
            "type": "ANALYSIS_COMPLETE",
            "payload": final_workflow
        }, client_id))
        
        logger.info(f"Analysis complete for client: {client_id}")

    except Exception as e:
        logger.error(f"Error during analysis for client {client_id}: {e}", exc_info=True)
        # Notify the client of the failure
        asyncio.run(manager.broadcast_json({
            "type": "ANALYSIS_FAILED",
            "payload": {"error": str(e)}
        }, client_id))


# --- API Endpoint to Trigger Analysis ---

@router.post("/recording/{client_id}/analyze")
async def analyze_recording(
    client_id: str,
    background_tasks: BackgroundTasks,
    request_data: Dict[str, Any]
):
    """
    Receives raw recording data and triggers the AI analysis in the background.
    Streams the results back to the client via WebSocket.
    """
    recording_data = request_data.get("recording_data")
    business_context = request_data.get("business_context", "No context provided.")

    if not recording_data:
        raise HTTPException(status_code=400, detail="recording_data is required.")

    # Check if the client is connected via WebSocket
    if client_id not in manager.active_connections:
        raise HTTPException(status_code=404, detail=f"No active WebSocket connection for client_id: {client_id}")

    # Add the analysis task to run in the background
    background_tasks.add_task(
        run_analysis_and_stream,
        client_id,
        recording_data,
        business_context
    )

    return {
        "status": "success",
        "message": "Analysis started. Results will be streamed via WebSocket."
    }
