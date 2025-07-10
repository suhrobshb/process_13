"""
Load Testing with Locust for AI Automation Platform
==================================================

This file defines comprehensive load testing scenarios for the AI automation platform
using Locust to simulate 1000+ concurrent workflows and validate system performance.
"""

import json
import random
import time
from locust import HttpUser, task, between, events
from typing import Dict, List, Any


class WorkflowUser(HttpUser):
    """
    Simulates a user creating and executing workflows
    """
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Setup for each user - authenticate and prepare data"""
        self.authenticate()
        self.workflow_templates = self.load_workflow_templates()
        self.user_id = random.randint(1000, 9999)
        self.created_workflows = []
        
    def authenticate(self):
        """Authenticate user and get token"""
        auth_data = {
            "username": f"testuser_{self.user_id}",
            "password": "testpassword123"
        }
        
        with self.client.post("/auth/login", json=auth_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
                response.success()
            else:
                # Create user if doesn't exist
                self.create_test_user()
                
    def create_test_user(self):
        """Create a test user for load testing"""
        user_data = {
            "username": f"testuser_{self.user_id}",
            "email": f"testuser_{self.user_id}@example.com",
            "password": "testpassword123",
            "role": "user"
        }
        
        with self.client.post("/auth/register", json=user_data, catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
                self.authenticate()  # Re-authenticate after creation
            else:
                response.failure(f"Failed to create user: {response.text}")
    
    def load_workflow_templates(self) -> List[Dict[str, Any]]:
        """Load predefined workflow templates for testing"""
        return [
            {
                "name": "Data Processing Workflow",
                "description": "Process CSV files and generate reports",
                "steps": [
                    {
                        "id": "step1",
                        "type": "file_processor",
                        "params": {"file_path": "/tmp/data.csv", "format": "csv"}
                    },
                    {
                        "id": "step2", 
                        "type": "data_analyzer",
                        "params": {"analysis_type": "summary_stats"}
                    },
                    {
                        "id": "step3",
                        "type": "report_generator",
                        "params": {"format": "pdf", "template": "standard"}
                    }
                ]
            },
            {
                "name": "Web Scraping Workflow",
                "description": "Scrape product data from e-commerce sites",
                "steps": [
                    {
                        "id": "step1",
                        "type": "enhanced_browser",
                        "params": {
                            "actions": [
                                {"type": "goto", "url": "https://example-store.com/products"},
                                {"type": "wait", "selector": ".product-list"},
                                {"type": "extract", "selector": ".product-item", "attribute": "data-product-id"}
                            ]
                        }
                    },
                    {
                        "id": "step2",
                        "type": "data_processor",
                        "params": {"clean_data": True, "validate": True}
                    }
                ]
            },
            {
                "name": "Email Automation Workflow",
                "description": "Send personalized emails based on user data",
                "steps": [
                    {
                        "id": "step1",
                        "type": "database_query",
                        "params": {"query": "SELECT * FROM users WHERE active = true"}
                    },
                    {
                        "id": "step2",
                        "type": "enhanced_llm",
                        "params": {
                            "provider": "openai",
                            "model": "gpt-3.5-turbo",
                            "prompt_template": "Generate personalized email for {{ user.name }}"
                        }
                    },
                    {
                        "id": "step3",
                        "type": "email_sender",
                        "params": {"template": "personalized", "batch_size": 10}
                    }
                ]
            },
            {
                "name": "Desktop Automation Workflow",
                "description": "Automate desktop application interactions",
                "steps": [
                    {
                        "id": "step1",
                        "type": "enhanced_desktop",
                        "params": {
                            "actions": [
                                {"type": "click", "x": 100, "y": 200},
                                {"type": "type", "text": "Test automation data"},
                                {"type": "hotkey", "keys": ["ctrl", "s"]}
                            ]
                        }
                    },
                    {
                        "id": "step2",
                        "type": "file_validator",
                        "params": {"check_existence": True, "validate_format": True}
                    }
                ]
            }
        ]
    
    @task(5)
    def create_workflow(self):
        """Create a new workflow (high frequency task)"""
        template = random.choice(self.workflow_templates)
        workflow_data = {
            "name": f"{template['name']} - {self.user_id}-{random.randint(1000, 9999)}",
            "description": template['description'],
            "steps": template['steps'],
            "tags": ["load_test", "auto_generated"],
            "schedule": None,  # Manual execution for testing
            "enabled": True
        }
        
        with self.client.post("/api/workflows", json=workflow_data, headers=self.headers, catch_response=True) as response:
            if response.status_code in [200, 201]:
                data = response.json()
                workflow_id = data.get("id")
                self.created_workflows.append(workflow_id)
                response.success()
            else:
                response.failure(f"Failed to create workflow: {response.text}")
    
    @task(10)
    def execute_workflow(self):
        """Execute an existing workflow (very high frequency task)"""
        if not self.created_workflows:
            self.create_workflow()
            return
            
        workflow_id = random.choice(self.created_workflows)
        execution_data = {
            "workflow_id": workflow_id,
            "context": {
                "user_id": self.user_id,
                "execution_time": time.time(),
                "test_mode": True
            }
        }
        
        with self.client.post("/api/executions", json=execution_data, headers=self.headers, catch_response=True, name="/api/executions") as response:
            if response.status_code in [200, 201]:
                data = response.json()
                execution_id = data.get("id")
                response.success()
                
                # Monitor execution status
                self.monitor_execution(execution_id)
            else:
                response.failure(f"Failed to execute workflow: {response.text}")
    
    def monitor_execution(self, execution_id: str):
        """Monitor workflow execution status"""
        max_checks = 30  # Maximum 30 status checks
        for i in range(max_checks):
            with self.client.get(f"/api/executions/{execution_id}", headers=self.headers, catch_response=True, name="/api/executions/[id]") as response:
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    
                    if status in ["completed", "failed", "cancelled"]:
                        response.success()
                        break
                    elif status in ["pending", "running"]:
                        response.success()
                        time.sleep(1)  # Wait before next check
                    else:
                        response.failure(f"Unknown execution status: {status}")
                        break
                else:
                    response.failure(f"Failed to get execution status: {response.text}")
                    break
    
    @task(3)
    def list_workflows(self):
        """List user workflows"""
        with self.client.get("/api/workflows", headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                workflows = data.get("workflows", [])
                response.success()
            else:
                response.failure(f"Failed to list workflows: {response.text}")
    
    @task(2)
    def get_workflow_details(self):
        """Get details for a specific workflow"""
        if not self.created_workflows:
            return
            
        workflow_id = random.choice(self.created_workflows)
        with self.client.get(f"/api/workflows/{workflow_id}", headers=self.headers, catch_response=True, name="/api/workflows/[id]") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get workflow details: {response.text}")
    
    @task(2)
    def list_executions(self):
        """List recent executions"""
        with self.client.get("/api/executions", headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to list executions: {response.text}")
    
    @task(1)
    def get_system_metrics(self):
        """Get system performance metrics"""
        with self.client.get("/api/metrics", headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get metrics: {response.text}")
    
    @task(1)
    def update_workflow(self):
        """Update an existing workflow"""
        if not self.created_workflows:
            return
            
        workflow_id = random.choice(self.created_workflows)
        update_data = {
            "description": f"Updated workflow at {time.time()}",
            "tags": ["load_test", "updated"]
        }
        
        with self.client.put(f"/api/workflows/{workflow_id}", json=update_data, headers=self.headers, catch_response=True, name="/api/workflows/[id]") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to update workflow: {response.text}")


class AdminUser(HttpUser):
    """
    Simulates an admin user performing system administration tasks
    """
    wait_time = between(5, 10)  # Longer wait time for admin tasks
    weight = 1  # Lower weight (fewer admin users)
    
    def on_start(self):
        """Setup for admin user"""
        self.authenticate_admin()
        self.admin_id = random.randint(1, 10)
    
    def authenticate_admin(self):
        """Authenticate admin user"""
        auth_data = {
            "username": f"admin_{self.admin_id}",
            "password": "adminpassword123"
        }
        
        with self.client.post("/auth/login", json=auth_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
                response.success()
            else:
                response.failure(f"Admin authentication failed: {response.text}")
    
    @task(5)
    def get_system_status(self):
        """Get overall system status"""
        with self.client.get("/api/admin/system/status", headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get system status: {response.text}")
    
    @task(3)
    def get_user_analytics(self):
        """Get user analytics and statistics"""
        with self.client.get("/api/admin/analytics/users", headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get user analytics: {response.text}")
    
    @task(2)
    def get_workflow_analytics(self):
        """Get workflow execution analytics"""
        with self.client.get("/api/admin/analytics/workflows", headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get workflow analytics: {response.text}")
    
    @task(1)
    def manage_system_settings(self):
        """Update system settings"""
        settings_data = {
            "max_concurrent_executions": random.randint(50, 200),
            "default_timeout": random.randint(30, 300),
            "log_level": random.choice(["INFO", "DEBUG", "WARNING"])
        }
        
        with self.client.post("/api/admin/settings", json=settings_data, headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to update settings: {response.text}")


class WebSocketUser(HttpUser):
    """
    Simulates users connecting to real-time WebSocket endpoints
    """
    wait_time = between(10, 30)  # Longer wait for WebSocket connections
    weight = 2  # Some users use real-time features
    
    def on_start(self):
        """Setup WebSocket user"""
        self.authenticate()
        self.ws_connections = []
    
    def authenticate(self):
        """Authenticate for WebSocket access"""
        auth_data = {
            "username": f"wsuser_{random.randint(1000, 9999)}",
            "password": "wspassword123"
        }
        
        with self.client.post("/auth/login", json=auth_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                response.success()
            else:
                response.failure(f"WebSocket user authentication failed: {response.text}")
    
    @task(3)
    def connect_execution_websocket(self):
        """Connect to execution status WebSocket"""
        # Note: This is a simplified simulation
        # In reality, you'd need websocket support in Locust
        ws_url = f"/ws/executions?token={self.token}"
        
        with self.client.get("/api/websocket/connect", headers={"Authorization": f"Bearer {self.token}"}, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"WebSocket connection failed: {response.text}")
    
    @task(2)
    def get_realtime_metrics(self):
        """Get real-time metrics via HTTP (simulating WebSocket data)"""
        with self.client.get("/api/realtime/metrics", headers={"Authorization": f"Bearer {self.token}"}, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get realtime metrics: {response.text}")


# Performance tracking and custom metrics
@events.request.add_listener
def track_request_performance(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Track custom performance metrics"""
    # Track slow requests
    if response_time > 5000:  # 5 seconds
        print(f"SLOW REQUEST: {name} took {response_time}ms")
    
    # Track large responses
    if response_length and response_length > 1024 * 1024:  # 1MB
        print(f"LARGE RESPONSE: {name} returned {response_length} bytes")


