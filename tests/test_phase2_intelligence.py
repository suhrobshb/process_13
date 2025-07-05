#!/usr/bin/env python3
"""
Tests for Phase 2: Intelligence Layer
=====================================

This module provides a comprehensive test suite for the core components
of the AI Engine's intelligence layer. It validates:

1.  **AILearningEngine**: Its ability to analyze raw event data and convert it
    into a structured, high-level workflow. This includes testing event
    clustering, intent recognition (via mocked LLM), and confidence scoring.

2.  **DynamicModuleGenerator**: Its capability to take a structured workflow
    and generate executable, sandboxed Python code along with corresponding
    validation tests.

3.  **Real-time Streaming**: The WebSocket integration that streams analysis
    results to the frontend as they are generated.

4.  **End-to-End Pipeline**: The seamless integration of the learning engine
    and the module generator, from raw recording to a validated, executable
    workflow module.

Mocking is used extensively to isolate components and to run these tests in
a headless environment without actual GUI interactions or LLM API calls.
"""

import json
import time
import pytest
from unittest.mock import patch, MagicMock, mock_open, AsyncMock

# Import the main classes to be tested
from ai_engine.ai_learning_engine import AILearningEngine
from ai_engine.dynamic_module_generator import DynamicModuleGenerator
from ai_engine.routers.websocket_router import run_analysis_and_stream, manager as connection_manager

# -------------------------------------------------------------------- #
# Fixtures and Sample Data
# -------------------------------------------------------------------- #

@pytest.fixture
def sample_raw_recording_data() -> list:
    """
    Provides a realistic, raw event stream as captured by the recording agent.
    Includes time gaps and window changes to test clustering logic.
    """
    base_time = time.time()
    return [
        # Action 1: Login
        {'timestamp': base_time, 'type': 'window_change', 'title': 'Login - Company CRM'},
        {'timestamp': base_time + 0.5, 'type': 'click', 'details': {'x': 300, 'y': 200, 'element_text': 'Username'}},
        {'timestamp': base_time + 1.0, 'type': 'type', 'details': {'text': 'admin'}},
        {'timestamp': base_time + 1.5, 'type': 'click', 'details': {'x': 300, 'y': 250, 'element_text': 'Password'}},
        {'timestamp': base_time + 2.0, 'type': 'type', 'details': {'text': 'password123'}},
        {'timestamp': base_time + 2.5, 'type': 'click', 'details': {'x': 300, 'y': 300, 'element_text': 'Submit'}},
        # --- Time gap and window change indicates a new action ---
        {'timestamp': base_time + 6.0, 'type': 'window_change', 'title': 'Dashboard - Company CRM'},
        # Action 2: Create Report
        {'timestamp': base_time + 6.5, 'type': 'click', 'details': {'x': 100, 'y': 50, 'element_text': 'Reports'}},
        {'timestamp': base_time + 7.0, 'type': 'click', 'details': {'x': 120, 'y': 80, 'element_text': 'New Sales Report'}},
        {'timestamp': base_time + 7.5, 'type': 'type', 'details': {'text': 'Q2 Sales Summary'}},
        {'timestamp': base_time + 8.0, 'type': 'key', 'key': 'Key.backspace'}, # Simulate a mistake
        {'timestamp': base_time + 8.5, 'type': 'click', 'details': {'x': 500, 'y': 600, 'element_text': 'Generate Report'}},
    ]

@pytest.fixture
def sample_structured_workflow() -> dict:
    """
    Provides a sample structured workflow, simulating the output of the AILearningEngine.
    This is used as input for testing the DynamicModuleGenerator in isolation.
    """
    return {
        "id": "test_workflow_123",
        "name": "Process New Purchase Order",
        "overall_confidence": 0.88,
        "nodes": [
            {
                "id": "step1_login",
                "type": "desktop",
                "data": {
                    "label": "Login to CRM",
                    "description": "User logs into the main CRM application.",
                    "confidence_score": 0.95,
                    "raw_actions": [
                        {'type': 'click', 'x': 300, 'y': 200},
                        {'type': 'type', 'text': 'admin'}
                    ]
                }
            },
            {
                "id": "step2_create_report",
                "type": "browser",
                "data": {
                    "label": "Create Sales Report",
                    "description": "User navigates to the reports section and generates a new report.",
                    "confidence_score": 0.81,
                    "raw_actions": [
                        {'type': 'goto', 'url': 'https://crm.company.com/reports'},
                        {'type': 'click', 'selector': '#new-report-btn'}
                    ]
                }
            }
        ],
        "edges": [{"source": "step1_login", "target": "step2_create_report"}]
    }

# -------------------------------------------------------------------- #
# Phase 2.1: AI Learning Engine Tests
# -------------------------------------------------------------------- #

