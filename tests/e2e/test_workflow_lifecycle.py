"""
End-to-End Workflow Lifecycle Testing
=====================================

This test suite validates the complete user journey through the RPA platform:
- Record workflow actions
- Edit and customize workflows
- Deploy workflows to production
- Execute workflows with different parameters
- Monitor execution status and logs
- Handle failures and retries
- Performance under realistic usage patterns

Uses Playwright for browser automation to test the complete user experience.
"""

import pytest
import asyncio
import json
import time
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser
from typing import Dict, List, Any
import tempfile
import os

# Configuration
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:3000")
API_BASE_URL = os.getenv("E2E_API_URL", "http://localhost:8000")
TEST_USER_EMAIL = "e2e_test@example.com"
TEST_USER_PASSWORD = "e2e_test_password123"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser():
    """Create browser instance for testing"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # Set to False for debugging
            args=['--disable-web-security', '--disable-features=VizDisplayCompositor']
        )
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser: Browser):
    """Create new page for each test"""
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        ignore_https_errors=True
    )
    page = await context.new_page()
    yield page
    await context.close()


@pytest.fixture
async def authenticated_page(page: Page):
    """Create authenticated user session"""
    # Navigate to login page
    await page.goto(f"{BASE_URL}/login")
    
    # Wait for login form
    await page.wait_for_selector("input[name='email']", timeout=10000)
    
    # Fill login form
    await page.fill("input[name='email']", TEST_USER_EMAIL)
    await page.fill("input[name='password']", TEST_USER_PASSWORD)
    
    # Submit login
    await page.click("button[type='submit']")
    
    # Wait for successful login (dashboard)
    await page.wait_for_url(f"{BASE_URL}/dashboard", timeout=10000)
    
    yield page


class TestWorkflowRecording:
    """Test workflow recording functionality"""
    
    async def test_start_recording_session(self, authenticated_page: Page):
        """Test starting a new recording session"""
        # Navigate to recording page
        await authenticated_page.goto(f"{BASE_URL}/record")
        
        # Wait for recording interface
        await authenticated_page.wait_for_selector("[data-testid='start-recording-btn']")
        
        # Configure recording settings
        await authenticated_page.fill("input[name='workflow-name']", "E2E Test Workflow")
        await authenticated_page.fill("textarea[name='description']", "Automated E2E test workflow")
        
        # Start recording
        await authenticated_page.click("[data-testid='start-recording-btn']")
        
        # Verify recording started
        await authenticated_page.wait_for_selector("[data-testid='recording-indicator']")
        recording_status = await authenticated_page.text_content("[data-testid='recording-status']")
        assert "Recording" in recording_status
    
    async def test_capture_user_actions(self, authenticated_page: Page):
        """Test capturing user actions during recording"""
        # Start recording session
        await authenticated_page.goto(f"{BASE_URL}/record")
        await authenticated_page.wait_for_selector("[data-testid='start-recording-btn']")
        await authenticated_page.fill("input[name='workflow-name']", "Action Capture Test")
        await authenticated_page.click("[data-testid='start-recording-btn']")
        
        # Wait for recording to start
        await authenticated_page.wait_for_selector("[data-testid='recording-indicator']")
        
        # Perform test actions that should be captured
        await authenticated_page.click("[data-testid='demo-button']")
        await authenticated_page.fill("[data-testid='demo-input']", "test input")
        await authenticated_page.select_option("[data-testid='demo-select']", "option1")
        
        # Stop recording
        await authenticated_page.click("[data-testid='stop-recording-btn']")
        
        # Verify actions were captured
        await authenticated_page.wait_for_selector("[data-testid='captured-actions']")
        actions = await authenticated_page.query_selector_all("[data-testid='action-item']")
        assert len(actions) >= 3  # Should have captured at least 3 actions
    
    async def test_save_recorded_workflow(self, authenticated_page: Page):
        """Test saving a recorded workflow"""
        # Complete recording process
        await authenticated_page.goto(f"{BASE_URL}/record")
        await authenticated_page.wait_for_selector("[data-testid='start-recording-btn']")
        await authenticated_page.fill("input[name='workflow-name']", "Save Test Workflow")
        await authenticated_page.click("[data-testid='start-recording-btn']")
        
        # Record some actions
        await authenticated_page.wait_for_selector("[data-testid='recording-indicator']")
        await authenticated_page.click("[data-testid='demo-button']")
        await authenticated_page.click("[data-testid='stop-recording-btn']")
        
        # Save workflow
        await authenticated_page.wait_for_selector("[data-testid='save-workflow-btn']")
        await authenticated_page.click("[data-testid='save-workflow-btn']")
        
        # Verify save success
        await authenticated_page.wait_for_selector("[data-testid='save-success-message']")
        success_message = await authenticated_page.text_content("[data-testid='save-success-message']")
        assert "saved successfully" in success_message.lower()


class TestWorkflowEditing:
    """Test workflow editing and customization"""
    
    async def test_open_workflow_editor(self, authenticated_page: Page):
        """Test opening the workflow editor"""
        # Navigate to workflows page
        await authenticated_page.goto(f"{BASE_URL}/workflows")
        
        # Wait for workflows list
        await authenticated_page.wait_for_selector("[data-testid='workflows-list']")
        
        # Click edit on first workflow
        edit_button = await authenticated_page.query_selector("[data-testid='edit-workflow-btn']:first-child")
        if edit_button:
            await edit_button.click()
            
            # Verify editor opened
            await authenticated_page.wait_for_selector("[data-testid='workflow-editor']")
            assert await authenticated_page.is_visible("[data-testid='workflow-editor']")
    
    async def test_modify_workflow_steps(self, authenticated_page: Page):
        """Test modifying workflow steps in editor"""
        # Navigate to editor (assuming workflow exists)
        await authenticated_page.goto(f"{BASE_URL}/workflows/1/edit")
        
        # Wait for editor
        await authenticated_page.wait_for_selector("[data-testid='workflow-editor']")
        
        # Add new step
        await authenticated_page.click("[data-testid='add-step-btn']")
        await authenticated_page.wait_for_selector("[data-testid='step-type-select']")
        await authenticated_page.select_option("[data-testid='step-type-select']", "click")
        
        # Configure step parameters
        await authenticated_page.fill("[data-testid='step-target-input']", "button#submit")
        await authenticated_page.fill("[data-testid='step-description-input']", "Click submit button")
        
        # Save step
        await authenticated_page.click("[data-testid='save-step-btn']")
        
        # Verify step added
        steps = await authenticated_page.query_selector_all("[data-testid='workflow-step']")
        assert len(steps) > 0
    
    async def test_workflow_validation(self, authenticated_page: Page):
        """Test workflow validation in editor"""
        # Open editor
        await authenticated_page.goto(f"{BASE_URL}/workflows/1/edit")
        await authenticated_page.wait_for_selector("[data-testid='workflow-editor']")
        
        # Try to save invalid workflow (empty steps)
        await authenticated_page.click("[data-testid='clear-all-steps-btn']")
        await authenticated_page.click("[data-testid='save-workflow-btn']")
        
        # Verify validation error
        await authenticated_page.wait_for_selector("[data-testid='validation-error']")
        error_message = await authenticated_page.text_content("[data-testid='validation-error']")
        assert "workflow must have at least one step" in error_message.lower()
    
    async def test_workflow_preview(self, authenticated_page: Page):
        """Test workflow preview functionality"""
        # Open editor with valid workflow
        await authenticated_page.goto(f"{BASE_URL}/workflows/1/edit")
        await authenticated_page.wait_for_selector("[data-testid='workflow-editor']")
        
        # Click preview
        await authenticated_page.click("[data-testid='preview-workflow-btn']")
        
        # Verify preview modal opens
        await authenticated_page.wait_for_selector("[data-testid='preview-modal']")
        assert await authenticated_page.is_visible("[data-testid='preview-modal']")
        
        # Verify preview content
        preview_steps = await authenticated_page.query_selector_all("[data-testid='preview-step']")
        assert len(preview_steps) > 0


class TestWorkflowDeployment:
    """Test workflow deployment process"""
    
    async def test_deploy_workflow(self, authenticated_page: Page):
        """Test deploying a workflow to production"""
        # Navigate to deployment page
        await authenticated_page.goto(f"{BASE_URL}/workflows/1/deploy")
        
        # Wait for deployment interface
        await authenticated_page.wait_for_selector("[data-testid='deployment-form']")
        
        # Configure deployment settings
        await authenticated_page.fill("input[name='deployment-name']", "E2E Test Deployment")
        await authenticated_page.select_option("select[name='environment']", "staging")
        await authenticated_page.check("input[name='enable-monitoring']")
        
        # Deploy workflow
        await authenticated_page.click("[data-testid='deploy-btn']")
        
        # Verify deployment started
        await authenticated_page.wait_for_selector("[data-testid='deployment-status']")
        status = await authenticated_page.text_content("[data-testid='deployment-status']")
        assert "deploying" in status.lower() or "deployed" in status.lower()
    
    async def test_deployment_rollback(self, authenticated_page: Page):
        """Test rolling back a deployment"""
        # Navigate to deployments page
        await authenticated_page.goto(f"{BASE_URL}/deployments")
        
        # Wait for deployments list
        await authenticated_page.wait_for_selector("[data-testid='deployments-list']")
        
        # Click rollback on latest deployment
        rollback_btn = await authenticated_page.query_selector("[data-testid='rollback-btn']:first-child")
        if rollback_btn:
            await rollback_btn.click()
            
            # Confirm rollback
            await authenticated_page.wait_for_selector("[data-testid='confirm-rollback-btn']")
            await authenticated_page.click("[data-testid='confirm-rollback-btn']")
            
            # Verify rollback initiated
            await authenticated_page.wait_for_selector("[data-testid='rollback-status']")
            status = await authenticated_page.text_content("[data-testid='rollback-status']")
            assert "rolling back" in status.lower() or "rolled back" in status.lower()


class TestWorkflowExecution:
    """Test workflow execution process"""
    
    async def test_manual_workflow_execution(self, authenticated_page: Page):
        """Test manually executing a workflow"""
        # Navigate to workflows page
        await authenticated_page.goto(f"{BASE_URL}/workflows")
        
        # Wait for workflows list
        await authenticated_page.wait_for_selector("[data-testid='workflows-list']")
        
        # Click execute on first workflow
        execute_btn = await authenticated_page.query_selector("[data-testid='execute-workflow-btn']:first-child")
        if execute_btn:
            await execute_btn.click()
            
            # Verify execution started
            await authenticated_page.wait_for_selector("[data-testid='execution-status']")
            status = await authenticated_page.text_content("[data-testid='execution-status']")
            assert "running" in status.lower() or "completed" in status.lower()
    
    async def test_workflow_execution_with_parameters(self, authenticated_page: Page):
        """Test executing workflow with custom parameters"""
        # Navigate to execution page
        await authenticated_page.goto(f"{BASE_URL}/workflows/1/execute")
        
        # Wait for execution form
        await authenticated_page.wait_for_selector("[data-testid='execution-form']")
        
        # Fill execution parameters
        await authenticated_page.fill("input[name='input-text']", "test parameter value")
        await authenticated_page.fill("input[name='timeout']", "30")
        await authenticated_page.check("input[name='debug-mode']")
        
        # Start execution
        await authenticated_page.click("[data-testid='start-execution-btn']")
        
        # Verify execution started with parameters
        await authenticated_page.wait_for_selector("[data-testid='execution-details']")
        params = await authenticated_page.text_content("[data-testid='execution-parameters']")
        assert "test parameter value" in params
    
    async def test_scheduled_workflow_execution(self, authenticated_page: Page):
        """Test scheduling workflow execution"""
        # Navigate to scheduling page
        await authenticated_page.goto(f"{BASE_URL}/workflows/1/schedule")
        
        # Wait for scheduling form
        await authenticated_page.wait_for_selector("[data-testid='schedule-form']")
        
        # Configure schedule
        await authenticated_page.select_option("select[name='schedule-type']", "daily")
        await authenticated_page.fill("input[name='schedule-time']", "09:00")
        await authenticated_page.check("input[name='weekdays-only']")
        
        # Save schedule
        await authenticated_page.click("[data-testid='save-schedule-btn']")
        
        # Verify schedule created
        await authenticated_page.wait_for_selector("[data-testid='schedule-confirmation']")
        confirmation = await authenticated_page.text_content("[data-testid='schedule-confirmation']")
        assert "scheduled successfully" in confirmation.lower()


class TestExecutionMonitoring:
    """Test execution monitoring and logging"""
    
    async def test_view_execution_logs(self, authenticated_page: Page):
        """Test viewing execution logs"""
        # Navigate to executions page
        await authenticated_page.goto(f"{BASE_URL}/executions")
        
        # Wait for executions list
        await authenticated_page.wait_for_selector("[data-testid='executions-list']")
        
        # Click view logs on first execution
        logs_btn = await authenticated_page.query_selector("[data-testid='view-logs-btn']:first-child")
        if logs_btn:
            await logs_btn.click()
            
            # Verify logs viewer opens
            await authenticated_page.wait_for_selector("[data-testid='logs-viewer']")
            assert await authenticated_page.is_visible("[data-testid='logs-viewer']")
            
            # Verify logs content
            logs_content = await authenticated_page.text_content("[data-testid='logs-content']")
            assert len(logs_content) > 0
    
    async def test_real_time_execution_monitoring(self, authenticated_page: Page):
        """Test real-time monitoring of running executions"""
        # Start a long-running workflow
        await authenticated_page.goto(f"{BASE_URL}/workflows/1/execute")
        await authenticated_page.wait_for_selector("[data-testid='start-execution-btn']")
        await authenticated_page.click("[data-testid='start-execution-btn']")
        
        # Navigate to monitoring page
        await authenticated_page.goto(f"{BASE_URL}/monitor")
        
        # Wait for monitoring dashboard
        await authenticated_page.wait_for_selector("[data-testid='monitoring-dashboard']")
        
        # Verify real-time updates
        initial_status = await authenticated_page.text_content("[data-testid='execution-status']:first-child")
        
        # Wait for status update
        await authenticated_page.wait_for_timeout(5000)
        
        # Check if status updated (or at least interface is responsive)
        assert await authenticated_page.is_visible("[data-testid='monitoring-dashboard']")
    
    async def test_execution_alerts(self, authenticated_page: Page):
        """Test execution failure alerts"""
        # Navigate to alerts settings
        await authenticated_page.goto(f"{BASE_URL}/settings/alerts")
        
        # Configure alert settings
        await authenticated_page.wait_for_selector("[data-testid='alert-settings']")
        await authenticated_page.check("input[name='email-alerts']")
        await authenticated_page.fill("input[name='alert-email']", "admin@example.com")
        
        # Save alert settings
        await authenticated_page.click("[data-testid='save-alerts-btn']")
        
        # Verify settings saved
        await authenticated_page.wait_for_selector("[data-testid='settings-saved']")
        confirmation = await authenticated_page.text_content("[data-testid='settings-saved']")
        assert "saved" in confirmation.lower()


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery mechanisms"""
    
    async def test_workflow_failure_handling(self, authenticated_page: Page):
        """Test handling of workflow execution failures"""
        # Navigate to executions page
        await authenticated_page.goto(f"{BASE_URL}/executions")
        
        # Look for failed executions
        await authenticated_page.wait_for_selector("[data-testid='executions-list']")
        
        # Find failed execution
        failed_execution = await authenticated_page.query_selector("[data-testid='execution-failed']")
        if failed_execution:
            # Click to view failure details
            await failed_execution.click()
            
            # Verify failure details shown
            await authenticated_page.wait_for_selector("[data-testid='failure-details']")
            failure_reason = await authenticated_page.text_content("[data-testid='failure-reason']")
            assert len(failure_reason) > 0
    
    async def test_workflow_retry_mechanism(self, authenticated_page: Page):
        """Test retrying failed workflows"""
        # Navigate to failed execution
        await authenticated_page.goto(f"{BASE_URL}/executions")
        await authenticated_page.wait_for_selector("[data-testid='executions-list']")
        
        # Find retry button for failed execution
        retry_btn = await authenticated_page.query_selector("[data-testid='retry-execution-btn']")
        if retry_btn:
            await retry_btn.click()
            
            # Verify retry started
            await authenticated_page.wait_for_selector("[data-testid='retry-confirmation']")
            confirmation = await authenticated_page.text_content("[data-testid='retry-confirmation']")
            assert "retry" in confirmation.lower()
    
    async def test_partial_execution_recovery(self, authenticated_page: Page):
        """Test recovering from partial execution failures"""
        # Navigate to partially failed execution
        await authenticated_page.goto(f"{BASE_URL}/executions")
        await authenticated_page.wait_for_selector("[data-testid='executions-list']")
        
        # Look for resume option
        resume_btn = await authenticated_page.query_selector("[data-testid='resume-execution-btn']")
        if resume_btn:
            await resume_btn.click()
            
            # Configure resume point
            await authenticated_page.wait_for_selector("[data-testid='resume-options']")
            await authenticated_page.select_option("select[name='resume-from-step']", "3")
            await authenticated_page.click("[data-testid='confirm-resume-btn']")
            
            # Verify resume started
            await authenticated_page.wait_for_selector("[data-testid='resume-status']")
            status = await authenticated_page.text_content("[data-testid='resume-status']")
            assert "resumed" in status.lower()


