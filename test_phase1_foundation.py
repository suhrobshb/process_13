import os
import json
import time
import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path
from sqlmodel import select  # needed for queries in workflow engine tests
from ai_engine.models.execution import Execution  # ensure Execution type is available

# Assume a testing environment where a display might not be available.
# We will mock the GUI libraries.
os.environ['DISPLAY'] = ':0'

# Mock necessary modules before they are imported by the application code
# This prevents errors in headless environments.
mock_pyautogui = MagicMock()
sys_modules = {
    'pyautogui': mock_pyautogui,
    'playwright.sync_api': MagicMock(),
    'pynput': MagicMock(),
    'pygetwindow': MagicMock(),
    'PIL': MagicMock(),
}
with patch.dict('sys.modules', sys_modules):
    from ai_engine.enhanced_runners.desktop_runner import DesktopRunner, PYAUTOGUI_AVAILABLE
    from ai_engine.enhanced_runners.browser_runner import BrowserRunner, PLAYWRIGHT_AVAILABLE
    from agent.recorder.multi_monitor_capture import MultiMonitorCapture
    from ai_engine.workflow_engine import WorkflowEngine, execute_workflow_by_id
    from ai_engine.models.workflow import Workflow
    from ai_engine.models.execution import Execution
    from ai_engine.database import get_session, create_db_and_tables, engine
    from sqlmodel import Session, SQLModel, create_engine as create_sql_engine, StaticPool

# -------------------------------------------------------------------- #
# Fixtures
# -------------------------------------------------------------------- #

@pytest.fixture(scope="function")
def test_db():
    """Fixture to set up a temporary in-memory SQLite database for each test function."""
    # We use a separate engine for tests to avoid conflicts with the main app engine
    test_engine = create_sql_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    
    def get_test_session():
        with Session(test_engine) as session:
            yield session

    # Override the app's get_session dependency with our test session
    original_get_session = get_session
    # This is a simplified way to handle dependency override for non-FastAPI app testing
    with patch('ai_engine.workflow_engine.get_session', get_test_session):
        yield test_engine
    
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def mock_pyautogui_fixture():
    """Provides a fresh mock for pyautogui for each test."""
    with patch('ai_engine.enhanced_runners.desktop_runner.pyautogui') as mock:
        mock.size.return_value = (1920, 1080)
        yield mock

@pytest.fixture
def mock_playwright_fixture():
    """Provides a fresh mock for playwright."""
    with patch('ai_engine.enhanced_runners.browser_runner.sync_playwright') as mock_sync:
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_sync.return_value.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        yield mock_page

# -------------------------------------------------------------------- #
# Phase 1.1: Enhanced Desktop/Browser Runners
# -------------------------------------------------------------------- #

class TestEnhancedRunners:
    """Tests for the DesktopRunner and BrowserRunner classes."""

    def test_desktop_runner_executes_actions(self, mock_pyautogui_fixture):
        """Verify DesktopRunner calls pyautogui functions for a sequence of actions."""
        # Arrange
        actions = [
            {"type": "click", "x": 100, "y": 150},
            {"type": "type", "text": "Hello AI!", "interval": 0.01},
            {"type": "hotkey", "keys": ["ctrl", "s"]}
        ]
        runner = DesktopRunner("desktop_step_1", {"actions": actions})

        # Act
        result = runner.execute()

        # Assert
        assert result["success"] is True
        assert len(result["results"]) == 3
        mock_pyautogui_fixture.click.assert_called_once_with(x=100, y=150, clicks=1, interval=0.1, button='left')
        mock_pyautogui_fixture.write.assert_called_once_with("Hello AI!", interval=0.01)
        mock_pyautogui_fixture.hotkey.assert_called_once_with("ctrl", "s")

    def test_browser_runner_executes_actions(self, mock_playwright_fixture):
        """Verify BrowserRunner calls Playwright functions for a sequence of actions."""
        # Arrange
        actions = [
            {"type": "goto", "url": "https://example.com"},
            {"type": "fill", "selector": "#username", "text": "testuser"},
            {"type": "click", "selector": "button[type='submit']"},
            {"type": "screenshot", "filepath": "login.png"}
        ]
        runner = BrowserRunner("browser_step_1", {"actions": actions})

        # Act
        result = runner.execute()

        # Assert
        assert result["success"] is True
        assert len(result["results"]) == 4
        mock_playwright_fixture.goto.assert_called_once_with("https://example.com", wait_until="load")
        mock_playwright_fixture.fill.assert_called_once_with("#username", "testuser")
        mock_playwright_fixture.click.assert_called_once_with("button[type='submit']", button="left", delay=50)
        mock_playwright_fixture.screenshot.assert_called()

# -------------------------------------------------------------------- #
# Phase 1.2: Basic Recording Agent
# -------------------------------------------------------------------- #

