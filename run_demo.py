#!/usr/bin/env python3
"""
AI Engine Demo Script
=====================

This script demonstrates the core functionality of the AI Engine by:
1. Testing individual workflow runners
2. Verifying database connectivity
3. Creating and executing sample workflows
4. Displaying execution results

Run this script with: python run_demo.py
"""

import os
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any, List

# Import AI Engine components
from ai_engine.workflow_runners import (
    ShellRunner, 
    HttpRunner, 
    LLMRunner, 
    ApprovalRunner,
    DecisionRunner,
    RunnerFactory
)
from ai_engine.workflow_engine import WorkflowEngine, execute_workflow_by_id
from ai_engine.database import engine, create_db_and_tables, get_session
from ai_engine.models.workflow import Workflow
from ai_engine.models.execution import Execution
from sqlmodel import Session, select, SQLModel

# Console formatting helpers
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD} {text} {Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")

def print_subheader(text):
    print(f"\n{Colors.BLUE}{Colors.BOLD} {text} {Colors.ENDC}")
    print(f"{Colors.BLUE}{'-' * (len(text) + 2)}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")

def print_json(data):
    print(f"{Colors.YELLOW}{json.dumps(data, indent=2)}{Colors.ENDC}")

def print_step(step, total):
    print(f"{Colors.BOLD}[{step}/{total}]{Colors.ENDC}", end=" ")

# Setup and initialization
def setup_database():
    """Initialize the database and create tables if they don't exist."""
    print_info("Setting up database...")
    create_db_and_tables()
    print_success("Database initialized")

# Test individual runners
def test_shell_runner():
    """Test the ShellRunner with a simple command."""
    print_subheader("Testing ShellRunner")
    
    # Simple echo command
    print_info("Running 'echo Hello, AI Engine!'...")
    runner = ShellRunner("demo_shell", {"command": "echo Hello, AI Engine!", "timeout": 5})
    result = runner.execute()
    
    if result["success"]:
        print_success("Command executed successfully")
        print_info(f"Output: {result['result']['stdout'].strip()}")
    else:
        print_error(f"Command failed: {result.get('error', 'Unknown error')}")
    
    return result["success"]

def test_http_runner():
    """Test the HttpRunner with a GET request to a public API."""
    print_subheader("Testing HttpRunner")
    
    print_info("Making GET request to httpbin.org/json...")
    runner = HttpRunner("demo_http", {
        "url": "https://httpbin.org/json",
        "method": "GET",
        "headers": {"Accept": "application/json"}
    })
    result = runner.execute()
    
    if result["success"]:
        print_success(f"HTTP request successful (Status: {result['result']['status_code']})")
        print_info("Response preview:")
        # Show just a preview of the response
        data = result['result']['json']
        print_json({k: data[k] for k in list(data.keys())[:2]})
    else:
        print_error(f"HTTP request failed: {result.get('error', 'Unknown error')}")
    
    return result["success"]

def test_llm_runner():
    """Test the LLMRunner with a simple prompt."""
    print_subheader("Testing LLMRunner")
    
    # Check if OpenAI API key is available
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print_info("No OpenAI API key found in environment. Using mock response.")
        # Create a mock result
        result = {
            "success": True,
            "result": {
                "content": "This is a mock response from the LLM runner.",
                "model": "gpt-3.5-turbo (mock)",
                "usage": {"total_tokens": 15, "prompt_tokens": 10, "completion_tokens": 5}
            }
        }
    else:
        print_info("Sending prompt to OpenAI...")
        runner = LLMRunner("demo_llm", {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "prompt": "Explain what an AI workflow engine does in one sentence."
        })
        result = runner.execute()
    
    if result["success"]:
        print_success("LLM request successful")
        print_info("Response:")
        print(f"  {Colors.YELLOW}\"{result['result']['content']}\"{Colors.ENDC}")
    else:
        print_error(f"LLM request failed: {result.get('error', 'Unknown error')}")
    
    return result["success"]

def test_decision_runner():
    """Test the DecisionRunner with a simple condition."""
    print_subheader("Testing DecisionRunner")
    
    print_info("Evaluating decision condition...")
    runner = DecisionRunner("demo_decision", {
        "conditions": [
            {"expression": "10 > 5", "target": "path_a"},
            {"expression": "20 < 10", "target": "path_b"}
        ],
        "default": "default_path"
    })
    result = runner.execute()
    
    if result["success"]:
        print_success("Decision evaluation successful")
        print_info(f"Selected path: {result['result']['target']}")
    else:
        print_error(f"Decision evaluation failed: {result.get('error', 'Unknown error')}")
    
    return result["success"]

def test_approval_runner():
    """Test the ApprovalRunner with auto-approval."""
    print_subheader("Testing ApprovalRunner")
    
    print_info("Creating approval request (with auto-approval for demo)...")
    runner = ApprovalRunner("demo_approval", {
        "title": "Demo Approval",
        "description": "This is a test approval for the demo script",
        "approvers": ["demo@example.com"],
        "wait": False  # Don't wait for actual approval
    })
    result = runner.execute()
    
    if result["success"]:
        print_success("Approval request created successfully")
        print_info(f"Approval ID: {result['result'].get('approval_id', 'N/A')}")
        print_info("Auto-approved for demo purposes")
    else:
        print_error(f"Approval request failed: {result.get('error', 'Unknown error')}")
    
    return result["success"]

# Create and execute a sample workflow
def create_sample_workflow(session):
    """Create a sample multi-step workflow in the database."""
    print_subheader("Creating Sample Workflow")
    
    # Define a multi-step workflow
    workflow_data = {
        "name": "Demo Workflow",
        "description": "A sample workflow created by the demo script",
        "status": "active",
        "created_by": "demo_user",
        "steps": [
            {
                "id": "step1",
                "type": "shell",
                "params": {
                    "command": "echo 'Step 1: Starting workflow'",
                    "timeout": 5
                }
            },
            {
                "id": "step2",
                "type": "http",
                "params": {
                    "url": "https://httpbin.org/get",
                    "method": "GET"
                }
            },
            {
                "id": "decision",
                "type": "decision",
                "params": {
                    "conditions": [
                        {"expression": "true", "target": "step3a"}
                    ],
                    "default": "step3b"
                }
            },
            {
                "id": "step3a",
                "type": "shell",
                "params": {
                    "command": "echo 'Step 3A: Primary path'",
                    "timeout": 5
                }
            },
            {
                "id": "step3b",
                "type": "shell",
                "params": {
                    "command": "echo 'Step 3B: Alternative path (should not run)'",
                    "timeout": 5
                }
            },
            {
                "id": "final",
                "type": "shell",
                "params": {
                    "command": "echo 'Final Step: Workflow completed at $(date)'",
                    "timeout": 5
                }
            }
        ]
    }
    
    # Create the workflow in the database
    workflow = Workflow(**workflow_data)
    session.add(workflow)
    session.commit()
    session.refresh(workflow)
    
    print_success(f"Created workflow with ID: {workflow.id}")
    print_info(f"Name: {workflow.name}")
    print_info(f"Steps: {len(workflow.steps)}")
    
    return workflow.id

def execute_sample_workflow(workflow_id):
    """Execute the sample workflow and display results."""
    print_subheader(f"Executing Workflow (ID: {workflow_id})")
    
    print_info("Starting workflow execution...")
    start_time = time.time()
    
    # Execute the workflow
    execution_id = execute_workflow_by_id(workflow_id)
    
    # Get the execution results
    with Session(engine) as session:
        execution = session.get(Execution, execution_id)
        
        # Wait for execution to complete (with timeout)
        timeout = 30  # seconds
        elapsed = 0
        while execution.status in ["running", "pending"] and elapsed < timeout:
            print_info(f"Execution status: {execution.status}... waiting")
            time.sleep(2)
            elapsed += 2
            session.refresh(execution)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if execution.status == "completed":
            print_success(f"Workflow execution completed in {duration:.2f} seconds")
            
            # Display results for each step
            results = execution.result.get("results", {})
            step_count = len(results)
            
            print_info(f"Execution steps ({step_count}):")
            for i, (step_id, step_result) in enumerate(results.items(), 1):
                success = step_result.get("success", False)
                step_type = step_id.split("_")[0] if "_" in step_id else step_id
                
                if success:
                    print(f"  {Colors.GREEN}✓{Colors.ENDC} [{i}/{step_count}] {step_id} ({step_type})")
                    
                    # Show specific output based on step type
                    if "shell" in step_id:
                        stdout = step_result.get("result", {}).get("stdout", "").strip()
                        if stdout:
                            print(f"    {Colors.YELLOW}Output: {stdout}{Colors.ENDC}")
                    elif "decision" in step_id:
                        target = step_result.get("result", {}).get("target", "unknown")
                        print(f"    {Colors.YELLOW}Selected path: {target}{Colors.ENDC}")
                else:
                    print(f"  {Colors.RED}✗{Colors.ENDC} [{i}/{step_count}] {step_id} ({step_type})")
                    error = step_result.get("error", "Unknown error")
                    print(f"    {Colors.RED}Error: {error}{Colors.ENDC}")
        else:
            print_error(f"Workflow execution failed or timed out. Status: {execution.status}")
            if execution.result and "error" in execution.result:
                print_error(f"Error: {execution.result['error']}")
        
        return execution.status == "completed"

def main():
    """Main demo function."""
    print_header("AI ENGINE DEMONSTRATION")
    print(f"{Colors.BOLD}Date:{Colors.ENDC} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Colors.BOLD}Python:{Colors.ENDC} {sys.version.split()[0]}")
    
    try:
        # Initialize database
        setup_database()
        
        # Test individual runners
        print_header("1. TESTING WORKFLOW RUNNERS")
        runners_success = all([
            test_shell_runner(),
            test_http_runner(),
            test_llm_runner(),
            test_decision_runner(),
            test_approval_runner()
        ])
        
        # Create and execute sample workflow
        print_header("2. SAMPLE WORKFLOW EXECUTION")
        with Session(engine) as session:
            workflow_id = create_sample_workflow(session)
            workflow_success = execute_sample_workflow(workflow_id)
        
        # Summary
        print_header("DEMO SUMMARY")
        if runners_success:
            print_success("All workflow runners tested successfully")
        else:
            print_error("Some workflow runners had issues")
            
        if workflow_success:
            print_success("Sample workflow executed successfully")
        else:
            print_error("Sample workflow execution had issues")
            
        if runners_success and workflow_success:
            print_success("AI Engine is fully operational!")
            print_info("Ready to process workflows and automate tasks")
        else:
            print_error("AI Engine has some issues that need to be addressed")
            
    except Exception as e:
        print_error(f"Demo failed with error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
