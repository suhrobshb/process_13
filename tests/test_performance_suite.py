"""
Performance Test Suite for RPA Platform
========================================

This comprehensive test suite validates system performance under various load conditions:
- Target: 1000+ concurrent workflow executions
- Response time: <2s for critical operations
- Memory/CPU profiling under load
- Database performance under concurrent access
- WebSocket connection handling

Run with: pytest tests/test_performance_suite.py -v
Load test: python -m locust -f tests/test_performance_suite.py --host=http://localhost:8000
"""

import asyncio
import time
import psutil
import pytest
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Dict, Any
from unittest.mock import patch
import threading

from locust import HttpUser, task, between
from locust.env import Environment
from locust.stats import stats_printer

# Local imports
from ai_engine.main import app
from ai_engine.database import get_session
from ai_engine.models.workflow import Workflow
from ai_engine.models.execution import Execution
from ai_engine.models.task import Task


@dataclass
class PerformanceMetrics:
    """Container for performance test results"""
    response_times: List[float]
    cpu_usage: List[float]
    memory_usage: List[float]
    concurrent_users: int
    success_rate: float
    throughput: float  # requests per second
    
    @property
    def avg_response_time(self) -> float:
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0
    
    @property
    def p95_response_time(self) -> float:
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        index = int(0.95 * len(sorted_times))
        return sorted_times[index]


class SystemMonitor:
    """Monitor system resources during performance tests"""
    
    def __init__(self):
        self.cpu_usage = []
        self.memory_usage = []
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start system resource monitoring"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop system resource monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_loop(self):
        """Monitor system resources every second"""
        while self.monitoring:
            self.cpu_usage.append(psutil.cpu_percent())
            self.memory_usage.append(psutil.virtual_memory().percent)
            time.sleep(1)


