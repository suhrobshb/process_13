"""
Desktop Automation Runner

This module provides a Runner implementation for desktop automation using PyAutoGUI.
It allows workflows to control mouse movements, clicks, keyboard input, and other
desktop interactions as part of an automated workflow.
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional
import pyautogui

# Configure PyAutoGUI safety features
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.1  # Small pause between PyAutoGUI commands

# Set up logging
logger = logging.getLogger("desktop_runner")

class DesktopRunner:
    """
    Runner for executing desktop automation actions using PyAutoGUI.
    
    This runner can be used to automate mouse and keyboard interactions
    with desktop applications as part of a workflow.
    """
    
    def __init__(self, step_id: str, params: Dict[str, Any]):
        """
        Initialize the Desktop Runner with step parameters.
        
        Args:
            step_id: Unique identifier for this step in the workflow
            params: Dictionary containing the actions to perform
        """
        self.step_id = step_id
        self.actions = params.get("actions", [])
        self.timeout = params.get("timeout", 60)  # Default 60 second timeout
        self.screen_size = pyautogui.size()
        
    def execute(self) -> Dict[str, Any]:
        """
        Execute the desktop automation actions.
        
        Returns:
            Dictionary with success status and results or error information
        """
        logger.info(f"Starting execution of desktop automation step {self.step_id}")
        start_time = time.time()
        
        try:
            results = []
            for i, action in enumerate(self.actions):
                # Check for timeout
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Desktop automation step {self.step_id} timed out after {self.timeout} seconds")
                
                # Execute the action
                result = self._execute_action(action, i)
                results.append(result)
                
                # Apply delay if specified
                delay = action.get("delay", 0.5)
                time.sleep(delay)
            
            logger.info(f"Step {self.step_id} completed in {time.time() - start_time:.2f}s")
            return {
                "success": True,
                "result": {
                    "actions_executed": len(results),
                    "action_results": results,
                    "execution_time": time.time() - start_time
                }
            }
            
        except Exception as e:
            logger.error(f"Error in desktop automation step {self.step_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "partial_results": results if 'results' in locals() else []
            }
    
    def _execute_action(self, action: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        Execute a single desktop automation action.
        
        Args:
            action: Dictionary describing the action to perform
            index: Index of this action in the sequence
            
        Returns:
            Dictionary with action result information
        """
        action_type = action.get("type", "")
        logger.debug(f"Executing desktop action {index}: {action_type}")
        
        result = {"type": action_type, "success": True}
        
        try:
            if action_type == "click":
                x, y = action.get("x"), action.get("y")
                button = action.get("button", "left")
                clicks = action.get("clicks", 1)
                
                # Validate coordinates
                if x is None or y is None:
                    raise ValueError(f"Missing coordinates for click action: {action}")
                
                # Execute click
                pyautogui.click(x=x, y=y, button=button, clicks=clicks)
                result["details"] = f"Clicked at ({x}, {y}) with {button} button, {clicks} times"
                
            elif action_type == "right_click":
                x, y = action.get("x"), action.get("y")
                pyautogui.rightClick(x=x, y=y)
                result["details"] = f"Right-clicked at ({x}, {y})"
                
            elif action_type == "double_click":
                x, y = action.get("x"), action.get("y")
                pyautogui.doubleClick(x=x, y=y)
                result["details"] = f"Double-clicked at ({x}, {y})"
                
            elif action_type == "move":
                x, y = action.get("x"), action.get("y")
                duration = action.get("duration", 0.5)
                pyautogui.moveTo(x=x, y=y, duration=duration)
                result["details"] = f"Moved to ({x}, {y}) over {duration}s"
                
            elif action_type == "drag":
                start_x, start_y = action.get("start_x"), action.get("start_y")
                end_x, end_y = action.get("end_x"), action.get("end_y")
                duration = action.get("duration", 0.5)
                
                # Move to start position
                pyautogui.moveTo(start_x, start_y)
                # Drag to end position
                pyautogui.dragTo(end_x, end_y, duration=duration)
                result["details"] = f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"
                
            elif action_type == "type":
                text = action.get("text", "")
                interval = action.get("interval", 0.1)
                pyautogui.write(text, interval=interval)
                result["details"] = f"Typed text: '{text}' with {interval}s interval"
                
            elif action_type == "hotkey":
                keys = action.get("keys", [])
                if not keys:
                    raise ValueError("No keys specified for hotkey action")
                
                pyautogui.hotkey(*keys)
                result["details"] = f"Pressed hotkey combination: {'+'.join(keys)}"
                
            elif action_type == "press":
                key = action.get("key", "")
                if not key:
                    raise ValueError("No key specified for press action")
                
                presses = action.get("presses", 1)
                interval = action.get("interval", 0.1)
                pyautogui.press(key, presses=presses, interval=interval)
                result["details"] = f"Pressed key '{key}' {presses} times"
                
            elif action_type == "screenshot":
                region = action.get("region")
                filename = action.get("filename", f"screenshot_{int(time.time())}.png")
                
                if region:
                    screenshot = pyautogui.screenshot(region=region)
                else:
                    screenshot = pyautogui.screenshot()
                    
                screenshot.save(filename)
                result["details"] = f"Screenshot saved to {filename}"
                result["filename"] = filename
                
            elif action_type == "locate_image":
                image_path = action.get("image_path")
                confidence = action.get("confidence", 0.9)
                
                if not image_path or not os.path.exists(image_path):
                    raise ValueError(f"Image not found: {image_path}")
                
                location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                if location:
                    result["details"] = f"Image found at {location}"
                    result["location"] = location
                else:
                    result["details"] = "Image not found on screen"
                    result["location"] = None
                    
            elif action_type == "wait_for_image":
                image_path = action.get("image_path")
                timeout = action.get("timeout", 10)
                confidence = action.get("confidence", 0.9)
                
                if not image_path or not os.path.exists(image_path):
                    raise ValueError(f"Image not found: {image_path}")
                
                start_wait = time.time()
                location = None
                
                while time.time() - start_wait < timeout:
                    location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                    if location:
                        break
                    time.sleep(0.5)
                
                if location:
                    result["details"] = f"Image found at {location} after {time.time() - start_wait:.2f}s"
                    result["location"] = location
                else:
                    result["details"] = f"Image not found after waiting {timeout}s"
                    result["location"] = None
                    
            else:
                raise ValueError(f"Unknown action type: {action_type}")
                
        except Exception as e:
            logger.error(f"Error executing desktop action {index} ({action_type}): {str(e)}")
            result["success"] = False
            result["error"] = str(e)
            
        return result

# Register this runner with the factory
def register_desktop_runner(factory):
    """Register the Desktop Runner with the provided factory."""
    factory.register("desktop", DesktopRunner)
