#!/usr/bin/env python3
"""
AI Engine Performance Testing Script
===================================

This script uses Locust to load test the AI Engine APIs and validate
the system's performance under different load conditions.

Features:
- Tests all major API endpoints (workflows, tasks, executions)
- Simulates realistic user behavior with weighted tasks
- Supports authentication and token management
- Collects detailed performance metrics
- Configurable test scenarios

Usage:
    # Run with web UI
    locust -f scripts/performance-test.py

    # Run headless with 100 users, 10 spawn rate, for 5 minutes
    locust -f scripts/performance-test.py --headless -u 100 -r 10 -t 5m

    # Run with specific host
    locust -f scripts/performance-test.py --host=https://ai-engine-api-url.com
"""

import json
import random
import time
import os
import logging
from typing import Dict, List, Optional, Tuple, Union

from locust import HttpUser, task, between, events, tag
from locust.exception import StopUser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("performance-test")

# Test configuration
DEFAULT_HOST = "http://localhost:8000"
AUTH_ENABLED = True
WORKFLOW_COUNT = 5  # Number of workflows to create per user
TASK_COUNT = 3      # Number of tasks to create per user

# Sample data for testing
SAMPLE_WORKFLOWS = [
    {
        "name": "Data Processing Workflow",
        "description": "Processes data files and generates reports",
        "status": "active",
        "steps": [
            {
                "id": "fetch_data",
                "type": "http",
                "params": {
                    "url": "https://api.example.com/data",
                    "method": "GET",
                    "headers": {"Accept": "application/json"}
                }
            },
            {
                "id": "process_data",
                "type": "shell",
                "params": {
                    "command": "echo 'Processing data'",
                    "timeout": 5
                }
            },
            {
                "id": "generate_report",
                "type": "llm",
                "params": {
                    "provider": "openai",
                    "model": "gpt-3.5-turbo",
                    "prompt": "Generate a summary report of the data"
                }
            }
        ]
    },
    {
        "name": "Customer Onboarding",
        "description": "Automates customer onboarding process",
        "status": "active",
        "steps": [
            {
                "id": "create_account",
                "type": "http",
                "params": {
                    "url": "https://api.example.com/accounts",
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "json": {"name": "Test Customer", "email": "test@example.com"}
                }
            },
            {
                "id": "send_welcome_email",
                "type": "llm",
                "params": {
                    "provider": "openai",
                    "model": "gpt-3.5-turbo",
                    "prompt": "Generate a welcome email for a new customer"
                }
            }
        ]
    },
    {
        "name": "Approval Workflow",
        "description": "Workflow with approval steps",
        "status": "active",
        "steps": [
            {
                "id": "request_approval",
                "type": "approval",
                "params": {
                    "title": "Expense Approval",
                    "description": "Approve expense report",
                    "approvers": ["manager@example.com"],
                    "wait": False
                }
            },
            {
                "id": "process_approval",
                "type": "decision",
                "params": {
                    "conditions": [
                        {"expression": "approved == true", "target": "approved_path"},
                        {"expression": "approved == false", "target": "rejected_path"}
                    ],
                    "default": "pending_path"
                }
            }
        ]
    },
    {
        "name": "Data Extraction Workflow",
        "description": "Extracts data from various sources",
        "status": "active",
        "steps": [
            {
                "id": "extract_web_data",
                "type": "browser",
                "params": {
                    "actions": [
                        {"type": "goto", "url": "https://example.com"},
                        {"type": "extract_all", "selector": ".data-item"}
                    ]
                }
            },
            {
                "id": "process_data",
                "type": "shell",
                "params": {
                    "command": "echo 'Processing extracted data'",
                    "timeout": 5
                }
            }
        ]
    },
    {
        "name": "Document Processing",
        "description": "Processes and analyzes documents",
        "status": "active",
        "steps": [
            {
                "id": "extract_text",
                "type": "shell",
                "params": {
                    "command": "echo 'Extracting text from document'",
                    "timeout": 5
                }
            },
            {
                "id": "analyze_text",
                "type": "llm",
                "params": {
                    "provider": "openai",
                    "model": "gpt-3.5-turbo",
                    "prompt": "Analyze the following document text and extract key information"
                }
            }
        ]
    }
]

# Sample task data (simulating recorded tasks)
SAMPLE_TASK_DATA = {
    "filename": "recorded_task.zip",
    "status": "uploaded",
    "extra_metadata": {
        "recording_duration": 45.2,
        "actions_detected": 12,
        "screens_captured": 8
    }
}

