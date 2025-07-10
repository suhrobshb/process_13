"""
Tests for Enhanced Runners Module
---------------------------------

This module contains tests for the enhanced runners that provide desktop and browser
automation capabilities. These tests use mocking to avoid actual automation during testing.
"""

import os
import time
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime

# Import the runners to test
from ai_engine.enhanced_runners.desktop_runner import DesktopRunner
from ai_engine.enhanced_runners.browser_runner import BrowserRunner

# -------------------------------------------------------------------- #
# Fixtures
# -------------------------------------------------------------------- #

@pytest.fixture
def mock_pyautogui():
    """Mock PyAutoGUI to avoid actual mouse/keyboard actions."""
    with patch('ai_engine.enhanced_runners.desktop_runner.pyautogui') as mock:
        # Configure basic mocks
        mock.size.return_value = (1920, 1080)
        mock.FAILSAFE = True
        mock.PAUSE = 0.1
        mock.screenshot.return_value = MagicMock()
        mock.locateOnScreen.return_value = (100, 100, 50, 50)
        yield mock

@pytest.fixture
def mock_playwright():
    """Mock Playwright to avoid browser automation."""
    with patch('ai_engine.enhanced_runners.browser_runner.sync_playwright') as mock_sync_playwright:
        # Create mock objects for the Playwright API
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_element = MagicMock()
        mock_response = MagicMock()
        
        # Configure the mock objects
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright
        mock_playwright.chromium = MagicMock()
        mock_playwright.firefox = MagicMock()
        mock_playwright.webkit = MagicMock()
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_playwright.firefox.launch.return_value = mock_browser
        mock_playwright.webkit.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_page.wait_for_selector.return_value = mock_element
        mock_page.goto.return_value = mock_response
        mock_response.status = 200
        
        yield {
            'playwright': mock_playwright,
            'browser': mock_browser,
            'page': mock_page,
            'element': mock_element,
            'response': mock_response
        }

# -------------------------------------------------------------------- #
# Desktop Runner Tests
# -------------------------------------------------------------------- #

