#!/usr/bin/env python3
"""
Enhanced AI Engine Demo Workflows
=================================

This script demonstrates the enhanced AI Engine capabilities with practical examples
of desktop automation, browser automation, and advanced LLM workflows.

Usage:
    python demo_enhanced_workflows.py [workflow_type] [workflow_name]

    workflow_type: desktop, browser, llm, or combined
    workflow_name: specific workflow to run (optional)

Examples:
    python demo_enhanced_workflows.py desktop screenshot_tool
    python demo_enhanced_workflows.py browser data_extraction
    python demo_enhanced_workflows.py llm content_generator
    python demo_enhanced_workflows.py combined customer_onboarding
"""

import os
import sys
import json
import time
import logging
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("enhanced_workflows")

# Import AI Engine components
from ai_engine.workflow_runners import RunnerFactory, execute_step
from ai_engine.workflow_engine import WorkflowEngine
from ai_engine.models.workflow import Workflow
from ai_engine.models.execution import Execution

# Try to import enhanced runners (with graceful fallback if dependencies missing)
try:
    from ai_engine.enhanced_runners.desktop_runner import DesktopRunner
    DESKTOP_AVAILABLE = True
except ImportError:
    logger.warning("Desktop automation not available. Install PyAutoGUI to enable.")
    DESKTOP_AVAILABLE = False

try:
    from ai_engine.enhanced_runners.browser_runner import BrowserRunner
    BROWSER_AVAILABLE = True
except ImportError:
    logger.warning("Browser automation not available. Install Playwright to enable.")
    BROWSER_AVAILABLE = False

# -------------------------------------------------------------------- #
# Desktop Automation Workflows
# -------------------------------------------------------------------- #

def desktop_screenshot_tool():
    """
    Workflow that takes screenshots of specified regions and saves them.
    
    This demonstrates:
    - Screen capture capabilities
    - File operations
    - Multi-monitor support
    """
    if not DESKTOP_AVAILABLE:
        logger.error("Desktop automation not available. Install PyAutoGUI to enable.")
        return False
    
    logger.info("Running Desktop Screenshot Tool workflow")
    
    # Create output directory
    screenshots_dir = "screenshots"
    os.makedirs(screenshots_dir, exist_ok=True)
    
    # Define workflow steps
    steps = [
        {
            "id": "screenshot_primary",
            "type": "desktop",
            "params": {
                "actions": [
                    {
                        "type": "screenshot",
                        "filename": f"{screenshots_dir}/full_screen_{int(time.time())}.png"
                    }
                ],
                "timeout": 10
            }
        },
        {
            "id": "screenshot_region",
            "type": "desktop",
            "params": {
                "actions": [
                    {
                        "type": "screenshot",
                        "region": (0, 0, 800, 600),  # x, y, width, height
                        "filename": f"{screenshots_dir}/region_{int(time.time())}.png"
                    }
                ],
                "timeout": 10
            }
        }
    ]
    
    # Execute steps
    results = []
    for step in steps:
        logger.info(f"Executing step: {step['id']}")
        result = execute_step(
            step_id=step["id"],
            step_type=step["type"],
            params=step["params"]
        )
        results.append(result)
        
        if not result["success"]:
            logger.error(f"Step {step['id']} failed: {result.get('error', 'Unknown error')}")
            return False
        
        logger.info(f"Step {step['id']} completed successfully")
    
    # Summarize results
    logger.info("Desktop Screenshot Tool workflow completed successfully")
    for result in results:
        if "result" in result and "action_results" in result["result"]:
            for action_result in result["result"]["action_results"]:
                if "filename" in action_result:
                    logger.info(f"Screenshot saved: {action_result['filename']}")
    
    return True

