"""
Workflow Engine
--------------

This module provides the core workflow execution engine for the AI Engine platform.
It handles parsing, validation, and execution of workflows defined in either the
legacy linear steps format or the new node/edge graph format from the visual editor.

Key features:
- Topological sorting of workflow steps based on dependencies
- Execution of different step types (shell, http, llm, approval, decision)
- Handling of conditional branching and decision points
- Support for human-in-the-loop approvals
- Comprehensive execution tracking and error handling
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Set, Optional, Tuple, Union
from collections import defaultdict, deque

from .models.workflow import Workflow
from .models.execution import Execution
from .database import get_session
from .workflow_runners import execute_step, RunnerFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("workflow_engine")


class WorkflowEngine:
    """
    Core engine for executing workflows defined in the AI Engine platform.
    Supports both legacy linear steps and node/edge graph representations.
    """
    
    def __init__(self, workflow_id: int = None, workflow: Workflow = None):
        """
        Initialize the workflow engine with either a workflow ID or a workflow object.
        
        Args:
            workflow_id: ID of the workflow to execute
            workflow: Workflow object to execute
        """
        self.workflow_id = workflow_id
        self.workflow = workflow
        self.execution_id = None
        self.execution = None
        self.context = {}  # Stores variables and results from previous steps
        self.executed_steps = set()  # Track which steps have been executed
        self.pending_approvals = {}  # Track steps waiting for approval
        
    def load_workflow(self) -> Workflow:
        """
        Load the workflow from the database if not already loaded.
        
        Returns:
            Loaded workflow object
        """
        if self.workflow:
            return self.workflow
            
        if not self.workflow_id:
            raise ValueError("No workflow_id or workflow provided")
            
        with get_session() as session:
            workflow = session.get(Workflow, self.workflow_id)
            if not workflow:
                raise ValueError(f"Workflow with ID {self.workflow_id} not found")
            
            self.workflow = workflow
            return workflow
    
    def create_execution_record(self) -> int:
        """
        Create an execution record in the database.
        
        Returns:
            ID of the created execution record
        """
        workflow = self.load_workflow()
        
        with get_session() as session:
            execution = Execution(
                workflow_id=workflow.id,
                status="running",
                started_at=datetime.utcnow(),
                extra_metadata={"steps_completed": 0}
            )
            session.add(execution)
            session.commit()
            session.refresh(execution)
            
            self.execution_id = execution.id
            self.execution = execution
            return execution.id
    
    def update_execution_status(self, status: str, error: str = None, result: Dict = None):
        """
        Update the execution record status in the database.
        
        Args:
            status: New status (running, completed, failed, waiting_approval)
            error: Error message if failed
            result: Execution result data
        """
        if not self.execution_id:
            logger.warning("No execution record to update")
            return
            
        with get_session() as session:
            execution = session.get(Execution, self.execution_id)
            if not execution:
                logger.error(f"Execution record {self.execution_id} not found")
                return
                
            execution.status = status
            execution.updated_at = datetime.utcnow()
            
            if status == "completed" or status == "failed":
                execution.completed_at = datetime.utcnow()
                
            if error:
                execution.error = error
                
            if result:
                execution.result = result
                
            # Update metadata
            metadata = execution.extra_metadata or {}
            metadata["steps_completed"] = len(self.executed_steps)
            metadata["last_updated"] = datetime.utcnow().isoformat()
            execution.extra_metadata = metadata
            
            session.add(execution)
            session.commit()
    
    def build_execution_graph(self) -> Tuple[Dict[str, List[str]], Dict[str, Dict]]:
        """
        Build a graph representation of the workflow for execution.
        Works with both legacy steps and node/edge formats.
        
        Returns:
            Tuple of (dependencies, step_definitions)
            - dependencies: Dict mapping step IDs to lists of dependent step IDs
            - step_definitions: Dict mapping step IDs to step definitions
        """
        workflow = self.load_workflow()
        
        # Check if we have the new node/edge format
        if workflow.nodes and workflow.edges:
            return self._build_graph_from_nodes_edges(workflow.nodes, workflow.edges)
        
        # Fall back to legacy steps format
        return self._build_graph_from_steps(workflow.steps)
    
    def _build_graph_from_nodes_edges(
        self, nodes: List[Dict], edges: List[Dict]
    ) -> Tuple[Dict[str, List[str]], Dict[str, Dict]]:
        """
        Build execution graph from node/edge representation.
        
        Args:
            nodes: List of node definitions from the visual editor
            edges: List of edge definitions connecting the nodes
            
        Returns:
            Tuple of (dependencies, step_definitions)
        """
        # Map of node ID -> list of nodes that depend on it
        dependencies = defaultdict(list)
        
        # Map of edge source -> target
        edge_map = defaultdict(list)
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and target:
                edge_map[source].append(target)
        
        # Build dependencies (reversed edges)
        for source, targets in edge_map.items():
            for target in targets:
                dependencies[target].append(source)
        
        # Create step definitions from nodes
        step_definitions = {}
        for node in nodes:
            node_id = node.get("id")
            if not node_id:
                continue
                
            node_type = node.get("type", "step")
            node_data = node.get("data", {})
            
            # Convert node to step definition
            step_def = {
                "id": node_id,
                "type": node_type,
                "params": {
                    "label": node_data.get("label", f"Step {node_id}"),
                }
            }
            
            # Add type-specific parameters
            if node_type == "approval":
                step_def["params"]["requiresApproval"] = node_data.get("requiresApproval", True)
                step_def["params"]["approvers"] = node_data.get("approvers", [])
                
            elif node_type == "decision":
                step_def["params"]["conditions"] = node_data.get("conditions", [])
                # Map outgoing edges to targets for decision nodes
                targets = edge_map.get(node_id, [])
                if targets:
                    step_def["params"]["targets"] = targets
                    
            elif node_type == "shell":
                step_def["params"]["command"] = node_data.get("command", "")
                
            elif node_type == "http":
                step_def["params"]["url"] = node_data.get("url", "")
                step_def["params"]["method"] = node_data.get("method", "GET")
                
            elif node_type == "llm":
                step_def["params"]["prompt"] = node_data.get("prompt", "")
                step_def["params"]["model"] = node_data.get("model", "")
            
            step_definitions[node_id] = step_def
            
        return dict(dependencies), step_definitions
    
    def _build_graph_from_steps(self, steps: List[Dict]) -> Tuple[Dict[str, List[str]], Dict[str, Dict]]:
        """
        Build execution graph from legacy linear steps format.
        
        Args:
            steps: List of step definitions in the legacy format
            
        Returns:
            Tuple of (dependencies, step_definitions)
        """
        dependencies = {}
        step_definitions = {}
        
        # For linear steps, each step depends on the previous one
        prev_step_id = None
        
        for i, step in enumerate(steps):
            step_id = step.get("id", f"step_{i}")
            
            # Store step definition
            step_with_id = step.copy()
            step_with_id["id"] = step_id
            step_definitions[step_id] = step_with_id
            
            # Set dependency on previous step
            if prev_step_id:
                dependencies[step_id] = [prev_step_id]
            else:
                dependencies[step_id] = []
                
            prev_step_id = step_id
            
        return dependencies, step_definitions
    
    def topological_sort(
        self, dependencies: Dict[str, List[str]]
    ) -> List[str]:
        """
        Perform topological sort to determine execution order.
        
        Args:
            dependencies: Dict mapping step IDs to their dependencies
            
        Returns:
            List of step IDs in execution order
        """
        # Build a graph of dependencies
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        # Initialize graph and in-degree counts
        for node, deps in dependencies.items():
            for dep in deps:
                graph[dep].append(node)
                in_degree[node] += 1
            
            # Ensure the node is in the graph even if it has no outgoing edges
            if node not in graph:
                graph[node] = []
                
            # Ensure dependencies are in the graph
            for dep in deps:
                if dep not in graph:
                    graph[dep] = []
        
        # Find all nodes with no dependencies (in-degree = 0)
        queue = deque([node for node in graph if in_degree[node] == 0])
        sorted_nodes = []
        
        # Process nodes in topological order
        while queue:
            node = queue.popleft()
            sorted_nodes.append(node)
            
            # Reduce in-degree of dependent nodes
            for dependent in graph[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # Check for cycles
        if len(sorted_nodes) != len(graph):
            logger.warning("Workflow contains cycles, some steps may not be executed")
            
        return sorted_nodes
    
    def execute_workflow(self) -> Dict[str, Any]:
        """
        Execute the workflow and return the result.
        
        Returns:
            Dict containing execution results
        """
        try:
            # Load workflow and create execution record
            workflow = self.load_workflow()
            self.create_execution_record()
            
            logger.info(f"Starting execution of workflow {workflow.id}: {workflow.name}")
            
            # Build execution graph
            dependencies, step_definitions = self.build_execution_graph()
            
            # Determine execution order
            execution_order = self.topological_sort(dependencies)
            
            if not execution_order:
                error_msg = "No executable steps found in workflow"
                self.update_execution_status("failed", error=error_msg)
                return {"status": "failed", "error": error_msg}
            
            # Execute steps in order
            result = self._execute_steps(execution_order, step_definitions)
            
            # Update final status
            if result.get("status") == "failed":
                self.update_execution_status("failed", error=result.get("error"), result=result)
            elif result.get("status") == "waiting_approval":
                self.update_execution_status("waiting_approval", result=result)
            else:
                self.update_execution_status("completed", result=result)
                
            return result
            
        except Exception as e:
            logger.exception(f"Error executing workflow: {str(e)}")
            self.update_execution_status("failed", error=str(e))
            return {"status": "failed", "error": str(e)}
    
    def _execute_steps(
        self, execution_order: List[str], step_definitions: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """
        Execute steps in the specified order.
        
        Args:
            execution_order: List of step IDs in execution order
            step_definitions: Dict mapping step IDs to step definitions
            
        Returns:
            Dict containing execution results
        """
        results = {}
        
        for step_id in execution_order:
            # Skip if step already executed
            if step_id in self.executed_steps:
                continue
                
            # Get step definition
            step_def = step_definitions.get(step_id)
            if not step_def:
                logger.warning(f"Step {step_id} not found in definitions, skipping")
                continue
                
            # Get step type and parameters
            step_type = step_def.get("type", "step")
            params = step_def.get("params", {})
            
            logger.info(f"Executing step {step_id} of type {step_type}")
            
            # Execute the step
            step_result = execute_step(step_id, step_type, params, self.context)
            results[step_id] = step_result
            
            # Check for execution success
            if not step_result.get("success", False):
                error_msg = step_result.get("error", "Unknown error")
                logger.error(f"Step {step_id} failed: {error_msg}")
                return {
                    "status": "failed",
                    "error": f"Step {step_id} failed: {error_msg}",
                    "step_id": step_id,
                    "results": results
                }
                
            # Handle specific step types
            if step_type == "approval" and step_result.get("result", {}).get("status") == "pending":
                # Step is waiting for approval
                self.pending_approvals[step_id] = step_result
                return {
                    "status": "waiting_approval",
                    "approval_id": step_result.get("result", {}).get("approval_id"),
                    "step_id": step_id,
                    "results": results
                }
                
            elif step_type == "decision":
                # Get target from decision result
                target = step_result.get("result", {}).get("target")
                if target and target in step_definitions:
                    # Execute the target step next (out of order)
                    target_result = self._execute_step(target, step_definitions)
                    results[target] = target_result
                    
                    if not target_result.get("success", False):
                        return {
                            "status": "failed",
                            "error": f"Decision target step {target} failed",
                            "step_id": target,
                            "results": results
                        }
            
            # Store step result in context for variable substitution in later steps
            self.context[f"step_{step_id}"] = step_result.get("result", {})
            if "result" in step_result and isinstance(step_result["result"], dict):
                for key, value in step_result["result"].items():
                    self.context[f"{step_id}_{key}"] = value
            
            # Mark step as executed
            self.executed_steps.add(step_id)
            
            # Update execution progress
            self.update_execution_status("running")
        
        return {
            "status": "completed",
            "results": results
        }
    
    def _execute_step(self, step_id: str, step_definitions: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Execute a single step.
        
        Args:
            step_id: ID of the step to execute
            step_definitions: Dict mapping step IDs to step definitions
            
        Returns:
            Dict containing step execution result
        """
        # Skip if already executed
        if step_id in self.executed_steps:
            return {"success": True, "skipped": True, "step_id": step_id}
            
        # Get step definition
        step_def = step_definitions.get(step_id)
        if not step_def:
            return {"success": False, "error": f"Step {step_id} not found", "step_id": step_id}
            
        # Get step type and parameters
        step_type = step_def.get("type", "step")
        params = step_def.get("params", {})
        
        # Execute the step
        step_result = execute_step(step_id, step_type, params, self.context)
        
        # If successful, mark as executed and update context
        if step_result.get("success", False):
            self.executed_steps.add(step_id)
            self.context[f"step_{step_id}"] = step_result.get("result", {})
            if "result" in step_result and isinstance(step_result["result"], dict):
                for key, value in step_result["result"].items():
                    self.context[f"{step_id}_{key}"] = value
        
        return step_result
    
    def handle_approval(self, approval_id: str, approved: bool, comments: str = None) -> Dict[str, Any]:
        """
        Handle an approval response and continue workflow execution if approved.
        
        Args:
            approval_id: ID of the approval to handle
            approved: Whether the approval was granted
            comments: Optional comments from the approver
            
        Returns:
            Dict containing execution results
        """
        # Find the step waiting for this approval
        step_id = None
        for sid, result in self.pending_approvals.items():
            if result.get("result", {}).get("approval_id") == approval_id:
                step_id = sid
                break
                
        if not step_id:
            return {"status": "failed", "error": f"Approval {approval_id} not found"}
            
        # Update approval result
        approval_result = self.pending_approvals[step_id].get("result", {})
        approval_result["status"] = "approved" if approved else "rejected"
        approval_result["approved"] = approved
        approval_result["comments"] = comments
        approval_result["processed_at"] = datetime.utcnow().isoformat()
        
        # Update context
        self.context[f"step_{step_id}"] = approval_result
        self.context[f"{step_id}_approved"] = approved
        
        # Mark step as executed
        self.executed_steps.add(step_id)
        
        if not approved:
            # If rejected, stop workflow execution
            result = {
                "status": "failed",
                "error": f"Approval {approval_id} was rejected",
                "approval_id": approval_id,
                "step_id": step_id
            }
            self.update_execution_status("failed", error=result["error"], result=result)
            return result
            
        # Continue workflow execution
        dependencies, step_definitions = self.build_execution_graph()
        execution_order = self.topological_sort(dependencies)
        
        # Filter out already executed steps
        remaining_steps = [s for s in execution_order if s not in self.executed_steps]
        
        if not remaining_steps:
            # All steps completed
            result = {"status": "completed", "approval_id": approval_id}
            self.update_execution_status("completed", result=result)
            return result
            
        # Execute remaining steps
        result = self._execute_steps(remaining_steps, step_definitions)
        
        # Update final status
        if result.get("status") == "failed":
            self.update_execution_status("failed", error=result.get("error"), result=result)
        elif result.get("status") == "waiting_approval":
            self.update_execution_status("waiting_approval", result=result)
        else:
            self.update_execution_status("completed", result=result)
            
        return result


