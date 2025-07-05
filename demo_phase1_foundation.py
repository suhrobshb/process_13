#!/usr/bin/env python3
"""
AI Engine - Phase 1 Foundation Demo
===================================

This script provides a comprehensive demonstration of the "Core Foundation"
of the AI Engine, showcasing the "Digital Employee" concept.

It simulates the entire end-to-end process:
1.  **Recording**: Presents a mock raw data stream from the Recording Agent.
2.  **Learning**: A simplified AI analysis function converts the raw data into a
    structured, human-readable workflow with distinct action steps.
3.  **Execution**: The Workflow Engine executes the generated workflow, using the
    enhanced Desktop and Browser runners to perform the tasks.

This demo uses mocking for the GUI automation libraries (`pyautogui`, `playwright`)
so it can be run in any environment, including headless servers. The output will
clearly state which actions are being performed.

Usage:
    python demo_phase1_foundation.py
"""

import os
import json
import time
import logging
from unittest.mock import MagicMock, patch

# --- Setup Environment for Demo ---
# Use a temporary SQLite database for this demo run
os.environ["DATABASE_URL"] = "sqlite:///demo_phase1.db"

# Mock GUI libraries before they are imported by our application code.
# This allows the script to run in a headless environment.
mock_pyautogui = MagicMock()
mock_playwright_page = MagicMock()
sys_modules = {
    'pyautogui': mock_pyautogui,
    'playwright.sync_api': MagicMock(
        sync_playwright=MagicMock(
            return_value=MagicMock(
                __enter__=MagicMock(
                    return_value=MagicMock(
                        chromium=MagicMock(
                            launch=MagicMock(
                                return_value=MagicMock(
                                    new_page=MagicMock(return_value=mock_playwright_page)
                                )
                            )
                        )
                    )
                )
            )
        )
    )
}

with patch.dict('sys.modules', sys_modules):
    from ai_engine.enhanced_runners.desktop_runner import DesktopRunner
    from ai_engine.enhanced_runners.browser_runner import BrowserRunner
    from ai_engine.workflow_engine import WorkflowEngine, execute_workflow_by_id
    from ai_engine.models.workflow import Workflow
    from ai_engine.database import create_db_and_tables, get_session
    from sqlmodel import Session

