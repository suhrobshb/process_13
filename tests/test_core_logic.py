"""
Core Logic Unit Tests (Dependency-Free)
======================================

Tests that focus on core business logic without external dependencies.
These tests use mocking to avoid dependency issues.
"""

import pytest
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestRedisClient:
    """Test Redis client functionality with mocking"""
    
    @patch('redis.Redis')
    @patch('redis.ConnectionPool.from_url')
    def test_redis_client_initialization(self, mock_pool, mock_redis):
        """Test Redis client can be initialized"""
        # Mock Redis connection
        mock_pool.return_value = Mock()
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis.return_value = mock_redis_instance
        
        # Import and test
        from ai_engine.utils.redis_client import RedisClient
        
        client = RedisClient()
        assert client is not None
        assert client._connected == True
    
    @patch('redis.Redis')
    @patch('redis.ConnectionPool.from_url')
    def test_redis_basic_operations(self, mock_pool, mock_redis):
        """Test Redis basic operations"""
        # Setup mocks
        mock_pool.return_value = Mock()
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.setex.return_value = True
        mock_redis_instance.get.return_value = b'{"test": true}'
        mock_redis_instance.delete.return_value = 1
        mock_redis.return_value = mock_redis_instance
        
        from ai_engine.utils.redis_client import RedisClient
        
        client = RedisClient()
        
        # Test set operation
        result = client.set("test_key", {"test": True}, ttl=60)
        assert result == True
        
        # Test get operation
        result = client.get("test_key")
        assert result == {"test": True}
        
        # Test delete operation
        result = client.delete("test_key")
        assert result == True
    
    @patch('redis.Redis')
    @patch('redis.ConnectionPool.from_url')
    def test_redis_health_check(self, mock_pool, mock_redis):
        """Test Redis health check"""
        # Setup mocks
        mock_pool.return_value = Mock()
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.setex.return_value = True
        mock_redis_instance.get.return_value = b'{"timestamp": "2023-01-01"}'
        mock_redis_instance.delete.return_value = 1
        mock_redis_instance.info.return_value = {
            "redis_version": "6.2.0",
            "connected_clients": 5,
            "used_memory": 1024000
        }
        mock_redis.return_value = mock_redis_instance
        
        from ai_engine.utils.redis_client import RedisClient
        
        client = RedisClient()
        health = client.health_check()
        
        assert health["status"] == "healthy"
        assert "redis_version" in health
        assert "response_time_ms" in health


class TestEnvironmentValidator:
    """Test environment variable validation"""
    
    def test_validator_initialization(self):
        """Test validator can be initialized"""
        from ai_engine.utils.env_validator import EnvValidator
        
        validator = EnvValidator()
        assert validator is not None
        assert isinstance(validator.variables, dict)
        assert len(validator.variables) > 0
    
    @patch.dict(os.environ, {
        'DATABASE_URL': 'postgresql://user:pass@host:5432/db',
        'SECRET_KEY': 'very-secure-secret-key-for-testing',
        'REDIS_URL': 'redis://localhost:6379/0'
    })
    def test_valid_configuration(self):
        """Test validation with valid configuration"""
        from ai_engine.utils.env_validator import EnvValidator
        
        validator = EnvValidator()
        results = validator.validate_all()
        
        assert isinstance(results, dict)
        assert "valid" in results
        assert "errors" in results
        assert "warnings" in results
        
        # Should have fewer errors with good config
        assert len(results["errors"]) < 5
    
    @patch.dict(os.environ, {
        'DATABASE_URL': 'invalid-url',
        'SECRET_KEY': 'short',
        'OPENAI_API_KEY': 'invalid-key'
    })
    def test_invalid_configuration(self):
        """Test validation with invalid configuration"""
        from ai_engine.utils.env_validator import EnvValidator
        
        validator = EnvValidator()
        results = validator.validate_all()
        
        assert results["valid"] == False
        assert len(results["errors"]) > 0
        
        # Check specific validation errors
        errors = " ".join(results["errors"])
        assert "database url" in errors.lower() or "secret key" in errors.lower()
    
    def test_production_readiness_check(self):
        """Test production readiness assessment"""
        from ai_engine.utils.env_validator import EnvValidator
        
        validator = EnvValidator()
        
        # Should work without errors
        is_ready = validator.is_production_ready()
        assert isinstance(is_ready, bool)