# Test metrics
class Metrics:
    """Tracks and reports performance metrics."""
    
    def __init__(self):
        self.workflow_ids = []
        self.task_ids = []
        self.execution_ids = []
        
    def add_workflow(self, workflow_id):
        self.workflow_ids.append(workflow_id)
        
    def add_task(self, task_id):
        self.task_ids.append(task_id)
        
    def add_execution(self, execution_id):
        self.execution_ids.append(execution_id)
        
    def get_random_workflow_id(self):
        if not self.workflow_ids:
            return None
        return random.choice(self.workflow_ids)
        
    def get_random_task_id(self):
        if not self.task_ids:
            return None
        return random.choice(self.task_ids)
        
    def get_random_execution_id(self):
        if not self.execution_ids:
            return None
        return random.choice(self.execution_ids)

# Authentication helper
class AuthManager:
    """Manages authentication and token handling."""
    
    def __init__(self, client):
        self.client = client
        self.token = None
        self.username = f"perftest_user_{int(time.time())}_{random.randint(1000, 9999)}"
        self.password = "Password123!"
        self.email = f"{self.username}@example.com"
        
    def register(self):
        """Register a new test user."""
        response = self.client.post(
            "/api/register",
            json={
                "username": self.username,
                "email": self.email,
                "password": self.password
            },
            name="/api/register"
        )
        
        if response.status_code not in (200, 201, 409):  # 409 if user already exists
            logger.error(f"Failed to register user: {response.status_code} - {response.text}")
            raise StopUser()
            
        return response.status_code in (200, 201)
        
    def login(self):
        """Login and obtain JWT token."""
        response = self.client.post(
            "/api/token",
            data={
                "username": self.username,
                "password": self.password
            },
            name="/api/token"
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to login: {response.status_code} - {response.text}")
            raise StopUser()
            
        self.token = response.json().get("access_token")
        return bool(self.token)
        
    def get_auth_header(self):
        """Get the authorization header with the JWT token."""
        if not self.token:
            self.login()
        return {"Authorization": f"Bearer {self.token}"}

# Main Locust user class
class AIEngineUser(HttpUser):
    """
    Simulates a user interacting with the AI Engine API.
    
    This user performs various tasks including:
    - Creating and managing workflows
    - Uploading and processing tasks
    - Executing workflows
    - Monitoring executions
    """
    
    # Wait between 1 and 5 seconds between tasks
    wait_time = between(1, 5)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = Metrics()
        self.auth = AuthManager(self.client)
        self.workflows_created = 0
        self.tasks_created = 0
        
    def on_start(self):
        """Initialize the user session."""
        if AUTH_ENABLED:
            # Register and login
            self.auth.register()
            self.auth.login()
            
        # Create initial workflows and tasks
        self._create_initial_workflows()
        self._create_initial_tasks()
    
    def _create_initial_workflows(self):
        """Create initial workflows for testing."""
        for _ in range(WORKFLOW_COUNT):
            workflow_data = random.choice(SAMPLE_WORKFLOWS)
            self.create_workflow(workflow_data)
    
    def _create_initial_tasks(self):
        """Create initial tasks for testing."""
        for _ in range(TASK_COUNT):
            self.upload_task()
    
    @tag("workflows")
    @task(3)
    def create_workflow(self, workflow_data=None):
        """Create a new workflow."""
        if not workflow_data:
            workflow_data = random.choice(SAMPLE_WORKFLOWS)
            
        # Add some randomization to make each workflow unique
        workflow_data = workflow_data.copy()
        workflow_data["name"] = f"{workflow_data['name']} - {random.randint(1000, 9999)}"
        
        headers = {}
        if AUTH_ENABLED:
            headers = self.auth.get_auth_header()
            
        with self.client.post(
            "/api/workflows",
            json=workflow_data,
            headers=headers,
            catch_response=True,
            name="/api/workflows [POST]"
        ) as response:
            if response.status_code in (200, 201):
                workflow_id = response.json().get("id")
                if workflow_id:
                    self.metrics.add_workflow(workflow_id)
                    self.workflows_created += 1
                    response.success()
                else:
                    response.failure("No workflow ID in response")
            else:
                response.failure(f"Failed to create workflow: {response.status_code}")
    
    @tag("workflows")
    @task(5)
    def list_workflows(self):
        """List all workflows."""
        headers = {}
        if AUTH_ENABLED:
            headers = self.auth.get_auth_header()
            
        self.client.get(
            "/api/workflows",
            headers=headers,
            name="/api/workflows [GET]"
        )
    
    @tag("workflows")
    @task(2)
    def get_workflow(self):
        """Get a specific workflow by ID."""
        workflow_id = self.metrics.get_random_workflow_id()
        if not workflow_id:
            return
            
        headers = {}
        if AUTH_ENABLED:
            headers = self.auth.get_auth_header()
            
        self.client.get(
            f"/api/workflows/{workflow_id}",
            headers=headers,
            name="/api/workflows/{id} [GET]"
        )
    
    @tag("executions")
    @task(3)
    def execute_workflow(self):
        """Execute a workflow."""
        workflow_id = self.metrics.get_random_workflow_id()
        if not workflow_id:
            return
            
        headers = {}
        if AUTH_ENABLED:
            headers = self.auth.get_auth_header()
            
        with self.client.post(
            f"/api/workflows/{workflow_id}/trigger",
            headers=headers,
            catch_response=True,
            name="/api/workflows/{id}/trigger [POST]"
        ) as response:
            if response.status_code == 200:
                execution_id = response.json().get("execution_id")
                if execution_id:
                    self.metrics.add_execution(execution_id)
                    response.success()
                else:
                    response.failure("No execution ID in response")
            else:
                response.failure(f"Failed to execute workflow: {response.status_code}")
    
    @tag("executions")
    @task(4)
    def list_executions(self):
        """List all workflow executions."""
        headers = {}
        if AUTH_ENABLED:
            headers = self.auth.get_auth_header()
            
        self.client.get(
            "/api/executions",
            headers=headers,
            name="/api/executions [GET]"
        )
    
    @tag("executions")
    @task(2)
    def get_execution(self):
        """Get a specific execution by ID."""
        execution_id = self.metrics.get_random_execution_id()
        if not execution_id:
            return
            
        headers = {}
        if AUTH_ENABLED:
            headers = self.auth.get_auth_header()
            
        self.client.get(
            f"/api/executions/{execution_id}",
            headers=headers,
            name="/api/executions/{id} [GET]"
        )
    
    @tag("tasks")
    @task(2)
    def upload_task(self):
        """Upload a task recording."""
        if not AUTH_ENABLED:
            return
            
        headers = self.auth.get_auth_header()
        
        # Simulate file upload with metadata
        files = {
            "file": ("task_recording.zip", b"mock recording data", "application/zip"),
            "metadata": (None, json.dumps(SAMPLE_TASK_DATA["extra_metadata"]), "application/json")
        }
        
        with self.client.post(
            "/api/tasks/upload",
            files=files,
            headers=headers,
            catch_response=True,
            name="/api/tasks/upload [POST]"
        ) as response:
            if response.status_code in (200, 201):
                task_id = response.json().get("id")
                if task_id:
                    self.metrics.add_task(task_id)
                    self.tasks_created += 1
                    response.success()
                else:
                    response.failure("No task ID in response")
            else:
                response.failure(f"Failed to upload task: {response.status_code}")
    
    @tag("tasks")
    @task(3)
    def list_tasks(self):
        """List all tasks."""
        if not AUTH_ENABLED:
            return
            
        headers = self.auth.get_auth_header()
        
        self.client.get(
            "/api/tasks",
            headers=headers,
            name="/api/tasks [GET]"
        )
    
    @tag("tasks")
    @task(1)
    def get_task(self):
        """Get a specific task by ID."""
        task_id = self.metrics.get_random_task_id()
        if not task_id or not AUTH_ENABLED:
            return
            
        headers = self.auth.get_auth_header()
        
        self.client.get(
            f"/api/tasks/{task_id}",
            headers=headers,
            name="/api/tasks/{id} [GET]"
        )
    
    @tag("tasks")
    @task(1)
    def get_task_clusters(self):
        """Get clusters for a specific task."""
        task_id = self.metrics.get_random_task_id()
        if not task_id or not AUTH_ENABLED:
            return
            
        headers = self.auth.get_auth_header()
        
        self.client.get(
            f"/api/tasks/{task_id}/clusters",
            headers=headers,
            name="/api/tasks/{id}/clusters [GET]"
        )
    
    @tag("health")
    @task(10)  # Higher weight for health checks
    def health_check(self):
        """Perform health check."""
        self.client.get("/health", name="/health [GET]")
    
    @tag("auth")
    @task(1)
    def refresh_token(self):
        """Refresh the authentication token."""
        if not AUTH_ENABLED:
            return
            
        self.auth.login()

# Event handlers
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test is starting."""
    logger.info("Starting AI Engine performance test")
    if not environment.host:
        environment.host = DEFAULT_HOST
    logger.info(f"Using host: {environment.host}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test is stopping."""
    logger.info("AI Engine performance test completed")
    
    # Calculate and report statistics
    total_workflows = sum(len(user.metrics.workflow_ids) for user in environment.runner.user_instances)
    total_tasks = sum(len(user.metrics.task_ids) for user in environment.runner.user_instances)
    total_executions = sum(len(user.metrics.execution_ids) for user in environment.runner.user_instances)
    
    logger.info(f"Total workflows created: {total_workflows}")
    logger.info(f"Total tasks uploaded: {total_tasks}")
    logger.info(f"Total workflow executions: {total_executions}")

# Main entry point for direct execution
if __name__ == "__main__":
    # This block will be executed when running the script directly
    # It's useful for development and testing
    print("AI Engine Performance Test")
    print("=========================")
    print("This script is designed to be run with Locust.")
    print("\nExample usage:")
    print("  locust -f scripts/performance-test.py")
    print("  locust -f scripts/performance-test.py --host=https://ai-engine-api-url.com")
    print("  locust -f scripts/performance-test.py --headless -u 100 -r 10 -t 5m")
