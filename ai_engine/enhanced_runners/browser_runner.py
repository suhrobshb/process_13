"""
Browser Automation Runner
=========================

This module provides a comprehensive runner for automating web browser interactions
using the Playwright library. It acts as a "digital employee" for web-based tasks,
allowing the AI Engine to navigate websites, fill forms, click elements, extract
data, and perform complex sequences of actions as defined in a workflow.

This runner is designed to be robust, with detailed error handling and a wide
range of supported actions to cover most web automation scenarios.
"""

import os
import time
import logging
from typing import Dict, Any, List

# Playwright is the core library for browser automation.
# It's imported with a try-except block for graceful failure in environments
# where it might not be installed.
try:
    from playwright.sync_api import sync_playwright, Page, Browser, ElementHandle, Playwright, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    # Define dummy classes so the file can be imported without Playwright
    Page, Browser, ElementHandle, Playwright, expect = (object, object, object, object, object)

# Configure logging
logger = logging.getLogger(__name__)


class BrowserRunner:
    """
    Executes a sequence of browser automation actions using Playwright.
    """

    def __init__(self, step_id: str, params: Dict[str, Any]):
        """
        Initializes the Browser Runner.

        Args:
            step_id (str): A unique identifier for this step.
            params (Dict[str, Any]): Parameters for the step, including the list of actions.
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Browser automation is not available. Please install Playwright with 'pip install playwright' and run 'playwright install'.")

        self.step_id = step_id
        self.actions = params.get("actions", [])
        self.timeout = params.get("timeout", 120)  # Overall step timeout in seconds
        self.browser_type = params.get("browser_type", "chromium").lower()
        self.headless = params.get("headless", True)
        self.screenshots_dir = params.get("screenshots_dir", f"storage/screenshots/{self.step_id}")
        self.default_action_timeout = params.get("action_timeout", 30000)  # Default timeout for individual actions in ms

        # Ensure screenshots directory exists
        os.makedirs(self.screenshots_dir, exist_ok=True)
        logger.info(f"BrowserRunner for step '{self.step_id}' initialized. Browser: {self.browser_type}, Headless: {self.headless}")

    def execute(self) -> Dict[str, Any]:
        """
        Executes the full sequence of browser actions.
        """
        logger.info(f"Executing browser automation step: {self.step_id}")
        start_time = time.time()
        action_results = []
        overall_success = True

        try:
            with sync_playwright() as playwright:
                browser = self._launch_browser(playwright)
                page = browser.new_page()
                page.set_default_timeout(self.default_action_timeout)

                for i, action_config in enumerate(self.actions, 1):
                    if time.time() - start_time > self.timeout:
                        raise TimeoutError(f"Step '{self.step_id}' timed out after {self.timeout} seconds.")

                    logger.info(f"Executing action {i}/{len(self.actions)}: {action_config.get('type')}")
                    action_result = self._execute_action(page, action_config)
                    action_results.append(action_result)

                    if not action_result["success"]:
                        overall_success = False
                        if action_config.get("stop_on_failure", True):
                            logger.error(f"Action failed, halting execution of step '{self.step_id}'.")
                            break
                    
                    time.sleep(action_config.get("delay_after", 0.25))

                # Take a final screenshot for verification
                final_screenshot_path = os.path.join(self.screenshots_dir, f"final_state_{int(time.time())}.png")
                page.screenshot(path=final_screenshot_path, full_page=True)
                logger.info(f"Final screenshot saved to {final_screenshot_path}")

                browser.close()

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

    def _launch_browser(self, playwright: Playwright) -> Browser:
        """Launches the specified browser type."""
        if self.browser_type == "firefox":
            return playwright.firefox.launch(headless=self.headless)
        if self.browser_type == "webkit":
            return playwright.webkit.launch(headless=self.headless)
        return playwright.chromium.launch(headless=self.headless)

    def _execute_action(self, page: Page, action: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a single browser action."""
        action_type = action.get("type", "unknown").lower()
        start_time = time.time()
        result = {"action_type": action_type, "success": True, "details": ""}

        try:
            selector = action.get("selector", "")
            
            if action_type == "goto":
                url = action.get("url", "")
                page.goto(url, wait_until=action.get("wait_until", "load"))
                result['details'] = f"Navigated to {url}"
            
            elif action_type == "click":
                expect(page.locator(selector)).to_be_visible()
                page.click(selector, button=action.get("button", "left"), delay=action.get("delay", 50))
                result['details'] = f"Clicked element: '{selector}'"
            
            elif action_type == "fill":
                expect(page.locator(selector)).to_be_visible()
                page.fill(selector, action.get("text", ""))
                result['details'] = f"Filled '{selector}' with text."
            
            elif action_type == "type":
                expect(page.locator(selector)).to_be_visible()
                page.type(selector, action.get("text", ""), delay=action.get("delay", 50))
                result['details'] = f"Typed into '{selector}'."

            elif action_type == "press":
                expect(page.locator(selector)).to_be_visible()
                page.press(selector, action.get("key", ""))
                result['details'] = f"Pressed key '{action.get('key')}' on '{selector}'."

            elif action_type == "screenshot":
                filepath = os.path.join(self.screenshots_dir, action.get('filepath', f"action_{int(time.time())}.png"))
                if selector:
                    expect(page.locator(selector)).to_be_visible()
                    page.locator(selector).screenshot(path=filepath)
                    result['details'] = f"Screenshot of element '{selector}' saved."
                else:
                    page.screenshot(path=filepath, full_page=action.get("full_page", True))
                    result['details'] = "Full page screenshot saved."
                result['output'] = {"filepath": filepath}

            elif action_type == "wait_for_selector":
                state = action.get("state", "visible")
                timeout = action.get("timeout") # Uses page default if None
                page.wait_for_selector(selector, state=state, timeout=timeout)
                result['details'] = f"Waited for selector '{selector}' to be {state}."

            elif action_type == "extract":
                expect(page.locator(selector)).to_be_visible()
                element = page.locator(selector)
                attribute = action.get("attribute")
                if attribute:
                    value = element.get_attribute(attribute)
                    result['details'] = f"Extracted attribute '{attribute}' from '{selector}'."
                else:
                    value = element.text_content()
                    result['details'] = f"Extracted text from '{selector}'."
                result['output'] = {"value": value}
            
            elif action_type == "extract_all":
                expect(page.locator(selector).first).to_be_visible()
                elements = page.locator(selector).all()
                attribute = action.get("attribute")
                values = []
                for element in elements:
                    if attribute:
                        values.append(element.get_attribute(attribute))
                    else:
                        values.append(element.text_content())
                result['details'] = f"Extracted {len(values)} values from '{selector}'."
                result['output'] = {"values": values}

            elif action_type == "eval":
                script = action.get("script", "")
                eval_result = page.evaluate(script)
                result['details'] = "Executed JavaScript."
                result['output'] = {"result": eval_result}

            elif action_type == "wait":
                time.sleep(action.get("duration", 1.0))
                result['details'] = f"Waited for {action.get('duration', 1.0)} seconds."

            else:
                raise ValueError(f"Unknown or unsupported action type: '{action_type}'")

        except Exception as e:
            logger.error(f"Action '{action_type}' failed: {e}", exc_info=True)
            result["success"] = False
            result["error"] = str(e)
            # Try to take a screenshot on failure for debugging
            try:
                error_path = os.path.join(self.screenshots_dir, f"error_{action_type}_{int(time.time())}.png")
                page.screenshot(path=error_path)
                result['error_screenshot'] = error_path
            except Exception as screenshot_error:
                logger.error(f"Could not take error screenshot: {screenshot_error}")

        result["duration_seconds"] = time.time() - start_time
        return result
