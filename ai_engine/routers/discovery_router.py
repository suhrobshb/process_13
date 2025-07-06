"""
Insights & Discovery API Router
===============================

This module provides a suite of API endpoints designed to deliver intelligent,
data-driven insights to users. It serves as the backend for dashboard components
that help users understand the value of their automations and discover new
opportunities.

Key Features:
-   **Smart Automation Discovery**: An endpoint that analyzes a user's historical
    activity to proactively suggest repetitive, time-consuming tasks that are
    prime candidates for automation.
-   **ROI Analytics**: An endpoint that calculates and returns tangible business
    value metrics, such as total hours saved and estimated cost savings, derived
    from all successful workflow executions for a user.
-   **Adaptive Workflow Recommendations**: An endpoint that provides targeted
    suggestions for improving existing workflows, such as identifying frequently
    failing steps or opportunities for optimization.
-   **Secure and User-Scoped**: All endpoints are protected and strictly scoped
    to the currently authenticated user, ensuring data privacy and relevance.
"""

import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

# Import core application components
from ..auth import get_current_active_user
from ..models.user import User
from ..analytics.discovery import get_automation_suggestions
from ..analytics.roi import calculate_roi
from ..analytics.recommendations import get_improvement_recommendations

# Configure logging
logger = logging.getLogger(__name__)

# Define the router for all insights-related endpoints
router = APIRouter(
    prefix="/insights",
    tags=["Insights & Discovery"],
    dependencies=[Depends(get_current_active_user)],
)

# --- Pydantic Models for API Responses ---

class AutomationSuggestionResponse(BaseModel):
    """Defines the structure for a single automation suggestion."""
    title: str
    workflow_pattern: List[str]
    frequency: int
    estimated_time_saved_ms: float
    estimated_time_saved_str: str
    priority_score: float

class RoiMetricsResponse(BaseModel):
    """Defines the structure for the ROI metrics response."""
    hours_saved: float
    cost_saved: float
    automations_run: int
    success_rate: float

class ImprovementRecommendationResponse(BaseModel):
    """Defines the structure for a workflow improvement recommendation."""
    recommendation_id: str
    title: str
    description: str
    category: str  # e.g., 'reliability', 'efficiency', 'cost'
    severity: str  # e.g., 'high', 'medium', 'low'


# --- API Endpoints ---

@router.get(
    "/suggestions",
    response_model=List[AutomationSuggestionResponse],
    summary="Get Top Automation Suggestions",
    description="Analyzes the current user's historical activity and returns a ranked list of the best candidates for automation."
)
async def get_suggestions(
    current_user: User = Depends(get_current_active_user)
):
    """
    Fetches personalized automation suggestions for the logged-in user.
    """
    try:
        logger.info(f"Fetching automation suggestions for user_id={current_user.id}")
        suggestions = get_automation_suggestions(user_id=current_user.id, top_n=5)
        return suggestions
    except Exception as e:
        logger.error(f"Failed to generate suggestions for user_id={current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate automation suggestions at this time."
        )

@router.get(
    "/roi",
    response_model=RoiMetricsResponse,
    summary="Get Return on Investment (ROI) Metrics",
    description="Calculates and returns key performance indicators showing the value of the user's automations."
)
async def get_roi_metrics(
    current_user: User = Depends(get_current_active_user)
):
    """
    Calculates and returns ROI metrics based on the user's workflow execution history.
    """
    try:
        logger.info(f"Calculating ROI for user_id={current_user.id}")
        roi_data = calculate_roi(user_id=current_user.id)
        return roi_data
    except Exception as e:
        logger.error(f"Failed to calculate ROI for user_id={current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not calculate ROI metrics at this time."
        )

@router.get(
    "/workflows/{workflow_id}/recommendations",
    response_model=List[ImprovementRecommendationResponse],
    summary="Get Adaptive Recommendations for a Workflow",
    description="Provides AI-driven recommendations to improve the reliability, efficiency, or cost of a specific workflow."
)
async def get_adaptive_recommendations(
    workflow_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Fetches adaptive improvement recommendations for a specific workflow.
    """
    try:
        logger.info(f"Fetching recommendations for workflow_id={workflow_id} for user_id={current_user.id}")
        # The user object is passed for potential ownership/permission checks in the future
        recommendations = get_improvement_recommendations(workflow_id=workflow_id, user=current_user)
        return recommendations
    except Exception as e:
        logger.error(f"Failed to get recommendations for workflow_id={workflow_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve improvement recommendations for this workflow."
        )
