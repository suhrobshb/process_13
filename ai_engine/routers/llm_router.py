"""
LLM Operations Router
=====================

This module provides API endpoints for interacting with Large Language Models (LLMs)
directly from the user interface. It serves as a backend for UI components that
allow users to test prompts, configure LLM-powered steps, and get immediate
feedback without executing a full workflow.

Key Features:
-   **On-Demand Execution**: An endpoint to run a single LLM step with a given
    prompt, context, and configuration.
-   **Secure Access**: All endpoints are protected and require user authentication,
    ensuring that only authorized users can consume potentially costly LLM resources.
-   **Integration with LLMRunner**: Leverages the existing `LLMRunner` to handle
    the complexities of interacting with different providers (OpenAI, Anthropic, etc.),
    prompt templating, and structured output parsing.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ai_engine.auth import get_current_active_user
from ai_engine.models.user import User
from ai_engine.enhanced_runners.llm_runner import LLMRunner

# Define the router for LLM operations
router = APIRouter(
    prefix="/llm",
    tags=["LLM Operations"],
)

# --- Pydantic Models for API Requests ---

class LLMExecuteRequest(BaseModel):
    """
    Defines the expected request body for executing an ad-hoc LLM step.
    This model mirrors the parameters needed by the LLMRunner.
    """
    provider: str
    model: str
    prompt_template: str
    context: Optional[Dict[str, Any]] = {}
    output_schema: Optional[Dict[str, Any]] = None
    llm_kwargs: Optional[Dict[str, Any]] = {}

# --- API Endpoints ---

@router.post("/execute", response_model=Dict[str, Any])
async def execute_llm_step(
    request: LLMExecuteRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Execute a single LLM step on-demand.
    
    This endpoint is designed for the frontend to test LLM prompts and configurations
    interactively. It takes all the necessary parameters, runs them through the
    LLMRunner, and returns the result.
    """
    try:
        # The parameters for the LLMRunner are sourced directly from the request model.
        runner_params = request.dict()
        
        # Instantiate the LLMRunner with the provided configuration.
        # The step_id is arbitrary as this is a one-off execution.
        runner = LLMRunner(step_id="ui_test_step", params=runner_params)
        
        # Execute the step with the provided context.
        result = runner.execute(context=request.context)
        
        if not result.get("success"):
            # If the runner itself reports a failure, return a 400 Bad Request.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LLM execution failed: {result.get('error', 'Unknown error')}"
            )
            
        return result
        
    except ValueError as ve:
        # Catch configuration errors from the runner (e.g., missing API key, unsupported provider).
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        # Catch any other unexpected errors during execution (e.g., API provider is down).
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during LLM execution: {str(e)}"
        )