class TestAILearningEngine:
    """Tests the functionality of the AILearningEngine."""

    def test_event_clustering(self, sample_raw_recording_data):
        """Verify that raw events are correctly grouped into logical actions."""
        # Arrange
        engine = AILearningEngine(sample_raw_recording_data)
        
        # Act
        clusters = engine._cluster_events_into_actions()
        
        # Assert
        assert len(clusters) == 2, "Should identify two distinct actions based on time gap and window change"
        assert len(clusters[0]) == 6, "First cluster (login) should contain 6 events"
        assert len(clusters[1]) == 5, "Second cluster (create report) should contain 5 events"
        assert clusters[0][0]['type'] == 'window_change'
        assert clusters[1][0]['type'] == 'window_change'

    def test_action_summarization_with_mock_llm(self):
        """Ensure the engine calls the LLM with the correct prompt to summarize actions."""
        # Arrange
        action_cluster = [
            {'type': 'click', 'details': {'element_text': 'Username'}},
            {'type': 'type', 'details': {'text': 'admin'}},
        ]
        engine = AILearningEngine([])
        
        # Act
        with patch.object(engine.llm, 'generate', return_value="Log into System") as mock_generate:
            title, _ = engine._get_action_summary_with_llm(action_cluster)
        
        # Assert
        assert title == "Log into System"
        mock_generate.assert_called_once()
        prompt_arg = mock_generate.call_args[0][0]
        assert "summarize the following sequence" in prompt_arg.lower()
        assert "Username" in prompt_arg
        assert "admin" in prompt_arg

    def test_confidence_scoring_logic(self):
        """Test the confidence scoring based on event patterns."""
        # Arrange
        engine = AILearningEngine([])
        
        # A clear, common pattern should have high confidence
        high_confidence_cluster = [
            {'type': 'click', 'details': {'element_text': 'Username'}},
            {'type': 'type', 'details': {'text': 'test'}},
            {'type': 'click', 'details': {'element_text': 'Password'}},
            {'type': 'type', 'details': {'text': 'pass'}},
            {'type': 'click', 'details': {'element_text': 'Submit'}},
        ]
        
        # A sequence with mistakes or cancellations should have lower confidence
        low_confidence_cluster = [
            {'type': 'type', 'details': {'text': 'wrng'}},
            {'type': 'key', 'key': 'Key.backspace'},
            {'type': 'key', 'key': 'Key.backspace'},
            {'type': 'type', 'details': {'text': 'correct'}},
            {'type': 'click', 'details': {'element_text': 'Cancel'}},
        ]
        
        # Act
        high_score = engine._calculate_confidence_score(high_confidence_cluster)
        low_score = engine._calculate_confidence_score(low_confidence_cluster)
        
        # Assert
        assert high_score > 0.85, "A clear login pattern should have high confidence"
        assert low_score < 0.80, "A sequence with errors and cancellations should have lower confidence"

    def test_end_to_end_workflow_generation(self, sample_raw_recording_data):
        """Test the full analysis process from raw events to a structured workflow."""
        # Arrange
        engine = AILearningEngine(sample_raw_recording_data)
        
        # Act
        workflow = engine.analyze_and_generate_workflow()
        
        # Assert
        assert "name" in workflow
        assert "overall_confidence" in workflow
        assert isinstance(workflow["overall_confidence"], float)
        assert "nodes" in workflow and len(workflow["nodes"]) == 2
        assert "edges" in workflow and len(workflow["edges"]) == 1
        
        # Check node structure
        node1 = workflow["nodes"][0]
        assert "id" in node1 and node1["id"] == "action_step_1"
        assert "type" in node1 and node1["type"] == "desktop"
        assert "data" in node1
        assert "label" in node1["data"]
        assert "confidence_score" in node1["data"]
        assert "raw_actions" in node1["data"] and len(node1["data"]["raw_actions"]) == 6
        
        # Check edge structure
        edge1 = workflow["edges"][0]
        assert edge1["source"] == "action_step_1"
        assert edge1["target"] == "action_step_2"

    def test_streaming_callback_is_invoked(self, sample_raw_recording_data):
        """Verify the stream_callback is called for each generated node."""
        # Arrange
        mock_callback = MagicMock()
        engine = AILearningEngine(sample_raw_recording_data, stream_callback=mock_callback)

        # Act
        engine.analyze_and_generate_workflow()

        # Assert
        assert mock_callback.call_count == 2, "Callback should be called once for each of the two clusters"
        # Check the payload of the first call
        first_call_args = mock_callback.call_args_list[0].args[0]
        assert first_call_args['id'] == 'action_step_1'
        assert 'label' in first_call_args['data']
        # Check the payload of the second call
        second_call_args = mock_callback.call_args_list[1].args[0]
        assert second_call_args['id'] == 'action_step_2'

# -------------------------------------------------------------------- #
# Phase 2.2: Dynamic Module Generator Tests
# -------------------------------------------------------------------- #

