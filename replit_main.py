#!/usr/bin/env python3
"""
AI Engine Replit Demo
=====================

This is a simplified version of the AI Engine designed to run on Replit.
It provides a web interface for testing all core functionality:

- Shell Runner: Execute shell commands
- HTTP Runner: Make HTTP requests
- Decision Runner: Test conditional logic
- LLM Runner: Interact with language models (requires OpenAI API key)
- Browser Runner: Automate browser interactions (if Playwright is available)

Usage:
    1. Set OPENAI_API_KEY in Replit Secrets for LLM functionality
    2. Run this file directly in Replit
    3. Access the web UI at the provided URL
"""

import os
import sys
import json
import time
import uuid
import logging
import asyncio
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Configure environment for Replit
os.environ["DATABASE_URL"] = "sqlite:///ai_engine_replit.db"
if "OPENAI_API_KEY" not in os.environ:
    # Check if running on Replit with secrets
    if "REPL_ID" in os.environ and os.path.exists("/tmp/secrets.json"):
        with open("/tmp/secrets.json") as f:
            secrets = json.load(f)
            if "OPENAI_API_KEY" in secrets:
                os.environ["OPENAI_API_KEY"] = secrets["OPENAI_API_KEY"]

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ai_engine_replit")

# Import AI Engine components
try:
    from fastapi import FastAPI, Request, Form, Depends, HTTPException, BackgroundTasks
    from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from sqlmodel import Session, select, SQLModel, Field, create_engine, Column, JSON
    import uvicorn
    
    # Import AI Engine components
    from ai_engine.database import create_db_and_tables, get_session, engine
    from ai_engine.models.workflow import Workflow
    from ai_engine.models.execution import Execution
    from ai_engine.workflow_runners import RunnerFactory, execute_step
    
    IMPORTS_SUCCESS = True
except ImportError as e:
    IMPORTS_SUCCESS = False
    IMPORT_ERROR = str(e)
    logger.error(f"Failed to import required modules: {e}")

# Create FastAPI app
app = FastAPI(title="AI Engine Replit Demo")

# Create templates directory if it doesn't exist
TEMPLATES_DIR = Path("templates")
TEMPLATES_DIR.mkdir(exist_ok=True)