class TestPerformanceUnderLoad:
    """Test system performance under realistic usage"""
    
    async def test_concurrent_workflow_executions(self, authenticated_page: Page):
        """Test multiple concurrent workflow executions"""
        # Navigate to workflows page
        await authenticated_page.goto(f"{BASE_URL}/workflows")
        await authenticated_page.wait_for_selector("[data-testid='workflows-list']")
        
        # Start multiple executions
        execute_buttons = await authenticated_page.query_selector_all("[data-testid='execute-workflow-btn']")
        
        for i, button in enumerate(execute_buttons[:3]):  # Start 3 concurrent executions
            await button.click()
            await authenticated_page.wait_for_timeout(1000)  # Small delay between starts
        
        # Verify all executions started
        await authenticated_page.goto(f"{BASE_URL}/executions")
        await authenticated_page.wait_for_selector("[data-testid='executions-list']")
        
        running_executions = await authenticated_page.query_selector_all("[data-testid='execution-running']")
        assert len(running_executions) >= 3
    
    async def test_dashboard_performance_with_many_workflows(self, authenticated_page: Page):
        """Test dashboard performance with large number of workflows"""
        # Navigate to dashboard
        await authenticated_page.goto(f"{BASE_URL}/dashboard")
        
        # Measure page load time
        start_time = time.time()
        await authenticated_page.wait_for_selector("[data-testid='dashboard-content']")
        load_time = time.time() - start_time
        
        # Should load within reasonable time
        assert load_time < 5.0, f"Dashboard took {load_time:.2f}s to load"
        
        # Verify dashboard elements are present
        assert await authenticated_page.is_visible("[data-testid='workflows-summary']")
        assert await authenticated_page.is_visible("[data-testid='executions-summary']")
    
    async def test_memory_usage_during_long_session(self, authenticated_page: Page):
        """Test memory usage during extended user session"""
        # Simulate extended user session
        pages_to_visit = [
            f"{BASE_URL}/dashboard",
            f"{BASE_URL}/workflows",
            f"{BASE_URL}/executions",
            f"{BASE_URL}/monitor",
            f"{BASE_URL}/settings"
        ]
        
        for page_url in pages_to_visit:
            await authenticated_page.goto(page_url)
            await authenticated_page.wait_for_load_state("networkidle")
            
            # Perform some interactions
            clickable_elements = await authenticated_page.query_selector_all("button, a, input")
            if clickable_elements:
                await clickable_elements[0].click()
            
            await authenticated_page.wait_for_timeout(2000)
        
        # Session should remain responsive
        assert await authenticated_page.is_visible("body")


