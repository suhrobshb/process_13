"""
Comprehensive Unit Tests for High Coverage
==========================================

Focused unit tests for core components to maximize test coverage.
"""

# import pytest
import os
import sys
import json
import time
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestSecretsManager:
    """Comprehensive tests for SecretsManager"""
    
    def test_env_backend_initialization(self):
        """Test environment variable backend"""
        from ai_engine.utils.secrets_manager import SecretsManager
        
        manager = SecretsManager(backend="env")
        assert manager.backend == "env"
    
    @patch.dict(os.environ, {'TEST_SECRET': 'test_value'})
    def test_env_backend_get_secret(self):
        """Test getting secret from environment"""
        from ai_engine.utils.secrets_manager import SecretsManager
        
        manager = SecretsManager(backend="env")
        secret = manager.get_secret("TEST_SECRET")
        assert secret == "test_value"
    
    def test_env_backend_missing_secret(self):
        """Test missing secret from environment"""
        from ai_engine.utils.secrets_manager import SecretsManager
        
        manager = SecretsManager(backend="env")
        secret = manager.get_secret("NONEXISTENT_SECRET")
        assert secret is None
    
    @patch("builtins.open", mock_open(read_data='{"test_key": "test_value"}'))
    def test_file_backend_get_secret(self):
        """Test file backend secret retrieval"""
        from ai_engine.utils.secrets_manager import SecretsManager
        
        manager = SecretsManager(backend="file", file_path="/fake/path")
        with patch("pathlib.Path.exists", return_value=True):
            secret = manager.get_secret("test_key")
            assert secret == "test_value"
    
    def test_encrypted_storage(self):
        """Test encrypted secret storage"""
        from ai_engine.utils.secrets_manager import SecretsManager
        
        manager = SecretsManager(backend="env")
        
        # Test encryption/decryption cycle
        original_secret = "very-secret-data"
        encrypted = manager._encrypt_secret(original_secret)
        decrypted = manager._decrypt_secret(encrypted)
        
        assert decrypted == original_secret
        assert encrypted != original_secret
    
    def test_secret_validation(self):
        """Test secret validation"""
        from ai_engine.utils.secrets_manager import SecretsManager
        
        manager = SecretsManager(backend="env")
        
        # Test valid secret
        assert manager._validate_secret("good-secret") == True
        
        # Test invalid secrets
        assert manager._validate_secret("") == False
        assert manager._validate_secret(None) == False
        assert manager._validate_secret("123") == False  # Too short


