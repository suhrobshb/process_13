"""
Comprehensive Real-Time WebSocket Router for AI Engine
=======================================================

This module provides a centralized, robust real-time communication layer for the
AI Engine platform. It uses WebSockets to manage persistent, bidirectional
connections with frontend clients, enabling a dynamic and interactive user
experience.

Key Responsibilities:
-   **Multi-Channel Connection Management**: A sophisticated ConnectionManager
    handles multiple, distinct communication channels for different parts of the
    application (e.g., live recording sessions, workflow execution monitoring,
    and system-wide alerts).
-   **Live Recording Studio Feed**: Streams raw captured events and AI-generated
    "Action Step" nodes to the UI in real-time as a user records a process.
-   **Real-time Workflow Execution Monitoring**: Pushes live status updates,
    step completions, and results for running workflows, allowing users to
    watch their automations execute.
-   **System-Wide Event Broadcasting**: Provides a channel for broadcasting
    global notifications, such as system maintenance alerts or major updates.
-   **Scalable Architecture**: Designed with production in mind. The default
    in-memory connection store can be easily swapped with a Redis Pub/Sub
    backend to support a distributed, multi-worker environment.
-   **Decoupled Broadcasting**: Provides simple async helper functions that other
    modules (like the AILearningEngine or WorkflowEngine) can call to send
    updates, without needing direct access to WebSocket objects.
"""

import asyncio
import logging
from typing import Dict, List, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Configure logging
logger = logging.getLogger(__name__)

# Define the router for all real-time WebSocket endpoints
router = APIRouter(prefix="/ws", tags=["Real-Time Communication"])

# --- Centralized Connection Manager ---

class ConnectionManager:
    """
    Manages all active WebSocket connections across different channels.

    In a production environment with multiple workers, this in-memory dictionary
    should be replaced by a Redis Pub/Sub system to broadcast messages across
    all server instances.
    """
    def __init__(self):
        # A dictionary where keys are channel names (e.g., "recording:123")
        # and values are lists of active WebSocket connections.
        self.active_connections: Dict[str, List[WebSocket]] = {}
        logger.info("Real-time ConnectionManager initialized.")

    async def connect(self, websocket: WebSocket, channel: str):
        """Accepts and stores a new WebSocket connection for a specific channel."""
        await websocket.accept()
        connections = self.active_connections.setdefault(channel, [])
        connections.append(websocket)
        logger.info(f"Client connected to channel '{channel}'. Total connections for channel: {len(connections)}")

    def disconnect(self, websocket: WebSocket, channel: str):
        """Removes a WebSocket connection from a channel."""
        if channel in self.active_connections:
            try:
                self.active_connections[channel].remove(websocket)
                # If the channel has no more listeners, clean it up
                if not self.active_connections[channel]:
                    del self.active_connections[channel]
                logger.info(f"Client disconnected from channel '{channel}'.")
            except ValueError:
                # This can happen if the connection is already removed, which is safe to ignore.
                pass

    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]):
        """Broadcasts a JSON message to all clients subscribed to a specific channel."""
        if channel in self.active_connections:
            # Create a list of connections to iterate over, in case of disconnections during broadcast
            connections_to_send = list(self.active_connections[channel])
            for connection in connections_to_send:
                try:
                    await connection.send_json(message)
                except Exception:
                    # If sending fails, assume the connection is dead and remove it.
                    self.disconnect(connection, channel)
            logger.debug(f"Broadcasted message to {len(connections_to_send)} clients on channel '{channel}'.")

# --- Singleton Instance of the Manager ---
# This global instance is shared across the application.
manager = ConnectionManager()

# --- WebSocket Endpoints ---

@router.websocket("/recording/{task_id}")
async def websocket_recording_session(websocket: WebSocket, task_id: int):
    """
    WebSocket endpoint for a live recording session.

    Clients connect here to receive a real-time stream of:
    1. Raw captured events (clicks, types).
    2. AI-generated "Action Step" nodes as the AILearningEngine processes the recording.
    """
    channel = f"recording:{task_id}"
    await manager.connect(websocket, channel)
    try:
        while True:
            # This loop keeps the connection alive. The server pushes messages;
            # it doesn't expect to receive any from the client in this case.
            # A timeout could be added here to close inactive connections.
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"An error occurred in the recording WebSocket for task {task_id}: {e}")
        manager.disconnect(websocket, channel)

@router.websocket("/execution/{execution_id}")
async def websocket_execution_monitoring(websocket: WebSocket, execution_id: int):
    """
    WebSocket endpoint for monitoring a specific workflow execution in real-time.

    Clients receive updates on:
    - Overall execution status (running, completed, failed).
    - Individual step status updates.
    - Intermediate results or logs from steps.
    """
    channel = f"execution:{execution_id}"
    await manager.connect(websocket, channel)
    try:
        while True:
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"An error occurred in the execution monitoring WebSocket for execution {execution_id}: {e}")
        manager.disconnect(websocket, channel)

@router.websocket("/system")
async def websocket_system_events(websocket: WebSocket):
    """
    WebSocket endpoint for system-wide notifications and events.

    Clients connected here will receive global alerts, such as:
    - System maintenance announcements.
    - Major platform updates.
    - Potentially, high-level administrative alerts.
    """
    channel = "system"
    await manager.connect(websocket, channel)
    try:
        while True:
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"An error occurred in the system event WebSocket: {e}")
        manager.disconnect(websocket, channel)


# --- Public Helper Functions for Broadcasting ---
# These async functions are the intended interface for other modules to send data
# to the frontend without needing to know about the WebSocket implementation details.

async def broadcast_recording_event(task_id: int, event_data: Dict[str, Any]):
    """
    Broadcasts an event related to a specific recording session.
    Called by the AILearningEngine.

    Args:
        task_id: The ID of the recording task.
        event_data: The JSON-serializable data to send.
    """
    channel = f"recording:{task_id}"
    await manager.broadcast_to_channel(channel, event_data)

async def broadcast_execution_update(execution_id: int, update_data: Dict[str, Any]):
    """
    Broadcasts a status update for a specific workflow execution.
    Called by the WorkflowEngine or Celery tasks.

    Args:
        execution_id: The ID of the workflow execution.
        update_data: The JSON-serializable data to send.
    """
    channel = f"execution:{execution_id}"
    await manager.broadcast_to_channel(channel, update_data)

async def broadcast_system_alert(alert_data: Dict[str, Any]):
    """
    Broadcasts a system-wide alert to all connected clients on the system channel.
    Called by administrative or system-level services.

    Args:
        alert_data: The JSON-serializable alert data to send.
    """
    channel = "system"
    await manager.broadcast_to_channel(channel, alert_data)
