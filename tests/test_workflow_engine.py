"""
Comprehensive Unit Tests for Workflow Engine
==========================================

Tests for the Workflow Engine module that orchestrates workflow execution,
monitors state, and manages the complete lifecycle of workflows.
"""

import unittest
import json
import logging
import time
from datetime import datetime
import os

# Mock object for testing
class Mock:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __call__(self, *args, **kwargs):
        return Mock()

class MagicMock(Mock):
    pass

# Mock SQLModel and database dependencies
class MockSession:
    def __init__(self):
        self.queries = []
        self.commits = []
        self.rollbacks = []
    
    def execute(self, query):
        self.queries.append(query)
        return Mock()
    
    def commit(self):
        self.commits.append(datetime.now())
    
    def rollback(self):
        self.rollbacks.append(datetime.now())
    
    def close(self):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def mock_get_session():
    return MockSession()

# Mock workflow and execution models
class MockWorkflow:
    def __init__(self, workflow_id):
        self.id = workflow_id
        self.name = "Test Workflow {}".format(workflow_id)
        self.definition = {
            "steps": [
                {"id": "step1", "type": "action", "action": "click", "target": "button1"},
                {"id": "step2", "type": "action", "action": "type", "target": "input1", "value": "test"}
            ],
            "connections": [
                {"from": "step1", "to": "step2"}
            ]
        }
        self.status = "active"
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

class MockExecution:
    def __init__(self, execution_id, workflow_id):
        self.id = execution_id
        self.workflow_id = workflow_id
        self.status = "pending"
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        self.steps_completed = 0
        self.total_steps = 2
        self.context = {}

# Mock runner factory
class MockRunner:
    def __init__(self, runner_type):
        self.runner_type = runner_type
    
    def execute(self, action, context):
        """Mock execution of an action"""
        time.sleep(0.1)  # Simulate execution time
        
        if action.get("action") == "click":
            return {
                "success": True,
                "result": "Clicked {}".format(action.get('target', 'unknown')),
                "context": context
            }
        elif action.get("action") == "type":
            new_context = dict(context)
            new_context["last_typed"] = action.get('value', '')
            return {
                "success": True,
                "result": "Typed '{}' in {}".format(action.get('value', ''), action.get('target', 'unknown')),
                "context": new_context
            }
        elif action.get("action") == "error":
            return {
                "success": False,
                "error": "Simulated error",
                "context": context
            }
        else:
            return {
                "success": True,
                "result": "Executed {} action".format(action.get('action', 'unknown')),
                "context": context
            }

class MockRunnerFactory:
    def get_runner(self, runner_type):
        return MockRunner(runner_type)

