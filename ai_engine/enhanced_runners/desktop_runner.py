"""
Desktop Automation Runner (The "Digital Employee")
=================================================

This module provides the core runner for replicating human-computer interactions.
It uses `pyautogui` to control the mouse, keyboard, and windows, allowing the
AI Engine to perform tasks on any desktop application or website as if a
human were doing it.

This is the universal fallback and primary execution method when direct API
integrations are not available or desired.

Key Features:
- Mouse control: Clicks, movement, dragging, scrolling.
- Keyboard control: Typing text, pressing individual keys, using hotkeys.
- Screen analysis: Taking screenshots, locating images on the screen.
- Window management: Activating, closing, minimizing, and maximizing windows.
- Robust error handling and detailed result logging for each action.
"""

import os
import time
import logging
from typing import Dict, Any, List

# PyAutoGUI is the core library for desktop automation.
# It's imported with a try-except block to handle environments without a display.
try:
    import pyautogui
    # Safety feature: move mouse to a corner to abort execution.
    pyautogui.FAILSAFE = True
    # A small default pause between actions to make automation more reliable.
    pyautogui.PAUSE = 0.25
    PYAUTOGUI_AVAILABLE = True
except Exception:
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Vision-utility imports (image matching & OCR)
# --------------------------------------------------------------------------- #
try:
    from ..automation_runners.vision_utils import (  # pylint: disable=import-error
        find_on_screen,
        wait_for_element as vision_wait_for_element,
        ocr_from_region,
        ElementNotFoundError,
    )
    VISION_AVAILABLE = True
except Exception:  # pragma: no cover – vision utils optional in headless CI
    VISION_AVAILABLE = False
    ElementNotFoundError = RuntimeError  # fallback to generic error


