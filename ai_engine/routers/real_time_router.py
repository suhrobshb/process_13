"""
Real-Time WebSocket Router
==========================

This module provides the real-time communication layer for the AI Engine,
enabling a live, interactive user experience during the recording and analysis
process. It uses WebSockets to push events and AI-generated action steps
to the frontend as they happen.

Key Features:
-   **Live Recording Feed**: Streams raw captured events (clicks, keystrokes)
    to the UI for immediate user feedback.
-   **Real-time Action Box Generation**: Broadcasts structured "Action Step"
    nodes as the AILearningEngine processes the recording, allowing users to
    see their workflow being built in real-time.
-   **Connection Management**: A simple in-memory manager for handling WebSocket
    clients. For production-scale deployments, this should be backed by a
    more robust system like Redis Pub/Sub.
"""

import asyncio
import logging
from typing import Dict, List, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/ws", tags=["Real-Time"])

# --- Connection Manager ---

class ConnectionManager:
    """Manages active WebSocket connections for real-time updates."""

    def __init__(self):
        # Maps a task_id to a list of active WebSocket connections for that task.
        self.active_connections: Dict[int, List[WebSocket]] = {}
        logger.info("Real-time ConnectionManager initialized.")

    async def connect(self, websocket: WebSocket, task_id: int):
        """Accepts and stores a new WebSocket connection."""
        await websocket.accept()
        connections = self.active_connections.setdefault(task_id, [])
        connections.append(websocket)
        logger.info(f"Client connected to task_id {task_id}. Total connections for task: {len(connections)}")

    def disconnect(self, websocket: WebSocket, task_id: int):
        """Removes a WebSocket connection."""
        if task_id in self.active_connections:
            self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
            logger.info(f"Client disconnected from task_id {task_id}.")

    async def broadcast_to_task(self, task_id: int, message: Dict[str, Any]):
        """Broadcasts a message to all clients connected to a specific task."""
        if task_id in self.active_connections:
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Handle cases where the connection might be closed unexpectedly
                    self.disconnect(connection, task_id)

# Instantiate the manager
manager = ConnectionManager()

# --- WebSocket Endpoint ---

@router.websocket("/recording/{task_id}")
async def websocket_recording(websocket: WebSocket, task_id: int):
    """
    WebSocket endpoint for a specific recording session.

    A frontend client connects to this endpoint to receive a live stream of
    events and AI-generated action steps for the given `task_id`.
    """
    await manager.connect(websocket, task_id)
    try:
        while True:
            # This loop keeps the connection alive and demonstrates pushing data.
            # In a real application, the push would be triggered by an external
            # system (like a Celery worker finishing a task) calling
            # `broadcast_event_to_frontend`.
            event = await get_next_event(task_id)
            await manager.broadcast_to_task(task_id, event)
    except WebSocketDisconnect:
        manager.disconnect(websocket, task_id)
    except Exception as e:
        logger.error(f"Error in WebSocket for task {task_id}: {e}")
        manager.disconnect(websocket, task_id)


# --- Helper Function for Broadcasting (to be called by other modules) ---

async def broadcast_event_to_frontend(task_id: int, event_data: Dict[str, Any]):
    """
    A helper function that other parts of the application (like the
    AILearningEngine or a task processor) can call to send real-time
    updates to the frontend.
    """
    await manager.broadcast_to_task(task_id, event_data)


# --- Stub for Demonstration ---

async def get_next_event(task_id: int) -> Dict:
    """
    Stub Function: In a real application, this logic would not live here.
    Instead, a message queue consumer (e.g., a Celery task listening to Redis)
    would call `broadcast_event_to_frontend`.

    This function is a placeholder to simulate receiving the next recording
    event for a given task_id from a message queue or another source.
    """
    # Simulate a short delay as if waiting for a message from a queue
    await asyncio.sleep(2.0)
    
    # Simulate a sample event for a new action step being generated
    sample_event = {
        "event": "action_step_generated",
        "task_id": task_id,
        "payload": {
            "id": f"step_{int(asyncio.get_running_loop().time())}",
            "name": "Click 'Submit' Button",
            "input": {"source": "previous_step.output"},
            "process": {
                "type": "desktop",
                "description": "The AI clicked on a button with the text 'Submit'.",
                "actions": [{"type": "click", "x": 1024, "y": 800}]
            },
            "output": {"variable": "submit_confirmation"}
        }
    }
    return sample_event