# Create basic templates
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Engine Demo</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        .header {
            background-color: #3498db;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .card {
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        .runner-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            grid-gap: 20px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input, textarea, select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        button {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #2980b9;
        }
        .result {
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            margin-top: 15px;
            white-space: pre-wrap;
            font-family: monospace;
            max-height: 300px;
            overflow-y: auto;
        }
        .success {
            color: #27ae60;
            font-weight: bold;
        }
        .error {
            color: #e74c3c;
            font-weight: bold;
        }
        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            border-bottom: 2px solid transparent;
        }
        .tab.active {
            border-bottom: 2px solid #3498db;
            font-weight: bold;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .executions-list {
            list-style: none;
            padding: 0;
        }
        .execution-item {
            padding: 10px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
        }
        .execution-item:hover {
            background-color: #f5f5f5;
        }
        .status-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-completed {
            background-color: #e6f7e6;
            color: #27ae60;
        }
        .status-failed {
            background-color: #fae6e6;
            color: #e74c3c;
        }
        .status-running {
            background-color: #e6f0f7;
            color: #3498db;
        }
        .status-pending {
            background-color: #f7f6e6;
            color: #f39c12;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>AI Engine Demo</h1>
        <p>Test all AI Engine functionality directly in your browser</p>
    </div>
    
    <div class="tabs">
        <div class="tab active" data-tab="runners">Runners</div>
        <div class="tab" data-tab="workflows">Workflows</div>
        <div class="tab" data-tab="executions">Executions</div>
        <div class="tab" data-tab="status">System Status</div>
    </div>
    
    <div id="runners" class="tab-content active">
        <h2>Test Runners</h2>
        <p>Test individual runner functionality:</p>
        
        <div class="runner-grid">
            <!-- Shell Runner -->
            <div class="card">
                <h3>Shell Runner</h3>
                <p>Execute shell commands</p>
                <form action="/run/shell" method="post">
                    <div class="form-group">
                        <label for="shell_command">Command:</label>
                        <input type="text" id="shell_command" name="command" value="echo 'Hello from Shell Runner'" required>
                    </div>
                    <div class="form-group">
                        <label for="shell_timeout">Timeout (seconds):</label>
                        <input type="number" id="shell_timeout" name="timeout" value="5" min="1" max="30">
                    </div>
                    <button type="submit">Run Command</button>
                </form>
                {% if shell_result %}
                <div class="result">
                    <div class="{% if shell_result.success %}success{% else %}error{% endif %}">
                        Status: {% if shell_result.success %}Success{% else %}Failed{% endif %}
                    </div>
                    <pre>{{ shell_result.output }}</pre>
                </div>
                {% endif %}
            </div>
            
            <!-- HTTP Runner -->
            <div class="card">
                <h3>HTTP Runner</h3>
                <p>Make HTTP requests</p>
                <form action="/run/http" method="post">
                    <div class="form-group">
                        <label for="http_url">URL:</label>
                        <input type="text" id="http_url" name="url" value="https://httpbin.org/get" required>
                    </div>
                    <div class="form-group">
                        <label for="http_method">Method:</label>
                        <select id="http_method" name="method">
                            <option value="GET">GET</option>
                            <option value="POST">POST</option>
                            <option value="PUT">PUT</option>
                            <option value="DELETE">DELETE</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="http_headers">Headers (JSON):</label>
                        <textarea id="http_headers" name="headers" rows="2">{"Accept": "application/json"}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="http_timeout">Timeout (seconds):</label>
                        <input type="number" id="http_timeout" name="timeout" value="10" min="1" max="30">
                    </div>
                    <button type="submit">Send Request</button>
                </form>
                {% if http_result %}
                <div class="result">
                    <div class="{% if http_result.success %}success{% else %}error{% endif %}">
                        Status: {% if http_result.success %}Success{% else %}Failed{% endif %}
                    </div>
                    <pre>{{ http_result.output }}</pre>
                </div>
                {% endif %}
            </div>
            
            <!-- Decision Runner -->
            <div class="card">
                <h3>Decision Runner</h3>
                <p>Test conditional logic</p>
                <form action="/run/decision" method="post">
                    <div class="form-group">
                        <label for="decision_expression">Expression:</label>
                        <input type="text" id="decision_expression" name="expression" value="value > 10" required>
                    </div>
                    <div class="form-group">
                        <label for="decision_value">Value:</label>
                        <input type="number" id="decision_value" name="value" value="20">
                    </div>
                    <div class="form-group">
                        <label for="decision_true_target">True Target:</label>
                        <input type="text" id="decision_true_target" name="true_target" value="high_value_path">
                    </div>
                    <div class="form-group">
                        <label for="decision_false_target">False Target:</label>
                        <input type="text" id="decision_false_target" name="false_target" value="low_value_path">
                    </div>
                    <button type="submit">Evaluate</button>
                </form>
                {% if decision_result %}
                <div class="result">
                    <div class="{% if decision_result.success %}success{% else %}error{% endif %}">
                        Status: {% if decision_result.success %}Success{% else %}Failed{% endif %}
                    </div>
                    <pre>{{ decision_result.output }}</pre>
                </div>
                {% endif %}
            </div>
            
            <!-- LLM Runner -->
            <div class="card">
                <h3>LLM Runner</h3>
                <p>Interact with language models</p>
                <form action="/run/llm" method="post">
                    <div class="form-group">
                        <label for="llm_prompt">Prompt:</label>
                        <textarea id="llm_prompt" name="prompt" rows="3" required>Write a short poem about AI.</textarea>
                    </div>
                    <div class="form-group">
                        <label for="llm_model">Model:</label>
                        <select id="llm_model" name="model">
                            <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                            <option value="gpt-4">GPT-4</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="llm_temperature">Temperature:</label>
                        <input type="number" id="llm_temperature" name="temperature" value="0.7" min="0" max="2" step="0.1">
                    </div>
                    <div class="form-group">
                        <label for="llm_max_tokens">Max Tokens:</label>
                        <input type="number" id="llm_max_tokens" name="max_tokens" value="100" min="1" max="1000">
                    </div>
                    <button type="submit">Generate</button>
                </form>
                {% if llm_result %}
                <div class="result">
                    <div class="{% if llm_result.success %}success{% else %}error{% endif %}">
                        Status: {% if llm_result.success %}Success{% else %}Failed{% endif %}
                    </div>
                    <pre>{{ llm_result.output }}</pre>
                </div>
                {% endif %}
            </div>
            
            <!-- Browser Runner -->
            <div class="card">
                <h3>Browser Runner</h3>
                <p>Automate browser interactions</p>
                <form action="/run/browser" method="post">
                    <div class="form-group">
                        <label for="browser_url">URL to visit:</label>
                        <input type="text" id="browser_url" name="url" value="https://example.com" required>
                    </div>
                    <div class="form-group">
                        <label for="browser_actions">Actions:</label>
                        <select id="browser_actions" name="action_type">
                            <option value="visit">Visit URL</option>
                            <option value="screenshot">Take Screenshot</option>
                            <option value="extract">Extract Content</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="browser_selector">CSS Selector (for extract):</label>
                        <input type="text" id="browser_selector" name="selector" value="h1">
                    </div>
                    <button type="submit">Run Browser Action</button>
                </form>
                {% if browser_result %}
                <div class="result">
                    <div class="{% if browser_result.success %}success{% else %}error{% endif %}">
                        Status: {% if browser_result.success %}Success{% else %}Failed{% endif %}
                    </div>
                    <pre>{{ browser_result.output }}</pre>
                    {% if browser_result.screenshot %}
                    <div>
                        <h4>Screenshot:</h4>
                        <img src="{{ browser_result.screenshot }}" style="max-width: 100%;">
                    </div>
                    {% endif %}
                </div>
                {% endif %}
            </div>
        </div>
    </div>
    
    <div id="workflows" class="tab-content">
        <h2>Workflows</h2>
        <div class="card">
            <h3>Create Workflow</h3>
            <form action="/workflows/create" method="post">
                <div class="form-group">
                    <label for="workflow_name">Name:</label>
                    <input type="text" id="workflow_name" name="name" value="Test Workflow" required>
                </div>
                <div class="form-group">
                    <label for="workflow_description">Description:</label>
                    <textarea id="workflow_description" name="description" rows="2">A test workflow</textarea>
                </div>
                <div class="form-group">
                    <label for="workflow_steps">Steps (JSON):</label>
                    <textarea id="workflow_steps" name="steps" rows="10" required>[
  {
    "id": "step1",
    "type": "shell",
    "params": {
      "command": "echo 'Step 1'",
      "timeout": 5
    }
  },
  {
    "id": "step2",
    "type": "shell",
    "params": {
      "command": "echo 'Step 2'",
      "timeout": 5
    }
  }
]</textarea>
                </div>
                <button type="submit">Create Workflow</button>
            </form>
        </div>
        
        <div class="card">
            <h3>Workflows</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background-color: #f5f5f5;">
                        <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">ID</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Name</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Description</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Status</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for workflow in workflows %}
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{{ workflow.id }}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{{ workflow.name }}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{{ workflow.description }}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{{ workflow.status }}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                            <a href="/workflows/{{ workflow.id }}/execute" style="text-decoration: none;">
                                <button style="background-color: #27ae60; padding: 5px 10px; font-size: 14px;">Execute</button>
                            </a>
                            <a href="/workflows/{{ workflow.id }}/delete" style="text-decoration: none;">
                                <button style="background-color: #e74c3c; padding: 5px 10px; font-size: 14px;">Delete</button>
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    
    <div id="executions" class="tab-content">
        <h2>Executions</h2>
        <div class="card">
            <h3>Recent Executions</h3>
            {% if executions %}
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background-color: #f5f5f5;">
                        <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">ID</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Workflow</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Status</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Started</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Duration</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for execution in executions %}
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{{ execution.id }}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{{ execution.workflow_id }}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                            <span class="status-badge status-{{ execution.status }}">{{ execution.status }}</span>
                        </td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{{ execution.start_time }}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{{ execution.duration }}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                            <a href="/executions/{{ execution.id }}" style="text-decoration: none;">
                                <button style="background-color: #3498db; padding: 5px 10px; font-size: 14px;">View</button>
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <p>No executions yet. Run a workflow to see executions here.</p>
            {% endif %}
        </div>
    </div>
    
    <div id="status" class="tab-content">
        <h2>System Status</h2>
        <div class="card">
            <h3>Environment</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">Python Version</td>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">{{ python_version }}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">Database URL</td>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">{{ database_url }}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">OpenAI API Key</td>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">{{ openai_key_status }}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">Desktop Automation</td>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">{{ desktop_automation_status }}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">Browser Automation</td>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">{{ browser_automation_status }}</td>
                </tr>
            </table>
        </div>
        
        <div class="card">
            <h3>Available Runners</h3>
            <ul style="list-style-type: none; padding: 0;">
                {% for runner in available_runners %}
                <li style="padding: 10px; border-bottom: 1px solid #ddd;">
                    <span style="font-weight: bold;">{{ runner.name }}</span>: {{ runner.status }}
                </li>
                {% endfor %}
            </ul>
        </div>
    </div>
    
    <script>
        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                // Hide all tab contents
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                
                // Deactivate all tabs
                document.querySelectorAll('.tab').forEach(t => {
                    t.classList.remove('active');
                });
                
                // Activate clicked tab
                tab.classList.add('active');
                
                // Show corresponding content
                const tabId = tab.getAttribute('data-tab');
                document.getElementById(tabId).classList.add('active');
            });
        });
    </script>