@events.worker_report.add_listener
def worker_report(client_id, data):
    """Custom worker reporting"""
    print(f"Worker {client_id} reported: {data}")


# Test scenario configurations
class LoadTestScenarios:
    """Define different load testing scenarios"""
    
    @staticmethod
    def normal_load():
        """Normal operational load"""
        return {
            "users": 100,
            "spawn_rate": 10,
            "run_time": "10m"
        }
    
    @staticmethod
    def peak_load():
        """Peak usage load"""
        return {
            "users": 500,
            "spawn_rate": 25,
            "run_time": "15m"
        }
    
    @staticmethod
    def stress_load():
        """Stress test load"""
        return {
            "users": 1000,
            "spawn_rate": 50,
            "run_time": "20m"
        }
    
    @staticmethod
    def spike_load():
        """Spike load test"""
        return {
            "users": 2000,
            "spawn_rate": 100,
            "run_time": "5m"
        }


# Health check functions
def health_check():
    """Perform health check before load testing"""
    import requests
    try:
        response = requests.get("http://localhost:8000/health", timeout=30)
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


if __name__ == "__main__":
    # This allows running the file directly for testing
    print("Load testing configuration loaded successfully")
    print("Available scenarios:", list(LoadTestScenarios.__dict__.keys()))
    
    # Example commands to run:
    print("\nExample Locust commands:")
    print("locust -f tests/perf/locustfile.py --headless -u 100 -r 10 -t 10m")
    print("locust -f tests/perf/locustfile.py --headless -u 1000 -r 50 -t 20m")
    print("locust -f tests/perf/locustfile.py --web-port 8089")