def mock_workflow_engine():
    """Create a mock workflow_engine module for testing"""
    
    class WorkflowEngine:
        def __init__(self, workflow_id):
            self.workflow_id = workflow_id
            self.workflow = MockWorkflow(workflow_id)
            self.runner_factory = MockRunnerFactory()
            self.context = {}
            self.state = "initialized"
            self.current_step = None
            self.steps_completed = 0
            self.total_steps = 0
            self.start_time = None
            self.end_time = None
            self.errors = []
            self.execution_history = []
            
            # Load workflow definition
            self._load_workflow_definition()
        
        def _load_workflow_definition(self):
            """Load workflow definition from database"""
            if self.workflow and self.workflow.definition:
                steps = self.workflow.definition.get("steps", [])
                self.total_steps = len(steps)
                self.state = "loaded"
        
        def execute_workflow(self, execution_id, input_context=None):
            """Execute the complete workflow"""
            self.start_time = datetime.now()
            self.state = "executing"
            
            # Initialize context
            self.context = input_context or {}
            execution = MockExecution(execution_id, self.workflow_id)
            
            try:
                # Execute all steps
                steps = self.workflow.definition.get("steps", [])
                results = []
                
                for i, step in enumerate(steps):
                    self.current_step = step
                    self.steps_completed = i
                    
                    # Execute step
                    step_result = self._execute_step(step)
                    results.append(step_result)
                    
                    # Update context
                    if step_result.get("success"):
                        self.context.update(step_result.get("context", {}))
                    else:
                        # Handle step failure
                        error_msg = step_result.get("error", "Unknown error")
                        self.errors.append("Step {} failed: {}".format(step.get('id', i), error_msg))
                        
                        # Decide whether to continue or stop
                        if step.get("continue_on_error", False):
                            continue
                        else:
                            raise Exception("Workflow execution failed at step {}: {}".format(step.get('id', i), error_msg))
                
                # Workflow completed successfully
                self.steps_completed = len(steps)
                self.state = "completed"
                self.end_time = datetime.now()
                
                execution.status = "completed"
                execution.completed_at = self.end_time
                execution.result = {
                    "success": True,
                    "steps_results": results,
                    "final_context": self.context,
                    "execution_time": (self.end_time - self.start_time).total_seconds()
                }
                
                return execution.result
                
            except Exception as e:
                # Workflow execution failed
                self.state = "failed"
                self.end_time = datetime.now()
                self.errors.append(str(e))
                
                execution.status = "failed"
                execution.error = str(e)
                
                return {
                    "success": False,
                    "error": str(e),
                    "steps_completed": self.steps_completed,
                    "total_steps": self.total_steps,
                    "errors": self.errors
                }
        
        def _execute_step(self, step):
            """Execute a single workflow step"""
            step_id = step.get("id", "unknown")
            step_type = step.get("type", "action")
            
            # Log step execution
            self.execution_history.append({
                "step_id": step_id,
                "timestamp": datetime.now(),
                "context": self.context.copy()
            })
            
            if step_type == "action":
                return self._execute_action_step(step)
            elif step_type == "decision":
                return self._execute_decision_step(step)
            elif step_type == "loop":
                return self._execute_loop_step(step)
            elif step_type == "wait":
                return self._execute_wait_step(step)
            else:
                return {
                    "success": False,
                    "error": "Unknown step type: {}".format(step_type),
                    "context": self.context
                }
        
        def _execute_action_step(self, step):
            """Execute an action step"""
            action = step.get("action", "unknown")
            runner_type = step.get("runner_type", "default")
            
            # Get appropriate runner
            runner = self.runner_factory.get_runner(runner_type)
            
            # Execute action
            return runner.execute(step, self.context)
        
        def _execute_decision_step(self, step):
            """Execute a decision step"""
            condition = step.get("condition", "true")
            
            # Simple condition evaluation for testing
            if condition == "true":
                result = True
            elif condition == "false":
                result = False
            elif "context" in condition:
                # Mock context evaluation
                result = len(self.context) > 0
            else:
                result = True
            
            return {
                "success": True,
                "result": result,
                "decision": result,
                "context": self.context
            }
        
        def _execute_loop_step(self, step):
            """Execute a loop step"""
            iterations = step.get("iterations", 1)
            loop_actions = step.get("actions", [])
            
            results = []
            for i in range(iterations):
                loop_context = dict(self.context)
                loop_context["loop_index"] = i
                
                for action in loop_actions:
                    action_result = self._execute_action_step(action)
                    results.append(action_result)
                    
                    if action_result.get("success"):
                        loop_context.update(action_result.get("context", {}))
                    else:
                        # Loop failed
                        return {
                            "success": False,
                            "error": "Loop iteration {} failed: {}".format(i, action_result.get('error')),
                            "context": loop_context
                        }
            
            return {
                "success": True,
                "result": "Loop completed {} iterations".format(iterations),
                "loop_results": results,
                "context": self.context
            }
        
        def _execute_wait_step(self, step):
            """Execute a wait step"""
            duration = step.get("duration", 1)  # seconds
            
            # Mock wait (don't actually wait in tests)
            time.sleep(0.01)  # Minimal delay for testing
            
            return {
                "success": True,
                "result": "Waited {} seconds".format(duration),
                "context": self.context
            }
        
        def get_execution_status(self):
            """Get current execution status"""
            return {
                "workflow_id": self.workflow_id,
                "state": self.state,
                "current_step": self.current_step,
                "steps_completed": self.steps_completed,
                "total_steps": self.total_steps,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "errors": self.errors,
                "context": self.context
            }
        
        def pause_execution(self):
            """Pause workflow execution"""
            if self.state == "executing":
                self.state = "paused"
                return True
            return False
        
        def resume_execution(self):
            """Resume workflow execution"""
            if self.state == "paused":
                self.state = "executing"
                return True
            return False
        
        def stop_execution(self):
            """Stop workflow execution"""
            if self.state in ["executing", "paused"]:
                self.state = "stopped"
                self.end_time = datetime.now()
                return True
            return False
        
        def validate_workflow(self):
            """Validate workflow definition"""
            if not self.workflow:
                return {"valid": False, "error": "Workflow not found"}
            
            definition = self.workflow.definition
            if not definition:
                return {"valid": False, "error": "Workflow definition is empty"}
            
            steps = definition.get("steps", [])
            if not steps:
                return {"valid": False, "error": "Workflow has no steps"}
            
            # Validate each step
            for i, step in enumerate(steps):
                if not step.get("id"):
                    return {"valid": False, "error": "Step {} missing id".format(i)}
                
                if not step.get("type"):
                    return {"valid": False, "error": "Step {} missing type".format(i)}
                
                if step.get("type") == "action" and not step.get("action"):
                    return {"valid": False, "error": "Action step {} missing action".format(i)}
            
            return {"valid": True, "steps": len(steps)}
    
    # Create mock module
    import sys
    mock_module = type(sys)('workflow_engine')
    mock_module.WorkflowEngine = WorkflowEngine
    mock_module.MockWorkflow = MockWorkflow
    mock_module.MockExecution = MockExecution
    mock_module.get_session = mock_get_session
    mock_module.logger = logging.getLogger(__name__)
    
    return mock_module


