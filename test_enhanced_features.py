#!/usr/bin/env python3
"""
Test Enhanced Features
======================

This script tests all the enhanced features of the Process 13 system including:
- Dashboard API endpoints
- Recording studio functionality 
- NLP command processing
- System health monitoring
- WebSocket connectivity
"""

import json
import time
import asyncio
import websockets
import requests
from datetime import datetime

API_BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

def print_test(name):
    print(f"\n{Colors.BLUE}{Colors.BOLD}🧪 Testing: {name}{Colors.ENDC}")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.ENDC}")

def test_dashboard_endpoints():
    """Test all dashboard-related API endpoints"""
    print_test("Dashboard API Endpoints")
    
    # Test dashboard stats
    try:
        response = requests.get(f"{API_BASE}/api/dashboard/stats")
        if response.status_code == 200:
            data = response.json()
            print_success(f"Dashboard stats: {data['workflows_count']} workflows, {data['hours_saved']} hours saved")
        else:
            print_error(f"Dashboard stats failed: {response.status_code}")
    except Exception as e:
        print_error(f"Dashboard stats error: {e}")
    
    # Test recent workflows
    try:
        response = requests.get(f"{API_BASE}/api/dashboard/recent-workflows")
        if response.status_code == 200:
            workflows = response.json()
            print_success(f"Recent workflows: {len(workflows)} workflows found")
            for wf in workflows[:2]:  # Show first 2
                print_info(f"  - {wf['name']}: {wf['status']} ({wf['efficiency']}% efficiency)")
        else:
            print_error(f"Recent workflows failed: {response.status_code}")
    except Exception as e:
        print_error(f"Recent workflows error: {e}")

def test_system_health():
    """Test system health monitoring"""
    print_test("System Health Monitoring")
    
    try:
        response = requests.get(f"{API_BASE}/api/system/health/detailed")
        if response.status_code == 200:
            health = response.json()
            print_success(f"System health: {health['overall_status']}")
            print_info(f"  - API: {health['api_status']}")
            print_info(f"  - Database: {health['database_status']}")
            print_info(f"  - AI Engine: {health['ai_engine_status']}")
            print_info(f"  - Uptime: {health['uptime']}")
        else:
            print_error(f"System health failed: {response.status_code}")
    except Exception as e:
        print_error(f"System health error: {e}")

def test_recording_studio():
    """Test recording studio functionality"""
    print_test("Recording Studio")
    
    # Start recording
    try:
        start_data = {"workflow_name": "Test Automation Workflow"}
        response = requests.post(f"{API_BASE}/api/recording/start", json=start_data)
        if response.status_code == 200:
            session = response.json()
            session_id = session['session_id']
            print_success(f"Recording started: {session_id}")
            
            # Wait a moment
            time.sleep(2)
            
            # Stop recording
            response = requests.post(f"{API_BASE}/api/recording/stop/{session_id}")
            if response.status_code == 200:
                print_success("Recording stopped successfully")
            else:
                print_error(f"Recording stop failed: {response.status_code}")
                
        else:
            print_error(f"Recording start failed: {response.status_code}")
    except Exception as e:
        print_error(f"Recording error: {e}")

def test_nlp_processing():
    """Test NLP command processing"""
    print_test("NLP Command Processing")
    
    test_commands = [
        "create workflow for invoice processing",
        "run workflow for data analysis", 
        "check system status",
        "automate email responses"
    ]
    
    for command in test_commands:
        try:
            data = {"command": command}
            response = requests.post(f"{API_BASE}/api/nlp/parse-command", json=data)
            if response.status_code == 200:
                result = response.json()
                confidence = result['confidence'] * 100
                print_success(f"Command '{command}' -> {result['parsed_intent']} ({confidence:.1f}%)")
            else:
                print_error(f"NLP processing failed for '{command}': {response.status_code}")
        except Exception as e:
            print_error(f"NLP error for '{command}': {e}")

def test_analytics():
    """Test analytics endpoints"""
    print_test("Analytics Endpoints")
    
    # Test ROI analytics
    try:
        response = requests.get(f"{API_BASE}/api/analytics/roi")
        if response.status_code == 200:
            data = response.json()
            print_success(f"ROI Analytics: ${data['total_cost_savings']} saved, {data['automation_rate']}% automation rate")
        else:
            print_error(f"ROI analytics failed: {response.status_code}")
    except Exception as e:
        print_error(f"ROI analytics error: {e}")
    
    # Test performance metrics
    try:
        response = requests.get(f"{API_BASE}/api/analytics/performance")
        if response.status_code == 200:
            data = response.json()
            print_success(f"Performance: {data['cpu_usage']}% CPU, {data['memory_usage']}% memory")
        else:
            print_error(f"Performance metrics failed: {response.status_code}")
    except Exception as e:
        print_error(f"Performance metrics error: {e}")

async def test_websocket_connection():
    """Test WebSocket real-time connectivity"""
    print_test("WebSocket Real-time Connection")
    
    try:
        uri = f"{WS_BASE}/ws/notifications"
        async with websockets.connect(uri) as websocket:
            print_success("WebSocket connected successfully")
            
            # Send a test message
            await websocket.send(json.dumps({
                "type": "test",
                "message": "Hello from test client"
            }))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print_success(f"WebSocket response: {response}")
            except asyncio.TimeoutError:
                print_warning("WebSocket timeout (this is expected)")
                
    except Exception as e:
        print_error(f"WebSocket connection failed: {e}")

def test_original_endpoints():
    """Test original API endpoints still work"""
    print_test("Original API Endpoints")
    
    # Test health check
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            print_success("Health check endpoint working")
        else:
            print_error(f"Health check failed: {response.status_code}")
    except Exception as e:
        print_error(f"Health check error: {e}")
    
    # Test ping
    try:
        response = requests.get(f"{API_BASE}/ping")
        if response.status_code == 200:
            print_success("Ping endpoint working")
        else:
            print_error(f"Ping failed: {response.status_code}")
    except Exception as e:
        print_error(f"Ping error: {e}")

def main():
    """Run all tests"""
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}🚀 Process 13 Enhanced Features Test Suite{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run synchronous tests
    test_original_endpoints()
    test_dashboard_endpoints()
    test_system_health()
    test_recording_studio()
    test_nlp_processing()
    test_analytics()
    
    # Run WebSocket test
    print_info("Testing WebSocket connection...")
    asyncio.run(test_websocket_connection())
    
    print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.GREEN}{Colors.BOLD}🎉 Test Suite Complete!{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}")
    
    print(f"\n{Colors.BLUE}📊 Frontend URLs:{Colors.ENDC}")
    print(f"• Enhanced Dashboard: http://localhost:3001/interactive_ui_enhanced.html")
    print(f"• Original Dashboard: http://localhost:3001/interactive_ui.html")
    print(f"• Full UI Preview: http://localhost:3001/user_interface_preview.html")
    
    print(f"\n{Colors.BLUE}🔧 API Documentation:{Colors.ENDC}")
    print(f"• FastAPI Docs: http://localhost:8000/docs")
    print(f"• API Base: http://localhost:8000")

if __name__ == "__main__":
    main()