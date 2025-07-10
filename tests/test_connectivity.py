"""
Connectivity Integration Tests
=============================

Tests to verify all backend services are properly connected and integrated.
"""

import pytest
import asyncio
import json
import time
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

# Import the main application and components
from ai_engine.main import app
from ai_engine.database import health_check as db_health_check
from ai_engine.utils.env_validator import validate_environment


class TestDatabaseConnectivity:
    """Test database connectivity and integration"""
    
    def test_database_health_check(self):
        """Test database health check function"""
        result = db_health_check()
        
        # Should return a valid health status
        assert isinstance(result, dict)
        assert "status" in result
        
        # Status should be either healthy or unhealthy
        assert result["status"] in ["healthy", "unhealthy"]
        
        if result["status"] == "unhealthy":
            assert "error" in result
            pytest.skip(f"Database not available: {result['error']}")
    
    def test_database_session_handling(self):
        """Test database session management"""
        from ai_engine.database import get_session, engine
        from sqlmodel import Session, text
        
        # Test session creation and cleanup
        session_generator = get_session()
        session = next(session_generator)
        
        assert isinstance(session, Session)
        
        # Test simple query
        try:
            result = session.execute(text("SELECT 1 as test"))
            assert result.fetchone().test == 1
        except Exception as e:
            pytest.skip(f"Database query failed: {e}")
        finally:
            # Ensure session is closed
            try:
                next(session_generator)
            except StopIteration:
                pass  # Expected when generator closes


class TestRedisConnectivity:
    """Test Redis connectivity and integration"""
    
    def test_redis_client_availability(self):
        """Test Redis client can be imported and initialized"""
        try:
            from ai_engine.utils.redis_client import get_redis_client, is_redis_available
            
            # Test client initialization
            client = get_redis_client()
            assert client is not None
            
            # Test availability check
            available = is_redis_available()
            assert isinstance(available, bool)
            
            if not available:
                pytest.skip("Redis not available for testing")
            
        except ImportError as e:
            pytest.skip(f"Redis client not available: {e}")
    
    def test_redis_health_check(self):
        """Test Redis health check"""
        try:
            from ai_engine.utils.redis_client import get_redis_client, is_redis_available
            
            if not is_redis_available():
                pytest.skip("Redis not available")
            
            client = get_redis_client()
            health = client.health_check()
            
            assert isinstance(health, dict)
            assert "status" in health
            
            if health["status"] == "healthy":
                assert "response_time_ms" in health
                assert "redis_version" in health
            else:
                assert "error" in health
                
        except ImportError:
            pytest.skip("Redis client not available")
    
    def test_redis_basic_operations(self):
        """Test basic Redis operations"""
        try:
            from ai_engine.utils.redis_client import get_redis_client, is_redis_available
            
            if not is_redis_available():
                pytest.skip("Redis not available")
            
            client = get_redis_client()
            
            # Test set/get operations
            test_key = "test_connectivity"
            test_value = {"timestamp": time.time(), "test": True}
            
            # Set value
            result = client.set(test_key, test_value, ttl=60, prefix="test")
            assert result is True
            
            # Get value
            retrieved = client.get(test_key, prefix="test")
            assert retrieved is not None
            assert retrieved["test"] is True
            
            # Delete value
            deleted = client.delete(test_key, prefix="test")
            assert deleted is True
            
            # Verify deletion
            missing = client.get(test_key, prefix="test")
            assert missing is None
            
        except ImportError:
            pytest.skip("Redis client not available")