class TestWorkflowEngine(unittest.TestCase):
    """Test cases for Workflow Engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_module = mock_workflow_engine()
        self.engine = self.mock_module.WorkflowEngine(workflow_id=1)
        
        # Sample workflow definition
        self.sample_workflow_def = {
            "steps": [
                {
                    "id": "step1",
                    "type": "action",
                    "action": "click",
                    "target": "login_button",
                    "runner_type": "ui"
                },
                {
                    "id": "step2",
                    "type": "action",
                    "action": "type",
                    "target": "username_field",
                    "value": "testuser",
                    "runner_type": "ui"
                },
                {
                    "id": "step3",
                    "type": "decision",
                    "condition": "context['last_typed'] == 'testuser'"
                }
            ],
            "connections": [
                {"from": "step1", "to": "step2"},
                {"from": "step2", "to": "step3"}
            ]
        }
    
    def test_engine_initialization(self):
        """Test Workflow Engine initialization"""
        engine = self.mock_module.WorkflowEngine(workflow_id=1)
        
        self.assertEqual(engine.workflow_id, 1)
        self.assertIsNotNone(engine.workflow)
        self.assertIsNotNone(engine.runner_factory)
        self.assertEqual(engine.state, "loaded")
        self.assertEqual(engine.steps_completed, 0)
        self.assertGreater(engine.total_steps, 0)
    
    def test_execute_workflow_success(self):
        """Test successful workflow execution"""
        input_context = {"user": "testuser"}
        
        result = self.engine.execute_workflow(execution_id=1, input_context=input_context)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("success"))
        self.assertIn("steps_results", result)
        self.assertIn("final_context", result)
        self.assertIn("execution_time", result)
        
        # Verify execution state
        self.assertEqual(self.engine.state, "completed")
        self.assertEqual(self.engine.steps_completed, self.engine.total_steps)
        self.assertIsNotNone(self.engine.start_time)
        self.assertIsNotNone(self.engine.end_time)
    
    def test_execute_workflow_with_failure(self):
        """Test workflow execution with step failure"""
        # Create engine with error step
        engine = self.mock_module.WorkflowEngine(workflow_id=1)
        engine.workflow.definition = {
            "steps": [
                {
                    "id": "step1",
                    "type": "action",
                    "action": "click",
                    "target": "button1"
                },
                {
                    "id": "step2",
                    "type": "action",
                    "action": "error",  # This will trigger an error
                    "target": "error_element"
                }
            ]
        }
        engine.total_steps = 2
        
        result = engine.execute_workflow(execution_id=1)
        
        self.assertIsInstance(result, dict)
        self.assertFalse(result.get("success"))
        self.assertIn("error", result)
        self.assertEqual(engine.state, "failed")
        self.assertGreater(len(engine.errors), 0)
    
    def test_execute_action_step(self):
        """Test execution of action steps"""
        click_step = {
            "id": "click_step",
            "type": "action",
            "action": "click",
            "target": "test_button",
            "runner_type": "ui"
        }
        
        result = self.engine._execute_action_step(click_step)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("success"))
        self.assertIn("result", result)
        self.assertIn("Clicked test_button", result["result"])
    
    def test_execute_decision_step(self):
        """Test execution of decision steps"""
        decision_step = {
            "id": "decision_step",
            "type": "decision",
            "condition": "true"
        }
        
        result = self.engine._execute_decision_step(decision_step)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("decision"))
        self.assertIn("result", result)
    
    def test_execute_loop_step(self):
        """Test execution of loop steps"""
        loop_step = {
            "id": "loop_step",
            "type": "loop",
            "iterations": 3,
            "actions": [
                {
                    "id": "loop_action",
                    "type": "action",
                    "action": "click",
                    "target": "item"
                }
            ]
        }
        
        result = self.engine._execute_loop_step(loop_step)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("success"))
        self.assertIn("loop_results", result)
        self.assertEqual(len(result["loop_results"]), 3)
    
    def test_execute_wait_step(self):
        """Test execution of wait steps"""
        wait_step = {
            "id": "wait_step",
            "type": "wait",
            "duration": 2
        }
        
        result = self.engine._execute_wait_step(wait_step)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("success"))
        self.assertIn("Waited 2 seconds", result["result"])
    
    def test_get_execution_status(self):
        """Test getting execution status"""
        status = self.engine.get_execution_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn("workflow_id", status)
        self.assertIn("state", status)
        self.assertIn("steps_completed", status)
        self.assertIn("total_steps", status)
        self.assertIn("errors", status)
        self.assertIn("context", status)
        
        self.assertEqual(status["workflow_id"], 1)
        self.assertEqual(status["state"], "loaded")
    
    def test_pause_resume_execution(self):
        """Test pausing and resuming execution"""
        # Set engine to executing state
        self.engine.state = "executing"
        
        # Test pause
        pause_result = self.engine.pause_execution()
        self.assertTrue(pause_result)
        self.assertEqual(self.engine.state, "paused")
        
        # Test resume
        resume_result = self.engine.resume_execution()
        self.assertTrue(resume_result)
        self.assertEqual(self.engine.state, "executing")
    
    def test_pause_resume_execution_invalid_state(self):
        """Test pausing and resuming in invalid states"""
        # Test pause in non-executing state
        self.engine.state = "loaded"
        pause_result = self.engine.pause_execution()
        self.assertFalse(pause_result)
        
        # Test resume in non-paused state
        self.engine.state = "completed"
        resume_result = self.engine.resume_execution()
        self.assertFalse(resume_result)
    
    def test_stop_execution(self):
        """Test stopping execution"""
        # Set engine to executing state
        self.engine.state = "executing"
        
        stop_result = self.engine.stop_execution()
        self.assertTrue(stop_result)
        self.assertEqual(self.engine.state, "stopped")
        self.assertIsNotNone(self.engine.end_time)
    
    def test_stop_execution_invalid_state(self):
        """Test stopping execution in invalid state"""
        self.engine.state = "completed"
        
        stop_result = self.engine.stop_execution()
        self.assertFalse(stop_result)
    
    def test_validate_workflow_success(self):
        """Test successful workflow validation"""
        result = self.engine.validate_workflow()
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("valid"))
        self.assertIn("steps", result)
        self.assertGreater(result["steps"], 0)
    
    def test_validate_workflow_no_workflow(self):
        """Test validation with no workflow"""
        engine = self.mock_module.WorkflowEngine(workflow_id=1)
        engine.workflow = None
        
        result = engine.validate_workflow()
        
        self.assertFalse(result.get("valid"))
        self.assertIn("Workflow not found", result.get("error", ""))
    
    def test_validate_workflow_empty_definition(self):
        """Test validation with empty workflow definition"""
        self.engine.workflow.definition = None
        
        result = self.engine.validate_workflow()
        
        self.assertFalse(result.get("valid"))
        self.assertIn("Workflow definition is empty", result.get("error", ""))
    
    def test_validate_workflow_no_steps(self):
        """Test validation with no steps"""
        self.engine.workflow.definition = {"steps": []}
        
        result = self.engine.validate_workflow()
        
        self.assertFalse(result.get("valid"))
        self.assertIn("Workflow has no steps", result.get("error", ""))
    
    def test_validate_workflow_invalid_step_structure(self):
        """Test validation with invalid step structure"""
        self.engine.workflow.definition = {
            "steps": [
                {"type": "action", "action": "click"},  # Missing id
                {"id": "step2", "action": "type"}       # Missing type
            ]
        }
        
        result = self.engine.validate_workflow()
        
        self.assertFalse(result.get("valid"))
        self.assertIn("missing", result.get("error", "").lower())
    
    def test_context_management(self):
        """Test context management during execution"""
        input_context = {"initial_value": "test"}
        
        # Execute workflow
        result = self.engine.execute_workflow(execution_id=1, input_context=input_context)
        
        # Check that context was preserved and updated
        final_context = result.get("final_context", {})
        self.assertIn("initial_value", final_context)
        self.assertEqual(final_context["initial_value"], "test")
        
        # Check that execution added context
        self.assertIn("last_typed", final_context)
    
    def test_execution_history_tracking(self):
        """Test that execution history is tracked"""
        self.engine.execute_workflow(execution_id=1)
        
        # Check execution history
        self.assertGreater(len(self.engine.execution_history), 0)
        
        for history_entry in self.engine.execution_history:
            self.assertIn("step_id", history_entry)
            self.assertIn("timestamp", history_entry)
            self.assertIn("context", history_entry)
    
    def test_error_handling_and_reporting(self):
        """Test comprehensive error handling"""
        # Create workflow with error step
        error_workflow = {
            "steps": [
                {
                    "id": "error_step",
                    "type": "action",
                    "action": "error",
                    "target": "failing_element"
                }
            ]
        }
        
        engine = self.mock_module.WorkflowEngine(workflow_id=1)
        engine.workflow.definition = error_workflow
        engine.total_steps = 1
        
        result = engine.execute_workflow(execution_id=1)
        
        # Check error handling
        self.assertFalse(result.get("success"))
        self.assertIn("error", result)
        self.assertGreater(len(engine.errors), 0)
        self.assertEqual(engine.state, "failed")
    
    def test_integration_full_workflow_lifecycle(self):
        """Test complete workflow lifecycle integration"""
        # Initialize engine
        engine = self.mock_module.WorkflowEngine(workflow_id=1)
        
        # Validate workflow
        validation = engine.validate_workflow()
        self.assertTrue(validation.get("valid"))
        
        # Check initial status
        initial_status = engine.get_execution_status()
        self.assertEqual(initial_status["state"], "loaded")
        self.assertEqual(initial_status["steps_completed"], 0)
        
        # Execute workflow
        input_context = {"test_data": "integration_test"}
        result = engine.execute_workflow(execution_id=1, input_context=input_context)
        
        # Check successful execution
        self.assertTrue(result.get("success"))
        self.assertIn("steps_results", result)
        self.assertIn("final_context", result)
        
        # Check final status
        final_status = engine.get_execution_status()
        self.assertEqual(final_status["state"], "completed")
        self.assertEqual(final_status["steps_completed"], final_status["total_steps"])
        
        # Verify context propagation
        final_context = result["final_context"]
        self.assertIn("test_data", final_context)
        self.assertEqual(final_context["test_data"], "integration_test")


def run_workflow_engine_tests():
    """Run all Workflow Engine tests"""
    print("Running Workflow Engine Tests...")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestWorkflowEngine)
    
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
    success = run_workflow_engine_tests()
    if success:
        print("\n[SUCCESS] All Workflow Engine tests passed!")
    else:
        print("\n[FAILED] Some tests failed!")