class DesktopRunner:
    """
    Executes a sequence of desktop automation actions, simulating a human user.
    """

    def __init__(self, step_id: str, params: Dict[str, Any]):
        """
        Initializes the Desktop Runner.

        Args:
            step_id (str): A unique identifier for this step in the workflow.
            params (Dict[str, Any]): A dictionary containing the parameters for this step.
                                     Expected to have an "actions" key with a list of action dicts.
        """
        if not PYAUTOGUI_AVAILABLE:
            raise ImportError("Desktop automation is not available. `pyautogui` could not be imported. This may be due to a missing display environment (e.g., running in a headless server).")

        self.step_id = step_id
        self.actions = params.get("actions", [])
        self.timeout = params.get("timeout", 300)  # Default 5-minute timeout for the entire step.
        self.screen_size = pyautogui.size()
        logger.info(f"DesktopRunner initialized for step '{self.step_id}' with {len(self.actions)} actions. Screen size: {self.screen_size}")

    def execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes the entire sequence of desktop actions.

        Args:
            context: Workflow context with variables from previous steps

        Returns:
            A dictionary containing the execution result, including success status,
            a list of individual action results, and total execution time.
        """
        context = context or {}
        logger.info(f"Executing desktop automation step: {self.step_id}")
        start_time = time.time()
        action_results = []
        overall_success = True

        try:
            for i, action_config in enumerate(self.actions, 1):
                # Check for overall step timeout
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Step '{self.step_id}' timed out after {self.timeout} seconds.")

                logger.info(f"Executing action {i}/{len(self.actions)}: {action_config.get('type')}")
                action_result = self._execute_action(action_config, context)
                action_results.append(action_result)

                if not action_result["success"]:
                    overall_success = False
                    # Decide whether to stop on failure or continue
                    if action_config.get("stop_on_failure", True):
                        logger.error(f"Action failed, and stop_on_failure is true. Halting execution of step '{self.step_id}'.")
                        break

                # Optional delay after each action
                time.sleep(action_config.get("delay_after", 0.5))

        except Exception as e:
            logger.error(f"An unexpected error occurred during execution of step '{self.step_id}': {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Step execution failed: {str(e)}",
                "results": action_results,
                "execution_time_seconds": time.time() - start_time,
            }

        execution_time = time.time() - start_time
        logger.info(f"Finished execution of step '{self.step_id}' in {execution_time:.2f} seconds.")

        return {
            "success": overall_success,
            "results": action_results,
            "execution_time_seconds": execution_time,
        }

    def _execute_action(self, action: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes a single desktop action dictionary.

        Args:
            action (Dict[str, Any]): The action to perform.
            context (Dict[str, Any]): Workflow context for variable substitution.

        Returns:
            A dictionary with the result of the single action.
        """
        context = context or {}
        
        # Apply context variable substitution to string parameters
        action = self._substitute_context_variables(action, context)
        action_type = action.get("type", "unknown").lower()
        start_time = time.time()
        result = {"action_type": action_type, "success": True, "details": ""}

        try:
            if action_type == "click":
                pyautogui.click(x=action.get('x'), y=action.get('y'),
                                clicks=action.get('clicks', 1),
                                interval=action.get('interval', 0.1),
                                button=action.get('button', 'left'))
                result['details'] = f"Clicked at ({action.get('x')}, {action.get('y')})."
            
            elif action_type == "type":
                pyautogui.write(action.get('text', ''), interval=action.get('interval', 0.05))
                result['details'] = f"Typed {len(action.get('text', ''))} characters."

            elif action_type == "press":
                pyautogui.press(action.get('keys', []), presses=action.get('presses', 1))
                result['details'] = f"Pressed key(s): {action.get('keys')}."

            elif action_type == "hotkey":
                pyautogui.hotkey(*action.get('keys', []))
                result['details'] = f"Executed hotkey: {'+'.join(action.get('keys', []))}."

            elif action_type == "move":
                pyautogui.moveTo(action.get('x'), action.get('y'), duration=action.get('duration', 0.25))
                result['details'] = f"Moved mouse to ({action.get('x')}, {action.get('y')})."

            elif action_type == "drag":
                pyautogui.dragTo(action.get('x'), action.get('y'), duration=action.get('duration', 0.5), button=action.get('button', 'left'))
                result['details'] = f"Dragged mouse to ({action.get('x')}, {action.get('y')})."

            elif action_type == "scroll":
                pyautogui.scroll(action.get('amount', 0), x=action.get('x'), y=action.get('y'))
                result['details'] = f"Scrolled by {action.get('amount', 0)} units."

            elif action_type == "screenshot":
                filepath = action.get('filepath', f"screenshot_{int(time.time())}.png")
                region = action.get('region') # Expects a tuple (left, top, width, height)
                img = pyautogui.screenshot(region=region)
                img.save(filepath)
                result['details'] = f"Screenshot saved to {filepath}."
                result['output'] = {"filepath": filepath}

            elif action_type == "locate_image":
                image_path = action.get('image_path')
                confidence = action.get('confidence', 0.9)
                location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                if location:
                    result['details'] = f"Image '{image_path}' found at {location}."
                    result['output'] = {"location": tuple(location)}
                else:
                    raise FileNotFoundError(f"Could not locate image '{image_path}' on screen.")

            elif action_type == "wait_for_image":
                image_path = action.get('image_path')
                timeout = action.get('timeout', 10)
                confidence = action.get('confidence', 0.9)
                wait_start = time.time()
                location = None
                while time.time() - wait_start < timeout:
                    location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                    if location:
                        break
                    time.sleep(0.5)
                if location:
                    result['details'] = f"Image '{image_path}' appeared at {location} after {time.time() - wait_start:.2f}s."
                    result['output'] = {"location": tuple(location)}
                else:
                    raise TimeoutError(f"Timed out waiting for image '{image_path}' to appear.")

            elif action_type == "get_active_window":
                active_window = pyautogui.getActiveWindow()
                if active_window:
                    result['details'] = f"Active window title: '{active_window.title}'."
                    result['output'] = {"title": active_window.title, "size": tuple(active_window.size)}
                else:
                    raise Exception("Could not get active window.")

            elif action_type == "activate_window":
                title = action.get('title')
                window = pyautogui.getWindowsWithTitle(title)
                if window:
                    window[0].activate()
                    result['details'] = f"Activated window with title '{title}'."
                else:
                    raise Exception(f"Window with title '{title}' not found.")

            elif action_type == "close_window":
                title = action.get('title')
                window = pyautogui.getWindowsWithTitle(title)
                if window:
                    window[0].close()
                    result['details'] = f"Closed window with title '{title}'."
                else:
                    raise Exception(f"Window with title '{title}' not found.")
            
            elif action_type == "wait":
                duration = action.get('duration', 1.0)
                time.sleep(duration)
                result['details'] = f"Waited for {duration} seconds."

            # ------------------------------------------------------------------
            # VISION-BASED ACTIONS
            # ------------------------------------------------------------------
            elif action_type == "vision_click":
                """
                Locate an element on screen by template image & click its center.
                Required:
                    template   – path to the template file
                Optional:
                    threshold  – match confidence (default 0.8)
                    wait_time  – seconds to wait before failing (default 10)
                """
                if not VISION_AVAILABLE:
                    raise RuntimeError("Vision utilities not available in this environment.")

                template = action.get("template")
                if not template:
                    raise ValueError("vision_click action requires 'template' path.")

                threshold = action.get("threshold", 0.8)
                wait_time = action.get("wait_time", 10)

                # Wait for element, then click
                x, y, conf = vision_wait_for_element(template, timeout=wait_time, threshold=threshold)
                pyautogui.click(x, y)
                result["details"] = f"Vision-click at ({x},{y}) with confidence {conf:.2f}."
                result["output"] = {"x": x, "y": y, "confidence": conf}

            elif action_type == "wait_for_element":
                """
                Wait until an image template appears on screen.
                Params:
                    template   – path to template file
                    timeout    – seconds to wait (default 10)
                    threshold  – confidence (default 0.8)
                """
                if not VISION_AVAILABLE:
                    raise RuntimeError("Vision utilities not available in this environment.")
                template = action.get("template")
                if not template:
                    raise ValueError("wait_for_element requires 'template' path.")

                timeout = action.get("timeout", 10)
                threshold = action.get("threshold", 0.8)
                x, y, conf = vision_wait_for_element(template, timeout=timeout, threshold=threshold)
                result["details"] = (
                    f"Element '{template}' detected at ({x},{y}) after wait. Confidence {conf:.2f}"
                )
                result["output"] = {"x": x, "y": y, "confidence": conf}

            elif action_type == "ocr_extract":
                """
                Extract text via OCR.
                Two modes:
                  1. Provide explicit region: left, top, width, height.
                  2. Provide template image -> locate then OCR around it with padding.
                """
                if not VISION_AVAILABLE:
                    raise RuntimeError("Vision utilities not available in this environment.")

                # Mode 1: explicit region
                if all(k in action for k in ("left", "top", "width", "height")):
                    left = action["left"]
                    top = action["top"]
                    width = action["width"]
                    height = action["height"]
                # Mode 2: template
                elif "template" in action:
                    tpl = action["template"]
                    pad = action.get("padding", 5)
                    x, y, _ = vision_wait_for_element(tpl, timeout=action.get("timeout", 10))
                    width = action.get("width", 120)
                    height = action.get("height", 40)
                    left = max(0, x - width // 2 - pad)
                    top = max(0, y - height // 2 - pad)
                else:
                    raise ValueError("ocr_extract requires either region coords or a template.")

                text = ocr_from_region(left, top, width, height)
                result["details"] = f"OCR extracted text: '{text[:50]}'"
                result["output"] = {"text": text}

            else:
                raise ValueError(f"Unknown or unsupported action type: '{action_type}'")

        except Exception as e:
            logger.error(f"Action '{action_type}' failed: {e}", exc_info=True)
            result["success"] = False
            result["error"] = str(e)

        result["duration_seconds"] = time.time() - start_time
        return result

    def _substitute_context_variables(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Substitute context variables in action parameters.
        
        Args:
            action: The action dictionary to process
            context: The workflow context containing variables
            
        Returns:
            The action dictionary with substituted variables
        """
        if not context:
            return action
            
        # Create a copy to avoid modifying the original
        substituted_action = action.copy()
        
        # Substitute variables in string values
        for key, value in substituted_action.items():
            if isinstance(value, str):
                for var_name, var_value in context.items():
                    if isinstance(var_value, (str, int, float, bool)):
                        placeholder = f"${{{var_name}}}"
                        if placeholder in value:
                            substituted_action[key] = value.replace(placeholder, str(var_value))
            elif isinstance(value, list):
                # Handle lists of strings (e.g., for hotkey actions)
                substituted_list = []
                for item in value:
                    if isinstance(item, str):
                        substituted_item = item
                        for var_name, var_value in context.items():
                            if isinstance(var_value, (str, int, float, bool)):
                                placeholder = f"${{{var_name}}}"
                                if placeholder in substituted_item:
                                    substituted_item = substituted_item.replace(placeholder, str(var_value))
                        substituted_list.append(substituted_item)
                    else:
                        substituted_list.append(item)
                substituted_action[key] = substituted_list
                
        return substituted_action

