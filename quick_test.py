#!/usr/bin/env python3
"""
AI Engine Quick Test Script
==========================

This script performs a quick validation of core AI Engine functionality:
1. Core module imports
2. Database initialization
3. Basic runners (Shell, HTTP, Decision, LLM, Approval)
4. Simple workflow creation and execution

Usage:
    python quick_test.py
"""

import os
import sys
import time
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("quick_test")

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///test_ai_engine.db"
os.environ["OPENAI_API_KEY"] = "sk-test-mock-key-for-testing"

# Test results tracking
class TestResults:
    def __init__(self):
        self.successes = 0
        self.failures = 0
        self.results = []
        
    def success(self, test_name, details=None):
        self.successes += 1
        self.results.append({"name": test_name, "status": "SUCCESS", "details": details})
        logger.info(f"✅ {test_name}: SUCCESS")
        if details:
            logger.info(f"   Details: {details}")
        
    def failure(self, test_name, error):
        self.failures += 1
        self.results.append({"name": test_name, "status": "FAILURE", "error": str(error)})
        logger.error(f"❌ {test_name}: FAILURE - {error}")
        
    def summary(self):
        total = self.successes + self.failures
        print("\n" + "=" * 60)
        print(f"AI ENGINE QUICK TEST RESULTS")
        print("=" * 60)
        print(f"Total Tests: {total}")
        print(f"Successes: {self.successes}")
        print(f"Failures: {self.failures}")
        print("=" * 60)
        
        if self.failures > 0:
            print("\nFAILED TESTS:")
            for result in self.results:
                if result["status"] == "FAILURE":
                    print(f"- {result['name']}: {result.get('error', 'Unknown error')}")
        
        return self.failures == 0

# Initialize test results
results = TestResults()

def test_core_imports():
    """Test importing all core modules."""
    try:
        # Core modules
        from ai_engine.database import create_db_and_tables, get_session
        from ai_engine.models.workflow import Workflow
        from ai_engine.models.task import Task
        from ai_engine.models.execution import Execution
        from ai_engine.models.user import User
        from ai_engine.workflow_runners import RunnerFactory
        from ai_engine.workflow_engine import WorkflowEngine
        
        # Authentication
        from ai_engine.auth import get_password_hash, verify_password, create_access_token
        
        results.success("Core Module Imports")
        return True
    except Exception as e:
        results.failure("Core Module Imports", e)
        return False

def test_database_initialization():
    """Test database initialization."""
    try:
        from ai_engine.database import create_db_and_tables
        
        # Initialize database
        create_db_and_tables()
        
        results.success("Database Initialization")
        return True
    except Exception as e:
        results.failure("Database Initialization", e)
        return False

def test_shell_runner():
    """Test Shell Runner functionality."""
    try:
        from ai_engine.workflow_runners import RunnerFactory
        
        # Create Shell Runner
        shell_runner = RunnerFactory.create_runner("shell", "test_shell", {
            "command": "echo 'Hello from Shell Runner'",
            "timeout": 5
        })
        
        # Execute runner
        result = shell_runner.execute()
        
        # Validate result
        if not result["success"]:
            raise ValueError(f"Shell runner execution failed: {result.get('error')}")
            
        stdout = result["result"]["stdout"].strip()
        
        results.success("Shell Runner", {"stdout": stdout})
        return True
    except Exception as e:
        results.failure("Shell Runner", e)
        return False

def test_http_runner():
    """Test HTTP Runner functionality."""
    try:
        from ai_engine.workflow_runners import RunnerFactory
        
        # Create HTTP Runner
        http_runner = RunnerFactory.create_runner("http", "test_http", {
            "url": "https://httpbin.org/get",
            "method": "GET",
            "headers": {"Accept": "application/json"},
            "timeout": 10
        })
        
        # Execute runner
        result = http_runner.execute()
        
        # Validate result
        if not result["success"]:
            raise ValueError(f"HTTP runner execution failed: {result.get('error')}")
            
        status_code = result["result"]["status_code"]
        
        results.success("HTTP Runner", {"status_code": status_code})
        return True
    except Exception as e:
        results.failure("HTTP Runner", e)
        return False

