"""
Real-Time Collaboration WebSocket Router
========================================

This module provides the primary WebSocket endpoint for enabling real-time,
multi-user collaboration on workflows. It acts as the web layer that connects
frontend clients to the sophisticated `CollaborationManager`.

Key Responsibilities:
-   **Endpoint Definition**: Exposes a secure WebSocket endpoint at
    `/ws/collab/{workflow_id}` for users to join a specific workflow editing session.
-   **Authentication**: Ensures that only authenticated users can establish a
    WebSocket connection, leveraging the existing application-wide authentication
    system.
-   **Connection Lifecycle Management**: Handles the complete lifecycle of a client's
    connection:
    -   **Connection**: Accepts new connections and registers the user with the
        `CollaborationManager`.
    -   **Message Handling**: Listens for incoming messages (e.g., node updates,
        cursor movements) and passes them to the manager for processing and
        broadcasting.
    -   **Disconnection**: Gracefully handles client disconnections, ensuring the
        session state is cleaned up correctly.
-   **Decoupling**: Keeps the web transport layer (WebSockets) separate from the
    core collaboration business logic, which resides in the `CollaborationManager`.
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from typing import Dict

# Import the core collaboration logic handler and authentication dependencies
from ..collaboration.collaboration_manager import collaboration_manager
from ..auth import get_current_active_user
from ..models.user import User

# Configure logging
logger = logging.getLogger(__name__)

# Define the router for collaboration endpoints
router = APIRouter(prefix="/ws/collab", tags=["Real-Time Collaboration"])


@router.websocket("/{workflow_id}")
async def collaboration_websocket_endpoint(
    websocket: WebSocket,
    workflow_id: int,
    # This dependency ensures the user is authenticated before the WebSocket connection is even accepted.
    # We can get the token from query params, headers, or cookies.
    # For this example, let's assume a simple query param token for WebSocket clients.
    # In a real app, you might implement a more robust token-passing mechanism.
    user: User = Depends(get_current_active_user)
):
    """
    Handles the WebSocket connection for a real-time collaboration session on a specific workflow.

    Each user connects to this endpoint for a given `workflow_id`. The server then
    manages their session, receives their edits, and broadcasts changes to all other
    participants in the same session.
    """
    if not user:
        # This case should ideally be handled by the dependency itself, but as a fallback:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Extract relevant user info to share with other collaborators
    user_info = {
        "username": user.username,
        "email": user.email,
        # Add any other relevant info like avatar URL, etc.
    }

    # Connect the user to the collaboration session
    await collaboration_manager.connect(workflow_id, user.id, user_info, websocket)

    try:
        # Loop indefinitely, waiting for messages from this client
        while True:
            # Wait for a message (e.g., a node move, a comment, a cursor update)
            message: Dict = await websocket.receive_json()
            
            # Pass the message to the manager to be processed and broadcasted.
            # The manager will handle conflict resolution and state updates.
            await collaboration_manager.handle_message(workflow_id, user.id, message)

    except WebSocketDisconnect:
        # This block is executed when the client's connection is closed.
        logger.info(f"WebSocket disconnected for user {user.id} on workflow {workflow_id}.")
        # Gracefully remove the user from the session.
        collaboration_manager.disconnect(workflow_id, user.id)
    except Exception as e:
        # Catch any other unexpected errors during the session.
        logger.error(
            f"An unexpected error occurred for user {user.id} in workflow {workflow_id} session: {e}",
            exc_info=True
        )
        # Ensure disconnection on error
        collaboration_manager.disconnect(workflow_id, user.id)
