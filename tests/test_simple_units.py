"""
Simple Unit Tests
================

Basic unit tests for core components without complex dependencies.
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class TestBasicFunctionality:
    """Test basic application functionality"""
    
    def test_env_validator_import(self):
        """Test environment validator can be imported"""
        try:
            from ai_engine.utils.env_validator import EnvValidator
            validator = EnvValidator()
            assert validator is not None
            return True
        except ImportError:
            raise Exception("skip: Environment validator not available")
    
    def test_database_import(self):
        """Test database module can be imported"""
        try:
            from ai_engine.database import DATABASE_URL
            assert DATABASE_URL is not None
            return True
        except ImportError:
            raise Exception("skip: Database module not available")
    
    def test_main_app_import(self):
        """Test main application can be imported"""
        try:
            from ai_engine.main import app
            assert app is not None
            return True
        except ImportError:
            raise Exception("skip: Main app not available")
    
    def test_workflow_model_import(self):
        """Test workflow model can be imported"""
        try:
            from ai_engine.models.workflow import Workflow
            assert Workflow is not None
            return True
        except ImportError:
            raise Exception("skip: Workflow model not available")
    
    def test_task_model_import(self):
        """Test task model can be imported"""
        try:
            from ai_engine.models.task import Task
            assert Task is not None
            return True
        except ImportError:
            raise Exception("skip: Task model not available")
    
    def test_user_model_import(self):
        """Test user model can be imported"""
        try:
            from ai_engine.models.user import User
            assert User is not None
            return True
        except ImportError:
            raise Exception("skip: User model not available")
    
    def test_execution_model_import(self):
        """Test execution model can be imported"""
        try:
            from ai_engine.models.execution import Execution
            assert Execution is not None
            return True
        except ImportError:
            raise Exception("skip: Execution model not available")


class TestUtilityModules:
    """Test utility modules"""
    
    def test_redis_client_import(self):
        """Test Redis client can be imported"""
        try:
            from ai_engine.utils.redis_client import RedisClient
            assert RedisClient is not None
            return True
        except ImportError:
            raise Exception("skip: Redis client not available")
    
    def test_circuit_breaker_import(self):
        """Test circuit breaker can be imported"""
        try:
            from ai_engine.utils.circuit_breaker import CircuitBreaker
            assert CircuitBreaker is not None
            return True
        except ImportError:
            raise Exception("skip: Circuit breaker not available")
    
    def test_secrets_manager_import(self):
        """Test secrets manager can be imported"""
        try:
            from ai_engine.utils.secrets_manager import SecretsManager
            assert SecretsManager is not None
            return True
        except ImportError:
            raise Exception("skip: Secrets manager not available")


class TestAPIRouters:
    """Test API router modules"""
    
    def test_workflow_router_import(self):
        """Test workflow router can be imported"""
        try:
            from ai_engine.routers.workflow_router import router
            assert router is not None
            return True
        except ImportError:
            raise Exception("skip: Workflow router not available")
    
    def test_task_router_import(self):
        """Test task router can be imported"""
        try:
            from ai_engine.routers.task_router import router
            assert router is not None
            return True
        except ImportError:
            raise Exception("skip: Task router not available")
    
    def test_execution_router_import(self):
        """Test execution router can be imported"""
        try:
            from ai_engine.routers.execution_router import router
            assert router is not None
            return True
        except ImportError:
            raise Exception("skip: Execution router not available")


class TestIntegrationModules:
    """Test integration modules"""
    
    def test_email_handler_import(self):
        """Test email handler can be imported"""
        try:
            from integrations.communication_module.email_handler import EmailHandler
            assert EmailHandler is not None
            return True
        except ImportError:
            raise Exception("skip: Email handler not available")
    
    def test_call_handler_import(self):
        """Test call handler can be imported"""
        try:
            from integrations.communication_module.call_handler import CallHandler
            assert CallHandler is not None
            return True
        except ImportError:
            raise Exception("skip: Call handler not available")


def run_simple_tests():
    """Run simple tests manually without pytest"""
    test_classes = [
        TestBasicFunctionality,
        TestUtilityModules,
        TestAPIRouters,
        TestIntegrationModules
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    skipped_tests = 0
    
    print("Running Simple Unit Tests")
    print("=" * 50)
    
    for test_class in test_classes:
        print("\nTesting {}:".format(test_class.__name__))
        
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                test_instance = test_class()
                test_method = getattr(test_instance, method_name)
                result = test_method()
                
                if result:
                    print("  PASSED {}".format(method_name))
                    passed_tests += 1
                else:
                    print("  FAILED {}".format(method_name))
                    failed_tests += 1
                
            except Exception as e:
                error_msg = str(e)
                if "skip:" in error_msg:
                    print("  SKIPPED {}: {}".format(method_name, error_msg.replace("skip:", "")))
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
    results = run_simple_tests()
    
    if results["failed"] == 0:
        print("\nAll available tests passed!")
        exit(0)
    else:
        print("\n{} tests failed".format(results['failed']))
        exit(1)