</body>
</html>
"""

# Write template to file
with open(TEMPLATES_DIR / "index.html", "w") as f:
    f.write(INDEX_TEMPLATE)

# Set up templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Initialize database
if IMPORTS_SUCCESS:
    try:
        create_db_and_tables()
        logger.info("Database initialized successfully")
        DB_INITIALIZED = True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        DB_INITIALIZED = False
else:
    DB_INITIALIZED = False

# Check for desktop automation
try:
    import pyautogui
    DESKTOP_AUTOMATION_AVAILABLE = True
except ImportError:
    DESKTOP_AUTOMATION_AVAILABLE = False

# Check for browser automation
try:
    from playwright.sync_api import sync_playwright
    BROWSER_AUTOMATION_AVAILABLE = True
except ImportError:
    BROWSER_AUTOMATION_AVAILABLE = False

# Test runners
def test_shell_runner(command: str, timeout: int = 5):
    """Test Shell Runner functionality."""
    try:
        shell_runner = RunnerFactory.create_runner("shell", "test_shell", {
            "command": command,
            "timeout": timeout
        })
        result = shell_runner.execute()
        return {
            "success": result["success"],
            "output": json.dumps(result, indent=2)
        }
    except Exception as e:
        return {
            "success": False,
            "output": f"Error: {str(e)}\n{traceback.format_exc()}"
        }

def test_http_runner(url: str, method: str = "GET", headers: Dict = None, timeout: int = 10):
    """Test HTTP Runner functionality."""
    try:
        http_runner = RunnerFactory.create_runner("http", "test_http", {
            "url": url,
            "method": method,
            "headers": headers or {"Accept": "application/json"},
            "timeout": timeout
        })
        result = http_runner.execute()
        return {
            "success": result["success"],
            "output": json.dumps(result, indent=2)
        }
    except Exception as e:
        return {
            "success": False,
            "output": f"Error: {str(e)}\n{traceback.format_exc()}"
        }

def test_decision_runner(expression: str, context: Dict = None):
    """Test Decision Runner functionality."""
    try:
        decision_runner = RunnerFactory.create_runner("decision", "test_decision", {
            "conditions": [
                {"expression": expression, "target": "true_path"}
            ],
            "default": "false_path"
        })
        result = decision_runner.execute(context or {})
        return {
            "success": result["success"],
            "output": json.dumps(result, indent=2)
        }
    except Exception as e:
        return {
            "success": False,
            "output": f"Error: {str(e)}\n{traceback.format_exc()}"
        }

def test_llm_runner(prompt: str, model: str = "gpt-3.5-turbo", temperature: float = 0.7, max_tokens: int = 100):
    """Test LLM Runner functionality."""
    try:
        if "OPENAI_API_KEY" not in os.environ or not os.environ["OPENAI_API_KEY"]:
            return {
                "success": False,
                "output": "Error: OpenAI API key not found. Please set OPENAI_API_KEY in Replit Secrets."
            }
            
        llm_runner = RunnerFactory.create_runner("llm", "test_llm", {
            "provider": "openai",
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens
        })
        result = llm_runner.execute()
        return {
            "success": result["success"],
            "output": json.dumps(result, indent=2)
        }
    except Exception as e:
        return {
            "success": False,
            "output": f"Error: {str(e)}\n{traceback.format_exc()}"
        }

def test_browser_runner(url: str, action_type: str = "visit", selector: str = None):
    """Test Browser Runner functionality."""
    try:
        if not BROWSER_AUTOMATION_AVAILABLE:
            return {
                "success": False,
                "output": "Error: Browser automation not available. Install Playwright with 'pip install playwright' and run 'playwright install'."
            }
            
        # Create a temporary directory for screenshots
        screenshots_dir = Path("browser_screenshots")
        screenshots_dir.mkdir(exist_ok=True)
        
        # Create actions based on action type
        actions = [{"type": "goto", "url": url, "wait_until": "load"}]
        screenshot_path = None
        
        if action_type == "screenshot":
            screenshot_path = str(screenshots_dir / f"screenshot_{int(time.time())}.png")
            actions.append({"type": "screenshot", "filename": screenshot_path})
        elif action_type == "extract" and selector:
            actions.append({"type": "extract", "selector": selector})
        
        # Create and execute browser runner
        browser_runner = RunnerFactory.create_runner("browser", "test_browser", {
            "browser_type": "chromium",
            "headless": True,
            "actions": actions,
            "timeout": 30
        })
        result = browser_runner.execute()
        
        # Check if screenshot was taken
        screenshot_url = None
        if screenshot_path and os.path.exists(screenshot_path):
            # In Replit, we can serve the screenshot file
            screenshot_url = f"/screenshots/{os.path.basename(screenshot_path)}"
        
        return {
            "success": result["success"],
            "output": json.dumps(result, indent=2),
            "screenshot": screenshot_url
        }
    except Exception as e:
        return {
            "success": False,
            "output": f"Error: {str(e)}\n{traceback.format_exc()}"
        }

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main dashboard."""
    if not IMPORTS_SUCCESS:
        return HTMLResponse(f"""
        <html>
        <head><title>AI Engine - Import Error</title></head>
        <body>
            <h1>Import Error</h1>
            <p>Failed to import required modules: {IMPORT_ERROR}</p>
            <p>Please make sure all dependencies are installed:</p>
            <pre>pip install fastapi uvicorn sqlmodel jinja2</pre>
        </body>
        </html>
        """)
        
    if not DB_INITIALIZED:
        return HTMLResponse(f"""
        <html>
        <head><title>AI Engine - Database Error</title></head>
        <body>
            <h1>Database Initialization Error</h1>
            <p>Failed to initialize database. Check logs for details.</p>
        </body>
        </html>
        """)
    
    # Get workflows
    workflows = []
    try:
        with Session(engine) as session:
            workflows = session.exec(select(Workflow)).all()
    except Exception as e:
        logger.error(f"Error fetching workflows: {e}")
    
    # Get executions
    executions = []
    try:
        with Session(engine) as session:
            db_executions = session.exec(select(Execution).order_by(Execution.id.desc()).limit(10)).all()
            for execution in db_executions:
                duration = ""
                if execution.start_time and execution.end_time:
                    start = datetime.fromisoformat(execution.start_time)
                    end = datetime.fromisoformat(execution.end_time)
                    duration = f"{(end - start).total_seconds():.2f}s"
                
                executions.append({
                    "id": execution.id,
                    "workflow_id": execution.workflow_id,
                    "status": execution.status,
                    "start_time": execution.start_time,
                    "duration": duration
                })
    except Exception as e:
        logger.error(f"Error fetching executions: {e}")
    
    # Check available runners
    available_runners = [
        {"name": "Shell Runner", "status": "Available"},
        {"name": "HTTP Runner", "status": "Available"},
        {"name": "Decision Runner", "status": "Available"},
        {"name": "LLM Runner", "status": "Available" if "OPENAI_API_KEY" in os.environ else "Missing API Key"},
        {"name": "Browser Runner", "status": "Available" if BROWSER_AUTOMATION_AVAILABLE else "Not Installed"},
        {"name": "Desktop Runner", "status": "Available" if DESKTOP_AUTOMATION_AVAILABLE else "Not Available in Replit"}
    ]
    
    # System status
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    database_url = os.environ.get("DATABASE_URL", "Not set")
    openai_key_status = "Configured" if "OPENAI_API_KEY" in os.environ else "Not configured"
    desktop_automation_status = "Available" if DESKTOP_AUTOMATION_AVAILABLE else "Not available in Replit"
    browser_automation_status = "Available" if BROWSER_AUTOMATION_AVAILABLE else "Not installed"
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "workflows": workflows,
        "executions": executions,
        "available_runners": available_runners,
        "python_version": python_version,
        "database_url": database_url,
        "openai_key_status": openai_key_status,
        "desktop_automation_status": desktop_automation_status,
        "browser_automation_status": browser_automation_status
    })

