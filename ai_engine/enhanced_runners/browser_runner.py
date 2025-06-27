"""
Browser Automation Runner

This module provides a Runner implementation for browser automation using Playwright.
It allows workflows to control web browsers, navigate to URLs, interact with web elements,
fill forms, and perform other browser-based actions as part of an automated workflow.
"""

import os
import time
import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from playwright.sync_api import sync_playwright, Page, Browser, ElementHandle
from urllib.parse import urlparse

# Set up logging
logger = logging.getLogger("browser_runner")

class BrowserRunner:
    """
    Runner for executing browser automation actions using Playwright.
    
    This runner can be used to automate web browser interactions
    as part of a workflow, including navigation, clicking elements,
    filling forms, and extracting data.
    """
    
    def __init__(self, step_id: str, params: Dict[str, Any]):
        """
        Initialize the Browser Runner with step parameters.
        
        Args:
            step_id: Unique identifier for this step in the workflow
            params: Dictionary containing the actions to perform
        """
        self.step_id = step_id
        self.actions = params.get("actions", [])
        self.timeout = params.get("timeout", 60)  # Default 60 second timeout
        self.browser_type = params.get("browser_type", "chromium")  # chromium, firefox, webkit
        self.headless = params.get("headless", True)  # Run headless by default
        self.screenshots_dir = params.get("screenshots_dir", "browser_screenshots")
        self.default_navigation_timeout = params.get("navigation_timeout", 30000)  # 30 seconds
        
        # Ensure screenshots directory exists
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
    
    def execute(self) -> Dict[str, Any]:
        """
        Execute the browser automation actions.
        
        Returns:
            Dictionary with success status and results or error information
        """
        logger.info(f"Starting execution of browser automation step {self.step_id}")
        start_time = time.time()
        
        try:
            with sync_playwright() as playwright:
                # Select browser type
                if self.browser_type == "firefox":
                    browser_instance = playwright.firefox
                elif self.browser_type == "webkit":
                    browser_instance = playwright.webkit
                else:
                    browser_instance = playwright.chromium
                
                # Launch browser
                browser = browser_instance.launch(headless=self.headless)
                
                # Create a new page
                page = browser.new_page(
                    viewport={'width': 1280, 'height': 800},
                    accept_downloads=True
                )
                page.set_default_navigation_timeout(self.default_navigation_timeout)
                
                # Execute actions
                results = []
                for i, action in enumerate(self.actions):
                    # Check for timeout
                    if time.time() - start_time > self.timeout:
                        raise TimeoutError(f"Browser automation step {self.step_id} timed out after {self.timeout} seconds")
                    
                    # Execute the action
                    result = self._execute_action(page, action, i)
                    results.append(result)
                    
                    # Apply delay if specified
                    delay = action.get("delay", 0.5)
                    time.sleep(delay)
                
                # Take final screenshot
                final_screenshot = f"{self.screenshots_dir}/{self.step_id}_final_{int(time.time())}.png"
                page.screenshot(path=final_screenshot)
                
                # Close browser
                browser.close()
                
                logger.info(f"Step {self.step_id} completed in {time.time() - start_time:.2f}s")
                return {
                    "success": True,
                    "result": {
                        "actions_executed": len(results),
                        "action_results": results,
                        "final_screenshot": final_screenshot,
                        "execution_time": time.time() - start_time
                    }
                }
                
        except Exception as e:
            logger.error(f"Error in browser automation step {self.step_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "partial_results": results if 'results' in locals() else []
            }
    
    def _execute_action(self, page: Page, action: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        Execute a single browser automation action.
        
        Args:
            page: Playwright Page object
            action: Dictionary describing the action to perform
            index: Index of this action in the sequence
            
        Returns:
            Dictionary with action result information
        """
        action_type = action.get("type", "")
        logger.debug(f"Executing browser action {index}: {action_type}")
        
        result = {"type": action_type, "success": True}
        
        try:
            if action_type == "goto":
                url = action.get("url", "")
                if not url:
                    raise ValueError("No URL specified for goto action")
                
                # Ensure URL has protocol
                if not url.startswith(("http://", "https://")):
                    url = f"https://{url}"
                
                # Navigate to URL
                response = page.goto(url, wait_until=action.get("wait_until", "load"))
                result["details"] = f"Navigated to {url}"
                result["status"] = response.status if response else None
                result["url"] = page.url
                
            elif action_type == "click":
                selector = action.get("selector", "")
                if not selector:
                    raise ValueError("No selector specified for click action")
                
                # Wait for selector to be visible
                page.wait_for_selector(selector, state="visible", timeout=action.get("timeout", 10000))
                
                # Click element
                page.click(selector, delay=action.get("click_delay", 0), button=action.get("button", "left"))
                result["details"] = f"Clicked element with selector: {selector}"
                
            elif action_type == "fill":
                selector = action.get("selector", "")
                text = action.get("text", "")
                if not selector:
                    raise ValueError("No selector specified for fill action")
                
                # Wait for selector to be visible
                page.wait_for_selector(selector, state="visible", timeout=action.get("timeout", 10000))
                
                # Fill form field
                page.fill(selector, text)
                result["details"] = f"Filled text in element with selector: {selector}"
                
            elif action_type == "select":
                selector = action.get("selector", "")
                value = action.get("value", "")
                if not selector:
                    raise ValueError("No selector specified for select action")
                
                # Select option
                page.select_option(selector, value=value)
                result["details"] = f"Selected option with value '{value}' in selector: {selector}"
                
            elif action_type == "check":
                selector = action.get("selector", "")
                if not selector:
                    raise ValueError("No selector specified for check action")
                
                # Check checkbox
                page.check(selector)
                result["details"] = f"Checked checkbox with selector: {selector}"
                
            elif action_type == "uncheck":
                selector = action.get("selector", "")
                if not selector:
                    raise ValueError("No selector specified for uncheck action")
                
                # Uncheck checkbox
                page.uncheck(selector)
                result["details"] = f"Unchecked checkbox with selector: {selector}"
                
            elif action_type == "screenshot":
                selector = action.get("selector")
                filename = action.get("filename", f"{self.screenshots_dir}/{self.step_id}_{index}_{int(time.time())}.png")
                
                if selector:
                    # Screenshot specific element
                    element = page.wait_for_selector(selector, state="visible", timeout=action.get("timeout", 10000))
                    element.screenshot(path=filename)
                    result["details"] = f"Screenshot of element {selector} saved to {filename}"
                else:
                    # Screenshot entire page
                    page.screenshot(path=filename, full_page=action.get("full_page", False))
                    result["details"] = f"Screenshot of page saved to {filename}"
                
                result["filename"] = filename
                
            elif action_type == "wait_for_selector":
                selector = action.get("selector", "")
                if not selector:
                    raise ValueError("No selector specified for wait_for_selector action")
                
                # Wait for selector
                state = action.get("state", "visible")  # visible, hidden, attached, detached
                timeout = action.get("timeout", 30000)
                page.wait_for_selector(selector, state=state, timeout=timeout)
                result["details"] = f"Waited for selector: {selector} to be {state}"
                
            elif action_type == "wait_for_navigation":
                # Wait for navigation to complete
                page.wait_for_navigation(
                    url=action.get("url"),
                    wait_until=action.get("wait_until", "load"),
                    timeout=action.get("timeout", 30000)
                )
                result["details"] = f"Waited for navigation to complete, current URL: {page.url}"
                result["url"] = page.url
                
            elif action_type == "wait_for_load_state":
                # Wait for specific load state
                state = action.get("state", "load")  # load, domcontentloaded, networkidle
                page.wait_for_load_state(state, timeout=action.get("timeout", 30000))
                result["details"] = f"Waited for page to reach load state: {state}"
                
            elif action_type == "press":
                selector = action.get("selector", "")
                key = action.get("key", "")
                if not key:
                    raise ValueError("No key specified for press action")
                
                if selector:
                    # Press key on specific element
                    page.press(selector, key)
                    result["details"] = f"Pressed key '{key}' on element with selector: {selector}"
                else:
                    # Press key on page
                    page.keyboard.press(key)
                    result["details"] = f"Pressed key '{key}' on page"
                
            elif action_type == "type":
                selector = action.get("selector", "")
                text = action.get("text", "")
                
                if selector:
                    # Type on specific element
                    page.type(selector, text, delay=action.get("delay", 100))
                    result["details"] = f"Typed text on element with selector: {selector}"
                else:
                    # Type on page
                    page.keyboard.type(text, delay=action.get("delay", 100))
                    result["details"] = f"Typed text on page"
                
            elif action_type == "eval":
                script = action.get("script", "")
                if not script:
                    raise ValueError("No script specified for eval action")
                
                # Evaluate JavaScript
                eval_result = page.evaluate(script)
                result["details"] = f"Evaluated JavaScript script"
                result["eval_result"] = str(eval_result)
                
            elif action_type == "extract":
                selector = action.get("selector", "")
                attribute = action.get("attribute")
                
                if not selector:
                    raise ValueError("No selector specified for extract action")
                
                # Wait for selector
                element = page.wait_for_selector(selector, state="visible", timeout=action.get("timeout", 10000))
                
                if attribute:
                    # Extract attribute
                    value = element.get_attribute(attribute)
                    result["details"] = f"Extracted attribute '{attribute}' from selector: {selector}"
                else:
                    # Extract text content
                    value = element.text_content()
                    result["details"] = f"Extracted text content from selector: {selector}"
                
                result["extracted_value"] = value
                
            elif action_type == "extract_all":
                selector = action.get("selector", "")
                attribute = action.get("attribute")
                
                if not selector:
                    raise ValueError("No selector specified for extract_all action")
                
                # Wait for at least one element
                page.wait_for_selector(selector, state="visible", timeout=action.get("timeout", 10000))
                
                # Get all elements
                elements = page.query_selector_all(selector)
                
                values = []
                for element in elements:
                    if attribute:
                        # Extract attribute
                        value = element.get_attribute(attribute)
                    else:
                        # Extract text content
                        value = element.text_content()
                    values.append(value)
                
                result["details"] = f"Extracted values from {len(values)} elements matching selector: {selector}"
                result["extracted_values"] = values
                
            elif action_type == "back":
                # Go back in browser history
                page.go_back(wait_until=action.get("wait_until", "load"))
                result["details"] = f"Navigated back to {page.url}"
                result["url"] = page.url
                
            elif action_type == "forward":
                # Go forward in browser history
                page.go_forward(wait_until=action.get("wait_until", "load"))
                result["details"] = f"Navigated forward to {page.url}"
                result["url"] = page.url
                
            elif action_type == "reload":
                # Reload the page
                page.reload(wait_until=action.get("wait_until", "load"))
                result["details"] = f"Reloaded page {page.url}"
                
            elif action_type == "set_viewport":
                width = action.get("width", 1280)
                height = action.get("height", 800)
                
                # Set viewport size
                page.set_viewport_size({"width": width, "height": height})
                result["details"] = f"Set viewport size to {width}x{height}"
                
            elif action_type == "wait":
                # Simple wait/sleep
                duration = action.get("duration", 1)
                time.sleep(duration)
                result["details"] = f"Waited for {duration} seconds"
                
            else:
                raise ValueError(f"Unknown action type: {action_type}")
                
        except Exception as e:
            logger.error(f"Error executing browser action {index} ({action_type}): {str(e)}")
            result["success"] = False
            result["error"] = str(e)
            
        return result

# Register this runner with the factory
def register_browser_runner(factory):
    """Register the Browser Runner with the provided factory."""
    factory.register("browser", BrowserRunner)
