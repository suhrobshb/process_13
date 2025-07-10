#!/usr/bin/env python3
"""
AI Engine Simple Demo
=====================

This script demonstrates the core functionality of the AI Engine by:
1. Setting up a SQLite database
2. Testing individual workflow runners
3. Showing successful execution results

Run this script with: python simple_demo.py
"""

import os
import sys
import json
from datetime import datetime

# Ensure we use SQLite for the demo
os.environ["DATABASE_URL"] = "sqlite:///demo.db"

# Import AI Engine components
from ai_engine.workflow_runners import (
    ShellRunner, 
    HttpRunner, 
    DecisionRunner
)
from ai_engine.database import create_db_and_tables

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
    print(f"\n{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * len(text)}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")

def print_json(data):
    print(f"{Colors.YELLOW}{json.dumps(data, indent=2)}{Colors.ENDC}")

def main():
    """Main demo function."""
    print_header("AI ENGINE DEMONSTRATION")
    print(f"{Colors.BOLD}Date:{Colors.ENDC} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Colors.BOLD}Python:{Colors.ENDC} {sys.version.split()[0]}")
    
    try:
        # Initialize database
        print_info("Setting up database...")
        create_db_and_tables()
        print_success("Database initialized")
        
        # Test ShellRunner
        print_header("1. SHELL COMMAND EXECUTION")
        print_info("Running 'echo Hello from AI Engine!'...")
        shell_runner = ShellRunner("demo_shell", {"command": "echo Hello from AI Engine!", "timeout": 5})
        shell_result = shell_runner.execute()
        
        if shell_result["success"]:
            print_success("Shell command executed successfully")
            print_info(f"Output: {shell_result['result']['stdout'].strip()}")
        else:
            print_error(f"Shell command failed: {shell_result.get('error', 'Unknown error')}")
        
        # Test HttpRunner
        print_header("2. HTTP REQUEST")
        print_info("Making GET request to httpbin.org/get...")
        http_runner = HttpRunner("demo_http", {
            "url": "https://httpbin.org/get",
            "method": "GET",
            "headers": {"Accept": "application/json"}
        })
        http_result = http_runner.execute()
        
        if http_result["success"]:
            print_success(f"HTTP request successful (Status: {http_result['result']['status_code']})")
            print_info("Response headers:")
            headers = http_result['result'].get('headers', {})
            if headers:
                for key, value in list(headers.items())[:3]:  # Show first 3 headers
                    print(f"  {key}: {value}")
        else:
            print_error(f"HTTP request failed: {http_result.get('error', 'Unknown error')}")
        
        # Test DecisionRunner
        print_header("3. DECISION LOGIC")
        print_info("Evaluating decision conditions...")
        decision_runner = DecisionRunner("demo_decision", {
            "conditions": [
                {"expression": "10 > 5", "target": "path_a"},
                {"expression": "20 < 10", "target": "path_b"}
            ],
            "default": "default_path"
        })
        decision_result = decision_runner.execute()
        
        if decision_result["success"]:
            print_success("Decision evaluation successful")
            print_info(f"Selected path: {decision_result['result']['target']}")
            print_info(f"Evaluation: 10 > 5 is {10 > 5}, so path_a was selected")
        else:
            print_error(f"Decision evaluation failed: {decision_result.get('error', 'Unknown error')}")
        
        # Summary
        print_header("AI ENGINE STATUS")
        all_success = all([
            shell_result["success"],
            http_result["success"],
            decision_result["success"]
        ])
        
        if all_success:
            print_success("All components tested successfully!")
            print_success("AI Engine is fully operational!")
            print_info("Ready to process workflows and automate tasks")
        else:
            print_error("Some components had issues")
            
    except Exception as e:
        print_error(f"Demo failed with error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
