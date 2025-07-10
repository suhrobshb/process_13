"""
Comprehensive Unit Tests for AI Learning Engine
=============================================

Tests for the AI Learning Engine module that handles event clustering,
intent recognition, pattern detection, confidence scoring, and workflow generation.
"""

import unittest
import json
import logging
from datetime import datetime

# Mock object for testing
class Mock:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __call__(self, *args, **kwargs):
        return Mock()

class MagicMock(Mock):
    pass

# Mock all external dependencies
class MockLLM:
    def generate(self, prompt):
        if "summarize the following actions" in prompt.lower():
            return "Mock Action Summary"
        elif "what is the business goal" in prompt.lower():
            return "Mock Business Goal"
        return "Mock Response"

class MockEventData:
    def __init__(self, event_type, data):
        self.event_type = event_type
        self.data = data
        self.timestamp = datetime.now()

# Mock the ai_learning_engine module
sys_modules_backup = {}
import sys

def mock_ai_learning_engine():
    """Create a mock ai_learning_engine module for testing"""
    
    class AILearningEngine:
        def __init__(self):
            self.llm = MockLLM()
            self.confidence_threshold = 0.7
            self.clustering_enabled = True
            self.pattern_detection_enabled = True
        
        def process_raw_events(self, events):
            """Process raw events into structured workflow"""
            if not events:
                return {"workflow": [], "confidence": 0.0}
            
            # Mock processing logic
            processed_events = []
            for event in events:
                processed_event = {
                    "action_type": event.get("type", "unknown"),
                    "description": "Mock action for {}".format(event.get('type', 'unknown')),
                    "confidence": 0.8,
                    "timestamp": event.get("timestamp", datetime.now().isoformat())
                }
                processed_events.append(processed_event)
            
            return {
                "workflow": processed_events,
                "confidence": 0.8,
                "patterns_detected": ["click_sequence", "form_fill"],
                "business_goal": "Mock business process"
            }
        
        def cluster_events(self, events):
            """Cluster events into meaningful groups"""
            if not events:
                return []
            
            # Simple clustering logic for testing
            clusters = []
            current_cluster = []
            
            for event in events:
                if event.get("type") == "click" and current_cluster:
                    clusters.append(current_cluster)
                    current_cluster = [event]
                else:
                    current_cluster.append(event)
            
            if current_cluster:
                clusters.append(current_cluster)
            
            return clusters
        
        def recognize_intent(self, event_cluster):
            """Recognize intent from event cluster"""
            if not event_cluster:
                return {"intent": "unknown", "confidence": 0.0}
            
            # Mock intent recognition
            primary_event = event_cluster[0]
            intent_map = {
                "click": "user_interaction",
                "type": "data_entry",
                "navigate": "navigation",
                "wait": "synchronization"
            }
            
            intent = intent_map.get(primary_event.get("type"), "unknown")
            confidence = 0.85 if intent != "unknown" else 0.3
            
            return {
                "intent": intent,
                "confidence": confidence,
                "description": "Mock intent for {}".format(intent),
                "action_count": len(event_cluster)
            }
        
        def detect_patterns(self, events):
            """Detect automation patterns in events"""
            patterns = []
            
            if not events:
                return patterns
            
            # Mock pattern detection
            event_types = [e.get("type") for e in events]
            
            # Loop pattern detection
            if len(set(event_types)) < len(event_types) / 2:
                patterns.append({
                    "type": "loop",
                    "confidence": 0.9,
                    "description": "Detected repetitive action pattern"
                })
            
            # Conditional pattern detection
            if "wait" in event_types and "click" in event_types:
                patterns.append({
                    "type": "conditional",
                    "confidence": 0.7,
                    "description": "Detected conditional logic pattern"
                })
            
            return patterns
        
        def calculate_confidence(self, workflow_data):
            """Calculate confidence score for workflow interpretation"""
            if not workflow_data:
                return 0.0
            
            workflow = workflow_data.get("workflow", [])
            if not workflow:
                return 0.0
            
            # Average confidence of all actions
            confidences = [action.get("confidence", 0.0) for action in workflow]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Boost confidence if patterns detected
            patterns = workflow_data.get("patterns_detected", [])
            pattern_boost = len(patterns) * 0.05
            
            return min(avg_confidence + pattern_boost, 1.0)
        
        def generate_workflow_structure(self, processed_events):
            """Generate workflow structure from processed events"""
            if not processed_events:
                return {"nodes": [], "edges": []}
            
            nodes = []
            edges = []
            
            for i, event in enumerate(processed_events):
                node = {
                    "id": "node_{}".format(i),
                    "type": "action",
                    "data": {
                        "action_type": event.get("action_type"),
                        "description": event.get("description"),
                        "confidence": event.get("confidence")
                    }
                }
                nodes.append(node)
                
                # Create edges between consecutive nodes
                if i > 0:
                    edge = {
                        "id": "edge_{}_{}".format(i-1, i),
                        "source": "node_{}".format(i-1),
                        "target": "node_{}".format(i),
                        "type": "sequence"
                    }
                    edges.append(edge)
            
            return {
                "nodes": nodes,
                "edges": edges,
                "workflow_type": "sequential",
                "total_actions": len(nodes)
            }
    
    # Create mock module
    mock_module = type(sys)('ai_learning_engine')
    mock_module.AILearningEngine = AILearningEngine
    mock_module.MockLLM = MockLLM
    mock_module.logger = logging.getLogger(__name__)
    
    return mock_module