def execute_workflow_by_id(workflow_id: int) -> Dict[str, Any]:
    """
    Helper function to execute a workflow by ID.
    
    Args:
        workflow_id: ID of the workflow to execute
        
    Returns:
        Dict containing execution results
    """
    engine = WorkflowEngine(workflow_id=workflow_id)
    return engine.execute_workflow()


def approve_workflow_step(execution_id: int, approval_id: str, approved: bool, comments: str = None) -> Dict[str, Any]:
    """
    Helper function to approve a workflow step.
    
    Args:
        execution_id: ID of the execution record
        approval_id: ID of the approval to handle
        approved: Whether the approval was granted
        comments: Optional comments from the approver
        
    Returns:
        Dict containing execution results
    """
    # Load execution record
    with get_session() as session:
        execution = session.get(Execution, execution_id)
        if not execution:
            return {"status": "failed", "error": f"Execution {execution_id} not found"}
            
        if execution.status != "waiting_approval":
            return {"status": "failed", "error": f"Execution {execution_id} is not waiting for approval"}
            
        workflow_id = execution.workflow_id
    
    # Create engine and handle approval
    engine = WorkflowEngine(workflow_id=workflow_id)
    engine.execution_id = execution_id
    engine.execution = execution
    
    # Load existing context and state from execution record
    if execution.result and isinstance(execution.result, dict):
        engine.context = execution.result.get("context", {})
        engine.executed_steps = set(execution.result.get("executed_steps", []))
        
        # Reconstruct pending approvals
        pending = execution.result.get("pending_approvals", {})
        for step_id, approval in pending.items():
            engine.pending_approvals[step_id] = approval
    
    return engine.handle_approval(approval_id, approved, comments)
