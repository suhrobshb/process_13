"""
End-to-End Authentication Tests
------------------------------

This module provides comprehensive end-to-end tests for the authentication system:
1. User registration and login flow
2. JWT token validation and authorization
3. Role-based access control
4. Tenant isolation
5. API endpoint security

These tests use FastAPI's TestClient and SQLite in-memory database for isolation.
"""

import os
import pytest
import jwt
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, status
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, StaticPool, select
from typing import Dict, Generator, List, Optional

# Import the modules to test
from ai_engine.main import app
from ai_engine.auth import (
    get_current_active_user, get_password_hash, 
    create_access_token, verify_password, SECRET_KEY, ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from ai_engine.models.user import User, Role, Tenant, UserRole
from ai_engine.database import get_session
from ai_engine.routers.auth_router import UserCreate, TenantCreate, RoleCreate

# Create a test database
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create a test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

# Override the get_session dependency
def get_test_session():
    with Session(engine) as session:
        yield session

# Override the app's dependency
app.dependency_overrides[get_session] = get_test_session

# Create a test client
client = TestClient(app)

# Test data
TEST_TENANTS = [
    {"name": "tenant1", "display_name": "Tenant 1", "description": "Test Tenant 1"},
    {"name": "tenant2", "display_name": "Tenant 2", "description": "Test Tenant 2"},
]

TEST_ROLES = [
    {"name": "admin", "description": "Administrator", "permissions": ["all:all"]},
    {"name": "editor", "description": "Editor", "permissions": ["workflows:edit", "tasks:edit"]},
    {"name": "viewer", "description": "Viewer", "permissions": ["workflows:view", "tasks:view"]},
]

TEST_USERS = [
    {"username": "admin_user", "email": "admin@example.com", "password": "adminpass", "tenant": "tenant1", "roles": ["admin"]},
    {"username": "editor_user", "email": "editor@example.com", "password": "editorpass", "tenant": "tenant1", "roles": ["editor"]},
    {"username": "viewer_user", "email": "viewer@example.com", "password": "viewerpass", "tenant": "tenant1", "roles": ["viewer"]},
    {"username": "tenant2_user", "email": "user@tenant2.com", "password": "userpass", "tenant": "tenant2", "roles": ["editor"]},
]

# Fixtures
@pytest.fixture(scope="function")
def setup_database():
    """Create tables and populate with test data."""
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Create test tenants
        tenant_map = {}
        for tenant_data in TEST_TENANTS:
            tenant = Tenant(**tenant_data)
            session.add(tenant)
            session.commit()
            session.refresh(tenant)
            tenant_map[tenant.name] = tenant
        
        # Create test roles
        role_map = {}
        for role_data in TEST_ROLES:
            role = Role(**role_data)
            session.add(role)
            session.commit()
            session.refresh(role)
            role_map[role.name] = role
        
        # Create test users
        for user_data in TEST_USERS:
            # Get tenant
            tenant = tenant_map[user_data["tenant"]]
            
            # Create user
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                tenant_id=tenant.id,
            )
            
            # Assign roles
            for role_name in user_data["roles"]:
                role = role_map[role_name]
                user.roles.append(role)
            
            session.add(user)
            session.commit()
    
    yield
    
    # Clean up
    SQLModel.metadata.drop_all(engine)

@pytest.fixture
def admin_token(setup_database):
    """Get a token for the admin user."""
    response = client.post(
        "/api/token",
        data={"username": "admin_user", "password": "adminpass"},
    )
    return response.json()["access_token"]

@pytest.fixture
def editor_token(setup_database):
    """Get a token for the editor user."""
    response = client.post(
        "/api/token",
        data={"username": "editor_user", "password": "editorpass"},
    )
    return response.json()["access_token"]

@pytest.fixture
def viewer_token(setup_database):
    """Get a token for the viewer user."""
    response = client.post(
        "/api/token",
        data={"username": "viewer_user", "password": "viewerpass"},
    )
    return response.json()["access_token"]

@pytest.fixture
def tenant2_token(setup_database):
    """Get a token for the tenant2 user."""
    response = client.post(
        "/api/token",
        data={"username": "tenant2_user", "password": "userpass"},
    )
    return response.json()["access_token"]