def desktop_form_filler():
    """
    Workflow that automates filling out a form in a desktop application.
    
    This demonstrates:
    - Application launching
    - Form navigation
    - Text input
    - Button clicking
    """
    if not DESKTOP_AVAILABLE:
        logger.error("Desktop automation not available. Install PyAutoGUI to enable.")
        return False
    
    logger.info("Running Desktop Form Filler workflow")
    
    # Define workflow steps
    steps = [
        {
            "id": "open_notepad",
            "type": "desktop",
            "params": {
                "actions": [
                    # Windows: Open Run dialog
                    {"type": "hotkey", "keys": ["win", "r"]},
                    {"type": "wait", "duration": 0.5},
                    # Type notepad and press Enter
                    {"type": "type", "text": "notepad", "interval": 0.05},
                    {"type": "press", "key": "enter"},
                    {"type": "wait", "duration": 1.5}
                ],
                "timeout": 15
            }
        },
        {
            "id": "fill_form_data",
            "type": "desktop",
            "params": {
                "actions": [
                    # Type form data
                    {"type": "type", "text": "Name: John Doe\n", "interval": 0.05},
                    {"type": "type", "text": "Email: john.doe@example.com\n", "interval": 0.05},
                    {"type": "type", "text": "Phone: (555) 123-4567\n", "interval": 0.05},
                    {"type": "type", "text": "Comments: This form was filled automatically by AI Engine.\n", "interval": 0.05},
                    {"type": "wait", "duration": 1}
                ],
                "timeout": 20
            }
        },
        {
            "id": "save_form",
            "type": "desktop",
            "params": {
                "actions": [
                    # Save the file
                    {"type": "hotkey", "keys": ["ctrl", "s"]},
                    {"type": "wait", "duration": 1},
                    {"type": "type", "text": f"form_data_{int(time.time())}.txt", "interval": 0.05},
                    {"type": "press", "key": "enter"},
                    {"type": "wait", "duration": 1}
                ],
                "timeout": 15
            }
        },
        {
            "id": "close_application",
            "type": "desktop",
            "params": {
                "actions": [
                    # Close notepad
                    {"type": "hotkey", "keys": ["alt", "f4"]},
                    {"type": "wait", "duration": 0.5}
                ],
                "timeout": 10
            }
        }
    ]
    
    # Execute steps
    for step in steps:
        logger.info(f"Executing step: {step['id']}")
        result = execute_step(
            step_id=step["id"],
            step_type=step["type"],
            params=step["params"]
        )
        
        if not result["success"]:
            logger.error(f"Step {step['id']} failed: {result.get('error', 'Unknown error')}")
            return False
        
        logger.info(f"Step {step['id']} completed successfully")
    
    logger.info("Desktop Form Filler workflow completed successfully")
    return True

def desktop_file_organizer():
    """
    Workflow that organizes files on the desktop by type.
    
    This demonstrates:
    - File operations
    - Conditional logic
    - System interaction
    """
    if not DESKTOP_AVAILABLE:
        logger.error("Desktop automation not available. Install PyAutoGUI to enable.")
        return False
    
    logger.info("Running Desktop File Organizer workflow")
    
    # First use shell runner to get file list and create directories
    shell_step = {
        "id": "prepare_directories",
        "type": "shell",
        "params": {
            "command": """
            mkdir -p ~/organized/documents ~/organized/images ~/organized/other
            echo "Directories created successfully"
            """,
            "timeout": 10
        }
    }
    
    result = execute_step(
        step_id=shell_step["id"],
        step_type=shell_step["type"],
        params=shell_step["params"]
    )
    
    if not result["success"]:
        logger.error(f"Failed to create directories: {result.get('error', 'Unknown error')}")
        return False
    
    # Now use desktop automation to move files
    desktop_step = {
        "id": "organize_files",
        "type": "desktop",
        "params": {
            "actions": [
                # Open file explorer
                {"type": "hotkey", "keys": ["win", "e"]},
                {"type": "wait", "duration": 1.5},
                
                # Navigate to desktop
                {"type": "hotkey", "keys": ["alt", "d"]},
                {"type": "wait", "duration": 0.5},
                {"type": "type", "text": "~/Desktop", "interval": 0.05},
                {"type": "press", "key": "enter"},
                {"type": "wait", "duration": 1.5},
                
                # Select all files
                {"type": "hotkey", "keys": ["ctrl", "a"]},
                {"type": "wait", "duration": 0.5},
                
                # Right-click for context menu
                {"type": "right_click", "x": 400, "y": 300},
                {"type": "wait", "duration": 0.5},
                
                # Take screenshot for verification
                {"type": "screenshot", "filename": "file_organizer_selection.png"}
            ],
            "timeout": 30
        }
    }
    
    result = execute_step(
        step_id=desktop_step["id"],
        step_type=desktop_step["type"],
        params=desktop_step["params"]
    )
    
    if not result["success"]:
        logger.error(f"Desktop automation failed: {result.get('error', 'Unknown error')}")
        return False
    
    logger.info("Desktop File Organizer workflow completed successfully")
    logger.info("Note: This is a demonstration workflow. In a real environment, it would move files to organized folders.")
    return True

# -------------------------------------------------------------------- #
# Browser Automation Workflows
# -------------------------------------------------------------------- #