class TestAPIConnectivity:
    """Test API endpoints and routing"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health endpoint connectivity"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
        
        # Check service statuses
        services = data["services"]
        assert "database" in services
        
        # Redis might not be available in all environments
        if "redis" in services:
            assert "status" in services["redis"]
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
    
    def test_cors_configuration(self, client):
        """Test CORS headers are properly configured"""
        response = client.options("/health")
        
        # Should not return 405 Method Not Allowed for OPTIONS
        assert response.status_code in [200, 204]
    
    def test_api_router_registration(self, client):
        """Test that API routers are properly registered"""
        
        # Test a few key endpoints to ensure routers are connected
        endpoints_to_test = [
            "/api/workflows",
            "/api/tasks", 
            "/api/executions"
        ]
        
        for endpoint in endpoints_to_test:
            response = client.get(endpoint)
            
            # Should not return 404 Not Found (router not registered)
            # May return 401/403 (auth required) or 200 (success)
            assert response.status_code != 404, f"Router for {endpoint} not registered"


class TestEnvironmentConfiguration:
    """Test environment variable configuration"""
    
    def test_environment_validation(self):
        """Test environment variable validation"""
        results = validate_environment()
        
        assert isinstance(results, dict)
        assert "valid" in results
        assert "errors" in results
        assert "warnings" in results
        
        # Should have basic structure even if invalid
        assert isinstance(results["errors"], list)
        assert isinstance(results["warnings"], list)
    
    def test_required_variables_present(self):
        """Test that critical environment variables are present"""
        import os
        
        # Check for critical variables
        critical_vars = ["DATABASE_URL", "SECRET_KEY"]
        
        missing_vars = []
        for var in critical_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            pytest.skip(f"Missing critical environment variables: {missing_vars}")
    
    def test_database_url_format(self):
        """Test database URL is properly formatted"""
        import os
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            pytest.skip("DATABASE_URL not configured")
        
        # Should be postgresql or sqlite
        assert db_url.startswith("postgresql://") or db_url.startswith("sqlite://")


class TestEmailIntegration:
    """Test email integration (optional)"""
    
    def test_email_handler_initialization(self):
        """Test email handler can be initialized"""
        try:
            from integrations.communication_module.email_handler import get_email_handler, is_email_configured
            
            handler = get_email_handler()
            assert handler is not None
            
            # Check configuration status
            configured = is_email_configured()
            assert isinstance(configured, bool)
            
            if not configured:
                pytest.skip("Email not configured")
            
        except ImportError as e:
            pytest.skip(f"Email handler not available: {e}")
    
    def test_email_health_check(self):
        """Test email service health check"""
        try:
            from integrations.communication_module.email_handler import get_email_handler, is_email_configured
            
            if not is_email_configured():
                pytest.skip("Email not configured")
            
            handler = get_email_handler()
            health = handler.health_check()
            
            assert isinstance(health, dict)
            assert "status" in health
            
            if health["status"] not in ["healthy", "not_configured"]:
                # May be unhealthy due to network/credentials - that's OK for testing
                assert health["status"] == "unhealthy"
                assert "error" in health
                
        except ImportError:
            pytest.skip("Email handler not available")


class TestWebSocketConnectivity:
    """Test WebSocket connectivity"""
    
    def test_websocket_router_registration(self):
        """Test WebSocket router is registered"""
        from ai_engine.main import app
        
        # Check that WebSocket routes are registered
        websocket_routes = [route for route in app.routes if hasattr(route, 'path') and 'ws' in route.path]
        
        # Should have at least one WebSocket route
        assert len(websocket_routes) > 0, "No WebSocket routes found"
    
    def test_websocket_endpoint_exists(self):
        """Test WebSocket endpoint responds"""
        client = TestClient(app)
        
        # Test WebSocket connection (basic check)
        try:
            with client.websocket_connect("/ws/recording/test") as websocket:
                # If we can connect, the endpoint exists
                assert True
        except Exception as e:
            # May fail due to authentication or other reasons, but should not be 404
            error_msg = str(e)
            assert "404" not in error_msg, f"WebSocket endpoint not found: {error_msg}"


class TestExternalServiceIntegration:
    """Test external service integrations"""
    
    def test_openai_integration_available(self):
        """Test OpenAI integration is available"""
        try:
            from ai_engine.enhanced_runners.llm_runner import LLMFactory
            
            # Test that we can create an OpenAI provider
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                try:
                    provider = LLMFactory.create_provider("openai", "gpt-3.5-turbo")
                    assert provider is not None
                except Exception as e:
                    # May fail due to network/auth, but should not be import error
                    assert "No module named" not in str(e)
                    
        except ImportError as e:
            pytest.skip(f"LLM integration not available: {e}")
    
    def test_circuit_breaker_integration(self):
        """Test circuit breaker is properly integrated"""
        try:
            from ai_engine.utils.circuit_breaker import circuit_breaker_manager
            
            # Test that circuit breaker manager is available
            assert circuit_breaker_manager is not None
            
            # Test basic functionality
            test_service = "test_connectivity_service"
            
            def test_function():
                return "success"
            
            # Should be able to call through circuit breaker
            result = circuit_breaker_manager.call(test_service, test_function)
            assert result == "success"
            
        except ImportError as e:
            pytest.skip(f"Circuit breaker not available: {e}")


# Integration test for complete system connectivity
class TestSystemIntegration:
    """End-to-end system integration tests"""
    
    def test_complete_health_check(self):
        """Test complete system health via API"""
        client = TestClient(app)
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify all expected services are reporting
        services = data.get("services", {})
        
        # Database should always be present
        assert "database" in services
        db_status = services["database"]["status"]
        assert db_status in ["healthy", "unhealthy"]
        
        # Overall status should be calculated correctly
        overall_status = data["status"]
        assert overall_status in ["healthy", "degraded", "unhealthy"]
    
    def test_application_startup_sequence(self):
        """Test that application starts up correctly"""
        # This test verifies that all imports and initializations work
        # by simply importing the main application
        try:
            from ai_engine.main import app
            assert app is not None
            
            # Verify routes are registered
            assert len(app.routes) > 0
            
            # Verify middleware is configured
            assert len(app.middleware_stack) > 0
            
        except Exception as e:
            pytest.fail(f"Application startup failed: {e}")


if __name__ == "__main__":
    # Run connectivity tests
    pytest.main([__file__, "-v"])