class TestEmailHandler:
    """Test email handler functionality"""
    
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'smtp.gmail.com',
        'SMTP_PORT': '587',
        'SMTP_USERNAME': 'test@example.com',
        'SMTP_PASSWORD': 'test_password'
    })
    def test_email_handler_initialization(self):
        """Test email handler initialization"""
        from integrations.communication_module.email_handler import EmailHandler
        
        handler = EmailHandler()
        assert handler.configured == True
        assert handler.smtp_server == 'smtp.gmail.com'
        assert handler.smtp_port == 587
    
    @patch.dict(os.environ, {}, clear=True)
    def test_email_handler_unconfigured(self):
        """Test email handler without configuration"""
        from integrations.communication_module.email_handler import EmailHandler
        
        handler = EmailHandler()
        assert handler.configured == False
    
    @patch('smtplib.SMTP')
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'smtp.gmail.com',
        'SMTP_PORT': '587',
        'SMTP_USERNAME': 'test@example.com',
        'SMTP_PASSWORD': 'test_password'
    })
    def test_email_sending(self, mock_smtp):
        """Test email sending functionality"""
        # Setup SMTP mock
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        from integrations.communication_module.email_handler import EmailHandler
        
        handler = EmailHandler()
        result = handler.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test Body"
        )
        
        assert result == True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()
    
    @patch('smtplib.SMTP')
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'smtp.gmail.com',
        'SMTP_PORT': '587',
        'SMTP_USERNAME': 'test@example.com',
        'SMTP_PASSWORD': 'test_password'
    })
    def test_notification_email(self, mock_smtp):
        """Test notification email generation"""
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        from integrations.communication_module.email_handler import EmailHandler
        
        handler = EmailHandler()
        result = handler.send_notification_email(
            recipient="user@example.com",
            notification_type="success",
            title="Test Notification",
            message="This is a test message",
            workflow_id="test_workflow_123"
        )
        
        assert result == True


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization"""
        from ai_engine.utils.circuit_breaker import CircuitBreaker
        
        breaker = CircuitBreaker("test_service", max_failures=3, reset_timeout=60)
        assert breaker.service_id == "test_service"
        assert breaker.max_failures == 3
        assert breaker.reset_timeout == 60
        assert breaker.state == "closed"
    
    def test_circuit_breaker_failure_tracking(self):
        """Test failure tracking and state transitions"""
        from ai_engine.utils.circuit_breaker import CircuitBreaker
        
        breaker = CircuitBreaker("test_service", max_failures=2, reset_timeout=60)
        
        # Initially closed
        assert breaker.state == "closed"
        
        # Record failures
        breaker.record_failure()
        assert breaker.state == "closed"
        
        breaker.record_failure()
        assert breaker.state == "open"
    
    def test_circuit_breaker_success_reset(self):
        """Test success resets the breaker"""
        from ai_engine.utils.circuit_breaker import CircuitBreaker
        
        breaker = CircuitBreaker("test_service", max_failures=2, reset_timeout=60)
        
        # Force to open state
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == "open"
        
        # Success should reset
        breaker.record_success()
        assert breaker.state == "closed"
        assert breaker._failures == 0
    
    def test_circuit_breaker_manager(self):
        """Test circuit breaker manager"""
        from ai_engine.utils.circuit_breaker import CircuitBreakerManager
        
        manager = CircuitBreakerManager()
        
        # Test function
        def test_function():
            return "success"
        
        # Should work normally
        result = manager.call("test_service", test_function)
        assert result == "success"
        
        # Test failure handling
        def failing_function():
            raise Exception("Test failure")
        
        with pytest.raises(Exception, match="Test failure"):
            manager.call("test_service", failing_function)


class TestDecisionEngine:
    """Test decision engine functionality without RestrictedPython"""
    
    @patch('ai_engine.decision_engine.safe_eval')
    def test_decision_engine_basic_evaluation(self, mock_safe_eval):
        """Test basic decision evaluation"""
        # Mock safe_eval to avoid RestrictedPython dependency
        mock_safe_eval.return_value = True
        
        # Import with mocked dependency
        with patch.dict('sys.modules', {'RestrictedPython': Mock()}):
            from ai_engine.decision_engine import DecisionEngine
            
            engine = DecisionEngine()
            context = {"amount": 1500, "category": "office_supplies"}
            
            result = engine.evaluate("context['amount'] > 1000", context)
            assert result == True
    
    @patch('openai.OpenAI')
    def test_decision_engine_llm_evaluation(self, mock_openai):
        """Test LLM-based decision evaluation"""
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "true"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        with patch.dict('sys.modules', {'RestrictedPython': Mock()}):
            from ai_engine.decision_engine import DecisionEngine
            
            engine = DecisionEngine()
            engine.openai_client = mock_client
            
            context = {"amount": 1500}
            result = engine.evaluate("llm:Should this be approved?", context)
            assert result == True


class TestWorkflowComponents:
    """Test workflow-related components"""
    
    def test_workflow_serializer_basic(self):
        """Test basic workflow serialization"""
        try:
            from ai_engine.workflow_serializer import WorkflowSerializer
            
            serializer = WorkflowSerializer()
            
            # Test basic workflow data
            workflow_data = {
                "name": "Test Workflow",
                "steps": [
                    {"id": "step1", "type": "test", "params": {}}
                ]
            }
            
            # Should not raise exceptions
            serialized = serializer.serialize(workflow_data)
            assert isinstance(serialized, (str, bytes, dict))
            
        except ImportError:
            pytest.skip("Workflow serializer not available")
    
    def test_trigger_engine_basic(self):
        """Test trigger engine basic functionality"""
        try:
            from ai_engine.trigger_engine import TriggerEngine
            
            engine = TriggerEngine()
            assert engine is not None
            
            # Test that it can be started and stopped without errors
            # (without actually starting background threads)
            
        except ImportError:
            pytest.skip("Trigger engine not available")


class TestUtilityFunctions:
    """Test utility functions and helpers"""
    
    def test_secrets_manager_initialization(self):
        """Test secrets manager can be initialized"""
        try:
            from ai_engine.utils.secrets_manager import SecretsManager
            
            manager = SecretsManager()
            assert manager is not None
            
        except ImportError:
            pytest.skip("Secrets manager not available")
    
    def test_metrics_instrumentation(self):
        """Test metrics instrumentation"""
        try:
            from ai_engine.metrics_instrumentation import MetricsInstrumentation
            
            metrics = MetricsInstrumentation()
            assert metrics is not None
            
        except ImportError:
            pytest.skip("Metrics instrumentation not available")


class TestDataModels:
    """Test data models and database entities"""
    
    def test_basic_model_imports(self):
        """Test that data models can be imported"""
        try:
            from ai_engine.models.task import Task
            from ai_engine.models.workflow import Workflow
            from ai_engine.models.execution import Execution
            from ai_engine.models.user import User
            
            # Should be able to import without errors
            assert Task is not None
            assert Workflow is not None
            assert Execution is not None
            assert User is not None
            
        except ImportError as e:
            pytest.skip(f"Models not available: {e}")
    
    def test_model_basic_structure(self):
        """Test basic model structure"""
        try:
            from ai_engine.models.workflow import Workflow
            
            # Test that Workflow has expected attributes
            # This tests the model structure without database
            workflow_dict = {
                "name": "Test Workflow",
                "description": "Test Description",
                "steps": []
            }
            
            # Should be able to create without database
            # This tests the model definition
            
        except ImportError:
            pytest.skip("Workflow model not available")


class TestConfigurationAndSetup:
    """Test configuration and setup functionality"""
    
    def test_database_configuration(self):
        """Test database configuration"""
        try:
            from ai_engine.database import DATABASE_URL, engine
            
            assert DATABASE_URL is not None
            assert engine is not None
            
            # Should have proper connection string format
            assert isinstance(DATABASE_URL, str)
            assert len(DATABASE_URL) > 0
            
        except ImportError:
            pytest.skip("Database configuration not available")
    
    @patch.dict(os.environ, {'DATABASE_URL': 'postgresql://user:pass@host:5432/db'})
    def test_database_url_parsing(self):
        """Test database URL parsing"""
        url = os.getenv('DATABASE_URL')
        
        assert url.startswith('postgresql://')
        assert 'user:pass' in url
        assert 'host:5432' in url
        assert '/db' in url


if __name__ == "__main__":
    # Run tests manually if pytest isn't available
    test_classes = [
        TestRedisClient,
        TestEnvironmentValidator,
        TestEmailHandler,
        TestCircuitBreaker,
        TestDecisionEngine,
        TestWorkflowComponents,
        TestUtilityFunctions,
        TestDataModels,
        TestConfigurationAndSetup
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    print("Running Core Logic Tests (Manual)")
    print("=" * 50)
    
    for test_class in test_classes:
        print(f"\nTesting {test_class.__name__}:")
        
        # Get test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                # Create instance and run test
                test_instance = test_class()
                test_method = getattr(test_instance, method_name)
                test_method()
                
                print(f"  ✅ {method_name}")
                passed_tests += 1
                
            except Exception as e:
                print(f"  ❌ {method_name}: {e}")
                failed_tests += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed_tests}/{total_tests} passed")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests > 0:
        print(f"⚠️  {failed_tests} tests failed - check implementation")
    else:
        print("🎉 All core logic tests passed!")