# Test user registration and login flow
def test_user_registration(setup_database):
    """Test user registration with valid data."""
    # First get tenant ID
    with Session(engine) as session:
        # SQLModel uses `session.exec(select(...))` instead of the old
        # SQLAlchemy 1.x `session.query()` style.
        tenant = session.exec(
            select(Tenant).where(Tenant.name == "tenant1")
        ).first()
    
    # Register a new user
    response = client.post(
        "/api/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword",
            "full_name": "New User",
            "tenant_id": tenant.id
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert "roles" in data
    assert "viewer" in data["roles"]  # Should get default viewer role

def test_user_registration_duplicate_username(setup_database):
    """Test user registration with duplicate username."""
    # First get tenant ID
    with Session(engine) as session:
        tenant = session.exec(
            select(Tenant).where(Tenant.name == "tenant1")
        ).first()
    
    # Try to register with existing username
    response = client.post(
        "/api/register",
        json={
            "username": "admin_user",  # Already exists
            "email": "different@example.com",
            "password": "newpassword",
            "tenant_id": tenant.id
        },
    )
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]

def test_user_login_valid(setup_database):
    """Test user login with valid credentials."""
    response = client.post(
        "/api/token",
        data={"username": "admin_user", "password": "adminpass"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Verify token
    token = data["access_token"]
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "admin_user"
    assert "admin" in payload["scopes"]

def test_user_login_invalid(setup_database):
    """Test user login with invalid credentials."""
    response = client.post(
        "/api/token",
        data={"username": "admin_user", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

# Test JWT token validation and authorization
def test_access_protected_route_with_token(admin_token):
    """Test accessing a protected route with a valid token."""
    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin_user"

def test_access_protected_route_without_token():
    """Test accessing a protected route without a token."""
    response = client.get("/api/users/me")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

def test_access_protected_route_with_invalid_token():
    """Test accessing a protected route with an invalid token."""
    response = client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]

def test_token_expiration():
    """Test token expiration."""
    # Create a token that expires immediately
    access_token = create_access_token(
        data={"sub": "admin_user", "scopes": ["admin"]},
        expires_delta=timedelta(seconds=1)
    )
    
    # Wait for token to expire
    import time
    time.sleep(2)
    
    # Try to use expired token
    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]

# Test role-based access control
def test_admin_access_all_users(admin_token):
    """Test that admin can access the list of all users."""
    response = client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 4  # At least our test users

def test_editor_cannot_access_all_users(editor_token):
    """Test that editor cannot access the list of all users."""
    response = client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions. Required role:" in response.json()["detail"]

def test_admin_create_tenant(admin_token):
    """Test that admin can create a new tenant."""
    response = client.post(
        "/api/tenants",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "new_tenant",
            "display_name": "New Tenant",
            "description": "A new test tenant"
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "new_tenant"

def test_editor_cannot_create_tenant(editor_token):
    """Test that editor cannot create a new tenant."""
    response = client.post(
        "/api/tenants",
        headers={"Authorization": f"Bearer {editor_token}"},
        json={
            "name": "another_tenant",
            "display_name": "Another Tenant",
            "description": "Another test tenant"
        },
    )
    assert response.status_code == 403
    assert "Not enough permissions. Required role:" in response.json()["detail"]

# Test tenant isolation
def test_tenant_isolation_workflows(editor_token, tenant2_token, setup_database):
    """Test that users can only see workflows from their own tenant."""
    # First, create a workflow as tenant1 editor
    workflow_response = client.post(
        "/api/workflows/",
        headers={"Authorization": f"Bearer {editor_token}"},
        json={
            "name": "Tenant1 Workflow",
            "description": "A workflow for tenant 1",
            "status": "draft",
            "created_by": "editor_user",  # This will be overridden by the API
            "steps": []
        },
    )
    assert workflow_response.status_code == 200
    workflow_id = workflow_response.json()["id"]
    
    # Create a workflow as tenant2 user
    workflow_response2 = client.post(
        "/api/workflows/",
        headers={"Authorization": f"Bearer {tenant2_token}"},
        json={
            "name": "Tenant2 Workflow",
            "description": "A workflow for tenant 2",
            "status": "draft",
            "created_by": "tenant2_user",  # This will be overridden by the API
            "steps": []
        },
    )
    assert workflow_response2.status_code == 200
    workflow_id2 = workflow_response2.json()["id"]
    
    # Tenant1 user should see their workflow but not tenant2's
    list_response = client.get(
        "/api/workflows/",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert list_response.status_code == 200
    workflows = list_response.json()
    tenant1_workflow_ids = [w["id"] for w in workflows]
    assert workflow_id in tenant1_workflow_ids
    assert workflow_id2 not in tenant1_workflow_ids
    
    # Tenant2 user should see their workflow but not tenant1's
    list_response2 = client.get(
        "/api/workflows/",
        headers={"Authorization": f"Bearer {tenant2_token}"},
    )
    assert list_response2.status_code == 200
    workflows2 = list_response2.json()
    tenant2_workflow_ids = [w["id"] for w in workflows2]
    assert workflow_id2 in tenant2_workflow_ids
    assert workflow_id not in tenant2_workflow_ids
    
    # Tenant2 user should not be able to access tenant1's workflow directly
    get_response = client.get(
        f"/api/workflows/{workflow_id}",
        headers={"Authorization": f"Bearer {tenant2_token}"},
    )
    assert get_response.status_code == 403
    assert "Not authorised to access this workflow" in get_response.json()["detail"]

# Test API endpoint security
def test_workflow_crud_permissions(admin_token, editor_token, viewer_token, setup_database):
    """Test CRUD permissions on workflows for different roles."""
    # Admin creates a workflow
    admin_workflow = client.post(
        "/api/workflows/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Admin Workflow",
            "description": "An admin workflow",
            "status": "draft",
            "created_by": "admin_user",
            "steps": []
        },
    )
    assert admin_workflow.status_code == 200
    admin_workflow_id = admin_workflow.json()["id"]
    
    # Editor creates a workflow
    editor_workflow = client.post(
        "/api/workflows/",
        headers={"Authorization": f"Bearer {editor_token}"},
        json={
            "name": "Editor Workflow",
            "description": "An editor workflow",
            "status": "draft",
            "created_by": "editor_user",
            "steps": []
        },
    )
    assert editor_workflow.status_code == 200
    editor_workflow_id = editor_workflow.json()["id"]
    
    # Viewer tries to create a workflow (should be allowed as we only check roles for admin endpoints)
    viewer_workflow = client.post(
        "/api/workflows/",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={
            "name": "Viewer Workflow",
            "description": "A viewer workflow",
            "status": "draft",
            "created_by": "viewer_user",
            "steps": []
        },
    )
    assert viewer_workflow.status_code == 200
    viewer_workflow_id = viewer_workflow.json()["id"]
    
    # Admin can update any workflow
    admin_update = client.put(
        f"/api/workflows/{editor_workflow_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Updated Editor Workflow",
            "description": "Updated by admin",
            "status": "draft",
            "created_by": "editor_user",
            "steps": []
        },
    )
    assert admin_update.status_code == 200
    assert admin_update.json()["name"] == "Updated Editor Workflow"
    
    # Editor can only update their own workflow
    editor_update_own = client.put(
        f"/api/workflows/{editor_workflow_id}",
        headers={"Authorization": f"Bearer {editor_token}"},
        json={
            "name": "Editor Updated Own",
            "description": "Editor updated their own workflow",
            "status": "draft",
            "created_by": "editor_user",
            "steps": []
        },
    )
    assert editor_update_own.status_code == 200
    
    # Editor cannot update admin's workflow
    editor_update_admin = client.put(
        f"/api/workflows/{admin_workflow_id}",
        headers={"Authorization": f"Bearer {editor_token}"},
        json={
            "name": "Try to update admin workflow",
            "description": "This should fail",
            "status": "draft",
            "created_by": "admin_user",
            "steps": []
        },
    )
    assert editor_update_admin.status_code == 403
    assert "Not authorised to access this workflow" in editor_update_admin.json()["detail"]
    
    # Viewer can read workflows
    viewer_read = client.get(
        f"/api/workflows/{viewer_workflow_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert viewer_read.status_code == 200
    
    # Admin can delete any workflow
    admin_delete = client.delete(
        f"/api/workflows/{editor_workflow_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_delete.status_code == 200
    assert admin_delete.json()["status"] == "deleted"

def test_user_me_endpoint(admin_token):
    """Test that users can access their own information."""
    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin_user"
    assert "admin" in data["roles"]

def test_change_password(admin_token):
    """Test changing password."""
    response = client.post(
        "/api/users/me/change-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "current_password": "adminpass",
            "new_password": "newadminpass"
        },
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password updated successfully"
    
    # Try to login with new password
    login_response = client.post(
        "/api/token",
        data={"username": "admin_user", "password": "newadminpass"},
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()

def test_change_password_wrong_current(admin_token):
    """Test changing password with wrong current password."""
    response = client.post(
        "/api/users/me/change-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "current_password": "wrongpassword",
            "new_password": "newadminpass"
        },
    )
    assert response.status_code == 400
    assert "Incorrect password" in response.json()["detail"]
