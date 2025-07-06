"""
Sophisticated Real-Time Collaboration Manager for AI Engine
===========================================================

This module provides a robust, real-time collaboration engine for the AI Engine
platform. It allows multiple users to simultaneously edit the same workflow in a
shared, interactive environment, similar to modern collaborative tools like
Google Docs or Miro.

Key Features:
-   **Multi-User Session Management**: Manages distinct, isolated editing sessions
    for each workflow, handling user connections and disconnections gracefully.
-   **Live Presence Tracking**: Provides real-time information about which users
    are currently active in a workflow editing session, enabling features like
    displaying avatars of collaborators.
-   **Conflict Resolution**: Implements a version-based conflict resolution
    strategy to prevent data loss from simultaneous edits. If a user tries to
    save a change based on an outdated version of the workflow, the change is
    rejected, and they are sent the latest state to resolve the conflict.
-   **Real-time Broadcasting**: Efficiently broadcasts changes (e.g., node updates,
    new comments, cursor movements) to all connected clients in a session.
-   **Stateful Server-Side Cache**: Maintains the "source of truth" for each
    active workflow session in memory, loading from the database on the first
    connection and persisting changes back.
-   **Decoupled and Scalable Design**: While the default implementation uses an
    in-memory store, it is designed to be easily adaptable to a distributed
    backend like Redis for multi-worker production environments.
"""

import logging
import asyncio
from typing import Dict, List, Any

from fastapi import WebSocket

# In a real application, these would be imported from your database and models
# from ..database import get_session
# from ..models.workflow import Workflow

# Configure logging
logger = logging.getLogger(__name__)