@app.post("/run/shell", response_class=HTMLResponse)
async def run_shell(
    request: Request,
    command: str = Form(...),
    timeout: int = Form(5)
):
    """Run a shell command."""
    shell_result = test_shell_runner(command, timeout)
    
    # Get workflows and executions for template
    workflows = []
    executions = []
    try:
        with Session(engine) as session:
            workflows = session.exec(select(Workflow)).all()
            db_executions = session.exec(select(Execution).order_by(Execution.id.desc()).limit(10)).all()
            for execution in db_executions:
                duration = ""
                if execution.start_time and execution.end_time:
                    start = datetime.fromisoformat(execution.start_time)
                    end = datetime.fromisoformat(execution.end_time)
                    duration = f"{(end - start).total_seconds():.2f}s"
                
                executions.append({
                    "id": execution.id,
                    "workflow_id": execution.workflow_id,
                    "status": execution.status,
                    "start_time": execution.start_time,
                    "duration": duration
                })
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "shell_result": shell_result,
        "workflows": workflows,
        "executions": executions
    })

@app.post("/run/http", response_class=HTMLResponse)
async def run_http(
    request: Request,
    url: str = Form(...),
    method: str = Form("GET"),
    headers: str = Form("{}"),
    timeout: int = Form(10)
):
    """Run an HTTP request."""
    try:
        headers_dict = json.loads(headers)
    except json.JSONDecodeError:
        headers_dict = {"Accept": "application/json"}
    
    http_result = test_http_runner(url, method, headers_dict, timeout)
    
    # Get workflows and executions for template
    workflows = []
    executions = []
    try:
        with Session(engine) as session:
            workflows = session.exec(select(Workflow)).all()
            db_executions = session.exec(select(Execution).order_by(Execution.id.desc()).limit(10)).all()
            for execution in db_executions:
                duration = ""
                if execution.start_time and execution.end_time:
                    start = datetime.fromisoformat(execution.start_time)
                    end = datetime.fromisoformat(execution.end_time)
                    duration = f"{(end - start).total_seconds():.2f}s"
                
                executions.append({
                    "id": execution.id,
                    "workflow_id": execution.workflow_id,
                    "status": execution.status,
                    "start_time": execution.start_time,
                    "duration": duration
                })
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "http_result": http_result,
        "workflows": workflows,
        "executions": executions
    })

