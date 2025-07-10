"""
Unit tests for workflow_runners.py
=================================

Tests for the workflow runner implementations, including:
- ShellRunner command execution
- HttpRunner API requests
- LLMRunner language model interactions
- ApprovalRunner human-in-the-loop processes
- Error handling and retry mechanisms
"""

import pytest
import json
import os
import time
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from workflow_runners import (
    Runner, ShellRunner, HttpRunner, LLMRunner, ApprovalRunner
)


class TestBaseRunner:
    """Test suite for base Runner class"""
    
    def test_runner_is_abstract(self):
        """Test that Runner is abstract and cannot be instantiated"""
        with pytest.raises(TypeError):
            Runner("test-step", {})
    
    def test_runner_initialization_subclass(self):
        """Test that Runner subclasses initialize correctly"""
        class TestRunner(Runner):
            def execute(self, context=None):
                return {"success": True}
        
        runner = TestRunner("test-step", {"param": "value"})
        assert runner.step_id == "test-step"
        assert runner.params == {"param": "value"}
        assert runner.start_time is None
        assert runner.end_time is None


class TestShellRunner:
    """Test suite for ShellRunner class"""
    
    @pytest.fixture
    def shell_runner(self):
        """Create a ShellRunner instance for testing"""
        params = {
            "command": "echo 'Hello World'",
            "timeout": 30,
            "working_directory": "/tmp"
        }
        return ShellRunner("shell-test", params)
    
    def test_shell_runner_initialization(self, shell_runner):
        """Test ShellRunner initializes correctly"""
        assert shell_runner.step_id == "shell-test"
        assert shell_runner.params["command"] == "echo 'Hello World'"
        assert shell_runner.params["timeout"] == 30
    
    @patch('subprocess.run')
    def test_shell_runner_execute_success(self, mock_run, shell_runner):
        """Test successful shell command execution"""
        # Mock successful subprocess execution
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Hello World\n",
            stderr="",
            args=["echo", "Hello World"]
        )
        
        result = shell_runner.execute()
        
        assert result["success"] is True
        assert result["step_id"] == "shell-test"
        assert "Hello World" in result["result"]["stdout"]
        assert result["result"]["return_code"] == 0
        assert "duration_ms" in result
        
        # Verify subprocess was called correctly
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_shell_runner_execute_failure(self, mock_run, shell_runner):
        """Test shell command execution failure"""
        # Mock failed subprocess execution
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Command not found\n",
            args=["invalid-command"]
        )
        
        result = shell_runner.execute()
        
        assert result["success"] is False
        assert "error" in result
        assert "Command not found" in result["error"]
        assert result["result"]["return_code"] == 1
    
    @patch('subprocess.run')
    def test_shell_runner_timeout(self, mock_run):
        """Test shell command timeout handling"""
        # Mock timeout exception
        mock_run.side_effect = subprocess.TimeoutExpired("sleep", 30)
        
        params = {
            "command": "sleep 60",
            "timeout": 1
        }
        runner = ShellRunner("timeout-test", params)
        
        result = runner.execute()
        
        assert result["success"] is False
        assert "timeout" in result["error"].lower()
    
    def test_shell_runner_working_directory(self):
        """Test shell command execution with working directory"""
        params = {
            "command": "pwd",
            "working_directory": "/tmp"
        }
        runner = ShellRunner("pwd-test", params)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="/tmp\n",
                stderr="",
                args=["pwd"]
            )
            
            result = runner.execute()
            
            # Check that cwd was set correctly
            call_args = mock_run.call_args
            assert call_args[1]["cwd"] == "/tmp"
    
    def test_shell_runner_environment_variables(self):
        """Test shell command execution with environment variables"""
        params = {
            "command": "echo $TEST_VAR",
            "environment": {"TEST_VAR": "test_value"}
        }
        runner = ShellRunner("env-test", params)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="test_value\n",
                stderr="",
                args=["echo", "$TEST_VAR"]
            )
            
            result = runner.execute()
            
            # Check that environment was set correctly
            call_args = mock_run.call_args
            assert "TEST_VAR" in call_args[1]["env"]
            assert call_args[1]["env"]["TEST_VAR"] == "test_value"


