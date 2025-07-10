"""
Comprehensive API Router Testing Suite
=====================================

This test suite validates all critical API endpoints across the platform:
- Authentication endpoints
- Workflow CRUD operations  
- Execution endpoints
- WebSocket connections
- Discovery and analytics endpoints
- Real-time monitoring endpoints

Tests cover:
- HTTP status codes
- Request/response validation
- Authentication/authorization
- Error handling
- Edge cases and input validation
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from ai_engine.main import app
from ai_engine.database import get_session
from ai_engine.models.user import User, Role, Tenant
from ai_engine.models.workflow import Workflow
from ai_engine.models.execution import Execution
from ai_engine.models.task import Task
from ai_engine.auth import get_password_hash, create_access_token


# Test database setup
@pytest.fixture(name="session")
def session_fixture():
    """Create test database session"""
    engine = create_engine(
        "sqlite://", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create test client with database dependency override"""
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Create test user for authentication"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(test_user: User):
    """Create authentication headers"""
    token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}


class TestAuthRouter:
    """Test authentication router endpoints"""
    
    def test_login_success(self, client: TestClient, test_user: User):
        """Test successful login"""
        response = client.post(
            "/auth/token",
            data={"username": test_user.username, "password": "testpassword"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials"""
        response = client.post(
            "/auth/token",
            data={"username": "invalid", "password": "invalid"}
        )
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_register_user(self, client: TestClient):
        """Test user registration"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword123"
        }
        
        response = client.post("/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert "hashed_password" not in data  # Password should not be returned
    
    def test_register_duplicate_user(self, client: TestClient, test_user: User):
        """Test registration with duplicate username"""
        user_data = {
            "username": test_user.username,
            "email": "duplicate@example.com",
            "password": "password123"
        }
        
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 400
    
    def test_get_current_user(self, client: TestClient, auth_headers: dict):
        """Test getting current user information"""
        response = client.get("/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert "email" in data
    
    def test_unauthorized_access(self, client: TestClient):
        """Test accessing protected endpoint without authentication"""
        response = client.get("/auth/me")
        assert response.status_code == 401


class TestWorkflowRouter:
    """Test workflow router endpoints"""
    
    def test_create_workflow(self, client: TestClient, auth_headers: dict):
        """Test workflow creation"""
        workflow_data = {
            "name": "Test Workflow",
            "description": "A test workflow",
            "steps": [
                {"action": "click", "target": "button", "parameters": {"x": 100, "y": 200}}
            ]
        }
        
        response = client.post("/workflows/", json=workflow_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == workflow_data["name"]
        assert data["description"] == workflow_data["description"]
        assert len(data["steps"]) == 1
    
    def test_create_workflow_invalid_data(self, client: TestClient, auth_headers: dict):
        """Test workflow creation with invalid data"""
        invalid_data = {
            "name": "",  # Empty name should fail validation
            "steps": []
        }
        
        response = client.post("/workflows/", json=invalid_data, headers=auth_headers)
        assert response.status_code == 422  # Validation error
    
    def test_list_workflows(self, client: TestClient, auth_headers: dict, session: Session):
        """Test listing workflows"""
        # Create test workflows
        for i in range(5):
            workflow = Workflow(
                name=f"Test Workflow {i}",
                description=f"Description {i}",
                steps=[{"action": "test"}]
            )
            session.add(workflow)
        session.commit()
        
        response = client.get("/workflows/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
    
    def test_list_workflows_pagination(self, client: TestClient, auth_headers: dict, session: Session):
        """Test workflow listing with pagination"""
        # Create test workflows
        for i in range(10):
            workflow = Workflow(
                name=f"Test Workflow {i}",
                description=f"Description {i}",
                steps=[{"action": "test"}]
            )
            session.add(workflow)
        session.commit()
        
        response = client.get("/workflows/?skip=5&limit=3", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
    
    def test_get_workflow(self, client: TestClient, auth_headers: dict, session: Session):
        """Test getting specific workflow"""
        workflow = Workflow(
            name="Test Workflow",
            description="Test Description",
            steps=[{"action": "test"}]
        )
        session.add(workflow)
        session.commit()
        session.refresh(workflow)
        
        response = client.get(f"/workflows/{workflow.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == workflow.id
        assert data["name"] == workflow.name
    
    def test_get_nonexistent_workflow(self, client: TestClient, auth_headers: dict):
        """Test getting non-existent workflow"""
        response = client.get("/workflows/99999", headers=auth_headers)
        assert response.status_code == 404
    
    @patch('ai_engine.tasks.execute_workflow')
    def test_execute_workflow(self, mock_execute, client: TestClient, auth_headers: dict, session: Session):
        """Test workflow execution"""
        workflow = Workflow(
            name="Test Workflow",
            description="Test Description",
            steps=[{"action": "test"}]
        )
        session.add(workflow)
        session.commit()
        session.refresh(workflow)
        
        mock_execute.return_value = {"status": "success", "execution_id": "test-123"}
        
        response = client.post(f"/workflows/{workflow.id}/execute", headers=auth_headers)
        
        assert response.status_code == 200
        mock_execute.assert_called_once()


class TestExecutionRouter:
    """Test execution router endpoints"""
    
    def test_list_executions(self, client: TestClient, auth_headers: dict, session: Session):
        """Test listing executions"""
        # Create test executions
        for i in range(3):
            execution = Execution(
                workflow_id=1,
                status=f"status_{i}",
                logs=f"Test logs {i}"
            )
            session.add(execution)
        session.commit()
        
        response = client.get("/executions/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
    
    def test_get_execution(self, client: TestClient, auth_headers: dict, session: Session):
        """Test getting specific execution"""
        execution = Execution(
            workflow_id=1,
            status="completed",
            logs="Test execution logs"
        )
        session.add(execution)
        session.commit()
        session.refresh(execution)
        
        response = client.get(f"/executions/{execution.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == execution.id
        assert data["status"] == execution.status
    
    def test_get_execution_logs(self, client: TestClient, auth_headers: dict, session: Session):
        """Test getting execution logs"""
        execution = Execution(
            workflow_id=1,
            status="completed",
            logs="Detailed execution logs here"
        )
        session.add(execution)
        session.commit()
        session.refresh(execution)
        
        response = client.get(f"/executions/{execution.id}/logs", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data


class TestTaskRouter:
    """Test task router endpoints"""
    
    def test_create_task(self, client: TestClient, auth_headers: dict):
        """Test task creation"""
        task_data = {
            "name": "Test Task",
            "description": "A test task",
            "workflow_id": 1,
            "action": "click",
            "parameters": {"x": 100, "y": 200}
        }
        
        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == task_data["name"]
        assert data["action"] == task_data["action"]
    
    def test_list_tasks(self, client: TestClient, auth_headers: dict, session: Session):
        """Test listing tasks"""
        # Create test tasks
        for i in range(3):
            task = Task(
                name=f"Test Task {i}",
                description=f"Description {i}",
                workflow_id=1,
                action="test",
                parameters={"test": i}
            )
            session.add(task)
        session.commit()
        
        response = client.get("/tasks/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


class TestDiscoveryRouter:
    """Test discovery router endpoints"""
    
    @patch('ai_engine.analytics.discovery.analyze_workflow_patterns')
    def test_analyze_patterns(self, mock_analyze, client: TestClient, auth_headers: dict):
        """Test workflow pattern analysis"""
        mock_analyze.return_value = {
            "patterns": ["click->type", "type->submit"],
            "confidence": 0.85
        }
        
        response = client.post("/discovery/analyze", 
                             json={"workflow_id": 1}, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "patterns" in data
        assert "confidence" in data
    
    @patch('ai_engine.analytics.recommendations.get_optimization_suggestions')
    def test_get_recommendations(self, mock_recommendations, client: TestClient, auth_headers: dict):
        """Test getting optimization recommendations"""
        mock_recommendations.return_value = {
            "suggestions": ["Add error handling", "Optimize click timing"],
            "priority": "high"
        }
        
        response = client.get("/discovery/recommendations/1", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data


class TestRealTimeRouter:
    """Test real-time monitoring router endpoints"""
    
    def test_get_system_metrics(self, client: TestClient, auth_headers: dict):
        """Test getting system metrics"""
        response = client.get("/realtime/metrics", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "cpu_usage" in data
        assert "memory_usage" in data
        assert "active_workflows" in data
    
    def test_get_workflow_status(self, client: TestClient, auth_headers: dict):
        """Test getting workflow status"""
        response = client.get("/realtime/workflows/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestRecordingRouter:
    """Test recording router endpoints"""
    
    @patch('ai_engine.recorder.multi_monitor_capture.start_recording')
    def test_start_recording(self, mock_start, client: TestClient, auth_headers: dict):
        """Test starting screen recording"""
        mock_start.return_value = {"recording_id": "rec-123", "status": "started"}
        
        response = client.post("/recording/start", 
                             json={"workflow_name": "Test Recording"}, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "recording_id" in data
        assert data["status"] == "started"
    
    @patch('ai_engine.recorder.multi_monitor_capture.stop_recording')
    def test_stop_recording(self, mock_stop, client: TestClient, auth_headers: dict):
        """Test stopping screen recording"""
        mock_stop.return_value = {"status": "stopped", "workflow_created": True}
        
        response = client.post("/recording/stop/rec-123", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"


class TestChatRouter:
    """Test chat router endpoints"""
    
    @patch('ai_engine.routers.chat_router.process_chat_message')
    def test_send_message(self, mock_process, client: TestClient, auth_headers: dict):
        """Test sending chat message"""
        mock_process.return_value = {
            "response": "I can help you create a workflow.",
            "suggestions": ["Create new workflow", "View existing workflows"]
        }
        
        message_data = {
            "message": "Help me create a workflow",
            "context": "workflow_creation"
        }
        
        response = client.post("/chat/message", json=message_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "suggestions" in data


class TestWebSocketRouter:
    """Test WebSocket router endpoints"""
    
    def test_websocket_connection(self, client: TestClient):
        """Test WebSocket connection establishment"""
        with client.websocket_connect("/ws") as websocket:
            # Send test message
            websocket.send_json({"type": "ping", "data": "test"})
            
            # Receive response
            data = websocket.receive_json()
            assert data["type"] == "pong"
    
    def test_websocket_authentication(self, client: TestClient, auth_headers: dict):
        """Test WebSocket with authentication"""
        token = auth_headers["Authorization"].split(" ")[1]
        
        with client.websocket_connect(f"/ws?token={token}") as websocket:
            websocket.send_json({"type": "status", "data": "authenticated"})
            data = websocket.receive_json()
            assert "status" in data


class TestErrorHandling:
    """Test error handling across all routers"""
    
    def test_internal_server_error_handling(self, client: TestClient, auth_headers: dict):
        """Test 500 error handling"""
        with patch('ai_engine.routers.workflow_router.get_session') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")
            
            response = client.get("/workflows/", headers=auth_headers)
            assert response.status_code == 500
    
    def test_validation_error_handling(self, client: TestClient, auth_headers: dict):
        """Test 422 validation error handling"""
        invalid_data = {
            "name": None,  # Invalid name
            "steps": "invalid_steps"  # Invalid steps format
        }
        
        response = client.post("/workflows/", json=invalid_data, headers=auth_headers)
        assert response.status_code == 422
        
        error_data = response.json()
        assert "detail" in error_data
    
    def test_rate_limiting(self, client: TestClient, auth_headers: dict):
        """Test rate limiting (if implemented)"""
        # Make multiple rapid requests
        responses = []
        for _ in range(100):
            response = client.get("/workflows/", headers=auth_headers)
            responses.append(response.status_code)
        
        # Should have at least some successful responses
        assert 200 in responses
        
        # Note: Add actual rate limiting check if implemented
        # assert 429 in responses  # Too Many Requests


class TestInputValidation:
    """Test input validation and sanitization"""
    
    def test_sql_injection_prevention(self, client: TestClient, auth_headers: dict):
        """Test SQL injection attempt prevention"""
        malicious_input = "'; DROP TABLE workflows; --"
        
        response = client.get(f"/workflows/{malicious_input}", headers=auth_headers)
        
        # Should return 422 (validation error) or 404, not 500
        assert response.status_code in [404, 422]
    
    def test_xss_prevention(self, client: TestClient, auth_headers: dict):
        """Test XSS prevention in workflow creation"""
        xss_payload = "<script>alert('xss')</script>"
        
        workflow_data = {
            "name": xss_payload,
            "description": xss_payload,
            "steps": [{"action": "click", "target": xss_payload}]
        }
        
        response = client.post("/workflows/", json=workflow_data, headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            # Ensure script tags are escaped or removed
            assert "<script>" not in data["name"]
            assert "<script>" not in data["description"]
    
    def test_large_payload_handling(self, client: TestClient, auth_headers: dict):
        """Test handling of large payloads"""
        large_payload = {
            "name": "A" * 10000,  # Very long name
            "description": "B" * 50000,  # Very long description
            "steps": [{"action": "click", "target": "button"}] * 1000  # Many steps
        }
        
        response = client.post("/workflows/", json=large_payload, headers=auth_headers)
        
        # Should handle gracefully - either accept or reject with proper error
        assert response.status_code in [200, 413, 422]  # OK, Payload Too Large, or Validation Error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])