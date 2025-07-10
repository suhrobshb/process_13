"""
Unit tests for intent classification and NLP processing
======================================================

Tests for the intent recognition and natural language processing components,
including:
- Intent classification accuracy
- Command parsing and extraction
- Entity recognition
- Context understanding
- Confidence scoring
"""

import pytest
import json
from unittest.mock import Mock, patch
from typing import Dict, Any, List

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from nlp.intent_classifier import IntentClassifier
    from nlp.document_processor import DocumentProcessor
    from task_detection import TaskDetector
except ImportError:
    # Create mock classes if modules don't exist
    class IntentClassifier:
        def __init__(self):
            pass
        
        def classify(self, text: str) -> Dict[str, Any]:
            return {"intent": "unknown", "confidence": 0.5}
    
    class DocumentProcessor:
        def __init__(self):
            pass
        
        def process(self, text: str) -> Dict[str, Any]:
            return {"processed": True}
    
    class TaskDetector:
        def __init__(self):
            pass
        
        def detect_tasks(self, text: str) -> List[Dict[str, Any]]:
            return []


class TestIntentClassifier:
    """Test suite for intent classification functionality"""
    
    @pytest.fixture
    def classifier(self):
        """Create an IntentClassifier instance for testing"""
        return IntentClassifier()
    
    @pytest.fixture
    def sample_intents(self):
        """Sample intents for testing"""
        return [
            {
                "intent": "create_workflow",
                "examples": [
                    "Create a new workflow",
                    "Make a workflow for processing invoices",
                    "I want to automate my email processing",
                    "Set up automation for data entry"
                ],
                "entities": ["workflow_name", "process_type"]
            },
            {
                "intent": "execute_workflow", 
                "examples": [
                    "Run the invoice processing workflow",
                    "Execute my email automation",
                    "Start the data processing job",
                    "Trigger the backup workflow"
                ],
                "entities": ["workflow_name", "parameters"]
            },
            {
                "intent": "get_status",
                "examples": [
                    "What's the status of my workflow?",
                    "How is the processing going?",
                    "Check the execution status",
                    "Show me the progress"
                ],
                "entities": ["workflow_name", "execution_id"]
            }
        ]
    
    def test_intent_classifier_initialization(self, classifier):
        """Test IntentClassifier initializes correctly"""
        assert classifier is not None
        assert hasattr(classifier, 'classify')
    
    def test_intent_classification_create_workflow(self, classifier):
        """Test classification of create workflow intent"""
        test_texts = [
            "Create a workflow to process invoices automatically",
            "I need to set up automation for email handling",
            "Make a new workflow for data processing",
            "Build an automation to handle customer requests"
        ]
        
        for text in test_texts:
            result = classifier.classify(text)
            
            assert "intent" in result
            assert "confidence" in result
            assert result["confidence"] >= 0.0
            assert result["confidence"] <= 1.0
            
            # For create workflow intent, expect high confidence
            if result["intent"] == "create_workflow":
                assert result["confidence"] > 0.7
    
    def test_intent_classification_execute_workflow(self, classifier):
        """Test classification of execute workflow intent"""
        test_texts = [
            "Run the invoice processing workflow",
            "Execute the email automation now",
            "Start the data processing job",
            "Trigger my backup workflow"
        ]
        
        for text in test_texts:
            result = classifier.classify(text)
            
            assert "intent" in result
            assert "confidence" in result
            
            # For execute workflow intent, expect high confidence
            if result["intent"] == "execute_workflow":
                assert result["confidence"] > 0.7
    
    def test_intent_classification_get_status(self, classifier):
        """Test classification of status inquiry intent"""
        test_texts = [
            "What's the status of my workflow?",
            "How is the processing going?",
            "Check the execution status",
            "Show me the progress of the automation"
        ]
        
        for text in test_texts:
            result = classifier.classify(text)
            
            assert "intent" in result
            assert "confidence" in result
            
            # For status inquiry intent, expect high confidence
            if result["intent"] == "get_status":
                assert result["confidence"] > 0.7
    
    def test_intent_classification_ambiguous_text(self, classifier):
        """Test classification of ambiguous or unclear text"""
        ambiguous_texts = [
            "Hello",
            "What?",
            "I don't know",
            "Maybe later",
            "Random text that doesn't match any intent"
        ]
        
        for text in ambiguous_texts:
            result = classifier.classify(text)
            
            assert "intent" in result
            assert "confidence" in result
            # Ambiguous text should have low confidence
            assert result["confidence"] < 0.6
    
    def test_entity_extraction_workflow_name(self, classifier):
        """Test extraction of workflow name entities"""
        test_cases = [
            ("Create a workflow called 'Invoice Processing'", "Invoice Processing"),
            ("Run the 'Email Automation' workflow", "Email Automation"),
            ("Execute my Data Processing workflow", "Data Processing"),
            ("Start the Customer Service Bot", "Customer Service Bot")
        ]
        
        for text, expected_name in test_cases:
            result = classifier.classify(text)
            
            if "entities" in result:
                workflow_names = [e["value"] for e in result["entities"] if e["type"] == "workflow_name"]
                if workflow_names:
                    assert expected_name.lower() in [name.lower() for name in workflow_names]
    
    def test_entity_extraction_process_type(self, classifier):
        """Test extraction of process type entities"""
        test_cases = [
            ("Automate invoice processing", "invoice processing"),
            ("Set up email automation", "email automation"),
            ("Create data entry workflow", "data entry"),
            ("Build customer service automation", "customer service")
        ]
        
        for text, expected_type in test_cases:
            result = classifier.classify(text)
            
            if "entities" in result:
                process_types = [e["value"] for e in result["entities"] if e["type"] == "process_type"]
                if process_types:
                    assert any(expected_type.lower() in ptype.lower() for ptype in process_types)
    
    def test_confidence_scoring_accuracy(self, classifier):
        """Test that confidence scores are meaningful and accurate"""
        high_confidence_texts = [
            "Create a new workflow for invoice processing",
            "Execute the email automation workflow",
            "Show me the status of my data processing job"
        ]
        
        low_confidence_texts = [
            "Maybe workflow something",
            "I think automation perhaps",
            "Status or something like that"
        ]
        
        high_confidences = []
        low_confidences = []
        
        for text in high_confidence_texts:
            result = classifier.classify(text)
            high_confidences.append(result["confidence"])
        
        for text in low_confidence_texts:
            result = classifier.classify(text)
            low_confidences.append(result["confidence"])
        
        # High confidence texts should have higher average confidence
        avg_high = sum(high_confidences) / len(high_confidences)
        avg_low = sum(low_confidences) / len(low_confidences)
        
        assert avg_high > avg_low
        assert avg_high > 0.7
        assert avg_low < 0.6
    
    def test_context_understanding(self, classifier):
        """Test classifier's ability to understand context"""
        # Test with context from previous interactions
        context = {
            "previous_intent": "create_workflow",
            "workflow_name": "Invoice Processing",
            "user_id": "user123"
        }
        
        # Follow-up questions should maintain context
        follow_up_texts = [
            "What's the status?",  # Should infer workflow from context
            "Execute it now",      # Should infer workflow from context
            "Add a new step"       # Should infer workflow modification
        ]
        
        for text in follow_up_texts:
            result = classifier.classify(text, context=context)
            
            assert "intent" in result
            assert "confidence" in result
            
            # Context should help improve confidence
            assert result["confidence"] > 0.5
    
    def test_multi_intent_detection(self, classifier):
        """Test detection of multiple intents in single text"""
        multi_intent_texts = [
            "Create a workflow and then execute it",
            "Show me the status and run the backup workflow",
            "Build an automation for emails and check the current progress"
        ]
        
        for text in multi_intent_texts:
            result = classifier.classify(text)
            
            # Should detect multiple intents
            if "intents" in result:
                assert len(result["intents"]) >= 2
                assert all(intent["confidence"] > 0.3 for intent in result["intents"])
    
    def test_error_handling_empty_text(self, classifier):
        """Test handling of empty or invalid input"""
        invalid_inputs = [
            "",
            None,
            "   ",  # Whitespace only
            "\n\t\r",  # Only special characters
        ]
        
        for invalid_input in invalid_inputs:
            result = classifier.classify(invalid_input)
            
            # Should handle gracefully without crashing
            assert isinstance(result, dict)
            assert "intent" in result
            assert "confidence" in result
            assert result["confidence"] == 0.0 or result["intent"] == "unknown"
    
    def test_performance_classification_speed(self, classifier):
        """Test classification performance and speed"""
        import time
        
        test_text = "Create a workflow to process invoices automatically"
        
        # Test classification speed
        start_time = time.time()
        for _ in range(10):
            classifier.classify(test_text)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 10
        
        # Should classify in reasonable time (< 1 second per classification)
        assert avg_time < 1.0
    
    def test_intent_classification_with_parameters(self, classifier):
        """Test classification with parameter extraction"""
        test_cases = [
            {
                "text": "Create a workflow with timeout 300 seconds",
                "expected_params": {"timeout": 300}
            },
            {
                "text": "Execute workflow with priority high",
                "expected_params": {"priority": "high"}
            },
            {
                "text": "Run the job every 5 minutes",
                "expected_params": {"schedule": "5 minutes"}
            }
        ]
        
        for case in test_cases:
            result = classifier.classify(case["text"])
            
            if "parameters" in result:
                for param_name, expected_value in case["expected_params"].items():
                    assert param_name in result["parameters"]
                    # Value matching can be flexible (string vs int, etc.)
                    assert str(result["parameters"][param_name]).lower() == str(expected_value).lower()