class TestHttpRunner:
    """Test suite for HttpRunner class"""
    
    @pytest.fixture
    def http_runner(self):
        """Create an HttpRunner instance for testing"""
        params = {
            "url": "https://api.example.com/data",
            "method": "GET",
            "headers": {"Authorization": "Bearer token123"},
            "timeout": 30
        }
        return HttpRunner("http-test", params)
    
    def test_http_runner_initialization(self, http_runner):
        """Test HttpRunner initializes correctly"""
        assert http_runner.step_id == "http-test"
        assert http_runner.params["url"] == "https://api.example.com/data"
        assert http_runner.params["method"] == "GET"
    
    @patch('requests.request')
    def test_http_runner_get_request(self, mock_request, http_runner):
        """Test HTTP GET request execution"""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.text = '{"data": "test"}'
        mock_response.headers = {"Content-Type": "application/json"}
        mock_request.return_value = mock_response
        
        result = http_runner.execute()
        
        assert result["success"] is True
        assert result["result"]["status_code"] == 200
        assert result["result"]["data"] == {"data": "test"}
        
        # Verify request was made correctly
        mock_request.assert_called_once_with(
            method="GET",
            url="https://api.example.com/data",
            headers={"Authorization": "Bearer token123"},
            timeout=30
        )
    
    @patch('requests.request')
    def test_http_runner_post_request(self, mock_request):
        """Test HTTP POST request execution"""
        params = {
            "url": "https://api.example.com/users",
            "method": "POST",
            "data": {"name": "John Doe", "email": "john@example.com"},
            "headers": {"Content-Type": "application/json"}
        }
        runner = HttpRunner("post-test", params)
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123, "name": "John Doe"}
        mock_response.text = '{"id": 123, "name": "John Doe"}'
        mock_request.return_value = mock_response
        
        result = runner.execute()
        
        assert result["success"] is True
        assert result["result"]["status_code"] == 201
        assert result["result"]["data"]["id"] == 123
        
        # Verify POST data was sent
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "POST"
        assert call_args[1]["json"] == {"name": "John Doe", "email": "john@example.com"}
    
    @patch('requests.request')
    def test_http_runner_error_response(self, mock_request):
        """Test HTTP error response handling"""
        params = {
            "url": "https://api.example.com/invalid",
            "method": "GET"
        }
        runner = HttpRunner("error-test", params)
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_request.return_value = mock_response
        
        result = runner.execute()
        
        assert result["success"] is False
        assert result["result"]["status_code"] == 404
        assert "404" in result["error"]
    
    @patch('requests.request')
    def test_http_runner_timeout(self, mock_request):
        """Test HTTP request timeout handling"""
        params = {
            "url": "https://api.example.com/slow",
            "method": "GET",
            "timeout": 1
        }
        runner = HttpRunner("timeout-test", params)
        
        mock_request.side_effect = requests.Timeout("Request timeout")
        
        result = runner.execute()
        
        assert result["success"] is False
        assert "timeout" in result["error"].lower()
    
    @patch('requests.request')
    def test_http_runner_connection_error(self, mock_request):
        """Test HTTP connection error handling"""
        params = {
            "url": "https://nonexistent.example.com/data",
            "method": "GET"
        }
        runner = HttpRunner("connection-test", params)
        
        mock_request.side_effect = requests.ConnectionError("Connection failed")
        
        result = runner.execute()
        
        assert result["success"] is False
        assert "connection" in result["error"].lower()
    
    def test_http_runner_retry_mechanism(self):
        """Test HTTP request retry mechanism"""
        params = {
            "url": "https://api.example.com/data",
            "method": "GET",
            "retry": {
                "max_attempts": 3,
                "delay": 0.1,
                "backoff": "exponential"
            }
        }
        runner = HttpRunner("retry-test", params)
        
        with patch('requests.request') as mock_request:
            # First two attempts fail, third succeeds
            mock_response_fail = Mock()
            mock_response_fail.status_code = 500
            mock_response_fail.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
            
            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"data": "success"}
            mock_response_success.text = '{"data": "success"}'
            
            mock_request.side_effect = [
                mock_response_fail,
                mock_response_fail,
                mock_response_success
            ]
            
            result = runner.execute()
            
            assert result["success"] is True
            assert result["result"]["status_code"] == 200
            assert mock_request.call_count == 3