# --- Logging and Console Helpers ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FoundationDemo")

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD} {text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")

def print_step(title):
    print(f"\n{Colors.CYAN}--- {title} ---{Colors.ENDC}")

# --- Demo Data and Simulation ---

def get_simulated_recording_data():
    """Simulates the raw output from the Basic Recording Agent."""
    return [
        {'type': 'window_change', 'title': 'Inbox - user@company.com - Outlook'},
        {'type': 'click', 'x': 250, 'y': 300, 'element_text': 'Email: New PO #12345 from Acme Corp'},
        {'type': 'double_click', 'x': 400, 'y': 500, 'element_text': 'po_12345.pdf'},
        {'type': 'window_change', 'title': 'po_12345.pdf - Adobe Acrobat Reader'},
        {'type': 'hotkey', 'keys': ['ctrl', 'c']},
        {'type': 'window_change', 'title': 'Google Chrome'},
        {'type': 'type', 'text': 'https://crm.company.com'},
        {'type': 'press', 'keys': ['enter']},
        {'type': 'fill', 'selector': '#search-customer', 'text': 'Acme Corp'},
        {'type': 'click', 'selector': 'button.search'},
        {'type': 'click', 'selector': 'a.order-history'},
        {'type': "type", "text": "PO12345", "selector": "#po-number"},
        {'type': 'hotkey', 'keys': ['ctrl', 'v']},
        {'type': 'click', 'selector': 'button#save-order'},
    ]

def simulate_ai_learning_engine(recording_data: list) -> dict:
    """
    Simulates the Phase 2 AI Learning Engine.
    Analyzes raw recording data and generates a structured, human-readable workflow.
    """
    # In a real scenario, an LLM would analyze the sequence and context.
    # Here, we use simple logic to group actions.
    workflow = {
        "name": "Process New Purchase Order from Email",
        "description": "AI-generated workflow from user recording on processing a new PO.",
        "nodes": [
            {
                "id": "step1_open_and_read_po",
                "type": "desktop",
                "data": {
                    "label": "Open and Read PO from Email",
                    "description": "AI will open the new PO email, open the attached PDF, and copy its contents.",
                    "actions": [
                        {'type': 'click', 'x': 250, 'y': 300},
                        {'type': 'double_click', 'x': 400, 'y': 500},
                        {'type': 'hotkey', 'keys': ['ctrl', 'c']},
                    ]
                }
            },
            {
                "id": "step2_update_crm",
                "type": "browser",
                "data": {
                    "label": "Update Web CRM with PO Details",
                    "description": "AI will navigate to the CRM, search for the customer, and enter the new PO details.",
                    "actions": [
                        {'type': 'goto', 'url': 'https://crm.company.com'},
                        {'type': 'fill', 'selector': '#search-customer', 'text': 'Acme Corp'},
                        {'type': 'click', 'selector': 'button.search'},
                        {'type': 'click', 'selector': 'a.order-history'},
                        {'type': "type", "text": "PO12345", "selector": "#po-number"},
                        {'type': 'hotkey', 'keys': ['ctrl', 'v']},
                        {'type': 'click', 'selector': 'button#save-order'},
                    ]
                }
            }
        ],
        "edges": [
            {"source": "step1_open_and_read_po", "target": "step2_update_crm"}
        ]
    }
    return workflow

def execute_demo_workflow(workflow_data: dict, db_engine):
    """
    Executes the generated workflow using the simple Workflow Engine.
    """
    with Session(db_engine) as session:
        # Create workflow in the database
        workflow = Workflow(**workflow_data)
        session.add(workflow)
        session.commit()
        session.refresh(workflow)
        
        print_step(f"Workflow '{workflow.name}' created with ID: {workflow.id}")
        
        # Instantiate and run the engine
        engine_instance = WorkflowEngine(workflow.id)
        engine_instance.run()
        
        # Retrieve and display execution results
        execution = session.get(Execution, engine_instance.execution.id)
        print_step("Execution Complete")
        print(f"  Status: {Colors.GREEN if execution.status == 'completed' else Colors.RED}{execution.status}{Colors.ENDC}")
        if execution.error:
            print(f"  Error: {execution.error}")
        
        print("  Executed Steps:")
        for step_id, result in execution.result.items():
            if step_id == "executed_steps": continue
            status = "✅" if result.get("success") else "❌"
            print(f"    {status} {step_id}")


# --- Main Demo Script ---

def main():
    """Orchestrates the demonstration of the Phase 1 Foundation."""
    
    print_header("Phase 1 Foundation Demo: The Digital Employee")
    
    # --- 1. Basic Recording Agent ---
    print_step("1. Simulating Recording Agent")
    raw_data = get_simulated_recording_data()
    print("Agent captured the following raw event sequence:")
    print(json.dumps(raw_data[:3], indent=2) + "\n  ...") # Show a snippet
    
    # --- 2. Simple Workflow Engine (with AI learning simulation) ---
    print_step("2. AI Learning Engine Analyzing Recording")
    generated_workflow = simulate_ai_learning_engine(raw_data)
    print("AI has generated the following structured workflow:")
    print(f"  Workflow Name: {Colors.YELLOW}{generated_workflow['name']}{Colors.ENDC}")
    for node in generated_workflow['nodes']:
        print(f"  - Step: {Colors.BOLD}{node['data']['label']}{Colors.ENDC} (Type: {node['type']})")
    
    # --- 3. Enhanced Desktop/Browser Runners ---
    print_step("3. Executing Workflow with Digital Employee Runners")
    
    # Setup a temporary database for the execution
    test_engine = create_sql_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    create_db_and_tables(test_engine)
    
    # Patch get_session to use our in-memory DB for this execution
    with patch('ai_engine.workflow_engine.get_session', lambda: Session(test_engine)):
        execute_demo_workflow(generated_workflow, test_engine)
        
    print_header("Demo Complete")
    print("This demo showcased the core foundation: recording user actions, converting them")
    print("into a structured workflow, and executing it using desktop and browser automation.")


if __name__ == "__main__":
    # Check if dependencies are mocked (i.e., we are in the right test setup)
    if 'pyautogui' not in sys.modules or 'playwright.sync_api' not in sys.modules:
        print(f"{Colors.RED}Error: This script must be run with mocked GUI libraries.{Colors.ENDC}")
        print("It is intended to demonstrate logic, not perform actual automation.")
        sys.exit(1)
        
    main()