@app.post("/run/decision", response_class=HTMLResponse)
async def run_decision(
    request: Request,
    expression: str = Form(...),
    value: int = Form(0),
    true_target: str = Form("high_value_path"),
    false_target: str = Form("low_value_path")
):
    """Run a decision evaluation."""
    context = {"value": value}
    decision_result = test_decision_runner(expression, context)
    
    # Get workflows and executions for template
    workflows = []
    executions = []
    try:
        with Session(engine) as session:
            workflows = session.exec(select(Workflow)).all()
            db_executions = session.exec(select(Execution).order_by(Execution.id.desc()).limit(10)).all()
            for execution in db_executions:
                duration = ""
                if execution.start_time and execution.end_time:
                    start = datetime.fromisoformat(execution.start_time)
                    end = datetime.fromisoformat(execution.end_time)
                    duration = f"{(end - start).total_seconds():.2f}s"
                
                executions.append({
                    "id": execution.id,
                    "workflow_id": execution.workflow_id,
                    "status": execution.status,
                    "start_time": execution.start_time,
                    "duration": duration
                })
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "decision_result": decision_result,
        "workflows": workflows,
        "executions": executions
    })

@app.post("/run/llm", response_class=HTMLResponse)
async def run_llm(
    request: Request,
    prompt: str = Form(...),
    model: str = Form("gpt-3.5-turbo"),
    temperature: float = Form(0.7),
    max_tokens: int = Form(100)
):
    """Run an LLM request."""
    llm_result = test_llm_runner(prompt, model, temperature, max_tokens)
    
    # Get workflows and executions for template
    workflows = []
    executions = []
    try:
        with Session(engine) as session:
            workflows = session.exec(select(Workflow)).all()
            db_executions = session.exec(select(Execution).order_by(Execution.id.desc()).limit(10)).all()
            for execution in db_executions:
                duration = ""
                if execution.start_time and execution.end_time:
                    start = datetime.fromisoformat(execution.start_time)
                    end = datetime.fromisoformat(execution.end_time)
                    duration = f"{(end - start).total_seconds():.2f}s"
                
                executions.append({
                    "id": execution.id,
                    "workflow_id": execution.workflow_id,
                    "status": execution.status,
                    "start_time": execution.start_time,
                    "duration": duration
                })
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "llm_result": llm_result,
        "workflows": workflows,
        "executions": executions
    })