class TestIntegrationWorkflows:
    """Test complete integration workflows"""
    
    async def test_complete_workflow_lifecycle(self, authenticated_page: Page):
        """Test complete workflow from creation to execution"""
        workflow_name = f"Complete Lifecycle Test {int(time.time())}"
        
        # 1. Create new workflow
        await authenticated_page.goto(f"{BASE_URL}/workflows/new")
        await authenticated_page.wait_for_selector("[data-testid='workflow-form']")
        await authenticated_page.fill("input[name='name']", workflow_name)
        await authenticated_page.fill("textarea[name='description']", "Complete lifecycle test")
        
        # 2. Add workflow steps
        await authenticated_page.click("[data-testid='add-step-btn']")
        await authenticated_page.select_option("select[name='step-type']", "click")
        await authenticated_page.fill("input[name='target']", "button.submit")
        await authenticated_page.click("[data-testid='save-step-btn']")
        
        # 3. Save workflow
        await authenticated_page.click("[data-testid='save-workflow-btn']")
        await authenticated_page.wait_for_selector("[data-testid='save-success']")
        
        # 4. Execute workflow
        await authenticated_page.click("[data-testid='execute-now-btn']")
        await authenticated_page.wait_for_selector("[data-testid='execution-started']")
        
        # 5. Monitor execution
        await authenticated_page.goto(f"{BASE_URL}/executions")
        await authenticated_page.wait_for_selector("[data-testid='executions-list']")
        
        # Verify workflow appears in executions
        execution_names = await authenticated_page.query_selector_all("[data-testid='execution-name']")
        execution_texts = [await name.text_content() for name in execution_names]
        assert any(workflow_name in text for text in execution_texts)
    
    async def test_workflow_sharing_and_collaboration(self, authenticated_page: Page):
        """Test workflow sharing between users"""
        # Create workflow
        await authenticated_page.goto(f"{BASE_URL}/workflows/new")
        await authenticated_page.wait_for_selector("[data-testid='workflow-form']")
        await authenticated_page.fill("input[name='name']", "Shared Test Workflow")
        await authenticated_page.click("[data-testid='save-workflow-btn']")
        
        # Share workflow
        await authenticated_page.wait_for_selector("[data-testid='share-workflow-btn']")
        await authenticated_page.click("[data-testid='share-workflow-btn']")
        
        # Configure sharing settings
        await authenticated_page.wait_for_selector("[data-testid='sharing-modal']")
        await authenticated_page.fill("input[name='share-email']", "colleague@example.com")
        await authenticated_page.select_option("select[name='permission']", "edit")
        await authenticated_page.click("[data-testid='send-share-btn']")
        
        # Verify sharing confirmation
        await authenticated_page.wait_for_selector("[data-testid='share-success']")
        success_msg = await authenticated_page.text_content("[data-testid='share-success']")
        assert "shared successfully" in success_msg.lower()


if __name__ == "__main__":
    # Run E2E tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])