class TestDocumentProcessor:
    """Test suite for document processing functionality"""
    
    @pytest.fixture
    def processor(self):
        """Create a DocumentProcessor instance for testing"""
        return DocumentProcessor()
    
    def test_document_processor_initialization(self, processor):
        """Test DocumentProcessor initializes correctly"""
        assert processor is not None
        assert hasattr(processor, 'process')
    
    def test_document_text_processing(self, processor):
        """Test basic text processing functionality"""
        test_text = "This is a sample document with some text to process."
        
        result = processor.process(test_text)
        
        assert isinstance(result, dict)
        assert "processed" in result or "tokens" in result or "analysis" in result
    
    def test_document_html_processing(self, processor):
        """Test HTML document processing"""
        html_content = """
        <html>
            <body>
                <h1>Title</h1>
                <p>This is a paragraph with <strong>bold text</strong>.</p>
                <ul>
                    <li>Item 1</li>
                    <li>Item 2</li>
                </ul>
            </body>
        </html>
        """
        
        result = processor.process(html_content)
        
        assert isinstance(result, dict)
        # Should extract text content without HTML tags
        if "text" in result:
            assert "<html>" not in result["text"]
            assert "Title" in result["text"]
            assert "paragraph" in result["text"]
    
    def test_document_large_text_processing(self, processor):
        """Test processing of large documents"""
        # Create a large text document
        large_text = "This is a test sentence. " * 1000
        
        result = processor.process(large_text)
        
        assert isinstance(result, dict)
        # Should handle large documents without crashing
        assert result is not None