@app.post("/run/browser", response_class=HTMLResponse)
async def run_browser(
    request: Request,
    url: str = Form(...),
    action_type: str = Form("visit"),
    selector: str = Form(None)
):
    """Run a browser automation action."""
    browser_result = test_browser_runner(url, action_type, selector)
    
    # Get workflows and executions for template
    workflows = []
    executions = []
    try:
        with Session(engine) as session:
            workflows = session.exec(select(Workflow)).all()
            db_executions = session.exec(select(Execution).order_by(Execution.id.desc()).limit(10)).all()
            for execution in db_executions:
                duration = ""
                if execution.start_time and execution.end_time:
                    start = datetime.fromisoformat(execution.start_time)
                    end = datetime.fromisoformat(execution.end_time)
                    duration = f"{(end - start).total_seconds():.2f}s"
                
                executions.append({
                    "id": execution.id,
                    "workflow_id": execution.workflow_id,
                    "status": execution.status,
                    "start_time": execution.start_time,
                    "duration": duration
                })
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "browser_result": browser_result,
        "workflows": workflows,
        "executions": executions
    })

@app.post("/workflows/create", response_class=HTMLResponse)
async def create_workflow(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    steps: str = Form("[]")
):
    """Create a new workflow."""
    try:
        steps_data = json.loads(steps)
        
        with Session(engine) as session:
            workflow = Workflow(
                name=name,
                description=description,
                status="active",
                steps=steps_data,
                created_by="replit_user"
            )
            session.add(workflow)
            session.commit()
            session.refresh(workflow)
            
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        return HTMLResponse(f"""
        <html>
        <head><title>AI Engine - Error</title></head>
        <body>
            <h1>Error Creating Workflow</h1>
            <p>{str(e)}</p>
            <p><a href="/">Back to Dashboard</a></p>
        </body>
        </html>
        """)