class TestDynamicModuleGenerator:
    """Tests the functionality of the DynamicModuleGenerator."""

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_code_generation_structure(self, mock_file, mock_mkdir, sample_structured_workflow):
        """Verify that the generated Python and test code have the correct structure."""
        # Arrange
        generator = DynamicModuleGenerator(sample_structured_workflow)
        
        # Act
        module_code, test_code = generator._generate_code()
        
        # Assert Module Code
        assert f"Workflow ID: {sample_structured_workflow['name']}" in module_code
        assert f"Overall Confidence: {sample_structured_workflow['overall_confidence']}" in module_code
        assert "WORKFLOW_NODES =" in module_code
        assert "def run(context: dict) -> dict:" in module_code
        assert "from ai_engine.enhanced_runners.desktop_runner import DesktopRunner" in module_code
        assert "from ai_engine.enhanced_runners.browser_runner import BrowserRunner" in module_code
        
        # Assert Test Code
        assert f"Workflow ID: {sample_structured_workflow['name']}" in test_code
        assert "def test_workflow_orchestration(" in test_code
        assert "MockDesktopRunner.assert_any_call" in test_code
        assert "MockBrowserRunner.assert_any_call" in test_code
        assert f"assert len(results) == {len(sample_structured_workflow['nodes'])}" in test_code

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pytest.main")
    def test_validation_process(self, mock_pytest_main, mock_file, mock_mkdir, sample_structured_workflow):
        """Test the validation logic for generated modules."""
        generator = DynamicModuleGenerator(sample_structured_workflow)
        
        # Scenario 1: Tests pass
        mock_pytest_main.return_value = pytest.ExitCode.OK
        validated_path = generator.generate_and_validate()
        assert validated_path is not None
        assert validated_path == generator.module_path
        
        # Scenario 2: Tests fail
        mock_pytest_main.return_value = pytest.ExitCode.TESTS_FAILED
        validated_path = generator.generate_and_validate()
        assert validated_path is None

# -------------------------------------------------------------------- #
# Phase 2.3: Real-time Analysis and Streaming Tests
# -------------------------------------------------------------------- #

class TestRealTimeAnalysisStreaming:
    """Tests the WebSocket and background analysis functionality."""

    @patch("ai_engine.routers.websocket_router.asyncio.run")
    def test_run_analysis_and_stream_task(self, mock_asyncio_run, sample_raw_recording_data):
        """
        Tests the background task that runs the analysis and streams results.
        """
        # Arrange
        client_id = "test_client_123"
        
        # Mock the connection manager's broadcast function to capture calls
        mock_broadcast = AsyncMock()
        with patch.object(connection_manager, 'broadcast_json', mock_broadcast):
            
            # Act
            run_analysis_and_stream(client_id, sample_raw_recording_data, "Test Context")

            # Assert
            # Should be called once for each node, plus one final "complete" message
            assert mock_broadcast.call_count == 3
            
            # Check the first streamed node
            first_call = mock_broadcast.call_args_list[0].args
            assert first_call[1] == client_id # Check client_id
            assert first_call[0]['type'] == 'NEW_WORKFLOW_NODE'
            assert first_call[0]['payload']['id'] == 'action_step_1'
            
            # Check the second streamed node
            second_call = mock_broadcast.call_args_list[1].args
            assert second_call[1] == client_id
            assert second_call[0]['type'] == 'NEW_WORKFLOW_NODE'
            assert second_call[0]['payload']['id'] == 'action_step_2'

            # Check the final completion message
            final_call = mock_broadcast.call_args_list[2].args
            assert final_call[1] == client_id
            assert final_call[0]['type'] == 'ANALYSIS_COMPLETE'
            assert 'nodes' in final_call[0]['payload']
            assert len(final_call[0]['payload']['nodes']) == 2

# -------------------------------------------------------------------- #
# Phase 2 Integration Test
# -------------------------------------------------------------------- #

class TestIntelligencePipeline:
    """Tests the full pipeline from recording analysis to module generation."""

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pytest.main")
    def test_full_pipeline(self, mock_pytest_main, mock_file, mock_mkdir, sample_raw_recording_data):
        """
        Verify that raw recording data can be processed into a validated, executable module.
        """
        # Arrange
        # --- Step 1: AI Learning ---
        learning_engine = AILearningEngine(sample_raw_recording_data)
        structured_workflow = learning_engine.analyze_and_generate_workflow()
        
        # Add an ID for the generator
        structured_workflow['id'] = 'pipeline_test_workflow'
        
        # --- Step 2: Module Generation & Validation ---
        mock_pytest_main.return_value = pytest.ExitCode.OK
        generator = DynamicModuleGenerator(structured_workflow)
        
        # Act
        validated_module_path = generator.generate_and_validate()
        
        # Assert
        assert validated_module_path is not None, "The pipeline should produce a valid module path"
        
        # Check that the generated files were "written"
        assert mock_file.call_count == 2 # __init__.py, module.py, test.py
        
        # Check that pytest validation was run
        mock_pytest_main.assert_called_once()
        
        # Check that the generated code is based on the learning engine's output
        # We can do this by checking the number of steps in the generated test code
        # Get the call arguments for the write method
        # The last call to write() should be for the test file
        test_code_written = mock_file.call_args.args[0]
        assert f"assert len(results) == {len(structured_workflow['nodes'])}" in test_code_written
