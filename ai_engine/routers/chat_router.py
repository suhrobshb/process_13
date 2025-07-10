"""
Natural Language Chat API Router
================================

This module provides a sophisticated, conversational interface for creating and
modifying workflows using natural language. It serves as the backend for a
chatbot-style UI, allowing users to describe their automation needs in plain
English and have the AI Engine translate them into structured, executable
workflows.

Key Features:
-   **Conversational Workflow Creation**: An endpoint that takes a user's
    description of a process and uses an LLM to generate a complete, structured
    workflow draft in the correct IPO (Input-Process-Output) format.
-   **Iterative Workflow Modification**: An endpoint to apply conversational
    changes to an existing workflow (e.g., "After the first step, add an
    approval step," or "Change the LLM prompt in the summarization step").
-   **LLM-Powered Translation**: Leverages the core NLU (Natural Language
    Understanding) analytics module to handle the complex task of converting
    unstructured text into a precise JSON workflow structure.
-   **Secure and User-Scoped**: All operations are authenticated and scoped to
    the current user, ensuring users can only interact with their own workflows.
-   **Integration with Versioning**: When modifying workflows, it correctly
    creates new versions, preserving a complete audit history of changes.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

# Import core application components
from ..auth import get_current_active_user
from ..models.user import User
from ..models.workflow import Workflow
from ..database import get_session

# Import the core NLU processing logic
# This module will contain the complex prompts and LLM calls.
from ..analytics.nlu import nlu_to_workflow, apply_nlu_modification_to_workflow

# Configure logging
logger = logging.getLogger(__name__)

# Define the router for chat-based operations
router = APIRouter(
    prefix="/chat",
    tags=["Chat & Natural Language"],
    dependencies=[Depends(get_current_active_user)],
)

# --- Pydantic Models for API Requests ---

class ChatWorkflowRequest(BaseModel):
    """Request body for creating or modifying a workflow via chat."""
    text: str
    # Optional context, like a session ID, could be added here in the future
    # session_id: Optional[str] = None

# --- API Endpoints ---

@router.post(
    "/create-workflow",
    response_model=Workflow,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Workflow from a Natural Language Description",
)
async def chat_create_workflow(
    request: ChatWorkflowRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """
    Takes a user's conversational description of a process and generates a new
    draft workflow.

    The endpoint uses a powerful LLM to translate the text into a structured
    workflow with defined IPO steps, ready for the user to review and refine
    in the visual editor.
    """
    logger.info(f"User '{current_user.username}' initiated workflow creation via chat: '{request.text}'")
    try:
        # Delegate the complex NLU task to the analytics module
        generated_steps = await nlu_to_workflow(request.text)

        if not generated_steps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The AI could not understand the request or generate a valid workflow. Please try rephrasing your description."
            )

        # Create a new workflow object with the generated steps
        new_workflow = Workflow(
            name=f"Draft from Chat: {request.text[:40]}...",
            description=f"This workflow was auto-generated from the following prompt: '{request.text}'",
            steps=generated_steps,
            created_by=current_user.username,
            status="draft",
        )

        session.add(new_workflow)
        session.commit()
        session.refresh(new_workflow)
        
        logger.info(f"Successfully created new draft workflow (ID: {new_workflow.id}) for user '{current_user.username}'")
        return new_workflow

    except Exception as e:
        logger.error(f"Failed to create workflow from chat for user '{current_user.username}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while generating the workflow: {str(e)}"
        )


@router.post(
    "/modify-workflow/{workflow_id}",
    response_model=Workflow,
    summary="Modify an Existing Workflow Using Natural Language",
)
async def chat_modify_workflow(
    workflow_id: int,
    request: ChatWorkflowRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """
    Applies a conversational modification to an existing workflow.

    This endpoint fetches the specified workflow, sends its current structure
    along with the user's modification instruction to an LLM, and saves the
    result as a new version of the workflow.
    """
    logger.info(f"User '{current_user.username}' requested modification for workflow {workflow_id}: '{request.text}'")
    
    # 1. Fetch the existing workflow
    existing_workflow = session.get(Workflow, workflow_id)
    if not existing_workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")

    # Optional: Add an ownership check here if users shouldn't edit others' workflows
    # if existing_workflow.created_by != current_user.username:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this workflow.")

    try:
        # 2. Delegate the modification task to the NLU module
        modified_steps = await apply_nlu_modification_to_workflow(
            original_steps=existing_workflow.steps,
            modification_instruction=request.text,
        )

        if not modified_steps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The AI could not apply the requested modification. Please try a different command."
            )

        # 3. Create a new version of the workflow with the changes
        new_version = Workflow.create_new_version(
            original=existing_workflow,
            updated_by=current_user.username,
            version_notes=f"Modified via chat: '{request.text}'",
            steps=modified_steps,
            # Reset status to draft for review, or keep as is, depending on business logic
            status="draft",
        )

        session.add(new_version)
        session.commit()
        session.refresh(new_version)

        logger.info(f"Successfully created new version (v{new_version.version}) for workflow {workflow_id}")
        return new_version

    except Exception as e:
        logger.error(f"Failed to modify workflow {workflow_id} from chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while modifying the workflow: {str(e)}"
        )