class TestDesktopRunner:
    """Tests for the DesktopRunner class."""
    
    def test_initialization(self):
        """Test that DesktopRunner initializes with correct parameters."""
        runner = DesktopRunner("test_step", {
            "actions": [{"type": "click", "x": 100, "y": 200}],
            "timeout": 30
        })
        
        assert runner.step_id == "test_step"
        assert len(runner.actions) == 1
        assert runner.timeout == 30
        
    def test_click_action(self, mock_pyautogui):
        """Test click action execution."""
        runner = DesktopRunner("click_test", {
            "actions": [{"type": "click", "x": 100, "y": 200, "button": "left", "clicks": 2}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["action_type"] == "click"
        assert result["results"][0]["success"] is True
        
        # Verify PyAutoGUI was called correctly
        mock_pyautogui.click.assert_called_once_with(x=100, y=200, button="left", clicks=2, interval=0.1)
    
    def test_move_action(self, mock_pyautogui):
        """Test mouse move action execution."""
        runner = DesktopRunner("move_test", {
            "actions": [{"type": "move", "x": 500, "y": 600, "duration": 0.5}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_pyautogui.moveTo.assert_called_once_with(500, 600, duration=0.5)
    
    def test_drag_action(self, mock_pyautogui):
        """Test drag action execution."""
        runner = DesktopRunner("drag_test", {
            "actions": [{
                "type": "drag",
                "x": 300, "y": 400,
                "duration": 1.0
            }]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_pyautogui.dragTo.assert_called_once_with(300, 400, duration=1.0, button='left')
    
    def test_type_action(self, mock_pyautogui):
        """Test typing action execution."""
        runner = DesktopRunner("type_test", {
            "actions": [{"type": "type", "text": "Hello, world!", "interval": 0.05}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_pyautogui.write.assert_called_once_with("Hello, world!", interval=0.05)
    
    def test_hotkey_action(self, mock_pyautogui):
        """Test hotkey action execution."""
        runner = DesktopRunner("hotkey_test", {
            "actions": [{"type": "hotkey", "keys": ["ctrl", "c"]}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_pyautogui.hotkey.assert_called_once_with("ctrl", "c")
    
    def test_press_action(self, mock_pyautogui):
        """Test key press action execution."""
        runner = DesktopRunner("press_test", {
            "actions": [{"type": "press", "keys": ["enter"], "presses": 2}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_pyautogui.press.assert_called_once_with(["enter"], presses=2)
    
    def test_screenshot_action(self, mock_pyautogui):
        """Test screenshot action execution."""
        runner = DesktopRunner("screenshot_test", {
            "actions": [{"type": "screenshot", "filepath": "test.png"}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_pyautogui.screenshot.assert_called_once()
        mock_pyautogui.screenshot.return_value.save.assert_called_once_with("test.png")
    
    def test_locate_image_action(self, mock_pyautogui):
        """Test locate image action execution."""
        runner = DesktopRunner("locate_image_test", {
            "actions": [{"type": "locate_image", "image_path": "test_image.png", "confidence": 0.8}]
        })
            
        result = runner.execute()
        
        assert result["success"] is True
        mock_pyautogui.locateOnScreen.assert_called_once_with("test_image.png", confidence=0.8)
        assert result["results"][0]["output"]["location"] == (100, 100, 50, 50)
    
    def test_wait_for_image_action(self, mock_pyautogui):
        """Test wait for image action execution."""
        runner = DesktopRunner("wait_image_test", {
            "actions": [{"type": "wait_for_image", "image_path": "test_wait_image.png", "timeout": 5, "confidence": 0.9}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_pyautogui.locateOnScreen.assert_called_with("test_wait_image.png", confidence=0.9)
        assert result["results"][0]["output"]["location"] == (100, 100, 50, 50)
    
    def test_unknown_action_type(self, mock_pyautogui):
        """Test handling of unknown action type."""
        runner = DesktopRunner("unknown_test", {
            "actions": [{"type": "nonexistent_action", "param": "value"}]
        })
        
        result = runner.execute()
        
        assert result["success"] is False
        assert "error" in result
        assert "Unknown action type" in result["error"]
    
    def test_timeout(self, mock_pyautogui):
        """Test timeout handling."""
        # Mock time.time to simulate timeout
        original_time = time.time
        
        try:
            mock_times = [100.0, 100.0, 200.0]  # First call for start time, second call exceeds timeout
            time.time = lambda: mock_times.pop(0) if mock_times else 300.0
            
            runner = DesktopRunner("timeout_test", {
                "actions": [
                    {"type": "click", "x": 100, "y": 100},
                    {"type": "click", "x": 200, "y": 200}  # This action should not execute due to timeout
                ],
                "timeout": 10  # 10 second timeout
            })
            
            result = runner.execute()
            
            assert result["success"] is False
            assert "error" in result
            assert "timed out" in result["error"].lower()
            assert len(result["results"]) == 0  # No actions completed before timeout
        finally:
            time.time = original_time
    
    def test_action_error_handling(self, mock_pyautogui):
        """Test error handling during action execution."""
        # Make PyAutoGUI click raise an exception
        mock_pyautogui.click.side_effect = Exception("Test error")
        
        runner = DesktopRunner("error_test", {
            "actions": [{"type": "click", "x": 100, "y": 100}]
        })
        
        result = runner.execute()
        
        assert result["success"] is False
        assert "error" in result
        assert "Test error" in result["error"]

# -------------------------------------------------------------------- #
# Browser Runner Tests
# -------------------------------------------------------------------- #

class TestBrowserRunner:
    """Tests for the BrowserRunner class."""
    
    def test_initialization(self):
        """Test that BrowserRunner initializes with correct parameters."""
        runner = BrowserRunner("test_browser", {
            "actions": [{"type": "goto", "url": "https://example.com"}],
            "timeout": 60,
            "browser_type": "firefox",
            "headless": False
        })
        
        assert runner.step_id == "test_browser"
        assert len(runner.actions) == 1
        assert runner.timeout == 60
        assert runner.browser_type == "firefox"
        assert runner.headless is False
        assert os.path.exists(runner.screenshots_dir)
    
    def test_goto_action(self, mock_playwright):
        """Test navigation action execution."""
        runner = BrowserRunner("goto_test", {
            "actions": [{"type": "goto", "url": "https://example.com", "wait_until": "networkidle"}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_playwright['page'].goto.assert_called_once_with(
            "https://example.com", wait_until="networkidle"
        )
    
    def test_click_action(self, mock_playwright):
        """Test click action execution."""
        runner = BrowserRunner("click_test", {
            "actions": [{"type": "click", "selector": "#button", "delay": 50, "button": "left"}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_playwright['page'].click.assert_called_once_with(
            "#button", delay=50, button="left"
        )
    
    def test_fill_action(self, mock_playwright):
        """Test form filling action execution."""
        runner = BrowserRunner("fill_test", {
            "actions": [{"type": "fill", "selector": "#username", "text": "testuser"}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_playwright['page'].fill.assert_called_once_with("#username", "testuser")
    
    def test_screenshot_action(self, mock_playwright):
        """Test screenshot action execution."""
        runner = BrowserRunner("screenshot_test", {
            "actions": [{"type": "screenshot", "filepath": "page.png", "full_page": True}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_playwright['page'].screenshot.assert_called_once_with(
            path=os.path.join(runner.screenshots_dir, "page.png"), full_page=True
        )
    
    def test_wait_for_selector_action(self, mock_playwright):
        """Test wait for selector action execution."""
        runner = BrowserRunner("wait_selector_test", {
            "actions": [{"type": "wait_for_selector", "selector": "#element", "state": "visible", "timeout": 5000}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_playwright['page'].wait_for_selector.assert_called_with(
            "#element", state="visible", timeout=5000
        )
    
    def test_press_action(self, mock_playwright):
        """Test key press action execution."""
        runner = BrowserRunner("press_test", {
            "actions": [{"type": "press", "selector": "#input", "key": "Enter"}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_playwright['page'].press.assert_called_once_with("#input", "Enter")
    
    def test_type_action(self, mock_playwright):
        """Test typing action execution."""
        runner = BrowserRunner("type_test", {
            "actions": [{"type": "type", "selector": "#input", "text": "Hello world", "delay": 50}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_playwright['page'].type.assert_called_once_with("#input", "Hello world", delay=50)
    
    def test_eval_action(self, mock_playwright):
        """Test JavaScript evaluation action execution."""
        runner = BrowserRunner("eval_test", {
            "actions": [{"type": "eval", "script": "document.title"}]
        })
        
        # Set up the evaluate mock to return a value
        mock_playwright['page'].evaluate.return_value = "Page Title"
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_playwright['page'].evaluate.assert_called_once_with("document.title")
        assert result["results"][0]["output"]["result"] == "Page Title"
    
    def test_extract_action(self, mock_playwright):
        """Test data extraction action execution."""
        runner = BrowserRunner("extract_test", {
            "actions": [{"type": "extract", "selector": ".content", "attribute": "data-id"}]
        })
        
        # Set up the get_attribute mock to return a value
        mock_playwright['page'].locator.return_value.get_attribute.return_value = "123"
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_playwright['page'].locator.assert_called_with(".content")
        mock_playwright['page'].locator.return_value.get_attribute.assert_called_once_with("data-id")
        assert result["results"][0]["output"]["value"] == "123"
    
    def test_extract_all_action(self, mock_playwright):
        """Test multiple elements extraction action execution."""
        runner = BrowserRunner("extract_all_test", {
            "actions": [{"type": "extract_all", "selector": ".items", "attribute": "href"}]
        })
        
        # Set up the query_selector_all mock to return multiple elements
        element1 = MagicMock()
        element2 = MagicMock()
        element1.get_attribute.return_value = "link1"
        element2.get_attribute.return_value = "link2"
        mock_playwright['page'].locator.return_value.all.return_value = [element1, element2]
        
        result = runner.execute()
        
        assert result["success"] is True
        mock_playwright['page'].locator.assert_called_with(".items")
        assert result["results"][0]["output"]["values"] == ["link1", "link2"]
    
    def test_browser_selection(self, mock_playwright):
        """Test browser type selection."""
        # Test Chromium (default)
        runner1 = BrowserRunner("chromium_test", {
            "actions": [{"type": "goto", "url": "https://example.com"}],
            "browser_type": "chromium"
        })
        runner1.execute()
        mock_playwright['playwright'].chromium.launch.assert_called_once()
        
        # Reset mocks
        mock_playwright['playwright'].chromium.launch.reset_mock()
        
        # Test Firefox
        runner2 = BrowserRunner("firefox_test", {
            "actions": [{"type": "goto", "url": "https://example.com"}],
            "browser_type": "firefox"
        })
        runner2.execute()
        mock_playwright['playwright'].firefox.launch.assert_called_once()
    
    def test_headless_mode(self, mock_playwright):
        """Test headless mode configuration."""
        # Test headless mode (default)
        runner1 = BrowserRunner("headless_test", {
            "actions": [{"type": "goto", "url": "https://example.com"}],
            "headless": True
        })
        runner1.execute()
        mock_playwright['playwright'].chromium.launch.assert_called_once_with(headless=True)
        
        # Reset mocks
        mock_playwright['playwright'].chromium.launch.reset_mock()
        
        # Test headed mode
        runner2 = BrowserRunner("headed_test", {
            "actions": [{"type": "goto", "url": "https://example.com"}],
            "headless": False
        })
        runner2.execute()
        mock_playwright['playwright'].chromium.launch.assert_called_once_with(headless=False)
    
    def test_error_handling(self, mock_playwright):
        """Test error handling during action execution."""
        # Make page.goto raise an exception
        mock_playwright['page'].goto.side_effect = Exception("Navigation failed")
        
        runner = BrowserRunner("error_test", {
            "actions": [{"type": "goto", "url": "https://example.com"}]
        })
        
        result = runner.execute()
        
        assert result["success"] is False
        assert "error" in result
        assert "Navigation failed" in result["error"]
    
    def test_final_screenshot(self, mock_playwright):
        """Test that a final screenshot is taken at the end of execution."""
        runner = BrowserRunner("final_screenshot_test", {
            "actions": [{"type": "goto", "url": "https://example.com"}]
        })
        
        result = runner.execute()
        
        assert result["success"] is True
        # Check that screenshot was called at least once (for the final state)
        mock_playwright['page'].screenshot.assert_called()

# -------------------------------------------------------------------- #
# Integration with RunnerFactory Tests
# -------------------------------------------------------------------- #

class TestRunnerFactoryIntegration:
    """Tests for integrating enhanced runners with the RunnerFactory."""
    
    def test_desktop_runner_creation(self):
        """Test that the factory can create a desktop runner."""
        from ai_engine.workflow_runners import RunnerFactory
        
        runner = RunnerFactory.create_runner("desktop", "test_desktop", {
            "actions": [{"type": "click", "x": 100, "y": 100}]
        })
        
        assert isinstance(runner, DesktopRunner)
        assert runner.step_id == "test_desktop"
    
    def test_browser_runner_creation(self):
        """Test that the factory can create a browser runner."""
        from ai_engine.workflow_runners import RunnerFactory
        
        runner = RunnerFactory.create_runner("browser", "test_browser", {
            "actions": [{"type": "goto", "url": "https://example.com"}]
        })
        
        assert isinstance(runner, BrowserRunner)
        assert runner.step_id == "test_browser"