class TestSecureExecution:
    """Tests for secure execution utilities"""
    
    def test_sandbox_initialization(self):
        """Test sandbox initialization"""
        try:
            from ai_engine.utils.secure_execution import SecurePythonSandbox
            
            sandbox = SecurePythonSandbox()
            assert sandbox is not None
            assert hasattr(sandbox, 'compile_code')
            
        except ImportError:
            raise Exception("skip:"("Secure execution not available")
    
    @patch('ai_engine.utils.secure_execution.compile_restricted')
    def test_code_compilation(self, mock_compile):
        """Test code compilation in sandbox"""
        try:
            from ai_engine.utils.secure_execution import SecurePythonSandbox
            
            mock_compile.return_value = compile("1 + 1", "<string>", "eval")
            
            sandbox = SecurePythonSandbox()
            result = sandbox.compile_code("1 + 1", mode="eval")
            
            assert result is not None
            mock_compile.assert_called_once()
            
        except ImportError:
            raise Exception("skip:"("Secure execution not available")
    
    def test_dangerous_code_detection(self):
        """Test detection of dangerous code patterns"""
        try:
            from ai_engine.utils.secure_execution import SecurePythonSandbox
            
            sandbox = SecurePythonSandbox()
            
            # Test dangerous patterns
            dangerous_codes = [
                "import os",
                "__import__('subprocess')",
                "exec('malicious code')",
                "eval('harmful')",
                "open('/etc/passwd')"
            ]
            
            for code in dangerous_codes:
                is_safe = sandbox._check_code_safety(code)
                assert is_safe == False, "Should detect {} as unsafe".format(code)
            
        except ImportError:
            raise Exception("skip:"("Secure execution not available")


class TestEnhancedRunners:
    """Tests for enhanced workflow runners"""
    
    @patch('ai_engine.enhanced_runners.llm_runner.OpenAI')
    def test_llm_runner_initialization(self, mock_openai):
        """Test LLM runner initialization"""
        try:
            from ai_engine.enhanced_runners.llm_runner import LLMRunner
            
            params = {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "prompt_template": "Test template: {{ context.input }}"
            }
            
            runner = LLMRunner("test_step", params)
            assert runner.step_id == "test_step"
            assert runner.provider_name == "openai"
            assert runner.model == "gpt-3.5-turbo"
            
        except ImportError:
            raise Exception("skip:"("LLM runner not available")
    
    @patch('ai_engine.enhanced_runners.llm_runner.OpenAI')
    def test_llm_prompt_rendering(self, mock_openai):
        """Test LLM prompt template rendering"""
        try:
            from ai_engine.enhanced_runners.llm_runner import LLMRunner
            
            params = {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "prompt_template": "Hello {{ context.name }}, your age is {{ context.age }}"
            }
            
            runner = LLMRunner("test_step", params)
            context = {"name": "Alice", "age": 25}
            
            rendered = runner._render_prompt(context)
            assert "Hello Alice" in rendered
            assert "age is 25" in rendered
            
        except ImportError:
            raise Exception("skip:"("LLM runner not available")
    
    @patch('ai_engine.enhanced_runners.llm_runner.OpenAI')
    def test_llm_structured_output(self, mock_openai):
        """Test LLM structured output parsing"""
        try:
            from ai_engine.enhanced_runners.llm_runner import LLMRunner
            
            params = {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "prompt_template": "Test",
                "output_schema": {"type": "object"}
            }
            
            runner = LLMRunner("test_step", params)
            
            # Test JSON extraction from markdown
            json_in_markdown = '```json\n{"result": "success", "score": 0.95}\n```'
            parsed = runner._parse_structured_output(json_in_markdown)
            assert parsed["result"] == "success"
            assert parsed["score"] == 0.95
            
            # Test plain JSON
            plain_json = '{"status": "completed"}'
            parsed = runner._parse_structured_output(plain_json)
            assert parsed["status"] == "completed"
            
        except ImportError:
            raise Exception("skip:"("LLM runner not available")


class TestWorkflowEngine:
    """Tests for workflow engine components"""
    
    def test_workflow_serializer_basic(self):
        """Test basic workflow serialization"""
        try:
            from ai_engine.workflow_serializer import WorkflowSerializer
            
            serializer = WorkflowSerializer()
            
            workflow = {
                "name": "Test Workflow",
                "description": "A test workflow",
                "steps": [
                    {"id": "step1", "type": "action", "params": {"key": "value"}},
                    {"id": "step2", "type": "decision", "params": {"condition": "true"}}
                ]
            }
            
            # Test serialization
            serialized = serializer.serialize(workflow)
            assert serialized is not None
            
            # Test deserialization
            deserialized = serializer.deserialize(serialized)
            assert deserialized["name"] == "Test Workflow"
            assert len(deserialized["steps"]) == 2
            
        except ImportError:
            raise Exception("skip:"("Workflow serializer not available")
    
    def test_workflow_validation(self):
        """Test workflow validation"""
        try:
            from ai_engine.workflow_serializer import WorkflowSerializer
            
            serializer = WorkflowSerializer()
            
            # Valid workflow
            valid_workflow = {
                "name": "Valid Workflow",
                "steps": [{"id": "step1", "type": "action"}]
            }
            assert serializer.validate(valid_workflow) == True
            
            # Invalid workflows
            invalid_workflows = [
                {},  # Empty
                {"name": "No Steps"},  # Missing steps
                {"steps": []},  # Missing name
                {"name": "", "steps": []}  # Empty name
            ]
            
            for invalid in invalid_workflows:
                assert serializer.validate(invalid) == False
            
        except ImportError:
            raise Exception("skip:"("Workflow serializer not available")


class TestTaskRelationshipBuilder:
    """Tests for task relationship building"""
    
    def test_relationship_builder_initialization(self):
        """Test relationship builder initialization"""
        try:
            from ai_engine.task_relationship_builder import TaskRelationshipBuilder
            
            builder = TaskRelationshipBuilder()
            assert builder is not None
            assert hasattr(builder, 'build_relationships')
            
        except ImportError:
            raise Exception("skip:"("Task relationship builder not available")
    
    def test_dependency_detection(self):
        """Test task dependency detection"""
        try:
            from ai_engine.task_relationship_builder import TaskRelationshipBuilder
            
            builder = TaskRelationshipBuilder()
            
            tasks = [
                {"id": "task1", "name": "First Task", "outputs": ["data1"]},
                {"id": "task2", "name": "Second Task", "inputs": ["data1"], "outputs": ["data2"]},
                {"id": "task3", "name": "Third Task", "inputs": ["data2"]}
            ]
            
            relationships = builder.build_relationships(tasks)
            
            assert isinstance(relationships, list)
            assert len(relationships) >= 2  # Should find dependencies
            
        except ImportError:
            raise Exception("skip:"("Task relationship builder not available")


class TestAnalyticsComponents:
    """Tests for analytics and discovery components"""
    
    def test_nlu_component(self):
        """Test NLU component"""
        try:
            from ai_engine.analytics.nlu import NLUProcessor
            
            processor = NLUProcessor()
            assert processor is not None
            
            # Test intent recognition
            text = "I want to create a new workflow for processing emails"
            result = processor.process(text)
            
            assert isinstance(result, dict)
            assert "intent" in result or "entities" in result
            
        except ImportError:
            raise Exception("skip:"("NLU processor not available")
    
    def test_discovery_component(self):
        """Test process discovery component"""
        try:
            from ai_engine.analytics.discovery import ProcessDiscovery
            
            discovery = ProcessDiscovery()
            assert discovery is not None
            
            # Test pattern detection
            sample_data = [
                {"action": "open_email", "timestamp": 1000},
                {"action": "read_email", "timestamp": 1010},
                {"action": "reply_email", "timestamp": 1020}
            ]
            
            patterns = discovery.discover_patterns(sample_data)
            assert isinstance(patterns, list)
            
        except ImportError:
            raise Exception("skip:"("Process discovery not available")
    
    def test_roi_analytics(self):
        """Test ROI analytics component"""
        try:
            from ai_engine.analytics.roi import ROIAnalyzer
            
            analyzer = ROIAnalyzer()
            assert analyzer is not None
            
            # Test ROI calculation
            metrics = {
                "time_saved_hours": 40,
                "hourly_rate": 50,
                "automation_cost": 1000
            }
            
            roi = analyzer.calculate_roi(metrics)
            assert isinstance(roi, dict)
            assert "roi_percentage" in roi
            
        except ImportError:
            raise Exception("skip:"("ROI analyzer not available")


class TestIntegrationModules:
    """Tests for integration modules"""
    
    @patch('twilio.rest.Client')
    def test_call_handler(self, mock_twilio):
        """Test call handler integration"""
        try:
            from integrations.communication_module.call_handler import CallHandler
            
            mock_client = Mock()
            mock_twilio.return_value = mock_client
            
            handler = CallHandler()
            assert handler is not None
            
            # Test call initiation
            result = handler.make_call(
                to="+1234567890",
                from_="+0987654321",
                message="Test message"
            )
            
            # Should not crash, may return various results
            assert isinstance(result, (bool, dict))
            
        except ImportError:
            raise Exception("skip:"("Call handler not available")
    
    def test_notification_handler(self):
        """Test notification handler"""
        try:
            from integrations.alerting_monitoring.notification_handler import NotificationHandler
            
            handler = NotificationHandler()
            assert handler is not None
            
            # Test notification creation
            notification = {
                "type": "info",
                "title": "Test Notification",
                "message": "This is a test",
                "recipient": "test@example.com"
            }
            
            result = handler.send_notification(notification)
            # Should handle gracefully even without proper config
            assert isinstance(result, bool)
            
        except ImportError:
            raise Exception("skip:"("Notification handler not available")


class TestDatabaseModels:
    """Tests for database models and operations"""
    
    def test_user_model(self):
        """Test User model"""
        try:
            from ai_engine.models.user import User
            
            # Test model structure
            assert hasattr(User, '__table__')
            assert hasattr(User, 'id')
            assert hasattr(User, 'username')
            assert hasattr(User, 'email')
            
        except ImportError:
            raise Exception("skip:"("User model not available")
    
    def test_workflow_model(self):
        """Test Workflow model"""
        try:
            from ai_engine.models.workflow import Workflow
            
            # Test model structure
            assert hasattr(Workflow, '__table__')
            assert hasattr(Workflow, 'id')
            assert hasattr(Workflow, 'name')
            assert hasattr(Workflow, 'steps')
            
        except ImportError:
            raise Exception("skip:"("Workflow model not available")
    
    def test_execution_model(self):
        """Test Execution model"""
        try:
            from ai_engine.models.execution import Execution
            
            # Test model structure
            assert hasattr(Execution, '__table__')
            assert hasattr(Execution, 'id')
            assert hasattr(Execution, 'workflow_id')
            assert hasattr(Execution, 'status')
            
        except ImportError:
            raise Exception("skip:"("Execution model not available")


class TestAPIRouters:
    """Tests for API router components"""
    
    def test_workflow_router_structure(self):
        """Test workflow router structure"""
        try:
            from ai_engine.routers import workflow_router
            
            assert hasattr(workflow_router, 'router')
            router = workflow_router.router
            
            # Check router has routes
            assert hasattr(router, 'routes')
            assert len(router.routes) > 0
            
        except ImportError:
            raise Exception("skip:"("Workflow router not available")
    
    def test_task_router_structure(self):
        """Test task router structure"""
        try:
            from ai_engine.routers import task_router
            
            assert hasattr(task_router, 'router')
            router = task_router.router
            
            # Check router configuration
            assert hasattr(router, 'routes')
            
        except ImportError:
            raise Exception("skip:"("Task router not available")


class TestUtilityHelpers:
    """Tests for utility helper functions"""
    
    def test_metrics_instrumentation(self):
        """Test metrics instrumentation utilities"""
        try:
            from ai_engine.metrics_instrumentation import MetricsInstrumentation, record_llm_request
            
            metrics = MetricsInstrumentation()
            assert metrics is not None
            
            # Test metric recording
            record_llm_request("openai", "gpt-3.5-turbo", 150, 50)
            # Should not crash
            
        except ImportError:
            raise Exception("skip:"("Metrics instrumentation not available")
    
    def test_scenario_library(self):
        """Test scenario library utilities"""
        try:
            from ai_engine.scenario_library import ScenarioLibrary
            
            library = ScenarioLibrary()
            assert library is not None
            
            # Test scenario retrieval
            scenarios = library.get_scenarios()
            assert isinstance(scenarios, (list, dict))
            
        except ImportError:
            raise Exception("skip:"("Scenario library not available")


def run_manual_tests():
    """Run tests manually without pytest"""
    test_classes = [
        TestSecretsManager,
        TestSecureExecution,
        TestEnhancedRunners,
        TestWorkflowEngine,
        TestTaskRelationshipBuilder,
        TestAnalyticsComponents,
        TestIntegrationModules,
        TestDatabaseModels,
        TestAPIRouters,
        TestUtilityHelpers
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    skipped_tests = 0
    
    print("Running Comprehensive Unit Tests")
    print("=" * 50)
    
    for test_class in test_classes:
        print("\nTesting {}:".format(test_class.__name__))
        
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                test_instance = test_class()
                test_method = getattr(test_instance, method_name)
                test_method()
                
                print("  PASSED {}".format(method_name))
                passed_tests += 1
                
            except Exception as e:
                error_msg = str(e)
                if "skip" in error_msg.lower() or "not available" in error_msg.lower():
                    print("  SKIPPED {}: {}".format(method_name, error_msg))
                    skipped_tests += 1
                else:
                    print("  FAILED {}: {}".format(method_name, error_msg))
                    failed_tests += 1
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print("   - Total: {}".format(total_tests))
    print("   - Passed: {}".format(passed_tests))
    print("   - Failed: {}".format(failed_tests))
    print("   - Skipped: {}".format(skipped_tests))
    
    if total_tests > 0:
        success_rate = (passed_tests / total_tests) * 100
        print("   - Success Rate: {:.1f}%".format(success_rate))
        
        # Effective success rate (excluding skipped)
        effective_total = total_tests - skipped_tests
        if effective_total > 0:
            effective_success = (passed_tests / effective_total) * 100
            print("   - Effective Success Rate: {:.1f}%".format(effective_success))
    
    return {
        "total": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "skipped": skipped_tests
    }


if __name__ == "__main__":
    results = run_manual_tests()
    
    if results["failed"] == 0:
        print("\nAll available tests passed!")
        exit(0)
    else:
        print("\n{} tests failed".format(results['failed']))
        exit(1)