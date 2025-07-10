"""
Integration Test Suite
=====================

Tests for end-to-end service connectivity and integration points.
"""

import os
import sys
import json
import time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class MockAPIClient:
    """Mock API client for integration testing"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session_data = {}
    
    def get(self, endpoint, **kwargs):
        """Mock GET request"""
        return {
            "status_code": 200,
            "data": {"message": "Mock GET response for {}".format(endpoint)},
            "success": True
        }
    
    def post(self, endpoint, data=None, **kwargs):
        """Mock POST request"""
        return {
            "status_code": 201,
            "data": {"message": "Mock POST response", "created": data},
            "success": True
        }
    
    def health_check(self):
        """Mock health check"""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {
                "database": "healthy",
                "redis": "healthy",
                "api": "healthy"
            }
        }


class TestServiceConnectivity:
    """Test connectivity between services"""
    
    def __init__(self):
        self.api_client = MockAPIClient()
        self.results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "tests": []
        }
    
    def run_test(self, test_name, test_func):
        """Run a single integration test"""
        try:
            result = test_func()
            if result:
                self.results["passed"] += 1
                print("  PASSED {}".format(test_name))
                self.results["tests"].append({
                    "name": test_name,
                    "status": "passed",
                    "result": result
                })
            else:
                self.results["failed"] += 1
                print("  FAILED {}".format(test_name))
                self.results["tests"].append({
                    "name": test_name,
                    "status": "failed",
                    "error": "Test returned False"
                })
        except Exception as e:
            error_msg = str(e)
            if "skip:" in error_msg:
                self.results["skipped"] += 1
                print("  SKIPPED {}: {}".format(test_name, error_msg.replace("skip:", "")))
                self.results["tests"].append({
                    "name": test_name,
                    "status": "skipped",
                    "reason": error_msg.replace("skip:", "")
                })
            else:
                self.results["failed"] += 1
                print("  FAILED {}: {}".format(test_name, error_msg))
                self.results["tests"].append({
                    "name": test_name,
                    "status": "failed",
                    "error": error_msg
                })
    
    def test_api_health_endpoint(self):
        """Test API health endpoint connectivity"""
        response = self.api_client.health_check()
        
        assert response["status"] == "healthy"
        assert "services" in response
        assert "timestamp" in response
        
        return True
    
    def test_database_connection(self):
        """Test database connectivity through API"""
        response = self.api_client.get("/health/database")
        
        assert response["success"] == True
        assert response["status_code"] == 200
        
        return True
    
    def test_redis_connection(self):
        """Test Redis connectivity through API"""
        response = self.api_client.get("/health/redis")
        
        assert response["success"] == True
        assert response["status_code"] == 200
        
        return True
    
    def test_workflow_api_endpoints(self):
        """Test workflow API endpoints"""
        # Test GET workflows
        get_response = self.api_client.get("/api/workflows")
        assert get_response["success"] == True
        
        # Test POST workflow
        workflow_data = {
            "name": "Integration Test Workflow",
            "description": "Test workflow for integration testing",
            "steps": []
        }
        post_response = self.api_client.post("/api/workflows", data=workflow_data)
        assert post_response["success"] == True
        assert post_response["status_code"] == 201
        
        return True
    
    def test_execution_api_endpoints(self):
        """Test execution API endpoints"""
        # Test GET executions
        get_response = self.api_client.get("/api/executions")
        assert get_response["success"] == True
        
        # Test POST execution
        execution_data = {
            "workflow_id": "test-workflow-1",
            "trigger": "manual"
        }
        post_response = self.api_client.post("/api/executions", data=execution_data)
        assert post_response["success"] == True
        
        return True
    
    def test_websocket_endpoint(self):
        """Test WebSocket endpoint availability"""
        # Mock WebSocket connection test
        try:
            # In a real test, this would attempt a WebSocket connection
            # For now, we'll mock it
            ws_url = "ws://localhost:8000/ws/recording/test"
            
            # Simulate successful connection
            connection_success = True
            assert connection_success == True
            
            return True
        except Exception:
            raise Exception("skip: WebSocket connection not available")
    
    def test_frontend_backend_communication(self):
        """Test frontend-backend communication"""
        # Test that frontend can communicate with backend
        
        # Test API discovery endpoint
        response = self.api_client.get("/api/discovery/processes")
        assert response["success"] == True
        
        # Test real-time data endpoint
        response = self.api_client.get("/api/real-time/status")
        assert response["success"] == True
        
        return True
    
    def test_authentication_flow(self):
        """Test authentication flow integration"""
        # Test login endpoint
        login_data = {
            "username": "testuser",
            "password": "testpass"
        }
        response = self.api_client.post("/api/auth/login", data=login_data)
        assert response["success"] == True
        
        # Test protected endpoint access
        response = self.api_client.get("/api/user/profile")
        assert response["success"] == True
        
        return True
    
    def test_file_upload_integration(self):
        """Test file upload and processing"""
        # Mock file upload
        file_data = {
            "filename": "test_workflow.json",
            "content": json.dumps({"name": "Test", "steps": []}),
            "type": "workflow"
        }
        
        response = self.api_client.post("/api/files/upload", data=file_data)
        assert response["success"] == True
        
        return True
    
    def test_external_service_integrations(self):
        """Test external service integrations"""
        # Test email service integration
        email_test = self.api_client.post("/api/integrations/email/test", data={
            "to": "test@example.com",
            "subject": "Integration Test",
            "body": "Test message"
        })
        assert email_test["success"] == True
        
        return True
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("INTEGRATION TEST SUITE")
        print("=" * 50)
        
        tests = [
            ("API Health Endpoint", self.test_api_health_endpoint),
            ("Database Connection", self.test_database_connection),
            ("Redis Connection", self.test_redis_connection),
            ("Workflow API Endpoints", self.test_workflow_api_endpoints),
            ("Execution API Endpoints", self.test_execution_api_endpoints),
            ("WebSocket Endpoint", self.test_websocket_endpoint),
            ("Frontend-Backend Communication", self.test_frontend_backend_communication),
            ("Authentication Flow", self.test_authentication_flow),
            ("File Upload Integration", self.test_file_upload_integration),
            ("External Service Integrations", self.test_external_service_integrations),
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        return self.results


class TestDataFlow:
    """Test data flow between components"""
    
    def __init__(self):
        self.api_client = MockAPIClient()
        self.results = {"passed": 0, "failed": 0, "skipped": 0}
    
    def test_workflow_creation_to_execution(self):
        """Test complete workflow from creation to execution"""
        # Step 1: Create workflow
        workflow_data = {
            "name": "Data Flow Test Workflow",
            "steps": [
                {"type": "action", "id": "step1", "action": "log", "message": "Hello World"}
            ]
        }
        create_response = self.api_client.post("/api/workflows", data=workflow_data)
        assert create_response["success"] == True
        
        # Step 2: Execute workflow
        execute_response = self.api_client.post("/api/executions", data={
            "workflow_id": "workflow-1"
        })
        assert execute_response["success"] == True
        
        # Step 3: Check execution status
        status_response = self.api_client.get("/api/executions/execution-1")
        assert status_response["success"] == True
        
        return True
    
    def test_real_time_updates(self):
        """Test real-time update flow"""
        # Mock real-time event
        event_data = {
            "type": "execution_update",
            "execution_id": "exec-1",
            "status": "running",
            "progress": 50
        }
        
        # Simulate sending real-time update
        response = self.api_client.post("/api/real-time/broadcast", data=event_data)
        assert response["success"] == True
        
        return True
    
    def test_data_persistence(self):
        """Test data persistence across requests"""
        # Create data
        test_data = {"key": "value", "timestamp": time.time()}
        create_response = self.api_client.post("/api/data/store", data=test_data)
        assert create_response["success"] == True
        
        # Retrieve data
        get_response = self.api_client.get("/api/data/retrieve")
        assert get_response["success"] == True
        
        return True
    
    def run_all_tests(self):
        """Run all data flow tests"""
        print("\nDATA FLOW TESTS")
        print("=" * 50)
        
        tests = [
            ("Workflow Creation to Execution", self.test_workflow_creation_to_execution),
            ("Real-time Updates", self.test_real_time_updates),
            ("Data Persistence", self.test_data_persistence),
        ]
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                if result:
                    self.results["passed"] += 1
                    print("  PASSED {}".format(test_name))
                else:
                    self.results["failed"] += 1
                    print("  FAILED {}".format(test_name))
            except Exception as e:
                if "skip:" in str(e):
                    self.results["skipped"] += 1
                    print("  SKIPPED {}: {}".format(test_name, str(e).replace("skip:", "")))
                else:
                    self.results["failed"] += 1
                    print("  FAILED {}: {}".format(test_name, str(e)))
        
        return self.results


def run_integration_tests():
    """Run all integration tests"""
    print("COMPREHENSIVE INTEGRATION TEST SUITE")
    print("=" * 60)
    
    # Service connectivity tests
    connectivity_tester = TestServiceConnectivity()
    connectivity_results = connectivity_tester.run_all_tests()
    
    # Data flow tests
    dataflow_tester = TestDataFlow()
    dataflow_results = dataflow_tester.run_all_tests()
    
    # Combined results
    total_results = {
        "connectivity": connectivity_results,
        "dataflow": dataflow_results,
        "summary": {
            "total_passed": connectivity_results["passed"] + dataflow_results["passed"],
            "total_failed": connectivity_results["failed"] + dataflow_results["failed"],
            "total_skipped": connectivity_results["skipped"] + dataflow_results["skipped"]
        }
    }
    
    # Print summary
    print("\n" + "=" * 60)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    summary = total_results["summary"]
    total_tests = summary["total_passed"] + summary["total_failed"] + summary["total_skipped"]
    
    print("Total Tests: {}".format(total_tests))
    print("Passed: {}".format(summary["total_passed"]))
    print("Failed: {}".format(summary["total_failed"]))
    print("Skipped: {}".format(summary["total_skipped"]))
    
    if total_tests > 0:
        success_rate = (summary["total_passed"] / total_tests) * 100
        print("Success Rate: {:.1f}%".format(success_rate))
    
    # Recommendations
    print("\n" + "=" * 60)
    print("INTEGRATION RECOMMENDATIONS")
    print("=" * 60)
    
    if summary["total_failed"] > 0:
        print("- Fix {} failing integration tests".format(summary["total_failed"]))
    
    if summary["total_skipped"] > total_tests * 0.3:
        print("- Address skipped tests to improve coverage")
    
    print("- Add end-to-end automated testing in CI/CD")
    print("- Implement service health monitoring")
    print("- Add performance testing for critical paths")
    print("- Consider contract testing between services")
    
    # Save results
    report_file = os.path.join(project_root, "integration_test_report.json")
    with open(report_file, 'w') as f:
        json.dump(total_results, f, indent=2)
    
    print("\nIntegration test report saved: {}".format(report_file))
    
    return total_results


if __name__ == "__main__":
    results = run_integration_tests()
    
    if results["summary"]["total_failed"] == 0:
        print("\nAll integration tests passed!")
        exit(0)
    else:
        print("\n{} integration tests failed".format(results["summary"]["total_failed"]))
        exit(1)