#!/usr/bin/env python3
"""
Synthetic Canary Workflows for Monitoring
========================================

This module implements synthetic canary workflows that run continuously
to monitor system health and performance. These workflows simulate real
user scenarios and provide early warning of system issues.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import requests
import schedule
from pathlib import Path

logger = logging.getLogger(__name__)


class CanaryStatus(Enum):
    """Status of canary workflow execution"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class CanaryResult:
    """Result of a canary workflow execution"""
    workflow_id: str
    execution_id: str
    status: CanaryStatus
    start_time: float
    end_time: Optional[float] = None
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        return result


class CanaryWorkflow:
    """Base class for canary workflows"""
    
    def __init__(self, workflow_id: str, name: str, description: str):
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.timeout = 300  # 5 minutes default timeout
        
    async def execute(self, context: Dict[str, Any]) -> CanaryResult:
        """Execute the canary workflow"""
        start_time = time.time()
        
        try:
            result = await self._execute_workflow(context)
            end_time = time.time()
            
            return CanaryResult(
                workflow_id=self.workflow_id,
                execution_id=context.get('execution_id', 'unknown'),
                status=CanaryStatus.SUCCESS,
                start_time=start_time,
                end_time=end_time,
                response_time=end_time - start_time,
                metrics=result
            )
            
        except asyncio.TimeoutError:
            return CanaryResult(
                workflow_id=self.workflow_id,
                execution_id=context.get('execution_id', 'unknown'),
                status=CanaryStatus.TIMEOUT,
                start_time=start_time,
                end_time=time.time(),
                error_message="Workflow execution timed out"
            )
        except Exception as e:
            return CanaryResult(
                workflow_id=self.workflow_id,
                execution_id=context.get('execution_id', 'unknown'),
                status=CanaryStatus.ERROR,
                start_time=start_time,
                end_time=time.time(),
                error_message=str(e)
            )
    
    async def _execute_workflow(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclasses to implement specific workflow logic"""
        raise NotImplementedError


class APIHealthCanary(CanaryWorkflow):
    """Canary workflow for API health monitoring"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(
            workflow_id="api_health_canary",
            name="API Health Check",
            description="Monitors core API endpoints for availability and performance"
        )
        self.base_url = base_url
        self.endpoints = [
            {"path": "/health", "method": "GET", "expected_status": 200},
            {"path": "/api/workflows", "method": "GET", "expected_status": 200},
            {"path": "/api/metrics", "method": "GET", "expected_status": 200},
        ]
        
    async def _execute_workflow(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API health checks"""
        results = []
        
        for endpoint in self.endpoints:
            endpoint_start = time.time()
            
            try:
                response = requests.request(
                    method=endpoint["method"],
                    url=f"{self.base_url}{endpoint['path']}",
                    timeout=30,
                    headers=context.get('headers', {})
                )
                
                endpoint_time = time.time() - endpoint_start
                
                result = {
                    "endpoint": endpoint["path"],
                    "method": endpoint["method"],
                    "status_code": response.status_code,
                    "response_time": endpoint_time,
                    "success": response.status_code == endpoint["expected_status"],
                    "content_length": len(response.content) if response.content else 0
                }
                
                results.append(result)
                
                # Validate response format for JSON endpoints
                if endpoint["path"].startswith("/api/") and response.content:
                    try:
                        response.json()
                        result["valid_json"] = True
                    except json.JSONDecodeError:
                        result["valid_json"] = False
                        result["success"] = False
                        
            except Exception as e:
                results.append({
                    "endpoint": endpoint["path"],
                    "method": endpoint["method"],
                    "error": str(e),
                    "response_time": time.time() - endpoint_start,
                    "success": False
                })
        
        return {
            "endpoint_results": results,
            "total_endpoints": len(self.endpoints),
            "successful_endpoints": sum(1 for r in results if r.get("success", False)),
            "average_response_time": sum(r.get("response_time", 0) for r in results) / len(results)
        }


class WorkflowExecutionCanary(CanaryWorkflow):
    """Canary workflow for testing end-to-end workflow execution"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(
            workflow_id="workflow_execution_canary",
            name="Workflow Execution Test",
            description="Tests complete workflow creation and execution pipeline"
        )
        self.base_url = base_url
        
    async def _execute_workflow(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow execution test"""
        workflow_data = {
            "name": f"Canary Test Workflow {datetime.now().isoformat()}",
            "description": "Synthetic canary workflow for monitoring",
            "steps": [
                {
                    "id": "step1",
                    "type": "data_processor",
                    "params": {
                        "operation": "test",
                        "data": {"canary": True, "timestamp": time.time()}
                    }
                }
            ],
            "tags": ["canary", "synthetic", "monitoring"]
        }
        
        headers = context.get('headers', {})
        
        # Step 1: Create workflow
        create_start = time.time()
        create_response = requests.post(
            f"{self.base_url}/api/workflows",
            json=workflow_data,
            headers=headers,
            timeout=30
        )
        create_time = time.time() - create_start
        
        if create_response.status_code not in [200, 201]:
            raise Exception(f"Failed to create workflow: {create_response.status_code}")
        
        workflow_id = create_response.json().get("id")
        
        # Step 2: Execute workflow
        execute_start = time.time()
        execute_response = requests.post(
            f"{self.base_url}/api/executions",
            json={"workflow_id": workflow_id, "context": {"canary": True}},
            headers=headers,
            timeout=30
        )
        execute_time = time.time() - execute_start
        
        if execute_response.status_code not in [200, 201]:
            raise Exception(f"Failed to execute workflow: {execute_response.status_code}")
        
        execution_id = execute_response.json().get("id")
        
        # Step 3: Monitor execution status
        monitor_start = time.time()
        max_wait = 120  # 2 minutes max wait
        
        while time.time() - monitor_start < max_wait:
            status_response = requests.get(
                f"{self.base_url}/api/executions/{execution_id}",
                headers=headers,
                timeout=30
            )
            
            if status_response.status_code != 200:
                raise Exception(f"Failed to get execution status: {status_response.status_code}")
            
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status in ["completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(2)
        
        monitor_time = time.time() - monitor_start
        
        # Step 4: Cleanup (optional)
        try:
            requests.delete(
                f"{self.base_url}/api/workflows/{workflow_id}",
                headers=headers,
                timeout=30
            )
        except:
            pass  # Cleanup is optional
        
        return {
            "workflow_creation_time": create_time,
            "workflow_execution_time": execute_time,
            "execution_monitoring_time": monitor_time,
            "total_time": create_time + execute_time + monitor_time,
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "final_status": status,
            "execution_successful": status == "completed"
        }


class DatabaseCanary(CanaryWorkflow):
    """Canary workflow for database connectivity and performance"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(
            workflow_id="database_canary",
            name="Database Health Check",
            description="Monitors database connectivity and performance"
        )
        self.base_url = base_url
        
    async def _execute_workflow(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database health checks"""
        headers = context.get('headers', {})
        
        # Test database connectivity through API
        db_start = time.time()
        
        # Test read operations
        read_response = requests.get(
            f"{self.base_url}/api/workflows?limit=1",
            headers=headers,
            timeout=30
        )
        read_time = time.time() - db_start
        
        if read_response.status_code != 200:
            raise Exception(f"Database read test failed: {read_response.status_code}")
        
        # Test write operations (create a test workflow)
        write_start = time.time()
        test_workflow = {
            "name": f"DB Test Workflow {datetime.now().isoformat()}",
            "description": "Database connectivity test",
            "steps": [{"id": "test", "type": "noop"}],
            "tags": ["canary", "db_test"]
        }
        
        write_response = requests.post(
            f"{self.base_url}/api/workflows",
            json=test_workflow,
            headers=headers,
            timeout=30
        )
        write_time = time.time() - write_start
        
        if write_response.status_code not in [200, 201]:
            raise Exception(f"Database write test failed: {write_response.status_code}")
        
        # Cleanup
        workflow_id = write_response.json().get("id")
        if workflow_id:
            try:
                requests.delete(
                    f"{self.base_url}/api/workflows/{workflow_id}",
                    headers=headers,
                    timeout=30
                )
            except:
                pass
        
        return {
            "database_read_time": read_time,
            "database_write_time": write_time,
            "total_database_time": read_time + write_time,
            "read_successful": True,
            "write_successful": True
        }


class AuthenticationCanary(CanaryWorkflow):
    """Canary workflow for authentication system monitoring"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(
            workflow_id="authentication_canary",
            name="Authentication System Check",
            description="Monitors authentication endpoints and token handling"
        )
        self.base_url = base_url
        
    async def _execute_workflow(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute authentication system checks"""
        
        # Test token validation
        token_start = time.time()
        
        # Test with valid token (if provided)
        if context.get('auth_token'):
            token_response = requests.get(
                f"{self.base_url}/api/workflows",
                headers={"Authorization": f"Bearer {context['auth_token']}"},
                timeout=30
            )
            token_time = time.time() - token_start
            
            token_valid = token_response.status_code == 200
        else:
            token_valid = None
            token_time = 0
        
        # Test without token (should fail)
        notoken_start = time.time()
        notoken_response = requests.get(
            f"{self.base_url}/api/workflows",
            timeout=30
        )
        notoken_time = time.time() - notoken_start
        
        # Should return 401 or 403
        auth_blocking_works = notoken_response.status_code in [401, 403]
        
        return {
            "token_validation_time": token_time,
            "token_valid": token_valid,
            "auth_blocking_time": notoken_time,
            "auth_blocking_works": auth_blocking_works,
            "total_auth_time": token_time + notoken_time
        }


class CanaryOrchestrator:
    """Orchestrates and manages canary workflow execution"""
    
    def __init__(self, base_url: str = "http://localhost:8000", auth_token: str = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.canaries: List[CanaryWorkflow] = []
        self.results: List[CanaryResult] = []
        self.running = False
        
        # Initialize canaries
        self.canaries = [
            APIHealthCanary(base_url),
            WorkflowExecutionCanary(base_url),
            DatabaseCanary(base_url),
            AuthenticationCanary(base_url)
        ]
        
        # Setup results storage
        self.results_dir = Path("monitoring/canary_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    async def run_all_canaries(self) -> List[CanaryResult]:
        """Run all canary workflows"""
        logger.info("Starting canary workflow execution")
        
        context = {
            'execution_id': f"canary_{int(time.time())}",
            'timestamp': datetime.now().isoformat(),
            'headers': {}
        }
        
        if self.auth_token:
            context['headers']['Authorization'] = f"Bearer {self.auth_token}"
            context['auth_token'] = self.auth_token
        
        results = []
        
        for canary in self.canaries:
            logger.info(f"Executing canary: {canary.name}")
            
            try:
                result = await canary.execute(context)
                results.append(result)
                
                logger.info(f"Canary {canary.name} completed: {result.status.value}")
                
            except Exception as e:
                logger.error(f"Canary {canary.name} failed: {e}")
                
                error_result = CanaryResult(
                    workflow_id=canary.workflow_id,
                    execution_id=context['execution_id'],
                    status=CanaryStatus.ERROR,
                    start_time=time.time(),
                    end_time=time.time(),
                    error_message=str(e)
                )
                results.append(error_result)
        
        # Store results
        self.results.extend(results)
        self.save_results(results)
        
        # Generate alerts if needed
        self.check_alerts(results)
        
        return results
    
    def save_results(self, results: List[CanaryResult]):
        """Save canary results to disk"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"canary_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump([result.to_dict() for result in results], f, indent=2)
        
        logger.info(f"Canary results saved to: {results_file}")
    
    def check_alerts(self, results: List[CanaryResult]):
        """Check for alert conditions and send notifications"""
        failed_canaries = [r for r in results if r.status != CanaryStatus.SUCCESS]
        
        if failed_canaries:
            logger.warning(f"Canary failures detected: {len(failed_canaries)}")
            
            for result in failed_canaries:
                logger.warning(f"Failed canary: {result.workflow_id} - {result.error_message}")
            
            # Send alerts (implement notification logic here)
            self.send_alert(failed_canaries)
    
    def send_alert(self, failed_results: List[CanaryResult]):
        """Send alerts for failed canaries"""
        # Implement alert sending logic (email, Slack, PagerDuty, etc.)
        alert_message = f"Canary Alert: {len(failed_results)} canaries failed"
        logger.critical(alert_message)
        
        # Example: Send to monitoring system
        # self.send_to_monitoring_system(alert_message, failed_results)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status based on recent canary results"""
        if not self.results:
            return {"status": "unknown", "reason": "No canary results available"}
        
        # Check last hour results
        recent_cutoff = time.time() - 3600  # 1 hour ago
        recent_results = [r for r in self.results if r.start_time > recent_cutoff]
        
        if not recent_results:
            return {"status": "stale", "reason": "No recent canary results"}
        
        # Calculate health metrics
        total_recent = len(recent_results)
        successful_recent = sum(1 for r in recent_results if r.status == CanaryStatus.SUCCESS)
        
        success_rate = successful_recent / total_recent if total_recent > 0 else 0
        
        if success_rate >= 0.9:
            status = "healthy"
        elif success_rate >= 0.7:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "success_rate": success_rate,
            "total_canaries": total_recent,
            "successful_canaries": successful_recent,
            "last_run": max(r.start_time for r in recent_results)
        }
    
    def start_scheduled_execution(self):
        """Start scheduled canary execution"""
        logger.info("Starting scheduled canary execution")
        
        # Schedule canary runs
        schedule.every(5).minutes.do(self.run_canaries_sync)
        
        self.running = True
        
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def run_canaries_sync(self):
        """Synchronous wrapper for async canary execution"""
        try:
            asyncio.run(self.run_all_canaries())
        except Exception as e:
            logger.error(f"Scheduled canary execution failed: {e}")
    
    def stop(self):
        """Stop scheduled execution"""
        self.running = False
        logger.info("Stopping canary orchestrator")


def main():
    """Main entry point for canary monitoring"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run synthetic canary workflows")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--token", help="Authentication token")
    parser.add_argument("--schedule", action="store_true", help="Run on schedule")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    orchestrator = CanaryOrchestrator(args.url, args.token)
    
    if args.once:
        # Run once and exit
        results = asyncio.run(orchestrator.run_all_canaries())
        
        success_count = sum(1 for r in results if r.status == CanaryStatus.SUCCESS)
        total_count = len(results)
        
        print(f"Canary execution completed: {success_count}/{total_count} successful")
        
        if success_count == total_count:
            return 0
        else:
            return 1
    
    elif args.schedule:
        # Run on schedule
        try:
            orchestrator.start_scheduled_execution()
        except KeyboardInterrupt:
            orchestrator.stop()
            return 0
    
    else:
        # Run once by default
        results = asyncio.run(orchestrator.run_all_canaries())
        
        success_count = sum(1 for r in results if r.status == CanaryStatus.SUCCESS)
        total_count = len(results)
        
        print(f"Canary execution completed: {success_count}/{total_count} successful")
        
        return 0 if success_count == total_count else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())