class WorkflowPerformanceUser(HttpUser):
    """Locust user for workflow performance testing"""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup user session"""
        # Login to get auth token
        response = self.client.post("/auth/login", json={
            "username": "test_user",
            "password": "test_password"
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}
    
    @task(3)
    def create_workflow(self):
        """Create a new workflow - high frequency task"""
        workflow_data = {
            "name": f"Performance Test Workflow {time.time()}",
            "description": "Automated performance test workflow",
            "steps": [
                {"action": "click", "target": "button", "parameters": {"x": 100, "y": 200}},
                {"action": "type", "target": "input", "parameters": {"text": "performance test"}}
            ]
        }
        
        with self.client.post("/workflows", 
                             json=workflow_data, 
                             headers=self.headers,
                             catch_response=True) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Failed to create workflow: {response.status_code}")
    
    @task(5)
    def list_workflows(self):
        """List workflows - highest frequency task"""
        with self.client.get("/workflows", 
                            headers=self.headers,
                            catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to list workflows: {response.status_code}")
    
    @task(2)
    def execute_workflow(self):
        """Execute workflow - medium frequency task"""
        # First get a workflow ID
        workflows_response = self.client.get("/workflows", headers=self.headers)
        if workflows_response.status_code == 200 and workflows_response.json():
            workflow_id = workflows_response.json()[0]["id"]
            
            with self.client.post(f"/workflows/{workflow_id}/execute",
                                 headers=self.headers,
                                 catch_response=True) as response:
                if response.status_code in [200, 201]:
                    response.success()
                else:
                    response.failure(f"Failed to execute workflow: {response.status_code}")
    
    @task(1)
    def get_execution_status(self):
        """Check execution status - low frequency task"""
        executions_response = self.client.get("/executions", headers=self.headers)
        if executions_response.status_code == 200 and executions_response.json():
            execution_id = executions_response.json()[0]["id"]
            
            with self.client.get(f"/executions/{execution_id}",
                                headers=self.headers,
                                catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get execution status: {response.status_code}")


class TestPerformanceSuite:
    """Comprehensive performance test suite"""
    
    @pytest.fixture
    def system_monitor(self):
        """Provide system monitoring fixture"""
        monitor = SystemMonitor()
        monitor.start_monitoring()
        yield monitor
        monitor.stop_monitoring()
    
    @pytest.fixture
    def base_url(self):
        """Base URL for API testing"""
        return "http://localhost:8000"
    
    def test_single_request_latency(self, base_url):
        """Test individual request latency - must be <2s"""
        start_time = time.time()
        response = requests.get(f"{base_url}/health")
        response_time = time.time() - start_time
        
        assert response.status_code == 200
        assert response_time < 2.0, f"Response time {response_time:.2f}s exceeds 2s threshold"
    
    def test_concurrent_workflow_creation(self, base_url, system_monitor):
        """Test concurrent workflow creation - target 100 concurrent requests"""
        concurrent_users = 100
        response_times = []
        success_count = 0
        
        def create_workflow(user_id):
            """Create workflow for a single user"""
            start_time = time.time()
            try:
                response = requests.post(f"{base_url}/workflows", json={
                    "name": f"Concurrent Test Workflow {user_id}",
                    "description": f"Performance test workflow {user_id}",
                    "steps": [{"action": "click", "target": "button"}]
                }, timeout=10)
                
                response_time = time.time() - start_time
                return {
                    "success": response.status_code in [200, 201],
                    "response_time": response_time,
                    "user_id": user_id
                }
            except Exception as e:
                return {
                    "success": False,
                    "response_time": time.time() - start_time,
                    "user_id": user_id,
                    "error": str(e)
                }
        
        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(create_workflow, i) for i in range(concurrent_users)]
            
            for future in as_completed(futures):
                result = future.result()
                response_times.append(result["response_time"])
                if result["success"]:
                    success_count += 1
        
        # Performance assertions
        success_rate = success_count / concurrent_users
        avg_response_time = sum(response_times) / len(response_times)
        p95_response_time = sorted(response_times)[int(0.95 * len(response_times))]
        
        print(f"\nConcurrent Workflow Creation Results:")
        print(f"Success Rate: {success_rate:.1%}")
        print(f"Average Response Time: {avg_response_time:.2f}s")
        print(f"95th Percentile: {p95_response_time:.2f}s")
        print(f"Max CPU Usage: {max(system_monitor.cpu_usage):.1f}%")
        print(f"Max Memory Usage: {max(system_monitor.memory_usage):.1f}%")
        
        assert success_rate >= 0.95, f"Success rate {success_rate:.1%} below 95% threshold"
        assert avg_response_time < 2.0, f"Average response time {avg_response_time:.2f}s exceeds 2s"
        assert p95_response_time < 5.0, f"95th percentile {p95_response_time:.2f}s exceeds 5s"
    
    def test_database_concurrent_access(self, system_monitor):
        """Test database performance under concurrent load"""
        concurrent_operations = 200
        
        def database_operation(operation_id):
            """Perform database operation"""
            start_time = time.time()
            try:
                # Simulate database-heavy operations
                with get_session() as session:
                    # Create test workflow
                    workflow = Workflow(
                        name=f"DB Test Workflow {operation_id}",
                        description="Database performance test",
                        steps=[{"action": "test"}]
                    )
                    session.add(workflow)
                    session.commit()
                    
                    # Query workflows
                    workflows = session.query(Workflow).limit(10).all()
                    
                    response_time = time.time() - start_time
                    return {"success": True, "response_time": response_time}
                    
            except Exception as e:
                return {"success": False, "response_time": time.time() - start_time, "error": str(e)}
        
        response_times = []
        success_count = 0
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(database_operation, i) for i in range(concurrent_operations)]
            
            for future in as_completed(futures):
                result = future.result()
                response_times.append(result["response_time"])
                if result["success"]:
                    success_count += 1
        
        success_rate = success_count / concurrent_operations
        avg_response_time = sum(response_times) / len(response_times)
        
        print(f"\nDatabase Concurrent Access Results:")
        print(f"Success Rate: {success_rate:.1%}")
        print(f"Average Response Time: {avg_response_time:.2f}s")
        
        assert success_rate >= 0.95, f"Database success rate {success_rate:.1%} below 95%"
        assert avg_response_time < 1.0, f"Database response time {avg_response_time:.2f}s exceeds 1s"
    
    def test_memory_leak_detection(self, base_url):
        """Test for memory leaks during sustained load"""
        initial_memory = psutil.virtual_memory().percent
        
        # Perform sustained operations
        for i in range(500):
            response = requests.get(f"{base_url}/workflows")
            if i % 100 == 0:
                current_memory = psutil.virtual_memory().percent
                memory_increase = current_memory - initial_memory
                
                print(f"Memory usage after {i} requests: {current_memory:.1f}% (+{memory_increase:.1f}%)")
                
                # Alert if memory increases by more than 20%
                assert memory_increase < 20, f"Potential memory leak: {memory_increase:.1f}% increase"
    
    def test_websocket_concurrent_connections(self, base_url):
        """Test WebSocket connection handling under load"""
        import websocket
        
        max_connections = 100
        successful_connections = 0
        
        def create_websocket_connection(connection_id):
            """Create a WebSocket connection"""
            try:
                ws_url = base_url.replace("http://", "ws://") + "/ws"
                ws = websocket.create_connection(ws_url, timeout=5)
                ws.send(json.dumps({"type": "ping", "data": f"connection_{connection_id}"}))
                response = ws.recv()
                ws.close()
                return True
            except Exception as e:
                print(f"WebSocket connection {connection_id} failed: {e}")
                return False
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(create_websocket_connection, i) for i in range(max_connections)]
            
            for future in as_completed(futures):
                if future.result():
                    successful_connections += 1
        
        connection_rate = successful_connections / max_connections
        print(f"\nWebSocket Connection Results:")
        print(f"Successful Connections: {successful_connections}/{max_connections} ({connection_rate:.1%})")
        
        assert connection_rate >= 0.90, f"WebSocket connection rate {connection_rate:.1%} below 90%"
    
    def test_workflow_execution_throughput(self, base_url, system_monitor):
        """Test workflow execution throughput - target 50+ executions/minute"""
        test_duration = 60  # seconds
        execution_count = 0
        start_time = time.time()
        
        def execute_workflow():
            """Execute a simple workflow"""
            try:
                response = requests.post(f"{base_url}/workflows/1/execute", timeout=5)
                return response.status_code in [200, 201]
            except:
                return False
        
        # Execute workflows for specified duration
        while time.time() - start_time < test_duration:
            if execute_workflow():
                execution_count += 1
            time.sleep(0.5)  # 2 executions per second target
        
        actual_duration = time.time() - start_time
        throughput = execution_count / (actual_duration / 60)  # executions per minute
        
        print(f"\nWorkflow Execution Throughput:")
        print(f"Executions: {execution_count} in {actual_duration:.1f}s")
        print(f"Throughput: {throughput:.1f} executions/minute")
        
        assert throughput >= 50, f"Throughput {throughput:.1f}/min below 50/min target"


def run_locust_performance_test():
    """
    Standalone function to run Locust performance test
    
    Usage:
    python -c "from tests.test_performance_suite import run_locust_performance_test; run_locust_performance_test()"
    """
    env = Environment(user_classes=[WorkflowPerformanceUser])
    env.create_local_runner()
    
    # Start test with 1000 users
    env.runner.start(1000, spawn_rate=10)
    
    # Run for 5 minutes
    import time
    time.sleep(300)
    
    env.runner.quit()
    
    # Print results
    stats = env.runner.stats
    print("\n" + "="*50)
    print("LOCUST PERFORMANCE TEST RESULTS")
    print("="*50)
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Failed Requests: {stats.total.num_failures}")
    print(f"Success Rate: {((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100):.1f}%")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"95th Percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"Max Response Time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests per Second: {stats.total.total_rps:.2f}")


if __name__ == "__main__":
    # Run performance test suite
    pytest.main([__file__, "-v", "--tb=short"])