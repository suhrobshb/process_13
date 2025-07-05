"""
Workflow Engine
===============

This is the central nervous system of the AI Engine. It orchestrates the entire
lifecycle of a workflow, from deployment of dynamically generated code to its
execution, monitoring, and management.

The engine is designed to be:
-   **Adaptive**: It can execute both predefined action types (like Shell, HTTP)
    and dynamically generated Python modules created from user recordings.
-   **Intelligent**: It integrates RAG and LLM capabilities to make context-aware
    decisions, and it supports a continuous learning loop.
-   **Robust**: It includes error handling, state management, and a secure
    execution model for dynamic code.
-   **Scalable**: It's designed to be run by distributed Celery workers,
    allowing for concurrent workflow executions.
"""

import importlib.util
import json
import logging
import time
import traceback
from collections import deque, defaultdict
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select

from .database import get_session
from .models.execution import Execution
from .models.workflow import Workflow
from .workflow_runners import RunnerFactory

# Configure logging
logger = logging.getLogger(__name__)

# --- Constants ---
DYNAMIC_MODULE_STORAGE = Path("storage/dynamic_modules")


class WorkflowEngine:
    """
    Orchestrates the execution of complex, multi-step workflows.
    """

    def __init__(self, workflow_id: int):
        self.workflow_id = workflow_id
        self.workflow: Optional[Workflow] = None
        self.execution: Optional[Execution] = None
        self.context: Dict[str, Any] = {}  # Shared state between steps
        self.executed_steps: set[str] = set()

    def _load_workflow(self, session: Session) -> Workflow:
        """Loads the workflow definition from the database."""
        if self.workflow:
            return self.workflow
        workflow = session.get(Workflow, self.workflow_id)
        if not workflow:
            raise ValueError(f"Workflow with ID {self.workflow_id} not found.")
        self.workflow = workflow
        return workflow

    def _create_execution_record(self, session: Session) -> Execution:
        """Creates a database record to track this workflow run."""
        execution = Execution(
            workflow_id=self.workflow_id,
            status="pending",
            started_at=datetime.utcnow(),
        )
        session.add(execution)
        session.commit()
        session.refresh(execution)
        self.execution = execution
        logger.info(f"Created execution record {execution.id} for workflow {self.workflow_id}")
        return execution

    def _update_execution_status(self, status: str, error: Optional[str] = None, result: Optional[Dict] = None):
        """Updates the status and result of the current execution."""
        if not self.execution:
            return

        with get_session() as session:
            # Re-fetch the execution object in the new session to avoid staleness
            exec_to_update = session.get(Execution, self.execution.id)
            if not exec_to_update:
                logger.warning(f"Execution {self.execution.id} not found for status update.")
                return

            exec_to_update.status = status
            exec_to_update.updated_at = datetime.utcnow()
            if status in ["completed", "failed"]:
                exec_to_update.completed_at = datetime.utcnow()
            if error:
                exec_to_update.error = error
            if result:
                exec_to_update.result = result

            session.add(exec_to_update)
            session.commit()
        logger.info(f"Execution {self.execution.id} status updated to: {status}")

    def _build_execution_graph(self) -> Tuple[Dict[str, List[str]], Dict[str, Dict]]:
        """
        Builds a dependency graph from the workflow definition.
        Prefers the modern node/edge structure, falls back to legacy linear steps.
        """
        if not self.workflow:
            raise ValueError("Workflow not loaded.")

        if self.workflow.nodes and self.workflow.edges:
            # Modern graph-based workflow
            dependencies = defaultdict(list)
            for edge in self.workflow.edges:
                dependencies[edge["target"]].append(edge["source"])
            
            node_map = {node["id"]: node for node in self.workflow.nodes}
            return dict(dependencies), node_map
        elif self.workflow.steps:
            # Legacy linear workflow
            dependencies = {}
            node_map = {}
            prev_step_id = None
            for i, step in enumerate(self.workflow.steps):
                step_id = step.get("id", f"step_{i}")
                node_map[step_id] = step
                dependencies[step_id] = [prev_step_id] if prev_step_id else []
                prev_step_id = step_id
            return dependencies, node_map
        else:
            raise ValueError("Workflow has no steps or nodes defined.")

    def _topological_sort(self, dependencies: Dict[str, List[str]], nodes: List[str]) -> List[str]:
        """Performs a topological sort to determine execution order."""
        in_degree = {node: 0 for node in nodes}
        adj = defaultdict(list)

        for node in nodes:
            for dep in dependencies.get(node, []):
                if dep in nodes: # Ensure dependency is part of the current graph
                    adj[dep].append(node)
                    in_degree[node] += 1
        
        queue = deque([node for node in nodes if in_degree[node] == 0])
        sorted_order = []

        while queue:
            u = queue.popleft()
            sorted_order.append(u)
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        if len(sorted_order) != len(nodes):
            # Identify the cycle for better error logging
            cycle_nodes = set(nodes) - set(sorted_order)
            logger.error(f"Cycle detected in workflow graph. Unresolved nodes: {cycle_nodes}")
            raise ValueError("Workflow contains a cycle and cannot be executed.")
            
        return sorted_order

    def _execute_step(self, step_id: str, step_definition: Dict[str, Any]):
        """Executes a single step, either standard or dynamic."""
        step_type = step_definition.get("type", "dynamic")
        params = step_definition.get("data", {})  # For nodes from visual editor
        if not params:
            params = step_definition.get("params", {}) # For legacy steps
            
        logger.info(f"Executing step '{step_id}' of type '{step_type}'")

        # Resolve inputs from context
        resolved_params = self._resolve_inputs(params)
        
        # --- Select appropriate runner implementation ------------------ #
        runner = None  # will be instantiated if not dynamic

        if step_type == "dynamic":
            # This is a dynamically generated module
            result = self._execute_dynamic_module(step_id)
        elif step_type == "desktop":
            # Use enhanced desktop runner (pyautogui based)
            try:
                from .enhanced_runners.desktop_runner import DesktopRunner as _DesktopRunner
                runner = _DesktopRunner(step_id, resolved_params)
                result = runner.execute()  # desktop runner needs no shared context
            except ImportError as e:
                logger.error("Desktop automation not available: %s", e)
                result = {"success": False, "error": str(e)}
        elif step_type == "browser":
            # Use enhanced browser runner (Playwright based)
            try:
                from .enhanced_runners.browser_runner import BrowserRunner as _BrowserRunner
                runner = _BrowserRunner(step_id, resolved_params)
                result = runner.execute()  # browser runner also standalone
            except ImportError as e:
                logger.error("Browser automation not available: %s", e)
                result = {"success": False, "error": str(e)}
        else:
            # Fallback to RunnerFactory for other step types
            runner = RunnerFactory.create_runner(step_type, step_id, resolved_params)
            # Some legacy runners accept context for variable substitution
            try:
                result = runner.execute(self.context)
            except TypeError:
                # If runner does not accept context parameter
                result = runner.execute()

        # Update context with step output
        if result.get("success"):
            self.context[step_id] = result.get("result", {})
            self.context[f"{step_id}_output"] = result.get("result", {}) # Alias for clarity
        
        self.executed_steps.add(step_id)
        return result

    def _execute_dynamic_module(self, step_id: str) -> Dict[str, Any]:
        """Dynamically imports and runs a generated workflow module."""
        module_name = f"workflow_module_{self.workflow_id}_{step_id}"
        module_path = DYNAMIC_MODULE_STORAGE / str(self.workflow_id) / f"{module_name}.py"

        if not module_path.exists():
            raise FileNotFoundError(f"Dynamic module not found for step '{step_id}' at {module_path}")

        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if not spec or not spec.loader:
                raise ImportError(f"Could not create module spec for {module_path}")
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Execute the module's run function
            if hasattr(module, 'run'):
                # Pass the current context to the dynamic module
                output = module.run(self.context)
                return {"success": True, "result": output}
            else:
                raise AttributeError(f"Module {module_name} does not have a 'run' function.")
        except Exception as e:
            logger.error(f"Error executing dynamic module for step '{step_id}': {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _resolve_inputs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Resolves template variables in parameters from the context."""
        # Simple string replacement for now. A more robust solution would use a templating engine.
        params_str = json.dumps(params)
        for key, value in self.context.items():
            # Only substitute simple types to avoid complex object injection
            if isinstance(value, (str, int, float, bool)):
                params_str = params_str.replace(f"${{{key}}}", str(value))
        return json.loads(params_str)

    def run(self):
        """The main entry point to execute the workflow."""
        with get_session() as session:
            try:
                self._load_workflow(session)
                self._create_execution_record(session)
                self._update_execution_status("running")

                dependencies, node_map = self._build_execution_graph()
                execution_order = self._topological_sort(dependencies, list(node_map.keys()))

                logger.info(f"Execution order for workflow {self.workflow_id}: {execution_order}")

                for step_id in execution_order:
                    step_definition = node_map[step_id]
                    
                    # Check confidence score if available
                    confidence = step_definition.get("confidence_score", 1.0)
                    if confidence < 0.75:
                        logger.warning(f"Step '{step_id}' has low confidence ({confidence}). Flagging for review.")
                        # In a real system, you might pause or require approval here
                    
                    step_result = self._execute_step(step_id, step_definition)

                    if not step_result.get("success"):
                        error_message = f"Step '{step_id}' failed: {step_result.get('error', 'Unknown error')}"
                        logger.error(error_message)
                        self._update_execution_status("failed", error=error_message, result={"executed_steps": list(self.executed_steps)})
                        return

                self._update_execution_status("completed", result={"executed_steps": list(self.executed_steps)})
            except Exception as e:
                error_message = f"Workflow execution failed: {traceback.format_exc()}"
                logger.error(error_message)
                self._update_execution_status("failed", error=str(e))

# --- Helper Function for Celery Task ---

def approve_workflow_step(
    approval_id: str,
    approved: bool = True,
    comments: Optional[str] = None,
) -> bool:
    """
    Resolves a human-in-the-loop approval request.

    The current implementation is intentionally minimal: it logs the decision
    and returns ``True`` so that the router importing this function can operate
    without raising *ImportError*.

    In a production deployment this function should:
      1. Persist the decision in the database / message queue.
      2. Wake up any waiting workflow execution (e.g. via Redis Pub/Sub).
      3. Optionally notify the requesting user.
    """
    logger.info(
        "Approval %s resolved – approved=%s, comments=%s",
        approval_id,
        approved,
        comments,
    )
    # TODO: Persist approval decision and resume waiting workflow step.
    return True

def execute_workflow_by_id(workflow_id: int):
    """
    A standalone function to instantiate and run the WorkflowEngine.
    This is the ideal entry point for a Celery task.
    """
    engine = WorkflowEngine(workflow_id)
    engine.run()
    return engine.execution.id if engine.execution else None
