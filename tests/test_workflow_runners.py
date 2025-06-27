import os
import json
import time
import pytest
import responses
import requests  # needed for RequestException in timeout test
from unittest import mock
from datetime import datetime

# Import the modules to test
from ai_engine.workflow_runners import (
    Runner, ShellRunner, HttpRunner, LLMRunner, ApprovalRunner, 
    DecisionRunner, RunnerFactory, execute_step
)

# -------------------------------------------------------------------- #
# Fixtures
# -------------------------------------------------------------------- #

@pytest.fixture
def sample_context():
    """Provide a sample context with variables for testing."""
    return {
        "user_id": 123,
        "username": "testuser",
        "email": "test@example.com",
        "is_admin": True,
        "score": 85.5,
        "items": ["item1", "item2", "item3"],
        "threshold": 80,
        "status": "success"
    }

@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for testing shell commands."""
    with mock.patch('subprocess.run') as mock_run:
        # Configure the mock to return a successful result by default
        mock_process = mock.Mock()
        mock_process.stdout = "Command output"
        mock_process.stderr = ""
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        yield mock_run

@pytest.fixture
def mock_openai():
    """Mock OpenAI client for testing LLM integration."""
    with mock.patch('openai.OpenAI') as mock_openai_class:
        # Configure the mock client
        mock_client = mock.Mock()
        
        # Mock chat completions
        mock_chat = mock.Mock()
        mock_chat_response = mock.Mock()
        mock_chat_response.choices = [mock.Mock()]
        mock_chat_response.choices[0].message.content = "This is a mock response from the LLM."
        mock_chat_response.usage = {"total_tokens": 150, "prompt_tokens": 50, "completion_tokens": 100}
        mock_chat.completions.create.return_value = mock_chat_response
        mock_client.chat = mock_chat
        
        # Mock completions (legacy)
        mock_completions = mock.Mock()
        mock_completion_response = mock.Mock()
        mock_completion_response.choices = [mock.Mock()]
        mock_completion_response.choices[0].text = "This is a mock response from the legacy completion API."
        mock_completion_response.usage = {"total_tokens": 120, "prompt_tokens": 40, "completion_tokens": 80}
        mock_completions.create.return_value = mock_completion_response
        mock_client.completions = mock_completions
        
        # Set up the client instance
        mock_openai_class.return_value = mock_client
        
        yield mock_openai_class

# -------------------------------------------------------------------- #
# ShellRunner Tests
# -------------------------------------------------------------------- #

class TestShellRunner:
    
    def test_successful_command(self, mock_subprocess):
        """Test that a successful command returns the expected result."""
        # Arrange
        runner = ShellRunner("test_step", {"command": "echo 'Hello World'"})
        
        # Act
        result = runner.execute()
        
        # Assert
        assert result["success"] is True
        assert "result" in result
        assert result["result"]["exit_code"] == 0
        assert mock_subprocess.call_count == 1
    
    def test_failed_command(self, mock_subprocess):
        """Test that a failed command returns an error."""
        # Arrange
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Command failed"
        runner = ShellRunner("test_step", {"command": "invalid_command"})
        
        # Act
        result = runner.execute()
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        # stderr is included only on success; ensure error message surfaces
        assert "command failed" in result["error"].lower()
    
    def test_variable_substitution(self, mock_subprocess, sample_context):
        """Test that variables in the command are substituted from context."""
        # Arrange
        runner = ShellRunner("test_step", {"command": "echo 'Hello ${username}'"})
        
        # Act
        result = runner.execute(sample_context)
        
        # Assert
        assert mock_subprocess.call_args[0][0] == "echo 'Hello testuser'"
    
    def test_timeout_handling(self, mock_subprocess):
        """Test that command timeout is handled correctly."""
        # Arrange
        mock_subprocess.side_effect = TimeoutError("Command timed out")
        runner = ShellRunner("test_step", {"command": "sleep 10", "timeout": 1})
        
        # Act
        result = runner.execute()
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "timed out" in result["error"].lower()
    
    def test_environment_variables(self, mock_subprocess):
        """Test that environment variables are passed correctly."""
        # Arrange
        runner = ShellRunner("test_step", {
            "command": "echo $TEST_VAR",
            "env": {"TEST_VAR": "test_value"}
        })
        
        # Act
        result = runner.execute()
        
        # Assert
        # Check that env was updated in the subprocess call
        called_env = mock_subprocess.call_args[1].get('env', {})
        assert "TEST_VAR" in called_env
        assert called_env["TEST_VAR"] == "test_value"

# -------------------------------------------------------------------- #
# HttpRunner Tests
# -------------------------------------------------------------------- #

class TestHttpRunner:
    
    @responses.activate
    def test_successful_get_request(self):
        """Test a successful GET request."""
        # Arrange
        responses.add(
            responses.GET,
            "https://api.example.com/data",
            json={"status": "success", "data": {"id": 1, "name": "Test"}},
            status=200
        )
        
        runner = HttpRunner("test_step", {"url": "https://api.example.com/data", "method": "GET"})
        
        # Act
        result = runner.execute()
        
        # Assert
        assert result["success"] is True
        assert result["result"]["status_code"] == 200
        assert result["result"]["body"]["status"] == "success"
    
    @responses.activate
    def test_successful_post_request(self):
        """Test a successful POST request with JSON body."""
        # Arrange
        responses.add(
            responses.POST,
            "https://api.example.com/data",
            json={"status": "created", "id": 123},
            status=201
        )
        
        runner = HttpRunner("test_step", {
            "url": "https://api.example.com/data",
            "method": "POST",
            "json": {"name": "Test", "value": 42}
        })
        
        # Act
        result = runner.execute()
        
        # Assert
        assert result["success"] is True
        assert result["result"]["status_code"] == 201
        assert result["result"]["body"]["status"] == "created"
    
    @responses.activate
    def test_failed_request(self):
        """Test handling of a failed request (4xx/5xx status code)."""
        # Arrange
        responses.add(
            responses.GET,
            "https://api.example.com/not-found",
            json={"error": "Resource not found"},
            status=404
        )
        
        runner = HttpRunner("test_step", {"url": "https://api.example.com/not-found", "method": "GET"})
        
        # Act
        result = runner.execute()
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        # On failure we no longer return 'result' key – error message must include status
        assert "404" in result["error"]
        # detailed backend message may vary, ensure generic phrase present
        assert "http request failed" in result["error"].lower()
    
    @responses.activate
    def test_variable_substitution(self, sample_context):
        """Test variable substitution in URL."""
        # Arrange
        responses.add(
            responses.GET,
            "https://api.example.com/users/123",
            json={"id": 123, "name": "testuser"},
            status=200
        )
        
        runner = HttpRunner("test_step", {"url": "https://api.example.com/users/${user_id}", "method": "GET"})
        
        # Act
        result = runner.execute(sample_context)
        
        # Assert
        assert result["success"] is True
        assert result["result"]["status_code"] == 200
    
    @responses.activate
    def test_request_timeout(self):
        """Test handling of request timeout."""
        # Arrange
        responses.add(
            responses.GET,
            "https://api.example.com/slow",
            body=requests.RequestException("Connection timed out")
        )
        
        runner = HttpRunner("test_step", {"url": "https://api.example.com/slow", "method": "GET", "timeout": 1})
        
        # Act
        result = runner.execute()
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "timed out" in result["error"].lower() or "request" in result["error"].lower()

# -------------------------------------------------------------------- #
# LLMRunner Tests
# -------------------------------------------------------------------- #

class TestLLMRunner:
    
    def test_openai_integration(self, mock_openai):
        """Test integration with OpenAI API."""
        # Arrange
        os.environ["OPENAI_API_KEY"] = "test-api-key"
        runner = LLMRunner("test_step", {
            "provider": "openai",
            "model": "gpt-4",
            "prompt": "Generate a test response"
        })
        
        # Act
        result = runner.execute()
        
        # Assert
        assert result["success"] is True
        assert "result" in result
        assert "content" in result["result"]
        assert isinstance(result["result"]["content"], str)
        assert mock_openai.call_count == 1
        assert mock_openai.call_args[1]["api_key"] == "test-api-key"
    
    def test_openai_chat_completion(self, mock_openai):
        """Test OpenAI chat completion API."""
        # Arrange
        os.environ["OPENAI_API_KEY"] = "test-api-key"
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Generate a test response"}
        ]
        runner = LLMRunner("test_step", {
            "provider": "openai",
            "model": "gpt-4",
            "prompt": messages
        })
        
        # Act
        result = runner.execute()
        
        # Assert
        assert result["success"] is True
        assert "result" in result
        assert "content" in result["result"]
        # Verify chat completion was called with messages
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.assert_called_once()
    
    def test_variable_substitution(self, mock_openai, sample_context):
        """Test variable substitution in prompt."""
        # Arrange
        os.environ["OPENAI_API_KEY"] = "test-api-key"
        runner = LLMRunner("test_step", {
            "provider": "openai",
            "model": "gpt-4",
            "prompt": "Hello ${username}, your score is ${score}"
        })
        
        # Act
        result = runner.execute(sample_context)
        
        # Assert
        assert result["success"] is True
        # Check that the substituted prompt was used
        mock_client = mock_openai.return_value
        assert "Hello testuser, your score is 85.5" in str(mock_client.completions.create.call_args)
    
    def test_missing_api_key(self, mock_openai):
        """Test error handling when API key is missing."""
        # Arrange
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
            
        runner = LLMRunner("test_step", {
            "provider": "openai",
            "model": "gpt-4",
            "prompt": "Generate a test response"
        })
        
        # Act
        result = runner.execute()
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "api key not provided" in result["error"].lower()
    
    def test_unsupported_provider(self):
        """Test error handling for unsupported LLM provider."""
        # Arrange
        runner = LLMRunner("test_step", {
            "provider": "unsupported",
            "model": "test-model",
            "prompt": "Generate a test response"
        })
        
        # Act
        result = runner.execute()
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "unsupported" in result["error"].lower()

# -------------------------------------------------------------------- #
# ApprovalRunner Tests
# -------------------------------------------------------------------- #

class TestApprovalRunner:
    
    @mock.patch('time.sleep')  # Mock sleep to speed up tests
    def test_approval_request_creation(self, mock_sleep):
        """Test creation of approval request."""
        # Arrange
        runner = ApprovalRunner("test_step", {
            "title": "Test Approval",
            "description": "Please approve this test",
            "approvers": ["user1@example.com", "user2@example.com"],
            "wait": False
        })
        
        # Act
        result = runner.execute()
        
        # Assert
        assert result["success"] is True
        assert "result" in result
        assert "approval_id" in result["result"]
        assert result["result"]["status"] == "pending"
        assert len(result["result"]["approvers"]) == 2
    
    @mock.patch('time.sleep')  # Mock sleep to speed up tests
    def test_wait_for_approval(self, mock_sleep):
        """Test waiting for approval."""
        # Arrange
        runner = ApprovalRunner("test_step", {
            "title": "Test Approval",
            "description": "Please approve this test",
            "approvers": ["user1@example.com"],
            "wait": True
        })
        
        # Act
        result = runner.execute()
        
        # Assert
        assert result["success"] is True
        assert "result" in result
        assert result["result"]["status"] == "approved"
        assert "approved_by" in result["result"]
        assert "approved_at" in result["result"]
        # Verify that sleep was called (simulating waiting)
        mock_sleep.assert_called_once()
    
    def test_variable_substitution(self, sample_context):
        """Test variable substitution in title and description."""
        # Arrange
        runner = ApprovalRunner("test_step", {
            "title": "Approval for ${username}",
            "description": "User ${username} with score ${score} needs approval",
            "approvers": ["admin@example.com"],
            "wait": False
        })
        
        # Act
        with mock.patch.object(runner, '_send_approval_notifications') as mock_send:
            result = runner.execute(sample_context)
        
        # Assert
        assert result["success"] is True
        # Check that variables were substituted in the notification call
        mock_send.assert_called_once()
        title_arg = mock_send.call_args[0][1]
        desc_arg = mock_send.call_args[0][2]
        assert "Approval for testuser" in title_arg
        assert "User testuser with score 85.5 needs approval" in desc_arg

# -------------------------------------------------------------------- #
# DecisionRunner Tests
# -------------------------------------------------------------------- #

class TestDecisionRunner:
    
    def test_condition_evaluation(self, sample_context):
        """Test evaluation of conditions."""
        # Arrange
        runner = DecisionRunner("test_step", {
            "conditions": [
                {"expression": "${score} > 90", "target": "high_score_path"},
                {"expression": "${score} > 70", "target": "medium_score_path"},
                {"expression": "${score} <= 70", "target": "low_score_path"}
            ],
            "default": "default_path"
        })
        
        # Act
        result = runner.execute(sample_context)
        
        # Assert
        assert result["success"] is True
        assert result["result"]["target"] == "medium_score_path"
        assert "${score} > 70" in result["result"]["matched_condition"]
    
    def test_default_path(self, sample_context):
        """Test that default path is used when no conditions match."""
        # Arrange
        runner = DecisionRunner("test_step", {
            "conditions": [
                {"expression": "${score} > 90", "target": "high_score_path"},
                {"expression": "${score} < 70", "target": "low_score_path"}
            ],
            "default": "default_path"
        })
        
        # Act
        result = runner.execute(sample_context)
        
        # Assert
        assert result["success"] is True
        assert result["result"]["target"] == "default_path"
        assert result["result"]["matched_condition"] is None
    
    def test_boolean_condition(self, sample_context):
        """Test evaluation of boolean conditions."""
        # Arrange
        runner = DecisionRunner("test_step", {
            "conditions": [
                {"expression": "${is_admin}", "target": "admin_path"},
                {"expression": "not ${is_admin}", "target": "user_path"}
            ]
        })
        
        # Act
        result = runner.execute(sample_context)
        
        # Assert
        assert result["success"] is True
        assert result["result"]["target"] == "admin_path"
    
    def test_complex_condition(self, sample_context):
        """Test evaluation of complex conditions."""
        # Arrange
        runner = DecisionRunner("test_step", {
            "conditions": [
                {
                    "expression": "${score} > ${threshold} and ${status} == 'success'",
                    "target": "success_path"
                },
                {
                    "expression": "${score} <= ${threshold} or ${status} != 'success'",
                    "target": "failure_path"
                }
            ]
        })
        
        # Act
        result = runner.execute(sample_context)
        
        # Assert
        assert result["success"] is True
        assert result["result"]["target"] == "success_path"
    
    def test_no_matching_conditions(self):
        """Test error handling when no conditions match and no default is provided."""
        # Arrange
        runner = DecisionRunner("test_step", {
            "conditions": [
                {"expression": "False", "target": "never_path"}
            ]
        })
        
        # Act
        result = runner.execute()
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "no default" in result["error"].lower()
    
    def test_invalid_expression(self, sample_context):
        """Test error handling for invalid expressions."""
        # Arrange
        runner = DecisionRunner("test_step", {
            "conditions": [
                {"expression": "${score} >>> 90", "target": "invalid_path"},
                {"expression": "${score} > 70", "target": "valid_path"}
            ],
            "default": "default_path"
        })
        
        # Act
        result = runner.execute(sample_context)
        
        # Assert
        assert result["success"] is True
        # Should skip the invalid expression and match the valid one
        assert result["result"]["target"] == "valid_path"

# -------------------------------------------------------------------- #
# RunnerFactory Tests
# -------------------------------------------------------------------- #

class TestRunnerFactory:
    
    def test_create_shell_runner(self):
        """Test creating a ShellRunner."""
        # Act
        runner = RunnerFactory.create_runner("shell", "test_step", {"command": "echo test"})
        
        # Assert
        assert isinstance(runner, ShellRunner)
        assert runner.step_id == "test_step"
        assert runner.params["command"] == "echo test"
    
    def test_create_http_runner(self):
        """Test creating an HttpRunner."""
        # Act
        runner = RunnerFactory.create_runner("http", "test_step", {"url": "https://example.com"})
        
        # Assert
        assert isinstance(runner, HttpRunner)
        assert runner.step_id == "test_step"
        assert runner.params["url"] == "https://example.com"
    
    def test_create_llm_runner(self):
        """Test creating an LLMRunner."""
        # Act
        runner = RunnerFactory.create_runner("llm", "test_step", {"model": "gpt-4"})
        
        # Assert
        assert isinstance(runner, LLMRunner)
        assert runner.step_id == "test_step"
        assert runner.params["model"] == "gpt-4"
    
    def test_create_approval_runner(self):
        """Test creating an ApprovalRunner."""
        # Act
        runner = RunnerFactory.create_runner("approval", "test_step", {"approvers": ["user@example.com"]})
        
        # Assert
        assert isinstance(runner, ApprovalRunner)
        assert runner.step_id == "test_step"
        assert runner.params["approvers"] == ["user@example.com"]
    
    def test_create_decision_runner(self):
        """Test creating a DecisionRunner."""
        # Act
        runner = RunnerFactory.create_runner("decision", "test_step", {"conditions": []})
        
        # Assert
        assert isinstance(runner, DecisionRunner)
        assert runner.step_id == "test_step"
        assert runner.params["conditions"] == []
    
    def test_unknown_runner_type(self):
        """Test error handling for unknown runner type."""
        # Act/Assert
        with pytest.raises(ValueError) as exc_info:
            RunnerFactory.create_runner("unknown", "test_step", {})
        
        assert "unknown step type" in str(exc_info.value).lower()

# -------------------------------------------------------------------- #
# Integration Tests
# -------------------------------------------------------------------- #

class TestIntegration:
    
    @mock.patch('subprocess.run')
    def test_execute_step_function(self, mock_subprocess):
        """Test the execute_step helper function."""
        # Arrange
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Test output"
        
        # Act
        result = execute_step("test_step", "shell", {"command": "echo test"})
        
        # Assert
        assert result["success"] is True
        assert result["step_id"] == "test_step"
        assert "result" in result
    
    @mock.patch('subprocess.run')
    def test_execute_step_error_handling(self, mock_subprocess):
        """Test error handling in execute_step function."""
        # Arrange
        mock_subprocess.side_effect = Exception("Test error")
        
        # Act
        result = execute_step("test_step", "shell", {"command": "echo test"})
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "Test error" in result["error"]
    
    @responses.activate
    @mock.patch('subprocess.run')
    def test_multi_step_workflow(self, mock_subprocess, sample_context):
        """Test a simple workflow with multiple steps."""
        # Arrange
        # Set up HTTP mock
        responses.add(
            responses.GET,
            "https://api.example.com/users/123",
            json={"id": 123, "name": "testuser", "role": "admin"},
            status=200
        )
        
        # Set up subprocess mock
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "File created"
        
        # Create context
        context = sample_context.copy()
        
        # Step 1: HTTP request to get user data
        http_result = execute_step(
            "fetch_user", 
            "http", 
            {"url": "https://api.example.com/users/${user_id}", "method": "GET"},
            context
        )
        
        # Update context with result and flatten useful fields
        context["user_data"] = http_result["result"]["body"]
        context["role"] = context["user_data"]["role"]
        context["user_name"] = context["user_data"]["name"]
        
        # Step 2: Decision based on user role
        decision_result = execute_step(
            "check_role",
            "decision",
            {
                "conditions": [
                    {"expression": "${role} == 'admin'", "target": "admin_path"},
                    {"expression": "${role} == 'user'", "target": "user_path"}
                ],
                "default": "default_path"
            },
            context
        )
        
        # Step 3: Shell command based on decision
        target = decision_result["result"]["target"]
        if target == "admin_path":
            shell_result = execute_step(
                "admin_action",
                "shell",
                {"command": "echo 'Admin action for ${user_name}' > admin.log"},
                context
            )
        
        # Assert
        assert http_result["success"] is True
        assert decision_result["success"] is True
        assert decision_result["result"]["target"] == "admin_path"
        assert shell_result["success"] is True
        # Check that the shell command was called with the right substituted value
        assert "Admin action for testuser" in mock_subprocess.call_args[0][0]
