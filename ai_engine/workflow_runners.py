"""
Workflow Runner Module
---------------------

This module provides various runner implementations for executing different types of workflow steps.
Each runner handles a specific type of task (shell commands, HTTP requests, LLM interactions, etc.)
and follows a common interface for execution and error handling.

Runners:
- ShellRunner: Executes shell commands and scripts
- HttpRunner: Makes HTTP requests to external APIs
- LLMRunner: Interacts with language models (OpenAI, etc.)
- ApprovalRunner: Handles human-in-the-loop approval steps
"""

import os
import json
import time
import logging
import subprocess
import requests
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from abc import ABC, abstractmethod
import ast

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("workflow_runner")

class Runner(ABC):
    """Base abstract class for all workflow step runners."""
    
    def __init__(self, step_id: str, params: Dict[str, Any]):
        """
        Initialize a runner with step parameters.
        
        Args:
            step_id: Unique identifier for the step
            params: Parameters specific to this step
        """
        self.step_id = step_id
        self.params = params
        self.start_time = None
        self.end_time = None
    
    @abstractmethod
    def execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute the step with the given context.
        
        Args:
            context: Execution context with variables from previous steps
            
        Returns:
            Dict containing execution results
        """
        pass
    
    def _start_execution(self):
        """Record execution start time."""
        self.start_time = datetime.utcnow()
        logger.info(f"Starting execution of step {self.step_id}")
    
    def _end_execution(self, success: bool, result: Dict[str, Any] = None, error: str = None):
        """
        Record execution end time and format the result.
        
        Args:
            success: Whether the execution was successful
            result: The execution result data
            error: Error message if execution failed
            
        Returns:
            Standardized execution result dict
        """
        self.end_time = datetime.utcnow()
        duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
        
        execution_result = {
            "step_id": self.step_id,
            "success": success,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_ms": duration_ms,
        }
        
        if success and result:
            execution_result["result"] = result
        
        if not success and error:
            execution_result["error"] = error
            logger.error(f"Step {self.step_id} failed: {error}")
        else:
            logger.info(f"Step {self.step_id} completed in {duration_ms}ms")
            
        return execution_result


class ShellRunner(Runner):
    """Executes shell commands and scripts."""
    
    def execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a shell command or script.
        
        Params expected in self.params:
            - command: The shell command to execute
            - timeout: Maximum execution time in seconds (default: 60)
            - shell: Whether to use shell execution (default: True)
            - env: Additional environment variables
            
        Returns:
            Execution result with stdout, stderr, and exit_code
        """
        context = context or {}
        self._start_execution()
        
        try:
            # Get parameters with defaults
            command = self.params.get("command")
            if not command:
                return self._end_execution(False, error="No command specified")
                
            # Substitute variables from context
            for key, value in context.items():
                if isinstance(value, (str, int, float, bool)):
                    command = command.replace(f"${{{key}}}", str(value))
            
            timeout = self.params.get("timeout", 60)
            use_shell = self.params.get("shell", True)
            
            # Prepare environment
            env = os.environ.copy()
            if self.params.get("env"):
                env.update(self.params["env"])
            
            # Execute command
            logger.info(f"Executing shell command: {command}")
            process = subprocess.run(
                command,
                shell=use_shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            
            # Process result
            result = {
                "stdout": process.stdout,
                "stderr": process.stderr,
                "exit_code": process.returncode
            }
            
            success = process.returncode == 0
            if not success:
                return self._end_execution(
                    False,
                    result=result,
                    error=f"Command failed with exit code {process.returncode}"
                )
                
            return self._end_execution(True, result=result)
            
        except subprocess.TimeoutExpired:
            return self._end_execution(
                False,
                error=f"Command timed out after {timeout} seconds"
            )
        except Exception as e:
            return self._end_execution(False, error=str(e))


class HttpRunner(Runner):
    """Makes HTTP requests to external APIs."""
    
    def execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute an HTTP request.
        
        Params expected in self.params:
            - url: The URL to call
            - method: HTTP method (GET, POST, PUT, DELETE, etc.)
            - headers: Request headers
            - data: Request body for POST/PUT
            - json: JSON body for POST/PUT
            - params: URL parameters
            - timeout: Request timeout in seconds
            - verify_ssl: Whether to verify SSL certificates
            
        Returns:
            Execution result with status_code, headers, and response body
        """
        context = context or {}
        self._start_execution()
        
        try:
            # Get parameters with defaults
            url = self.params.get("url")
            if not url:
                return self._end_execution(False, error="No URL specified")
                
            # Apply variable substitution from context
            for key, value in context.items():
                if isinstance(value, (str, int, float, bool)):
                    url = url.replace(f"${{{key}}}", str(value))
            
            method = self.params.get("method", "GET").upper()
            headers = self.params.get("headers", {})
            timeout = self.params.get("timeout", 30)
            verify_ssl = self.params.get("verify_ssl", True)
            
            # Prepare request kwargs
            request_kwargs = {
                "headers": headers,
                "timeout": timeout,
                "verify": verify_ssl,
            }
            
            # Add appropriate body based on the method
            if method in ["POST", "PUT", "PATCH"]:
                if "json" in self.params:
                    request_kwargs["json"] = self.params["json"]
                elif "data" in self.params:
                    request_kwargs["data"] = self.params["data"]
            
            if "params" in self.params:
                request_kwargs["params"] = self.params["params"]
            
            # Execute request
            logger.info(f"Making {method} request to {url}")
            response = requests.request(method, url, **request_kwargs)
            
            # Process response
            try:
                response_body = response.json()
            except ValueError:
                response_body = response.text
                
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body
            }
            
            # Check if request was successful (2xx status code)
            success = 200 <= response.status_code < 300
            if not success:
                return self._end_execution(
                    False,
                    result=result,
                    error=f"HTTP request failed with status code {response.status_code}"
                )
                
            return self._end_execution(True, result=result)
            
        except requests.RequestException as e:
            return self._end_execution(False, error=f"HTTP request error: {str(e)}")
        except Exception as e:
            return self._end_execution(False, error=str(e))


class LLMRunner(Runner):
    """Interacts with language models (OpenAI, etc.)."""
    
    def execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute an LLM request.
        
        Params expected in self.params:
            - provider: LLM provider (openai, anthropic, etc.)
            - model: Model name (gpt-4, claude-2, etc.)
            - prompt: Text prompt or messages array
            - temperature: Sampling temperature
            - max_tokens: Maximum tokens to generate
            - api_key: Optional API key (falls back to environment)
            
        Returns:
            Execution result with generated text and usage stats
        """
        context = context or {}
        self._start_execution()
        
        try:
            # Get parameters
            provider = self.params.get("provider", "openai").lower()
            model = self.params.get("model")
            prompt = self.params.get("prompt")
            
            if not model:
                return self._end_execution(False, error="No model specified")
            if not prompt:
                return self._end_execution(False, error="No prompt specified")
            
            # Apply variable substitution from context
            if isinstance(prompt, str):
                for key, value in context.items():
                    if isinstance(value, (str, int, float, bool)):
                        prompt = prompt.replace(f"${{{key}}}", str(value))
            
            # Handle different providers
            if provider == "openai":
                return self._execute_openai(prompt, model)
            else:
                return self._end_execution(False, error=f"Unsupported LLM provider: {provider}")
                
        except Exception as e:
            return self._end_execution(False, error=str(e))
    
    # ------------------------------------------------------------------ #
    # New OpenAI client (>=1.0) implementation
    # ------------------------------------------------------------------ #
    def _execute_openai(self, prompt: Union[str, list], model: str):
        """
        Execute request using OpenAI Python-SDK ≥ 1.0.
        """
        try:
            # Import lazily so we don't add a hard dependency at import-time
            from openai import OpenAI

            api_key = (
                self.params.get("api_key")
                or os.environ.get("OPENAI_API_KEY")
            )
            if not api_key:
                return self._end_execution(
                    False, error="OpenAI API key not provided"
                )

            client = OpenAI(api_key=api_key)

            temperature = self.params.get("temperature", 0.7)
            max_tokens = self.params.get("max_tokens", 1000)

            # Chat models (prompt as list of dicts)  vs  legacy completion
            if isinstance(prompt, list):
                response = client.chat.completions.create(
                    model=model,
                    messages=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content
            else:
                response = client.completions.create(
                    model=model,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].text

            return self._end_execution(
                True,
                result={
                    "content": content,
                    "usage": dict(response.usage) if hasattr(response, "usage") else {},
                    "model": model,
                },
            )

        except Exception as e:  # pylint: disable=broad-except
            return self._end_execution(
                False, error=f"OpenAI client error: {str(e)}"
            )


class ApprovalRunner(Runner):
    """Handles human-in-the-loop approval steps."""
    
    def execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create an approval request and wait for response.
        
        Params expected in self.params:
            - title: Approval request title
            - description: Detailed description of what needs approval
            - approvers: List of user IDs or emails who can approve
            - timeout_hours: How long to wait for approval before timing out
            - notification_method: How to notify approvers (email, slack, etc.)
            - wait: Whether to wait for approval or return immediately
            
        Returns:
            If wait=True: Waits and returns approval status
            If wait=False: Returns immediately with approval_id
        """
        context = context or {}
        self._start_execution()
        
        try:
            # Get parameters
            title = self.params.get("title", f"Approval required for step {self.step_id}")
            description = self.params.get("description", "Please review and approve this workflow step.")
            approvers = self.params.get("approvers", [])
            timeout_hours = self.params.get("timeout_hours", 24)
            notification_method = self.params.get("notification_method", "email")
            wait = self.params.get("wait", False)
            
            # Apply variable substitution
            for key, value in context.items():
                if isinstance(value, (str, int, float, bool)):
                    title = title.replace(f"${{{key}}}", str(value))
                    description = description.replace(f"${{{key}}}", str(value))
            
            # Create approval request (in real implementation, this would interact with a database)
            approval_id = f"approval_{int(time.time())}_{self.step_id}"
            
            logger.info(f"Created approval request {approval_id} for step {self.step_id}")
            
            # Send notifications (simplified implementation)
            self._send_approval_notifications(approval_id, title, description, approvers, notification_method)
            
            # If not waiting, return immediately
            if not wait:
                return self._end_execution(True, result={
                    "approval_id": approval_id,
                    "status": "pending",
                    "approvers": approvers,
                    "expires_at": (datetime.utcnow().timestamp() + timeout_hours * 3600)
                })
            
            # Wait for approval (simplified implementation)
            # In a real system, this would query a database or message queue
            # Here we just simulate waiting and always approve after a delay
            logger.info(f"Waiting for approval {approval_id}...")
            time.sleep(5)  # Simulate waiting
            
            # Simulate approval
            approval_result = {
                "approval_id": approval_id,
                "status": "approved",
                "approved_by": approvers[0] if approvers else "system",
                "approved_at": datetime.utcnow().isoformat(),
                "comments": "Automatically approved for demonstration"
            }
            
            return self._end_execution(True, result=approval_result)
            
        except Exception as e:
            return self._end_execution(False, error=str(e))
    
    def _send_approval_notifications(self, approval_id, title, description, approvers, method):
        """Send notifications to approvers (simplified implementation)."""
        logger.info(f"Would send {method} notifications to {approvers} for approval {approval_id}")
        # In a real implementation, this would send emails or Slack messages
        # For example:
        # if method == "email":
        #     send_email(approvers, f"Approval Request: {title}", description)
        # elif method == "slack":
        #     send_slack_message(approvers, title, description)


class DecisionRunner(Runner):
    """Evaluates conditions and determines workflow path."""
    
    def execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Evaluate conditions and determine which path to take.
        
        Params expected in self.params:
            - conditions: List of condition objects with expressions and targets
            - default: Default target if no conditions match
            
        Returns:
            Execution result with the selected target path
        """
        context = context or {}
        self._start_execution()
        
        try:
            conditions = self.params.get("conditions", [])
            default_target = self.params.get("default")
            
            if not conditions and not default_target:
                return self._end_execution(False, error="No conditions or default target specified")
            
            # Evaluate each condition
            for condition in conditions:
                expression = condition.get("expression")
                target = condition.get("target")
                
                if not expression or not target:
                    continue
                
                # Simple expression evaluation (in a real system, use a proper expression parser)
                # This is a simplified implementation that handles basic comparisons
                try:
                    # Tiny expression-evaluator using AST to avoid `eval`
                    def _safe_eval(expr: str) -> bool:
                        tree = ast.parse(expr, mode="eval")
                        allowed_nodes = (
                            ast.Expression,
                            ast.BoolOp,
                            ast.BinOp,
                            ast.UnaryOp,
                            ast.Compare,
                            ast.Name,
                            ast.Load,
                            ast.Constant,
                            ast.And,
                            ast.Or,
                            ast.Eq,
                            ast.NotEq,
                            ast.Gt,
                            ast.GtE,
                            ast.Lt,
                            ast.LtE,
                        )
                        for node in ast.walk(tree):
                            if not isinstance(node, allowed_nodes):
                                raise ValueError(
                                    f"Unsupported expression element: {type(node).__name__}"
                                )
                        compiled = compile(tree, "<expr>", "eval")
                        return bool(eval(compiled, {}, {}))  # noqa: S307

                    # Replace template vars
                    eval_expr = expression
                    for k, v in context.items():
                        if isinstance(v, (str, int, float, bool)):
                            eval_expr = eval_expr.replace(f"${{{k}}}", repr(v))

                    if _safe_eval(eval_expr):
                        logger.info(f"Condition '{expression}' evaluated to True, taking path to '{target}'")
                        return self._end_execution(True, result={
                            "target": target,
                            "matched_condition": expression
                        })
                except Exception as e:
                    logger.warning(f"Error evaluating condition '{expression}': {str(e)}")
            
            # If no conditions matched, use default target
            if default_target:
                logger.info(f"No conditions matched, taking default path to '{default_target}'")
                return self._end_execution(True, result={
                    "target": default_target,
                    "matched_condition": None
                })
            
            # No matching condition and no default
            return self._end_execution(False, error="No conditions matched and no default target specified")
            
        except Exception as e:
            return self._end_execution(False, error=str(e))


class RunnerFactory:
    """Factory class to create appropriate runners based on step type."""
    
    @staticmethod
    def create_runner(step_type: str, step_id: str, params: Dict[str, Any]) -> Runner:
        """
        Create and return the appropriate runner for the given step type.
        
        Args:
            step_type: Type of step to execute
            step_id: Unique identifier for the step
            params: Parameters for the step
            
        Returns:
            Appropriate Runner instance
            
        Raises:
            ValueError: If step_type is unknown
        """
        runners = {
            "shell": ShellRunner,
            "http": HttpRunner,
            "llm": LLMRunner,
            "approval": ApprovalRunner,
            "decision": DecisionRunner,
            # --- Enhanced automation runners ------------------------------ #
            # The following imports are optional / heavy-weight.  We import
            # lazily so that projects that don’t need desktop / browser
            # automation aren’t forced to install extra dependencies.
            "desktop": None,
            "browser": None,
        }
        
        # Lazily import the enhanced runners only when requested
        step_key = step_type.lower()
        if step_key in ("desktop", "browser") and runners[step_key] is None:
            try:
                if step_key == "desktop":
                    from ai_engine.enhanced_runners.desktop_runner import (  # type: ignore
                        DesktopRunner,
                    )
                    runners["desktop"] = DesktopRunner
                else:  # browser
                    from ai_engine.enhanced_runners.browser_runner import (  # type: ignore
                        BrowserRunner,
                    )
                    runners["browser"] = BrowserRunner
            except ModuleNotFoundError as exc:  # pragma: no cover
                raise ValueError(
                    f"Runner type '{step_type}' requires optional dependencies "
                    "that are not installed.  Install extras in requirements.txt."
                ) from exc

        runner_class = runners.get(step_type.lower())
        if not runner_class:
            raise ValueError(f"Unknown step type: {step_type}")
        
        return runner_class(step_id, params)


def execute_step(
    step_id: str,
    step_type: str,
    params: Dict[str, Any],
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Helper function to execute a single workflow step.
    
    Args:
        step_id: Unique identifier for the step
        step_type: Type of step to execute
        params: Parameters for the step
        context: Execution context with variables from previous steps
        
    Returns:
        Execution result
    """
    try:
        runner = RunnerFactory.create_runner(step_type, step_id, params)
        return runner.execute(context or {})
    except Exception as e:
        logger.error(f"Error executing step {step_id}: {str(e)}")
        return {
            "step_id": step_id,
            "success": False,
            "error": str(e),
            "start_time": datetime.utcnow().isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "duration_ms": 0
        }