class TestRecordingAgent:
    """Tests for the MultiMonitorCapture class."""

    @patch('agent.recorder.multi_monitor_capture.keyboard.Listener')
    @patch('agent.recorder.multi_monitor_capture.mouse.Listener')
    @patch('agent.recorder.multi_monitor_capture.ImageGrab.grab')
    @patch('agent.recorder.multi_monitor_capture.gw')
    def test_recording_lifecycle_and_output(self, mock_gw, mock_grab, mock_mouse, mock_keyboard, tmp_path):
        """Verify the recorder starts, stops, and writes events to a JSON file."""
        # Arrange
        output_dir = tmp_path / "recording_output"
        recorder = MultiMonitorCapture(output_dir=str(output_dir))
        
        # Simulate some events being captured by the (mocked) listeners
        recorder.events = [
            {"type": "click", "timestamp": time.time(), "x": 100, "y": 100},
            {"type": "key", "timestamp": time.time(), "key": "a"},
            {"type": "screenshot", "timestamp": time.time(), "path": str(output_dir / "screen.png")}
        ]

        # Act
        recorder.start()
        time.sleep(0.1) # Give threads a moment to "run"
        recorder.stop()

        # Assert
        # Check that listeners were started and stopped
        mock_keyboard.return_value.start.assert_called_once()
        mock_mouse.return_value.start.assert_called_once()
        mock_keyboard.return_value.stop.assert_called_once()
        mock_mouse.return_value.stop.assert_called_once()
        
        # Check that an events.json file was created
        events_file = output_dir / "events.json"
        assert events_file.exists()
        
        # Check the content of the file
        with open(events_file, 'r') as f:
            data = json.load(f)
        assert len(data) == 3
        assert data[0]['type'] == 'click'
        assert data[1]['type'] == 'key'

# -------------------------------------------------------------------- #
# Phase 1.3: Simple Workflow Engine
# -------------------------------------------------------------------- #

class TestWorkflowEngineIntegration:
    """Tests the WorkflowEngine's ability to execute workflows with enhanced runners."""

    @patch('ai_engine.workflow_engine.DesktopRunner')
    def test_engine_executes_desktop_step(self, MockDesktopRunner, test_db):
        """Verify the engine correctly identifies and executes a desktop step."""
        # Arrange
        mock_runner_instance = MockDesktopRunner.return_value
        mock_runner_instance.execute.return_value = {"success": True, "results": []}
        
        with Session(test_db) as session:
            # Create a workflow with a desktop step
            workflow = Workflow(
                name="Desktop Test Workflow",
                nodes=[{"id": "step1", "type": "desktop", "data": {"actions": []}}],
                edges=[]
            )
            session.add(workflow)
            session.commit()
            workflow_id = workflow.id

        # Act
        execute_workflow_by_id(workflow_id)

        # Assert
        MockDesktopRunner.assert_called_once()
        mock_runner_instance.execute.assert_called_once()
        
        with Session(test_db) as session:
            execution = session.exec(select(Execution).where(Execution.workflow_id == workflow_id)).first()
            assert execution is not None
            assert execution.status == "completed"

    @patch('ai_engine.workflow_engine.BrowserRunner')
    def test_engine_executes_browser_step(self, MockBrowserRunner, test_db):
        """Verify the engine correctly identifies and executes a browser step."""
        # Arrange
        mock_runner_instance = MockBrowserRunner.return_value
        mock_runner_instance.execute.return_value = {"success": True, "results": []}

        with Session(test_db) as session:
            workflow = Workflow(
                name="Browser Test Workflow",
                nodes=[{"id": "step1", "type": "browser", "data": {"actions": []}}],
                edges=[]
            )
            session.add(workflow)
            session.commit()
            workflow_id = workflow.id

        # Act
        execute_workflow_by_id(workflow_id)

        # Assert
        MockBrowserRunner.assert_called_once()
        mock_runner_instance.execute.assert_called_once()

        with Session(test_db) as session:
            execution = session.exec(select(Execution).where(Execution.workflow_id == workflow_id)).first()
            assert execution is not None
            assert execution.status == "completed"

    @patch('ai_engine.workflow_engine.DesktopRunner')
    @patch('ai_engine.workflow_engine.BrowserRunner')
    def test_engine_executes_hybrid_workflow(self, MockBrowserRunner, MockDesktopRunner, test_db):
        """Verify the engine executes a workflow with both desktop and browser steps."""
        # Arrange
        MockDesktopRunner.return_value.execute.return_value = {"success": True}
        MockBrowserRunner.return_value.execute.return_value = {"success": True}

        with Session(test_db) as session:
            workflow = Workflow(
                name="Hybrid Test Workflow",
                nodes=[
                    {"id": "step1", "type": "desktop", "data": {}},
                    {"id": "step2", "type": "browser", "data": {}}
                ],
                edges=[{"source": "step1", "target": "step2"}]
            )
            session.add(workflow)
            session.commit()
            workflow_id = workflow.id

        # Act
        execute_workflow_by_id(workflow_id)

        # Assert
        MockDesktopRunner.assert_called_once()
        MockBrowserRunner.assert_called_once()

        with Session(test_db) as session:
            execution = session.exec(select(Execution).where(Execution.workflow_id == workflow_id)).first()
            assert execution.status == "completed"
            assert len(execution.result['executed_steps']) == 2
