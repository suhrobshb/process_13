"""
Workflow Runner Module
---------------------

This module provides various runner implementations for executing different types of workflow steps.
Each runner handles a specific type of task (shell commands, HTTP requests, LLM interactions, etc.)
and follows a common interface for execution and error handling.

Runners:
- ShellRunner: Executes shell commands and scripts
- HttpRunner: Makes HTTP requests to external APIs
- LLMRunner: Interacts with language models (OpenAI, etc.), now with RAG support.
- ApprovalRunner: Handles human-in-the-loop approval steps
- RAGDecisionRunner: NEW - Makes intelligent decisions using context from user data.
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
    """
    Interacts with language models (OpenAI, etc.).
    Enhanced with RAG capabilities for context-aware responses.
    """
    
    def execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute an LLM request, optionally augmenting with RAG context.
        
        Params expected in self.params:
            - provider: LLM provider (e.g., "openai")
            - model: Model name (e.g., "gpt-4")
            - prompt: Text prompt or messages array
            - temperature, max_tokens, etc.
            - rag_params: (Optional) Dict with "query" and "data_source_ids"
        
        Returns:
            Execution result with generated text and usage stats.
        """
        context = context or {}
        self._start_execution()
        
        try:
            # Get parameters
            provider = self.params.get("provider", "openai").lower()
            model = self.params.get("model")
            prompt = self.params.get("prompt")
            rag_params = self.params.get("rag_params")
            
            if not model:
                return self._end_execution(False, error="No model specified")
            if not prompt:
                return self._end_execution(False, error="No prompt specified")
            
            # Apply variable substitution from context
            if isinstance(prompt, str):
                for key, value in context.items():
                    if isinstance(value, (str, int, float, bool)):
                        prompt = prompt.replace(f"${{{key}}}", str(value))
            
            # --- RAG Integration ---
            source_documents = []
            if rag_params and isinstance(rag_params, dict):
                rag_query = rag_params.get("query")
                data_source_ids = rag_params.get("data_source_ids")
                
                if rag_query and data_source_ids:
                    logger.info(f"Performing RAG query for step {self.step_id}")
                    try:
                        from ai_engine.rag_engine import RAGEngine
                        
                        user_id = context.get("user_id")
                        tenant_id = context.get("tenant_id")
                        if not user_id or not tenant_id:
                            raise ValueError("RAG requires user_id and tenant_id in context")
                            
                        rag_engine = RAGEngine(user_id, tenant_id)
                        rag_result = rag_engine.query(rag_query, data_source_ids)
                        
                        # Augment the prompt with retrieved context
                        retrieved_context = "\n".join([doc.page_content for doc in rag_result.get("source_documents", [])])
                        augmented_prompt = f"Context:\n{retrieved_context}\n\nQuestion: {prompt}"
                        prompt = augmented_prompt
                        source_documents = rag_result.get("source_documents", [])
                        
                    except Exception as e:
                        logger.warning(f"RAG query failed for step {self.step_id}: {e}")
                        # Proceed without RAG context
            
            # Handle different providers
            if provider == "openai":
                openai_result = self._execute_openai(prompt, model)
                if openai_result["success"]:
                    openai_result["result"]["source_documents"] = [doc.metadata for doc in source_documents]
                return openai_result
            else:
                return self._end_execution(False, error=f"Unsupported LLM provider: {provider}")
                
        except Exception as e:
            return self._end_execution(False, error=str(e))
    
    def _execute_openai(self, prompt: Union[str, list], model: str):
        """Execute request using OpenAI Python-SDK ≥ 1.0."""
        try:
            from openai import OpenAI

            api_key = self.params.get("api_key") or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                return self._end_execution(False, error="OpenAI API key not provided")

            client = OpenAI(api_key=api_key)
            temperature = self.params.get("temperature", 0.7)
            max_tokens = self.params.get("max_tokens", 1000)

            if isinstance(prompt, list):
                response = client.chat.completions.create(
                    model=model, messages=prompt, temperature=temperature, max_tokens=max_tokens
                )
                content = response.choices[0].message.content
            else:
                response = client.completions.create(
                    model=model, prompt=prompt, temperature=temperature, max_tokens=max_tokens
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
        except Exception as e:
            return self._end_execution(False, error=f"OpenAI client error: {str(e)}")


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
            
            for condition in conditions:
                expression = condition.get("expression")
                target = condition.get("target")
                
                if not expression or not target:
                    continue
                
                try:
                    def _safe_eval(expr: str) -> bool:
                        tree = ast.parse(expr, mode="eval")
                        allowed_nodes = (
                            ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp,
                            ast.Compare, ast.Name, ast.Load, ast.Constant,
                            ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Gt, ast.GtE, ast.Lt, ast.LtE
                        )
                        for node in ast.walk(tree):
                            if not isinstance(node, allowed_nodes):
                                raise ValueError(f"Unsupported expression element: {type(node).__name__}")
                        compiled = compile(tree, "<expr>", "eval")
                        return bool(eval(compiled, {}, {}))

                    eval_expr = expression
                    for k, v in context.items():
                        if isinstance(v, (str, int, float, bool)):
                            eval_expr = eval_expr.replace(f"${{{k}}}", repr(v))

                    if _safe_eval(eval_expr):
                        logger.info(f"Condition '{expression}' evaluated to True, taking path to '{target}'")
                        return self._end_execution(True, result={"target": target, "matched_condition": expression})
                except Exception as e:
                    logger.warning(f"Error evaluating condition '{expression}': {str(e)}")
            
            if default_target:
                logger.info(f"No conditions matched, taking default path to '{default_target}'")
                return self._end_execution(True, result={"target": default_target, "matched_condition": None})
            
            return self._end_execution(False, error="No conditions matched and no default target specified")
            
        except Exception as e:
            return self._end_execution(False, error=str(e))


class RAGDecisionRunner(Runner):
    """
    Makes intelligent decisions based on context from the RAG engine.
    """
    def execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Uses RAG to retrieve context and an LLM to choose an outcome.
        
        Params expected in self.params:
            - query: The question to ask the RAG system.
            - data_source_ids: List of data source IDs to query.
            - outcomes: List of possible string outcomes (e.g., ["approve", "reject"]).
            - llm_params: Standard LLM parameters (model, provider, etc.).
        """
        context = context or {}
        self._start_execution()
        
        try:
            query = self.params.get("query")
            data_source_ids = self.params.get("data_source_ids")
            outcomes = self.params.get("outcomes")
            llm_params = self.params.get("llm_params", {})
            
            if not all([query, data_source_ids, outcomes]):
                return self._end_execution(False, error="Missing required parameters: query, data_source_ids, outcomes")
            
            # 1. Retrieve context using RAG
            from ai_engine.rag_engine import RAGEngine
            user_id = context.get("user_id")
            tenant_id = context.get("tenant_id")
            if not user_id or not tenant_id:
                raise ValueError("RAG requires user_id and tenant_id in context")
            
            rag_engine = RAGEngine(user_id, tenant_id)
            rag_result = rag_engine.query(query, data_source_ids)
            retrieved_context = "\n".join([doc.page_content for doc in rag_result.get("source_documents", [])])
            
            # 2. Construct decision-making prompt
            decision_prompt = f"""
            Based on the following context:
            ---
            {retrieved_context}
            ---
            And the user's question: "{query}"

            Which of the following outcomes is most appropriate?
            Possible outcomes: {outcomes}

            Respond with ONLY the chosen outcome from the list.
            """
            
            # 3. Call LLM to make a decision
            llm_runner = LLMRunner(self.step_id, {
                "provider": llm_params.get("provider", "openai"),
                "model": llm_params.get("model", "gpt-4"),
                "prompt": decision_prompt,
                "temperature": 0.1,
                "max_tokens": 50
            })
            llm_result = llm_runner.execute(context)
            
            if not llm_result["success"]:
                return self._end_execution(False, error=f"LLM decision failed: {llm_result.get('error')}")
            
            # 4. Parse and validate the outcome
            chosen_outcome = llm_result["result"]["content"].strip().lower()
            if chosen_outcome not in [o.lower() for o in outcomes]:
                logger.warning(f"LLM returned an invalid outcome '{chosen_outcome}'. Falling back to default.")
                chosen_outcome = outcomes[0] # Fallback to the first outcome
            
            return self._end_execution(True, result={
                "chosen_outcome": chosen_outcome,
                "source_documents": rag_result.get("source_documents", [])
            })
            
        except Exception as e:
            return self._end_execution(False, error=str(e))


class RunnerFactory:
    """Factory class to create appropriate runners based on step type."""
    
    @staticmethod
    def create_runner(step_type: str, step_id: str, params: Dict[str, Any]) -> Runner:
        """
        Create and return the appropriate runner for the given step type.
        """
        runners = {
            "shell": ShellRunner,
            "http": HttpRunner,
            "llm": LLMRunner,
            "approval": ApprovalRunner,
            "decision": DecisionRunner,
            "rag_decision": RAGDecisionRunner,
            "desktop": None,
            "browser": None,
        }
        
        step_key = step_type.lower()
        if step_key in ("desktop", "browser") and runners[step_key] is None:
            try:
                if step_key == "desktop":
                    from ai_engine.enhanced_runners.desktop_runner import DesktopRunner
                    runners["desktop"] = DesktopRunner
                else:
                    from ai_engine.enhanced_runners.browser_runner import BrowserRunner
                    runners["browser"] = BrowserRunner
            except ModuleNotFoundError as exc:
                raise ValueError(
                    f"Runner type '{step_type}' requires optional dependencies that are not installed."
                ) from exc

        runner_class = runners.get(step_key)
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