@app.get("/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: int, background_tasks: BackgroundTasks):
    """Execute a workflow."""
    try:
        from ai_engine.workflow_engine import execute_workflow_by_id
        
        # Execute workflow in background
        execution_id = execute_workflow_by_id(workflow_id)
        
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        return HTMLResponse(f"""
        <html>
        <head><title>AI Engine - Error</title></head>
        <body>
            <h1>Error Executing Workflow</h1>
            <p>{str(e)}</p>
            <p><a href="/">Back to Dashboard</a></p>
        </body>
        </html>
        """)

@app.get("/workflows/{workflow_id}/delete")
async def delete_workflow(workflow_id: int):
    """Delete a workflow."""
    try:
        with Session(engine) as session:
            workflow = session.get(Workflow, workflow_id)
            if workflow:
                session.delete(workflow)
                session.commit()
                
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error deleting workflow: {e}")
        return HTMLResponse(f"""
        <html>
        <head><title>AI Engine - Error</title></head>
        <body>
            <h1>Error Deleting Workflow</h1>
            <p>{str(e)}</p>
            <p><a href="/">Back to Dashboard</a></p>
        </body>
        </html>
        """)

@app.get("/executions/{execution_id}")
async def view_execution(request: Request, execution_id: int):
    """View execution details."""
    try:
        with Session(engine) as session:
            execution = session.get(Execution, execution_id)
            if not execution:
                raise HTTPException(status_code=404, detail="Execution not found")
                
            # Format execution details for display
            execution_details = {
                "id": execution.id,
                "workflow_id": execution.workflow_id,
                "status": execution.status,
                "start_time": execution.start_time,
                "end_time": execution.end_time,
                "result": json.dumps(execution.result, indent=2) if execution.result else None,
                "error": execution.error
            }
            
            return HTMLResponse(f"""
            <html>
            <head>
                <title>AI Engine - Execution {execution_id}</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    h1, h2, h3 {{
                        color: #2c3e50;
                    }}
                    .header {{
                        background-color: #3498db;
                        color: white;
                        padding: 20px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                    }}
                    .card {{
                        background-color: #fff;
                        border-radius: 5px;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                        padding: 20px;
                        margin-bottom: 20px;
                    }}
                    .result {{
                        background-color: #f9f9f9;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        padding: 15px;
                        white-space: pre-wrap;
                        font-family: monospace;
                        max-height: 500px;
                        overflow-y: auto;
                    }}
                    .success {{
                        color: #27ae60;
                    }}
                    .error {{
                        color: #e74c3c;
                    }}
                    .back-button {{
                        display: inline-block;
                        background-color: #3498db;
                        color: white;
                        padding: 10px 15px;
                        text-decoration: none;
                        border-radius: 4px;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Execution #{execution_id}</h1>
                </div>
                
                <div class="card">
                    <h2>Execution Details</h2>
                    <table style="width: 100%;">
                        <tr>
                            <td style="font-weight: bold; padding: 10px;">Workflow ID</td>
                            <td>{execution_details['workflow_id']}</td>
                        </tr>
                        <tr>
                            <td style="font-weight: bold; padding: 10px;">Status</td>
                            <td class="{execution_details['status']}">{execution_details['status']}</td>
                        </tr>
                        <tr>
                            <td style="font-weight: bold; padding: 10px;">Start Time</td>
                            <td>{execution_details['start_time']}</td>
                        </tr>
                        <tr>
                            <td style="font-weight: bold; padding: 10px;">End Time</td>
                            <td>{execution_details['end_time']}</td>
                        </tr>
                    </table>
                </div>
                
                <div class="card">
                    <h2>Results</h2>
                    <div class="result">
                        {execution_details['result'] or 'No results available'}
                    </div>
                </div>
                
                {f'''
                <div class="card">
                    <h2>Error</h2>
                    <div class="result error">
                        {execution_details['error']}
                    </div>
                </div>
                ''' if execution_details['error'] else ''}
                
                <a href="/" class="back-button">Back to Dashboard</a>
            </body>
            </html>
            """)
    except Exception as e:
        logger.error(f"Error viewing execution: {e}")
        return HTMLResponse(f"""
        <html>
        <head><title>AI Engine - Error</title></head>
        <body>
            <h1>Error Viewing Execution</h1>
            <p>{str(e)}</p>
            <p><a href="/">Back to Dashboard</a></p>
        </body>
        </html>
        """)

@app.get("/screenshots/{filename}")
async def get_screenshot(filename: str):
    """Serve screenshot files."""
    screenshots_dir = Path("browser_screenshots")
    file_path = screenshots_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")
        
    return FileResponse(str(file_path))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "imports": IMPORTS_SUCCESS, "database": DB_INITIALIZED}