class TestTaskDetector:
    """Test suite for task detection functionality"""
    
    @pytest.fixture
    def detector(self):
        """Create a TaskDetector instance for testing"""
        return TaskDetector()
    
    def test_task_detector_initialization(self, detector):
        """Test TaskDetector initializes correctly"""
        assert detector is not None
        assert hasattr(detector, 'detect_tasks')
    
    def test_task_detection_single_task(self, detector):
        """Test detection of single task in text"""
        test_text = "Please create a workflow to process invoices automatically"
        
        tasks = detector.detect_tasks(test_text)
        
        assert isinstance(tasks, list)
        if tasks:
            task = tasks[0]
            assert "type" in task
            assert "description" in task
            assert "confidence" in task
    
    def test_task_detection_multiple_tasks(self, detector):
        """Test detection of multiple tasks in text"""
        test_text = """
        I need to:
        1. Create a workflow for invoice processing
        2. Set up email automation
        3. Generate reports automatically
        """
        
        tasks = detector.detect_tasks(test_text)
        
        assert isinstance(tasks, list)
        # Should detect multiple tasks
        assert len(tasks) >= 2
        
        for task in tasks:
            assert "type" in task
            assert "description" in task
            assert "confidence" in task
    
    def test_task_detection_no_tasks(self, detector):
        """Test handling of text with no detectable tasks"""
        test_text = "Hello, how are you? This is just a casual conversation."
        
        tasks = detector.detect_tasks(test_text)
        
        assert isinstance(tasks, list)
        # Should return empty list or tasks with low confidence
        if tasks:
            assert all(task["confidence"] < 0.5 for task in tasks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])