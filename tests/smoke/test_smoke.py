#!/usr/bin/env python3
"""
Smoke Test for AI Engine Core Functionality
===========================================

This test provides a simple, direct validation of the core AI components
without requiring a full test environment, database, or external APIs.

It validates the following key pipelines:
1.  **AI Learning Engine**: Confirms that raw recording data can be analyzed
    and transformed into a structured workflow.
2.  **Dynamic Module Generation**: Ensures the structured workflow can be used
    to generate valid Python code and test strings.
3.  **Enhanced LLM Runner**: Checks the logic of the LLM runner, including
    prompt templating, using a mocked provider.
4.  **Real-time Streaming**: Verifies that the AILearningEngine correctly
    invokes its streaming callback during analysis.

To run smoke tests: pytest -m smoke
"""

import json
import time
import logging
import pytest
from unittest.mock import patch, MagicMock, mock_open

# Set up basic logging to see output from the modules
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")

# --- Import Core Engine Components ---
try:
    from ai_engine.ai_learning_engine import AILearningEngine
    from ai_engine.dynamic_module_generator import DynamicModuleGenerator
    from ai_engine.enhanced_runners.llm_runner import LLMRunner
except ImportError as e:
    pytest.skip(f"AI Engine modules not available: {e}", allow_module_level=True)


# --- Mock Data for Testing ---

def get_sample_raw_recording():
    """Provides a realistic, raw event stream for testing."""
    base_time = time.time()
    return [
        {'timestamp': base_time, 'type': 'window_change', 'title': 'Login - Company CRM'},
        {'timestamp': base_time + 1.0, 'type': 'type', 'details': {'text': 'admin'}},
        {'timestamp': base_time + 5.0, 'type': 'window_change', 'title': 'Dashboard - Company CRM'},
        {'timestamp': base_time + 6.0, 'type': 'click', 'details': {'element_text': 'Generate Report'}},
    ]

# --- Test Functions ---

@pytest.mark.smoke
def test_learning_engine():
    """
    Tests if the AILearningEngine can process raw events into a structured workflow.
    """
    print("\n--- 🧪 1. Testing AI Learning Engine ---")
    engine = AILearningEngine(get_sample_raw_recording())
    structured_workflow = engine.analyze_and_generate_workflow()

    assert isinstance(structured_workflow, dict)
    assert "nodes" in structured_workflow and len(structured_workflow["nodes"]) > 0
    assert "edges" in structured_workflow
    assert "overall_confidence" in structured_workflow

    print("✅ SUCCESS: AI Learning Engine generated a valid structured workflow.")
    print(f"   - Nodes created: {len(structured_workflow['nodes'])}")
    print(f"   - Overall Confidence: {structured_workflow['overall_confidence']}")
    return structured_workflow

@pytest.mark.smoke
@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=mock_open)
def test_module_generator(mock_open, mock_mkdir):
    """
    Tests if the DynamicModuleGenerator can create code from a structured workflow.
    Mocks file system operations to prevent actual file creation.
    """
    print("\n--- 🧪 2. Testing Dynamic Module Generator ---")
    
    # Create a sample workflow for testing
    structured_workflow = {
        'id': 'quick_test_wf',
        'nodes': [{'id': 'step1', 'type': 'desktop', 'data': {'label': 'Test Step'}}],
        'edges': []
    }
    
    generator = DynamicModuleGenerator(structured_workflow)
    module_code, test_code = generator._generate_code()

    assert isinstance(module_code, str) and len(module_code) > 0
    assert "def run(context: dict)" in module_code
    assert "from ai_engine.enhanced_runners" in module_code

    assert isinstance(test_code, str) and len(test_code) > 0
    assert "def test_workflow_orchestration" in test_code
    assert "MockDesktopRunner.assert_any_call" in test_code

    print("✅ SUCCESS: Dynamic Module Generator created valid code and test strings.")

@pytest.mark.smoke
@patch("ai_engine.enhanced_runners.llm_runner.LLMFactory.create_provider")
def test_llm_runner(mock_create_provider):
    """
    Tests the LLMRunner's logic, especially prompt templating, using a mocked provider.
    """
    print("\n--- 🧪 3. Testing Enhanced LLM Runner ---")
    
    # Setup the mock provider to return a predictable response
    mock_provider = MagicMock()
    mock_provider.generate.return_value = {
        "text": "This is a successful mock response.",
        "metadata": {"provider": "mock"}
    }
    mock_create_provider.return_value = mock_provider

    # Define the runner's parameters
    params = {
        "provider": "openai",
        "model": "mock-model",
        "prompt_template": "Summarize this: {{ previous_step.data }}"
    }
    context = {"previous_step": {"data": "Some important text."}}

    runner = LLMRunner("test_llm_step", params)
    result = runner.execute(context)

    # Verify the prompt was rendered correctly
    mock_provider.generate.assert_called_once_with("Summarize this: Some important text.")

    # Verify the result structure
    assert result["success"] is True
    assert result["result"]["raw_text"] == "This is a successful mock response."

    print("✅ SUCCESS: LLM Runner correctly rendered prompt and processed mock response.")

@pytest.mark.smoke
def test_streaming_callback():
    """
    Tests if the AILearningEngine's real-time streaming callback is invoked.
    """
    print("\n--- 🧪 4. Testing Real-time Streaming Callback ---")
    
    streamed_nodes = []
    def simple_stream_callback(node):
        print(f"   -> Streamed node received: {node.get('id')}")
        streamed_nodes.append(node)

    engine = AILearningEngine(
        get_sample_raw_recording(),
        stream_callback=simple_stream_callback
    )
    engine.analyze_and_generate_workflow()

    assert len(streamed_nodes) > 0, "Callback was not invoked."
    assert len(streamed_nodes) == 2, f"Expected 2 nodes to be streamed, but got {len(streamed_nodes)}."
    assert "id" in streamed_nodes[0] and "data" in streamed_nodes[0]

    print(f"✅ SUCCESS: Streaming callback was invoked {len(streamed_nodes)} times as expected.")