class TestLLMRunner:
    """Test suite for LLMRunner class"""
    
    @pytest.fixture
    def llm_runner(self):
        """Create an LLMRunner instance for testing"""
        params = {
            "model": "gpt-3.5-turbo",
            "prompt": "What is the capital of France?",
            "max_tokens": 100,
            "temperature": 0.7
        }
        return LLMRunner("llm-test", params)
    
    def test_llm_runner_initialization(self, llm_runner):
        """Test LLMRunner initializes correctly"""
        assert llm_runner.step_id == "llm-test"
        assert llm_runner.params["model"] == "gpt-3.5-turbo"
        assert llm_runner.params["prompt"] == "What is the capital of France?"
    
    @patch('openai.ChatCompletion.create')
    def test_llm_runner_execute_success(self, mock_create, llm_runner):
        """Test successful LLM execution"""
        # Mock OpenAI response
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "The capital of France is Paris."
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 8,
                "total_tokens": 18
            }
        }
        mock_create.return_value = mock_response
        
        result = llm_runner.execute()
        
        assert result["success"] is True
        assert "Paris" in result["result"]["response"]
        assert result["result"]["usage"]["total_tokens"] == 18
        
        # Verify OpenAI API was called correctly
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[1]["model"] == "gpt-3.5-turbo"
        assert call_args[1]["max_tokens"] == 100
    
    @patch('openai.ChatCompletion.create')
    def test_llm_runner_api_error(self, mock_create, llm_runner):
        """Test LLM API error handling"""
        # Mock OpenAI API error
        mock_create.side_effect = Exception("API rate limit exceeded")
        
        result = llm_runner.execute()
        
        assert result["success"] is False
        assert "rate limit" in result["error"].lower()
    
    def test_llm_runner_prompt_templating(self):
        """Test LLM prompt templating with context variables"""
        params = {
            "model": "gpt-3.5-turbo",
            "prompt": "Hello {{user_name}}, please explain {{topic}}",
            "max_tokens": 100
        }
        runner = LLMRunner("template-test", params)
        
        context = {
            "user_name": "John",
            "topic": "artificial intelligence"
        }
        
        with patch('openai.ChatCompletion.create') as mock_create:
            mock_response = {
                "choices": [{"message": {"content": "Hello John, AI is..."}}],
                "usage": {"total_tokens": 15}
            }
            mock_create.return_value = mock_response
            
            result = runner.execute(context)
            
            # Check that template variables were substituted
            call_args = mock_create.call_args
            prompt = call_args[1]["messages"][0]["content"]
            assert "Hello John" in prompt
            assert "artificial intelligence" in prompt
    
    def test_llm_runner_rag_integration(self):
        """Test LLM runner with RAG (Retrieval-Augmented Generation) integration"""
        params = {
            "model": "gpt-3.5-turbo",
            "prompt": "Answer based on the context: {{question}}",
            "use_rag": True,
            "rag_context": "company_knowledge"
        }
        runner = LLMRunner("rag-test", params)
        
        context = {
            "question": "What is our company policy on remote work?"
        }
        
        with patch('openai.ChatCompletion.create') as mock_create:
            with patch.object(runner, '_get_rag_context') as mock_rag:
                mock_rag.return_value = "Company policy allows remote work 3 days per week."
                
                mock_response = {
                    "choices": [{"message": {"content": "Based on company policy..."}}],
                    "usage": {"total_tokens": 20}
                }
                mock_create.return_value = mock_response
                
                result = runner.execute(context)
                
                assert result["success"] is True
                mock_rag.assert_called_once()


