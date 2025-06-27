"""
Scenario Library Module
----------------------

This module provides access to predefined workflow actions and scenarios that can be used
in the workflow editor. It loads actions from the predefined_actions.json file and exposes
them through a simple API for both internal use and the frontend.

Actions are organized by category (http, shell, llm, approval, decision) and can be
retrieved individually or in groups.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_ACTIONS_PATH = "storage/fixed/predefined_actions.json"

class ScenarioLibrary:
    """
    Manages access to predefined workflow actions and scenarios.
    
    This class loads actions from a JSON file and provides methods to access them
    by category or ID. It's designed to be used both internally by the workflow engine
    and externally by the frontend through the API endpoints.
    """
    
    def __init__(self, actions_path: str = DEFAULT_ACTIONS_PATH):
        """
        Initialize the scenario library.
        
        Args:
            actions_path: Path to the JSON file containing predefined actions
        """
        self.actions_path = actions_path
        self.categories = {}
        self.actions_by_id = {}
        self.version = "1.0"
        self._load_actions()
    
    def _load_actions(self) -> None:
        """Load actions from the JSON file."""
        try:
            if not os.path.exists(self.actions_path):
                logger.warning(f"Actions file not found: {self.actions_path}")
                return
                
            with open(self.actions_path, 'r') as f:
                data = json.load(f)
                
            self.version = data.get("version", "1.0")
            self.categories = data.get("categories", {})
            
            # Build a lookup table for actions by ID
            for category_id, category in self.categories.items():
                for action in category.get("actions", []):
                    action_id = action.get("id")
                    if action_id:
                        self.actions_by_id[action_id] = action
            
            logger.info(f"Loaded {len(self.actions_by_id)} actions from {self.actions_path}")
            
        except Exception as e:
            logger.error(f"Error loading actions: {str(e)}")
            # Initialize with empty data
            self.categories = {}
            self.actions_by_id = {}
    
    def get_all_actions(self) -> Dict[str, Any]:
        """
        Get all available actions organized by category.
        
        Returns:
            Dict containing all categories and their actions
        """
        return {
            "version": self.version,
            "categories": self.categories
        }
    
    def get_actions_by_category(self, category_id: str) -> Dict[str, Any]:
        """
        Get all actions in a specific category.
        
        Args:
            category_id: ID of the category to retrieve
            
        Returns:
            Dict containing category information and actions
            
        Raises:
            KeyError: If category_id is not found
        """
        if category_id not in self.categories:
            raise KeyError(f"Category not found: {category_id}")
            
        return self.categories[category_id]
    
    def get_action_by_id(self, action_id: str) -> Dict[str, Any]:
        """
        Get a specific action by ID.
        
        Args:
            action_id: ID of the action to retrieve
            
        Returns:
            Dict containing action information
            
        Raises:
            KeyError: If action_id is not found
        """
        if action_id not in self.actions_by_id:
            raise KeyError(f"Action not found: {action_id}")
            
        return self.actions_by_id[action_id]
    
    def get_action_categories(self) -> List[Dict[str, str]]:
        """
        Get a list of available action categories.
        
        Returns:
            List of dicts with category ID, title, and description
        """
        return [
            {
                "id": category_id,
                "title": category.get("title", category_id),
                "description": category.get("description", "")
            }
            for category_id, category in self.categories.items()
        ]


# Create a singleton instance
_library = None

def get_scenario_library() -> ScenarioLibrary:
    """
    Get or create the singleton ScenarioLibrary instance.
    
    Returns:
        ScenarioLibrary instance
    """
    global _library
    if _library is None:
        _library = ScenarioLibrary()
    return _library


# FastAPI Router
# -----------------------------------------------------------------------------

router = APIRouter(prefix="/library", tags=["scenario-library"])

@router.get("/")
def get_all_actions(library: ScenarioLibrary = Depends(get_scenario_library)):
    """Get all available actions organized by category."""
    return library.get_all_actions()

@router.get("/categories")
def get_categories(library: ScenarioLibrary = Depends(get_scenario_library)):
    """Get a list of available action categories."""
    return library.get_action_categories()

@router.get("/categories/{category_id}")
def get_category_actions(category_id: str, library: ScenarioLibrary = Depends(get_scenario_library)):
    """Get all actions in a specific category."""
    try:
        return library.get_actions_by_category(category_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Category not found: {category_id}")

@router.get("/actions/{action_id}")
def get_action(action_id: str, library: ScenarioLibrary = Depends(get_scenario_library)):
    """Get a specific action by ID."""
    try:
        return library.get_action_by_id(action_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Action not found: {action_id}")