def browser_data_extraction():
    """
    Workflow that extracts data from a website.
    
    This demonstrates:
    - Web navigation
    - Element selection
    - Data extraction
    - Structured output
    """
    if not BROWSER_AVAILABLE:
        logger.error("Browser automation not available. Install Playwright to enable.")
        return False
    
    logger.info("Running Browser Data Extraction workflow")
    
    # Define workflow steps
    steps = [
        {
            "id": "navigate_to_site",
            "type": "browser",
            "params": {
                "browser_type": "chromium",
                "headless": True,  # Run headless for server environments
                "actions": [
                    {"type": "goto", "url": "https://quotes.toscrape.com/", "wait_until": "networkidle"},
                    {"type": "screenshot", "filename": "quotes_homepage.png"}
                ],
                "timeout": 30
            }
        },
        {
            "id": "extract_quotes",
            "type": "browser",
            "params": {
                "actions": [
                    # Extract all quotes
                    {"type": "extract_all", "selector": ".quote .text", "timeout": 5000},
                    # Extract all authors
                    {"type": "extract_all", "selector": ".quote .author", "timeout": 5000},
                    # Extract all tags
                    {"type": "extract_all", "selector": ".quote .tag", "timeout": 5000}
                ],
                "timeout": 30
            }
        }
    ]
    
    # Execute steps and collect results
    quotes = []
    authors = []
    tags = []
    
    for step in steps:
        logger.info(f"Executing step: {step['id']}")
        result = execute_step(
            step_id=step["id"],
            step_type=step["type"],
            params=step["params"]
        )
        
        if not result["success"]:
            logger.error(f"Step {step['id']} failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Store extracted data
        if step["id"] == "extract_quotes" and "result" in result and "action_results" in result["result"]:
            action_results = result["result"]["action_results"]
            if len(action_results) >= 3:
                quotes = action_results[0].get("extracted_values", [])
                authors = action_results[1].get("extracted_values", [])
                tags = action_results[2].get("extracted_values", [])
        
        logger.info(f"Step {step['id']} completed successfully")
    
    # Process and save the extracted data
    extracted_data = []
    for i in range(min(len(quotes), len(authors))):
        extracted_data.append({
            "quote": quotes[i],
            "author": authors[i],
            "tags": [tag for tag in tags if tag.startswith(authors[i].lower())]
        })
    
    # Save the data to a JSON file
    output_file = "extracted_quotes.json"
    with open(output_file, "w") as f:
        json.dump(extracted_data, f, indent=2)
    
    logger.info(f"Data extraction completed. Extracted {len(extracted_data)} quotes.")
    logger.info(f"Data saved to {output_file}")
    
    return True

def browser_form_submission():
    """
    Workflow that fills out and submits a web form.
    
    This demonstrates:
    - Form interaction
    - Input field handling
    - Button clicking
    - Form submission
    """
    if not BROWSER_AVAILABLE:
        logger.error("Browser automation not available. Install Playwright to enable.")
        return False
    
    logger.info("Running Browser Form Submission workflow")
    
    # Define workflow steps
    steps = [
        {
            "id": "navigate_to_form",
            "type": "browser",
            "params": {
                "browser_type": "chromium",
                "headless": False,  # Set to True for headless operation
                "actions": [
                    {"type": "goto", "url": "https://httpbin.org/forms/post", "wait_until": "networkidle"},
                    {"type": "screenshot", "filename": "form_initial.png"}
                ],
                "timeout": 30
            }
        },
        {
            "id": "fill_form",
            "type": "browser",
            "params": {
                "actions": [
                    # Fill out the form fields
                    {"type": "fill", "selector": "input[name='custname']", "text": "John Doe"},
                    {"type": "fill", "selector": "input[name='custtel']", "text": "555-123-4567"},
                    {"type": "fill", "selector": "input[name='custemail']", "text": "john.doe@example.com"},
                    {"type": "select", "selector": "select[name='size']", "value": "medium"},
                    {"type": "check", "selector": "input[name='topping'][value='bacon']"},
                    {"type": "check", "selector": "input[name='topping'][value='cheese']"},
                    {"type": "fill", "selector": "textarea[name='comments']", "text": "This order was submitted automatically by AI Engine."},
                    {"type": "screenshot", "filename": "form_filled.png"}
                ],
                "timeout": 30
            }
        },
        {
            "id": "submit_form",
            "type": "browser",
            "params": {
                "actions": [
                    # Submit the form
                    {"type": "click", "selector": "button[type='submit']"},
                    {"type": "wait_for_navigation", "wait_until": "networkidle"},
                    {"type": "screenshot", "filename": "form_submitted.png"},
                    # Extract the response
                    {"type": "extract", "selector": "pre", "timeout": 5000}
                ],
                "timeout": 30
            }
        }
    ]
    
    # Execute steps
    submission_result = None
    
    for step in steps:
        logger.info(f"Executing step: {step['id']}")
        result = execute_step(
            step_id=step["id"],
            step_type=step["type"],
            params=step["params"]
        )
        
        if not result["success"]:
            logger.error(f"Step {step['id']} failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Store form submission result
        if step["id"] == "submit_form" and "result" in result and "action_results" in result["result"]:
            action_results = result["result"]["action_results"]
            if len(action_results) >= 4:  # The fourth action is the extract
                submission_result = action_results[3].get("extracted_value")
        
        logger.info(f"Step {step['id']} completed successfully")
    
    if submission_result:
        logger.info(f"Form submitted successfully. Response: {submission_result[:100]}...")
    else:
        logger.info("Form submitted successfully, but couldn't extract response.")
    
    logger.info("Browser Form Submission workflow completed successfully")
    return True

def browser_multi_page_workflow():
    """
    Workflow that navigates through multiple pages and performs actions.
    
    This demonstrates:
    - Complex navigation
    - Conditional actions
    - Data collection across pages
    """
    if not BROWSER_AVAILABLE:
        logger.error("Browser automation not available. Install Playwright to enable.")
        return False
    
    logger.info("Running Browser Multi-Page workflow")
    
    # Define workflow steps
    steps = [
        {
            "id": "navigate_to_site",
            "type": "browser",
            "params": {
                "browser_type": "chromium",
                "headless": True,
                "actions": [
                    {"type": "goto", "url": "https://quotes.toscrape.com/", "wait_until": "networkidle"},
                    {"type": "screenshot", "filename": "quotes_page1.png"}
                ],
                "timeout": 30
            }
        },
        {
            "id": "extract_page1",
            "type": "browser",
            "params": {
                "actions": [
                    # Extract quotes from first page
                    {"type": "extract_all", "selector": ".quote .text", "timeout": 5000},
                    # Check if next page exists
                    {"type": "extract", "selector": ".next a", "attribute": "href", "timeout": 5000}
                ],
                "timeout": 30
            }
        },
        {
            "id": "navigate_to_page2",
            "type": "browser",
            "params": {
                "actions": [
                    # Click next page
                    {"type": "click", "selector": ".next a", "timeout": 5000},
                    {"type": "wait_for_navigation", "wait_until": "networkidle"},
                    {"type": "screenshot", "filename": "quotes_page2.png"}
                ],
                "timeout": 30
            }
        },
        {
            "id": "extract_page2",
            "type": "browser",
            "params": {
                "actions": [
                    # Extract quotes from second page
                    {"type": "extract_all", "selector": ".quote .text", "timeout": 5000}
                ],
                "timeout": 30
            }
        }
    ]
    
    # Execute steps and collect results
    page1_quotes = []
    page2_quotes = []
    next_page_url = None
    
    for step in steps:
        logger.info(f"Executing step: {step['id']}")
        result = execute_step(
            step_id=step["id"],
            step_type=step["type"],
            params=step["params"]
        )
        
        if not result["success"]:
            logger.error(f"Step {step['id']} failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Store extracted data
        if step["id"] == "extract_page1" and "result" in result and "action_results" in result["result"]:
            action_results = result["result"]["action_results"]
            if len(action_results) >= 1:
                page1_quotes = action_results[0].get("extracted_values", [])
            if len(action_results) >= 2:
                next_page_url = action_results[1].get("extracted_value")
        
        if step["id"] == "extract_page2" and "result" in result and "action_results" in result["result"]:
            action_results = result["result"]["action_results"]
            if len(action_results) >= 1:
                page2_quotes = action_results[0].get("extracted_values", [])
        
        logger.info(f"Step {step['id']} completed successfully")
    
    # Combine and save the results
    all_quotes = page1_quotes + page2_quotes
    
    logger.info(f"Multi-page workflow completed. Extracted {len(all_quotes)} quotes across pages.")
    logger.info(f"Page 1: {len(page1_quotes)} quotes, Page 2: {len(page2_quotes)} quotes")
    
    # Save the combined data
    output_file = "multi_page_quotes.json"
    with open(output_file, "w") as f:
        json.dump(all_quotes, f, indent=2)
    
    logger.info(f"Data saved to {output_file}")
    
    return True

# -------------------------------------------------------------------- #
# LLM Workflow Examples
# -------------------------------------------------------------------- #

def llm_content_generator():
    """
    Workflow that generates content using LLMs with structured prompts.
    
    This demonstrates:
    - Advanced prompting
    - Content generation
    - Template usage
    """
    logger.info("Running LLM Content Generator workflow")
    
    # Define workflow steps
    steps = [
        {
            "id": "generate_product_description",
            "type": "llm",
            "params": {
                "provider": "openai",
                "model": "gpt-4",
                "prompt": [
                    {"role": "system", "content": "You are a product marketing specialist who writes compelling product descriptions."},
                    {"role": "user", "content": "Create a product description for a new AI-powered smart home assistant called 'HomeGenius'. It features voice control, energy management, security monitoring, and personalized routines. Target audience is tech-savvy homeowners aged 30-50. Keep it under 200 words and focus on benefits, not just features."}
                ],
                "temperature": 0.7,
                "max_tokens": 300
            }
        },
        {
            "id": "generate_social_media",
            "type": "llm",
            "params": {
                "provider": "openai",
                "model": "gpt-4",
                "prompt": [
                    {"role": "system", "content": "You are a social media marketing expert who creates engaging posts."},
                    {"role": "user", "content": "Create 3 different social media posts (Twitter, Instagram, and LinkedIn) to promote the HomeGenius smart home assistant. Each post should be appropriate for its platform in terms of length and style. Include relevant hashtags for each platform."}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
        }
    ]
    
    # Execute steps
    product_description = None
    social_media_posts = None
    
    for step in steps:
        logger.info(f"Executing step: {step['id']}")
        result = execute_step(
            step_id=step["id"],
            step_type=step["type"],
            params=step["params"]
        )
        
        if not result["success"]:
            logger.error(f"Step {step['id']} failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Store generated content
        if step["id"] == "generate_product_description" and "result" in result:
            product_description = result["result"].get("content", "")
        
        if step["id"] == "generate_social_media" and "result" in result:
            social_media_posts = result["result"].get("content", "")
        
        logger.info(f"Step {step['id']} completed successfully")
    
    # Save the generated content
    if product_description and social_media_posts:
        output_file = "generated_marketing_content.md"
        with open(output_file, "w") as f:
            f.write("# Generated Marketing Content\n\n")
            f.write("## Product Description\n\n")
            f.write(product_description)
            f.write("\n\n## Social Media Posts\n\n")
            f.write(social_media_posts)
        
        logger.info(f"Content generation completed. Output saved to {output_file}")
    
    logger.info("LLM Content Generator workflow completed successfully")
    return True

def llm_data_extraction():
    """
    Workflow that extracts structured data from unstructured text.
    
    This demonstrates:
    - Information extraction
    - JSON output formatting
    - Data processing
    """
    logger.info("Running LLM Data Extraction workflow")
    
    # Sample unstructured text
    sample_text = """
    Meeting Minutes: Quarterly Review - Q2 2025
    Date: June 15, 2025
    Attendees: Sarah Johnson (CEO), Michael Chen (CTO), Priya Patel (CFO), David Wilson (COO)
    
    Key Points Discussed:
    1. Q2 revenue reached $4.2M, up 15% from Q1
    2. New product launch scheduled for August 10th
    3. Hiring plan: 5 engineers, 2 designers by end of Q3
    4. Customer satisfaction score improved to 92% (from 87% last quarter)
    
    Action Items:
    - Michael to finalize product roadmap by June 30
    - Priya to prepare budget revision by July 5
    - David to streamline operations process by July 15
    - Sarah to meet with key investors week of July 10
    
    Next meeting scheduled for July 20, 2025 at 10:00 AM
    """
    
    # Define workflow steps
    steps = [
        {
            "id": "extract_meeting_data",
            "type": "llm",
            "params": {
                "provider": "openai",
                "model": "gpt-4",
                "prompt": [
                    {"role": "system", "content": "You are a data extraction assistant. Extract structured information from the text and return it as JSON with the following schema: {\"meeting_date\": \"YYYY-MM-DD\", \"attendees\": [{\"name\": \"Full Name\", \"role\": \"Title\"}], \"key_points\": [\"point1\", \"point2\"], \"action_items\": [{\"assignee\": \"Name\", \"task\": \"Description\", \"due_date\": \"YYYY-MM-DD\"}], \"next_meeting\": \"YYYY-MM-DD HH:MM\"}"},
                    {"role": "user", "content": sample_text}
                ],
                "temperature": 0.1,
                "max_tokens": 800,
                "response_format": {"type": "json_object"}
            }
        },
        {
            "id": "generate_summary",
            "type": "llm",
            "params": {
                "provider": "openai",
                "model": "gpt-4",
                "prompt": [
                    {"role": "system", "content": "You are an executive assistant who creates concise meeting summaries."},
                    {"role": "user", "content": f"Create a brief executive summary of these meeting minutes, highlighting the most important points and action items:\n\n{sample_text}"}
                ],
                "temperature": 0.5,
                "max_tokens": 300
            }
        }
    ]
    
    # Execute steps
    extracted_data = None
    summary = None
    
    for step in steps:
        logger.info(f"Executing step: {step['id']}")
        result = execute_step(
            step_id=step["id"],
            step_type=step["type"],
            params=step["params"]
        )
        
        if not result["success"]:
            logger.error(f"Step {step['id']} failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Store results
        if step["id"] == "extract_meeting_data" and "result" in result:
            extracted_data = result["result"].get("content", "")
            try:
                # Try to parse as JSON
                extracted_data = json.loads(extracted_data)
            except json.JSONDecodeError:
                logger.warning("Failed to parse extracted data as JSON")
        
        if step["id"] == "generate_summary" and "result" in result:
            summary = result["result"].get("content", "")
        
        logger.info(f"Step {step['id']} completed successfully")
    
    # Save the results
    if extracted_data:
        with open("extracted_meeting_data.json", "w") as f:
            json.dump(extracted_data, f, indent=2)
        logger.info("Extracted data saved to extracted_meeting_data.json")
    
    if summary:
        with open("meeting_summary.txt", "w") as f:
            f.write(summary)
        logger.info("Meeting summary saved to meeting_summary.txt")
    
    logger.info("LLM Data Extraction workflow completed successfully")
    return True

def llm_decision_workflow():
    """
    Workflow that uses LLMs for decision making and routing.
    
    This demonstrates:
    - LLM-based decision making
    - Conditional workflows
    - Multi-step processing
    """
    logger.info("Running LLM Decision workflow")
    
    # Sample customer inquiry
    customer_inquiry = """
    Subject: Issue with recent order #12345
    
    Hello,
    
    I placed an order for a HomeGenius smart home assistant on June 10th (Order #12345),
    but the package arrived today with a damaged screen. The box also looked like it had
    been roughly handled during shipping. Everything else seems to be working fine,
    but I can't use all the features with the cracked screen.
    
    I'd like to get a replacement unit as soon as possible. I've already set up all my
    smart home devices with this one, so I'm hoping I can just transfer my settings to
    the new unit without having to start over.
    
    Please let me know what the next steps are.
    
    Thanks,
    Jennifer Martinez
    """
    
    # Define workflow steps
    steps = [
        {
            "id": "classify_inquiry",
            "type": "llm",
            "params": {
                "provider": "openai",
                "model": "gpt-4",
                "prompt": [
                    {"role": "system", "content": "You are a customer service routing assistant. Classify the customer inquiry into one of these categories: 'billing_issue', 'technical_support', 'return_or_replacement', 'product_inquiry', 'shipping_issue', 'account_management', 'other'. Respond with only the category name."},
                    {"role": "user", "content": customer_inquiry}
                ],
                "temperature": 0.1,
                "max_tokens": 20
            }
        }
    ]
    
    # Execute classification step
    inquiry_type = None
    
    for step in steps:
        logger.info(f"Executing step: {step['id']}")
        result = execute_step(
            step_id=step["id"],
            step_type=step["type"],
            params=step["params"]
        )
        
        if not result["success"]:
            logger.error(f"Step {step['id']} failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Store classification result
        if step["id"] == "classify_inquiry" and "result" in result:
            inquiry_type = result["result"].get("content", "").strip().lower()
        
        logger.info(f"Step {step['id']} completed successfully")
    
    logger.info(f"Inquiry classified as: {inquiry_type}")
    
    # Define next steps based on classification
    next_steps = {
        "return_or_replacement": {
            "id": "handle_replacement",
            "type": "llm",
            "params": {
                "provider": "openai",
                "model": "gpt-4",
                "prompt": [
                    {"role": "system", "content": "You are a customer service representative handling a return or replacement request. Generate a response that: 1) Apologizes for the issue, 2) Provides clear instructions for the replacement process, 3) Explains how to transfer settings from the old device to the new one, and 4) Provides an estimated timeline."},
                    {"role": "user", "content": customer_inquiry}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
        },
        "technical_support": {
            "id": "handle_technical_support",
            "type": "llm",
            "params": {
                "provider": "openai",
                "model": "gpt-4",
                "prompt": [
                    {"role": "system", "content": "You are a technical support specialist. Generate a response that: 1) Acknowledges the technical issue, 2) Provides troubleshooting steps to try first, 3) Explains how to contact direct technical support if needed."},
                    {"role": "user", "content": customer_inquiry}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
        },
        "shipping_issue": {
            "id": "handle_shipping_issue",
            "type": "llm",
            "params": {
                "provider": "openai",
                "model": "gpt-4",
                "prompt": [
                    {"role": "system", "content": "You are a shipping and logistics specialist. Generate a response that: 1) Apologizes for the shipping issue, 2) Explains the process for reporting damaged packages, 3) Provides next steps for resolution."},
                    {"role": "user", "content": customer_inquiry}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
        }
    }
    
    # Default handler for other categories
    default_handler = {
        "id": "handle_general_inquiry",
        "type": "llm",
        "params": {
            "provider": "openai",
            "model": "gpt-4",
            "prompt": [
                {"role": "system", "content": "You are a customer service representative. Generate a helpful response to this customer inquiry."},
                {"role": "user", "content": customer_inquiry}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
    }
    
    # Select the appropriate handler based on classification
    handler = next_steps.get(inquiry_type, default_handler)
    
    # Execute the handler step
    logger.info(f"Executing handler: {handler['id']}")
    result = execute_step(
        step_id=handler["id"],
        step_type=handler["type"],
        params=handler["params"]
    )
    
    if not result["success"]:
        logger.error(f"Handler step failed: {result.get('error', 'Unknown error')}")
        return False
    
    # Get the response
    response = result["result"].get("content", "")
    
    # Save the response
    with open("customer_response.txt", "w") as f:
        f.write(f"Inquiry Type: {inquiry_type}\n\n")
        f.write("Customer Inquiry:\n")
        f.write(customer_inquiry)
        f.write("\n\nGenerated Response:\n")
        f.write(response)
    
    logger.info("Customer response generated and saved to customer_response.txt")
    logger.info("LLM Decision workflow completed successfully")
    
    return True

# -------------------------------------------------------------------- #
# Combined Workflow Examples
# -------------------------------------------------------------------- #

def combined_customer_onboarding():
    """
    End-to-end workflow that combines desktop, browser, and LLM automation
    for a complete customer onboarding process.
    
    This demonstrates:
    - Integration of multiple automation types
    - Complex workflow orchestration
    - Real-world business process automation
    """
    logger.info("Running Combined Customer Onboarding workflow")
    
    # Check if required runners are available
    if not DESKTOP_AVAILABLE:
        logger.warning("Desktop automation not available. Some steps will be skipped.")
    
    if not BROWSER_AVAILABLE:
        logger.warning("Browser automation not available. Some steps will be skipped.")
    
    # Step 1: Generate customer onboarding documents using LLM
    logger.info("Step 1: Generating onboarding documents")
    
    customer_info = {
        "name": "Acme Corporation",
        "industry": "Manufacturing",
        "size": "Medium (100-500 employees)",
        "contact": "John Smith, CTO",
        "email": "john.smith@acmecorp.example",
        "phone": "(555) 123-4567",
        "requirements": "Cloud-based inventory management with real-time analytics and mobile access"
    }
    
    llm_step = {
        "id": "generate_onboarding_docs",
        "type": "llm",
        "params": {
            "provider": "openai",
            "model": "gpt-4",
            "prompt": [
                {"role": "system", "content": "You are a customer onboarding specialist. Generate a complete onboarding package including: 1) Welcome letter, 2) Implementation timeline, 3) Required information checklist, 4) Next steps. Format your response in Markdown."},
                {"role": "user", "content": f"Generate an onboarding package for a new customer with the following information:\n\n{json.dumps(customer_info, indent=2)}"}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
    }
    
    result = execute_step(
        step_id=llm_step["id"],
        step_type=llm_step["type"],
        params=llm_step["params"]
    )
    
    if not result["success"]:
        logger.error(f"Failed to generate onboarding documents: {result.get('error', 'Unknown error')}")
        return False
    
    onboarding_docs = result["result"].get("content", "")
    
    # Save the generated documents
    with open("onboarding_package.md", "w") as f:
        f.write(onboarding_docs)
    
    logger.info("Onboarding documents generated and saved to onboarding_package.md")
    
    # Step 2: Create customer account in web portal (Browser automation)
    if BROWSER_AVAILABLE:
        logger.info("Step 2: Creating customer account in web portal")
        
        browser_step = {
            "id": "create_customer_account",
            "type": "browser",
            "params": {
                "browser_type": "chromium",
                "headless": True,
                "actions": [
                    # Note: This is a demonstration. In a real workflow, you would use your actual customer portal URL
                    {"type": "goto", "url": "https://example.com/customer-portal", "wait_until": "networkidle"},
                    {"type": "click", "selector": "#create-account-button"},
                    {"type": "fill", "selector": "#company-name", "text": customer_info["name"]},
                    {"type": "fill", "selector": "#industry", "text": customer_info["industry"]},
                    {"type": "fill", "selector": "#contact-name", "text": customer_info["contact"]},
                    {"type": "fill", "selector": "#email", "text": customer_info["email"]},
                    {"type": "fill", "selector": "#phone", "text": customer_info["phone"]},
                    {"type": "fill", "selector": "#requirements", "text": customer_info["requirements"]},
                    {"type": "screenshot", "filename": "account_creation_form.png"},
                    # In a real workflow, you would submit the form
                    # {"type": "click", "selector": "#submit-button"},
                    # {"type": "wait_for_navigation", "wait_until": "networkidle"},
                    # {"type": "screenshot", "filename": "account_creation_confirmation.png"}
                ],
                "timeout": 60
            }
        }
        
        logger.info("Browser automation would create the customer account here")
        logger.info("(Skipping actual form submission in this demo)")
    else:
        logger.info("Skipping web portal account creation (browser automation not available)")
    
    # Step 3: Update local CRM system (Desktop automation)
    if DESKTOP_AVAILABLE:
        logger.info("Step 3: Updating local CRM system")
        
        desktop_step = {
            "id": "update_crm",
            "type": "desktop",
            "params": {
                "actions": [
                    # Open CRM application (simulated with Notepad)
                    {"type": "hotkey", "keys": ["win", "r"]},
                    {"type": "wait", "duration": 0.5},
                    {"type": "type", "text": "notepad", "interval": 0.05},
                    {"type": "press", "key": "enter"},
                    {"type": "wait", "duration": 1.5},
                    
                    # Enter customer information
                    {"type": "type", "text": "=== NEW CUSTOMER RECORD ===\n", "interval": 0.05},
                    {"type": "type", "text": f"Company: {customer_info['name']}\n", "interval": 0.05},
                    {"type": "type", "text": f"Industry: {customer_info['industry']}\n", "interval": 0.05},
                    {"type": "type", "text": f"Size: {customer_info['size']}\n", "interval": 0.05},
                    {"type": "type", "text": f"Contact: {customer_info['contact']}\n", "interval": 0.05},
                    {"type": "type", "text": f"Email: {customer_info['email']}\n", "interval": 0.05},
                    {"type": "type", "text": f"Phone: {customer_info['phone']}\n", "interval": 0.05},
                    {"type": "type", "text": f"Requirements: {customer_info['requirements']}\n", "interval": 0.05},
                    {"type": "type", "text": f"Onboarding Date: {datetime.now().strftime('%Y-%m-%d')}\n", "interval": 0.05},
                    {"type": "wait", "duration": 1},
                    
                    # Save the file (simulating CRM update)
                    {"type": "hotkey", "keys": ["ctrl", "s"]},
                    {"type": "wait", "duration": 1},
                    {"type": "type", "text": f"crm_record_{customer_info['name'].replace(' ', '_')}.txt", "interval": 0.05},
                    {"type": "press", "key": "enter"},
                    {"type": "wait", "duration": 1},
                    
                    # Close the application
                    {"type": "hotkey", "keys": ["alt", "f4"]},
                    {"type": "wait", "duration": 0.5}
                ],
                "timeout": 60
            }
        }
        
        logger.info("Desktop automation would update the CRM here")
        logger.info("(Simulated with Notepad in this demo)")
    else:
        logger.info("Skipping local CRM update (desktop automation not available)")
    
    # Step 4: Generate follow-up email using LLM
    logger.info("Step 4: Generating follow-up email")
    
    llm_step = {
        "id": "generate_followup_email",
        "type": "llm",
        "params": {
            "provider": "openai",
            "model": "gpt-4",
            "prompt": [
                {"role": "system", "content": "You are a customer success manager. Generate a follow-up email to send to a new customer after their onboarding has been initiated. The email should: 1) Welcome them, 2) Summarize what has been done so far, 3) Explain next steps, 4) Provide your contact information for questions."},
                {"role": "user", "content": f"Generate a follow-up email for this new customer:\n\n{json.dumps(customer_info, indent=2)}"}
            ],
            "temperature": 0.7,
            "max_tokens": 800
        }
    }
    
    result = execute_step(
        step_id=llm_step["id"],
        step_type=llm_step["type"],
        params=llm_step["params"]
    )
    
    if not result["success"]:
        logger.error(f"Failed to generate follow-up email: {result.get('error', 'Unknown error')}")
        return False
    
    followup_email = result["result"].get("content", "")
    
    # Save the generated email
    with open("followup_email.txt", "w") as f:
        f.write(followup_email)
    
    logger.info("Follow-up email generated and saved to followup_email.txt")
    
    # Final step: Send email notification (simulated)
    logger.info("Step 5: Sending email notification (simulated)")
    
    # In a real workflow, you would integrate with an email sending service
    # For this demo, we'll just log it
    logger.info(f"Email would be sent to: {customer_info['email']}")
    logger.info("Subject: Welcome to Our Platform - Your Onboarding is Underway!")
    
    logger.info("Combined Customer Onboarding workflow completed successfully")
    return True

# -------------------------------------------------------------------- #
# Main Function
# -------------------------------------------------------------------- #

def main():
    """
    Main function to run the demo workflows.
    """
    parser = argparse.ArgumentParser(description="Run enhanced AI Engine demo workflows")
    parser.add_argument("workflow_type", choices=["desktop", "browser", "llm", "combined", "all"],
                        help="Type of workflow to run")
    parser.add_argument("workflow_name", nargs="?", default=None,
                        help="Specific workflow to run (optional)")
    
    args = parser.parse_args()
    
    # Dictionary of available workflows
    workflows = {
        "desktop": {
            "screenshot_tool": desktop_screenshot_tool,
            "form_filler": desktop_form_filler,
            "file_organizer": desktop_file_organizer
        },
        "browser": {
            "data_extraction": browser_data_extraction,
            "form_submission": browser_form_submission,
            "multi_page_workflow": browser_multi_page_workflow
        },
        "llm": {
            "content_generator": llm_content_generator,
            "data_extraction": llm_data_extraction,
            "decision_workflow": llm_decision_workflow
        },
        "combined": {
            "customer_onboarding": combined_customer_onboarding
        }
    }
    
    # Run all workflows of a specific type
    if args.workflow_name is None:
        if args.workflow_type == "all":
            logger.info("Running all workflows")
            for workflow_type, type_workflows in workflows.items():
                for name, func in type_workflows.items():
                    logger.info(f"Running {workflow_type}/{name}")
                    func()
        else:
            logger.info(f"Running all {args.workflow_type} workflows")
            for name, func in workflows[args.workflow_type].items():
                logger.info(f"Running {args.workflow_type}/{name}")
                func()
    # Run a specific workflow
    else:
        if args.workflow_name in workflows[args.workflow_type]:
            logger.info(f"Running {args.workflow_type}/{args.workflow_name}")
            workflows[args.workflow_type][args.workflow_name]()
        else:
            logger.error(f"Unknown workflow: {args.workflow_name}")
            logger.info(f"Available {args.workflow_type} workflows: {', '.join(workflows[args.workflow_type].keys())}")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