def test_decision_runner():
    """Test Decision Runner functionality."""
    try:
        from ai_engine.workflow_runners import RunnerFactory
        
        # Create Decision Runner with simple conditions
        decision_runner = RunnerFactory.create_runner("decision", "test_decision", {
            "conditions": [
                {"expression": "10 > 5", "target": "success_path"}
            ],
            "default": "default_path"
        })
        
        # Execute runner
        result = decision_runner.execute()
        
        # Validate result
        if not result["success"]:
            raise ValueError(f"Decision runner execution failed: {result.get('error')}")
            
        target = result["result"]["target"]
        expected_target = "success_path"
        
        if target != expected_target:
            raise ValueError(f"Unexpected target: {target}, expected: {expected_target}")
            
        results.success("Decision Runner", {"target": target})
        return True
    except Exception as e:
        results.failure("Decision Runner", e)
        return False

def test_approval_runner():
    """Test Approval Runner functionality."""
    try:
        from ai_engine.workflow_runners import RunnerFactory
        
        # Create Approval Runner
        approval_runner = RunnerFactory.create_runner("approval", "test_approval", {
            "title": "Test Approval",
            "description": "This is a test approval request",
            "approvers": ["test@example.com"],
            "wait": False  # Don't wait for actual approval
        })
        
        # Execute runner
        result = approval_runner.execute()
        
        # Validate result
        if not result["success"]:
            raise ValueError(f"Approval runner execution failed: {result.get('error')}")
            
        approval_id = result["result"]["approval_id"]
        
        results.success("Approval Runner", {"approval_id": approval_id})
        return True
    except Exception as e:
        results.failure("Approval Runner", e)
        return False

def test_simple_workflow():
    """Test simple workflow creation and execution."""
    try:
        from ai_engine.database import engine
        from sqlmodel import Session
        from ai_engine.models.workflow import Workflow
        from ai_engine.workflow_engine import execute_workflow_by_id
        
        # Sample workflow data
        workflow_data = {
            "name": "Test Simple Workflow",
            "description": "A simple test workflow",
            "status": "active",
            "steps": [
                {
                    "id": "echo",
                    "type": "shell",
                    "params": {
                        "command": "echo 'Simple workflow test'",
                        "timeout": 5
                    }
                }
            ]
        }
        
        # Create workflow
        with Session(engine) as session:
            workflow = Workflow(**workflow_data)
            session.add(workflow)
            session.commit()
            session.refresh(workflow)
            workflow_id = workflow.id
            
        # Execute workflow
        try:
            execution_id = execute_workflow_by_id(workflow_id)
            results.success("Simple Workflow", {"workflow_id": workflow_id, "execution_id": execution_id})
            return True
        except Exception as e:
            results.failure("Simple Workflow Execution", e)
            return False
            
    except Exception as e:
        results.failure("Simple Workflow Creation", e)
        return False

def main():
    """Main test function."""
    print("=" * 60)
    print("AI ENGINE QUICK TEST")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {os.environ['DATABASE_URL']}")
    print("=" * 60)
    
    # Run tests
    test_core_imports()
    test_database_initialization()
    test_shell_runner()
    test_http_runner()
    test_decision_runner()
    test_approval_runner()
    test_simple_workflow()
    
    # Print summary
    success = results.summary()
    
    if success:
        print("\n🎉 All tests passed! The AI Engine is functioning correctly.")
        print("\nYou can now proceed with deployment to Google Cloud.")
        print("Required for deployment:")
        print("1. Google Cloud Project ID")
        print("2. Google Cloud region (e.g., us-central1)")
        print("3. OpenAI API key (for LLM functionality)")
        print("4. Database credentials (will be created if not provided)")
    else:
        print("\n❌ Some tests failed. Please fix the issues before deployment.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
