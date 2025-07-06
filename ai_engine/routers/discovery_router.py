"""
Automation Discovery API Router
===============================

This module provides the REST API endpoints for the Smart Automation Discovery
feature. It exposes the analytics calculated by the `discovery.py` module,
allowing the frontend to fetch personalized automation suggestions for the
currently logged-in user.

Key Responsibilities:
-   **Expose Discovery Analytics**: Provides an endpoint to get a ranked list of
    the most frequent and time-consuming tasks performed by a user.
-   **Enforce Authentication**: All endpoints are protected and require a valid
    authenticated user session, ensuring that users can only see their own
    automation suggestions.
-   **Provide Actionable Data**: The endpoint is designed to return data in a
    format that the frontend can easily consume to display suggestions, such as
    "Top 5 tasks you can automate."
"""

import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status

# Import the core analytics function and the authentication dependency
from ..analytics.discovery import get_automation_suggestions
from ..auth import get_current_active_user
from ..models.user import User

# Configure logging
logger = logging.getLogger(__name__)

# Define the router for discovery-related endpoints
router = APIRouter(
    prefix="/discovery",
    tags=["Automation Discovery"],
    # All endpoints in this router will require an authenticated user
    dependencies=[Depends(get_current_active_user)],
)

# --- API Endpoints ---

@router.get(
    "/suggestions",
    response_model=Dict[str, List[Dict[str, Any]]],
    summary="Get Top Automation Suggestions",
    description="Analyzes the current user's historical activity and returns a ranked list of the best candidates for automation."
)
async def get_top_automation_suggestions(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetches personalized automation suggestions for the logged-in user.

    This endpoint calls the discovery analytics engine to find repetitive and
    time-consuming tasks from the user's activity logs.

    Returns:
        A dictionary containing a list of suggestion objects, sorted by priority.
    """
    try:
        logger.info(f"Fetching automation suggestions for user_id={current_user.id}")
        
        # Call the core analytics function with the user's ID
        suggestions = get_automation_suggestions(user_id=current_user.id, top_n=5)
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error(
            f"Failed to generate automation suggestions for user_id={current_user.id}: {e}",
            exc_info=True
        )
        # In case of an unexpected error in the analytics engine, return an internal server error.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing your activity for automation suggestions."
        )

# --- Future Endpoint Stubs ---
#
# The following are placeholders for future enhancements, such as allowing a user
# to one-click generate a draft workflow from a suggestion.
#
# @router.post("/suggestions/{suggestion_id}/generate-workflow", status_code=status.HTTP_201_CREATED)
# async def generate_workflow_from_suggestion(
#     suggestion_id: str, # This would be an ID derived from the suggestion payload
#     current_user: User = Depends(get_current_active_user)
# ):
#     """
#     (Future Implementation)
#     Takes a specific automation suggestion and automatically generates a draft
#     workflow from its underlying pattern.
#     """
#     # 1. Fetch the suggestion details from a cache or re-run discovery for that pattern.
#     # 2. Convert the pattern's event signatures into a structured workflow (IPO format).
#     # 3. Save the new workflow to the database with a 'draft' status.
#     # 4. Return the newly created workflow object.
#     raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Feature not yet implemented.")