def main():
    """Run the application."""
    # Create Replit-specific .replit file if needed
    if "REPL_ID" in os.environ:
        with open(".replit", "w") as f:
            f.write("""
[nix]
channel = "stable-22_11"

[env]
PYTHONHASHSEED = "0"
PYTHONPATH = "."

[unitTest]
language = "python3"

[languages.python3]
pattern = "**/*.py"
syntax = "python"

[languages.python3.languageServer]
start = ["pyls"]

[gitHubImport]
requiredFiles = [".replit", "replit.nix", "replit_main.py"]

[deployment]
run = ["python", "replit_main.py"]
deploymentTarget = "cloudrun"
            """)
            
        # Create requirements.txt if it doesn't exist
        if not os.path.exists("requirements.txt"):
            with open("requirements.txt", "w") as f:
                f.write("""
fastapi>=0.68.0
uvicorn>=0.15.0
sqlmodel>=0.0.8
jinja2>=3.0.0
python-multipart>=0.0.5
requests>=2.26.0
# Optional dependencies for enhanced runners
playwright>=1.42.0
openai>=1.0.0
                """)
    
    # Run the application
    print("=" * 60)
    print("AI ENGINE REPLIT DEMO")
    print("=" * 60)
    print(f"Python Version: {sys.version}")
    print(f"Database URL: {os.environ.get('DATABASE_URL')}")
    print(f"OpenAI API Key: {'Configured' if 'OPENAI_API_KEY' in os.environ else 'Not configured'}")
    print(f"Desktop Automation: {'Available' if DESKTOP_AUTOMATION_AVAILABLE else 'Not available'}")
    print(f"Browser Automation: {'Available' if BROWSER_AUTOMATION_AVAILABLE else 'Not available'}")
    print("=" * 60)
    print("Starting web server...")
    
    # Run uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    main()