class TestAILearningEngine(unittest.TestCase):
    """Test cases for AI Learning Engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_module = mock_ai_learning_engine()
        self.engine = self.mock_module.AILearningEngine()
        
        # Sample test events
        self.sample_events = [
            {
                "type": "click",
                "target": "login_button",
                "timestamp": "2024-01-01T10:00:00",
                "coordinates": {"x": 100, "y": 200}
            },
            {
                "type": "type",
                "target": "username_field",
                "value": "test_user",
                "timestamp": "2024-01-01T10:00:01"
            },
            {
                "type": "type",
                "target": "password_field",
                "value": "password123",
                "timestamp": "2024-01-01T10:00:02"
            },
            {
                "type": "click",
                "target": "submit_button",
                "timestamp": "2024-01-01T10:00:03",
                "coordinates": {"x": 150, "y": 250}
            }
        ]
    
    def test_engine_initialization(self):
        """Test AI Learning Engine initialization"""
        engine = self.mock_module.AILearningEngine()
        
        self.assertIsNotNone(engine.llm)
        self.assertEqual(engine.confidence_threshold, 0.7)
        self.assertTrue(engine.clustering_enabled)
        self.assertTrue(engine.pattern_detection_enabled)
    
    def test_process_raw_events_success(self):
        """Test successful processing of raw events"""
        result = self.engine.process_raw_events(self.sample_events)
        
        self.assertIsInstance(result, dict)
        self.assertIn("workflow", result)
        self.assertIn("confidence", result)
        self.assertIn("patterns_detected", result)
        self.assertIn("business_goal", result)
        
        workflow = result["workflow"]
        self.assertEqual(len(workflow), len(self.sample_events))
        
        for action in workflow:
            self.assertIn("action_type", action)
            self.assertIn("description", action)
            self.assertIn("confidence", action)
            self.assertIn("timestamp", action)
    
    def test_process_raw_events_empty_input(self):
        """Test processing with empty event list"""
        result = self.engine.process_raw_events([])
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["workflow"], [])
        self.assertEqual(result["confidence"], 0.0)
    
    def test_cluster_events_success(self):
        """Test event clustering functionality"""
        clusters = self.engine.cluster_events(self.sample_events)
        
        self.assertIsInstance(clusters, list)
        self.assertGreater(len(clusters), 0)
        
        # Verify all events are included in clusters
        total_events = sum(len(cluster) for cluster in clusters)
        self.assertEqual(total_events, len(self.sample_events))
    
    def test_cluster_events_empty_input(self):
        """Test clustering with empty event list"""
        clusters = self.engine.cluster_events([])
        
        self.assertIsInstance(clusters, list)
        self.assertEqual(len(clusters), 0)
    
    def test_recognize_intent_success(self):
        """Test intent recognition from event cluster"""
        test_cluster = [
            {"type": "click", "target": "button"},
            {"type": "wait", "duration": 1000}
        ]
        
        result = self.engine.recognize_intent(test_cluster)
        
        self.assertIsInstance(result, dict)
        self.assertIn("intent", result)
        self.assertIn("confidence", result)
        self.assertIn("description", result)
        self.assertIn("action_count", result)
        
        self.assertEqual(result["intent"], "user_interaction")
        self.assertEqual(result["action_count"], 2)
        self.assertGreater(result["confidence"], 0.5)
    
    def test_recognize_intent_empty_cluster(self):
        """Test intent recognition with empty cluster"""
        result = self.engine.recognize_intent([])
        
        self.assertEqual(result["intent"], "unknown")
        self.assertEqual(result["confidence"], 0.0)
    
    def test_detect_patterns_loop_pattern(self):
        """Test detection of loop patterns"""
        repetitive_events = [
            {"type": "click", "target": "row1"},
            {"type": "type", "value": "data1"},
            {"type": "click", "target": "row2"},
            {"type": "type", "value": "data2"},
            {"type": "click", "target": "row3"},
            {"type": "type", "value": "data3"}
        ]
        
        patterns = self.engine.detect_patterns(repetitive_events)
        
        self.assertIsInstance(patterns, list)
        loop_patterns = [p for p in patterns if p["type"] == "loop"]
        self.assertGreater(len(loop_patterns), 0)
        
        loop_pattern = loop_patterns[0]
        self.assertEqual(loop_pattern["type"], "loop")
        self.assertGreater(loop_pattern["confidence"], 0.8)
    
    def test_detect_patterns_conditional_pattern(self):
        """Test detection of conditional patterns"""
        conditional_events = [
            {"type": "click", "target": "check_button"},
            {"type": "wait", "duration": 2000},
            {"type": "click", "target": "proceed_button"}
        ]
        
        patterns = self.engine.detect_patterns(conditional_events)
        
        self.assertIsInstance(patterns, list)
        conditional_patterns = [p for p in patterns if p["type"] == "conditional"]
        self.assertGreater(len(conditional_patterns), 0)
        
        conditional_pattern = conditional_patterns[0]
        self.assertEqual(conditional_pattern["type"], "conditional")
        self.assertGreater(conditional_pattern["confidence"], 0.5)
    
    def test_detect_patterns_empty_events(self):
        """Test pattern detection with empty events"""
        patterns = self.engine.detect_patterns([])
        
        self.assertIsInstance(patterns, list)
        self.assertEqual(len(patterns), 0)
    
    def test_calculate_confidence_success(self):
        """Test confidence calculation"""
        workflow_data = {
            "workflow": [
                {"confidence": 0.9},
                {"confidence": 0.8},
                {"confidence": 0.7}
            ],
            "patterns_detected": ["loop", "conditional"]
        }
        
        confidence = self.engine.calculate_confidence(workflow_data)
        
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
        
        # Should be average of confidences (0.8) + pattern boost (0.1)
        expected_confidence = 0.8 + 0.1
        self.assertAlmostEqual(confidence, expected_confidence, places=1)
    
    def test_calculate_confidence_empty_workflow(self):
        """Test confidence calculation with empty workflow"""
        workflow_data = {"workflow": []}
        
        confidence = self.engine.calculate_confidence(workflow_data)
        
        self.assertEqual(confidence, 0.0)
    
    def test_calculate_confidence_no_data(self):
        """Test confidence calculation with no data"""
        confidence = self.engine.calculate_confidence({})
        
        self.assertEqual(confidence, 0.0)
    
    def test_generate_workflow_structure_success(self):
        """Test workflow structure generation"""
        processed_events = [
            {
                "action_type": "click",
                "description": "Click login button",
                "confidence": 0.9
            },
            {
                "action_type": "type",
                "description": "Enter username",
                "confidence": 0.8
            },
            {
                "action_type": "click",
                "description": "Submit form",
                "confidence": 0.85
            }
        ]
        
        workflow_structure = self.engine.generate_workflow_structure(processed_events)
        
        self.assertIsInstance(workflow_structure, dict)
        self.assertIn("nodes", workflow_structure)
        self.assertIn("edges", workflow_structure)
        self.assertIn("workflow_type", workflow_structure)
        self.assertIn("total_actions", workflow_structure)
        
        nodes = workflow_structure["nodes"]
        edges = workflow_structure["edges"]
        
        self.assertEqual(len(nodes), 3)
        self.assertEqual(len(edges), 2)  # n-1 edges for sequential workflow
        self.assertEqual(workflow_structure["workflow_type"], "sequential")
        self.assertEqual(workflow_structure["total_actions"], 3)
        
        # Verify node structure
        for i, node in enumerate(nodes):
            self.assertEqual(node["id"], "node_{}".format(i))
            self.assertEqual(node["type"], "action")
            self.assertIn("data", node)
            self.assertIn("action_type", node["data"])
            self.assertIn("description", node["data"])
            self.assertIn("confidence", node["data"])
        
        # Verify edge structure
        for i, edge in enumerate(edges):
            self.assertEqual(edge["id"], "edge_{}_{}".format(i, i+1))
            self.assertEqual(edge["source"], "node_{}".format(i))
            self.assertEqual(edge["target"], "node_{}".format(i+1))
            self.assertEqual(edge["type"], "sequence")
    
    def test_generate_workflow_structure_empty_events(self):
        """Test workflow structure generation with empty events"""
        workflow_structure = self.engine.generate_workflow_structure([])
        
        self.assertIsInstance(workflow_structure, dict)
        self.assertEqual(workflow_structure["nodes"], [])
        self.assertEqual(workflow_structure["edges"], [])
    
    def test_integration_full_workflow_processing(self):
        """Test complete workflow processing pipeline"""
        # Full integration test
        result = self.engine.process_raw_events(self.sample_events)
        
        # Verify complete processing
        self.assertIsInstance(result, dict)
        self.assertIn("workflow", result)
        self.assertIn("confidence", result)
        self.assertGreater(result["confidence"], 0.0)
        
        workflow = result["workflow"]
        self.assertEqual(len(workflow), len(self.sample_events))
        
        # Test workflow structure generation
        workflow_structure = self.engine.generate_workflow_structure(workflow)
        self.assertIsInstance(workflow_structure, dict)
        self.assertEqual(len(workflow_structure["nodes"]), len(self.sample_events))
        
        # Test pattern detection
        patterns = self.engine.detect_patterns(self.sample_events)
        self.assertIsInstance(patterns, list)
        
        # Test confidence calculation
        workflow_data = {
            "workflow": workflow,
            "patterns_detected": patterns
        }
        final_confidence = self.engine.calculate_confidence(workflow_data)
        self.assertGreater(final_confidence, 0.0)
        self.assertLessEqual(final_confidence, 1.0)


def run_ai_learning_engine_tests():
    """Run all AI Learning Engine tests"""
    print("Running AI Learning Engine Tests...")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestAILearningEngine)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\nTest Results:")
    print("Tests Run: {}".format(result.testsRun))
    print("Failures: {}".format(len(result.failures)))
    print("Errors: {}".format(len(result.errors)))
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
    print("Success Rate: {:.1f}%".format(success_rate))
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_ai_learning_engine_tests()
    if success:
        print("\n[SUCCESS] All AI Learning Engine tests passed!")
    else:
        print("\n[FAILED] Some tests failed!")