class TestApprovalRunner:
    """Test suite for ApprovalRunner class"""
    
    @pytest.fixture
    def approval_runner(self):
        """Create an ApprovalRunner instance for testing"""
        params = {
            "approval_type": "manual",
            "message": "Please approve the invoice processing workflow",
            "approvers": ["manager@company.com"],
            "timeout": 3600  # 1 hour
        }
        return ApprovalRunner("approval-test", params)
    
    def test_approval_runner_initialization(self, approval_runner):
        """Test ApprovalRunner initializes correctly"""
        assert approval_runner.step_id == "approval-test"
        assert approval_runner.params["approval_type"] == "manual"
        assert "manager@company.com" in approval_runner.params["approvers"]
    
    @patch('requests.post')
    def test_approval_runner_send_notification(self, mock_post, approval_runner):
        """Test sending approval notification"""
        mock_post.return_value = Mock(status_code=200)
        
        # Mock approval response
        with patch.object(approval_runner, '_wait_for_approval') as mock_wait:
            mock_wait.return_value = {
                "approved": True,
                "approver": "manager@company.com",
                "timestamp": "2024-01-01T12:00:00Z"
            }
            
            result = approval_runner.execute()
            
            assert result["success"] is True
            assert result["result"]["approved"] is True
            assert result["result"]["approver"] == "manager@company.com"
    
    def test_approval_runner_timeout(self, approval_runner):
        """Test approval timeout handling"""
        # Mock timeout scenario
        with patch.object(approval_runner, '_wait_for_approval') as mock_wait:
            mock_wait.side_effect = TimeoutError("Approval timeout")
            
            result = approval_runner.execute()
            
            assert result["success"] is False
            assert "timeout" in result["error"].lower()
    
    def test_approval_runner_rejection(self, approval_runner):
        """Test approval rejection handling"""
        with patch.object(approval_runner, '_wait_for_approval') as mock_wait:
            mock_wait.return_value = {
                "approved": False,
                "approver": "manager@company.com",
                "reason": "Budget constraints",
                "timestamp": "2024-01-01T12:00:00Z"
            }
            
            result = approval_runner.execute()
            
            assert result["success"] is False
            assert result["result"]["approved"] is False
            assert "Budget constraints" in result["result"]["reason"]


class TestRunnerErrorHandling:
    """Test suite for error handling across all runners"""
    
    def test_runner_exception_handling(self):
        """Test that runners handle unexpected exceptions gracefully"""
        runner = ShellRunner("error-test", {"command": "echo test"})
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Unexpected error")
            
            result = runner.execute()
            
            assert result["success"] is False
            assert "error" in result
            assert "Unexpected error" in result["error"]
    
    def test_runner_execution_metrics(self):
        """Test that runners record execution metrics"""
        runner = ShellRunner("metrics-test", {"command": "echo test"})
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="test", stderr="")
            
            result = runner.execute()
            
            assert "start_time" in result
            assert "end_time" in result
            assert "duration_ms" in result
            assert result["duration_ms"] >= 0
    
    def test_runner_context_passing(self):
        """Test that context is properly passed between runners"""
        runner = ShellRunner("context-test", {"command": "echo {{variable}}"})
        
        context = {"variable": "test_value"}
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="test_value", stderr="")
            
            result = runner.execute(context)
            
            assert result["success"] is True
            # Verify context variable was substituted
            call_args = mock_run.call_args
            assert "test_value" in str(call_args)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])