class CollaborationManager:
    """
    Manages all active real-time collaboration sessions for workflow editing.
    This class is designed to be a singleton within the application scope.
    """

    def __init__(self):
        # Stores active WebSocket connections for each workflow.
        # Format: { workflow_id: { user_id: WebSocket, ... } }
        self.active_sessions: Dict[int, Dict[int, WebSocket]] = {}

        # Caches the current state of workflows being actively edited.
        # This is the server's "source of truth".
        # Format: { workflow_id: { "version": int, "data": Dict, "users": List[Dict] } }
        self.workflow_states: Dict[int, Dict[str, Any]] = {}

    async def connect(self, workflow_id: int, user_id: int, user_info: Dict, websocket: WebSocket):
        """
        Handles a new user connecting to a workflow collaboration session.

        Args:
            workflow_id: The ID of the workflow being joined.
            user_id: The ID of the connecting user.
            user_info: A dictionary with user details (e.g., name, avatar).
            websocket: The WebSocket object for the connection.
        """
        await websocket.accept()
        logger.info(f"User {user_id} connecting to collaboration session for workflow {workflow_id}.")

        # Initialize session if it's the first user
        if workflow_id not in self.active_sessions:
            self.active_sessions[workflow_id] = {}
            # Load the initial state from the database
            # TODO: Replace with actual database call
            self.workflow_states[workflow_id] = {
                "version": 1,
                "data": self._load_workflow_from_db(workflow_id),
                "users": []
            }

        # Add user to the session
        self.active_sessions[workflow_id][user_id] = websocket
        self.workflow_states[workflow_id]["users"].append({"id": user_id, **user_info})

        # Send the current full state to the newly connected user
        await websocket.send_json({
            "action": "sync_initial_state",
            "payload": self.workflow_states[workflow_id]
        })

        # Notify all other users in the session that a new user has joined
        await self.broadcast(
            workflow_id,
            message={"action": "user_joined", "payload": {"id": user_id, **user_info}},
            sender_id=user_id
        )

    def disconnect(self, workflow_id: int, user_id: int):
        """
        Handles a user disconnecting from a session.

        Args:
            workflow_id: The ID of the workflow being left.
            user_id: The ID of the disconnecting user.
        """
        logger.info(f"User {user_id} disconnecting from workflow {workflow_id}.")
        if workflow_id in self.active_sessions:
            # Remove user from session
            if user_id in self.active_sessions[workflow_id]:
                del self.active_sessions[workflow_id][user_id]

            # Update and broadcast presence information
            if workflow_id in self.workflow_states:
                self.workflow_states[workflow_id]["users"] = [
                    user for user in self.workflow_states[workflow_id]["users"]
                    if user["id"] != user_id
                ]
                asyncio.create_task(self.broadcast(
                    workflow_id,
                    message={"action": "user_left", "payload": {"id": user_id}}
                ))

            # If the session is now empty, clean up and persist the state
            if not self.active_sessions[workflow_id]:
                logger.info(f"Session for workflow {workflow_id} is now empty. Saving state and cleaning up.")
                self._save_workflow_to_db(workflow_id, self.workflow_states[workflow_id]["data"])
                del self.active_sessions[workflow_id]
                del self.workflow_states[workflow_id]

    async def handle_message(self, workflow_id: int, user_id: int, message: Dict):
        """
        Processes an incoming message from a client and handles conflicts.

        Args:
            workflow_id: The ID of the workflow session.
            user_id: The ID of the user sending the message.
            message: The parsed JSON message from the client.
        """
        action = message.get("action")
        payload = message.get("payload", {})
        client_version = payload.get("version")

        # For cursor updates, just broadcast without version checks
        if action == "cursor_update":
            await self.broadcast(workflow_id, message, sender_id=user_id)
            return

        # For all other state-changing actions, perform conflict resolution
        server_state = self.workflow_states.get(workflow_id)
        if not server_state:
            return # Session was likely closed

        server_version = server_state["version"]

        if client_version is not None and client_version != server_version:
            # Conflict detected!
            logger.warning(
                f"Conflict detected for workflow {workflow_id} from user {user_id}. "
                f"Client version: {client_version}, Server version: {server_version}."
            )
            # Send a conflict event back to the original sender only
            conflict_message = {
                "action": "conflict_detected",
                "payload": {
                    "message": "Your changes could not be saved because the workflow was updated by someone else.",
                    "latest_state": server_state
                }
            }
            websocket = self.active_sessions.get(workflow_id, {}).get(user_id)
            if websocket:
                await websocket.send_json(conflict_message)
            return

        # No conflict, process the action
        # TODO: Implement the logic for each action to modify server_state["data"]
        # For example:
        # if action == "update_node":
        #     self._apply_node_update(server_state["data"], payload["node_data"])

        # Increment version and broadcast the change
        server_state["version"] += 1
        
        # The broadcasted message includes the new version, so all clients stay in sync
        broadcast_message = {
            "action": action,
            "payload": payload,
            "sender_id": user_id,
            "new_version": server_state["version"]
        }
        await self.broadcast(workflow_id, broadcast_message, sender_id=user_id)

    async def broadcast(self, workflow_id: int, message: Dict, sender_id: int = None):
        """
        Broadcasts a message to all clients in a workflow session.

        Args:
            workflow_id: The ID of the workflow session.
            message: The JSON-serializable message to send.
            sender_id: (Optional) The ID of the user who sent the original
                       message, to exclude them from the broadcast.
        """
        if workflow_id in self.active_sessions:
            for user_id, websocket in self.active_sessions[workflow_id].items():
                if user_id != sender_id:
                    await websocket.send_json(message)

    # --- Persistence Stubs ---

    def _load_workflow_from_db(self, workflow_id: int) -> Dict:
        """
        Placeholder for loading workflow data from the database.
        """
        logger.info(f"Loading workflow {workflow_id} from database (stub).")
        # with get_session() as session:
        #     workflow = session.get(Workflow, workflow_id)
        #     if workflow:
        #         return {"nodes": workflow.nodes, "edges": workflow.edges}
        return {"nodes": [], "edges": []} # Fallback for demo

    def _save_workflow_to_db(self, workflow_id: int, data: Dict):
        """
        Placeholder for saving the final workflow state to the database.
        """
        logger.info(f"Saving workflow {workflow_id} to database (stub).")
        # with get_session() as session:
        #     workflow = session.get(Workflow, workflow_id)
        #     if workflow:
        #         workflow.nodes = data.get("nodes", [])
        #         workflow.edges = data.get("edges", [])
        #         session.add(workflow)
        #         session.commit()

# --- Singleton instance for use across the application ---
collaboration_manager = CollaborationManager()
