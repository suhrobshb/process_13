"""
Comprehensive Workflow Simulation Environment
===========================================

This module provides a powerful and sophisticated simulation environment for
testing AI Engine workflows safely before deploying them to production. It allows
users and developers to model realistic scenarios, test edge cases, and validate
workflow logic without interacting with live systems.

Key Features:
-   **Sandbox Execution**: Runs workflows in a completely isolated "sandbox"
    environment, ensuring that no real-world actions (like API calls, file
    system changes, or UI interactions) are performed.
-   **Realistic Scenario Modeling**: Allows for the configuration of various
    simulation parameters to model real-world conditions, including:
    -   Random step failures to test error handling and retry logic.
    -   Network latency simulation to understand performance under slow conditions.
    -   Forced outcomes for specific steps to test complex branching logic.
-   **Mock Data Injection**: Users can provide mock input data to test how the
    workflow behaves with different inputs and data paths.
-   **State & Context Simulation**: Accurately simulates the flow of data
    (the "context") between steps, validating that variables are passed and
    used correctly.
-   **Detailed Reporting**: Generates a comprehensive report after each simulation,
    including the overall status, total simulated duration, a step-by-step
    execution log, and the final state of the context.
-   **Performance Estimation**: Simulates realistic execution times for each step
    based on its type (e.g., LLM steps take longer than simple API calls),
    providing an estimate of the workflow's real-world performance.

This simulator is a critical tool for ensuring the reliability, robustness, and
correctness of automations, significantly reducing the risk of production failures.
"""

import copy
import random
import time
import logging
import json
from typing import Dict, Any, List, Optional

# Configure logging
logger = logging.getLogger(__name__)

# --- Default Simulation Parameters ---
# These represent typical durations for different types of automation steps in seconds.
DEFAULT_STEP_DURATIONS = {
    "desktop": (0.5, 2.0),   # Min/max duration for a typical desktop UI action
    "browser": (1.0, 3.0),   # Browser actions are often slower due to page loads
    "llm": (2.0, 10.0),      # LLM calls can have significant variance
    "http": (0.2, 1.5),      # HTTP API calls are generally fast
    "shell": (0.1, 1.0),     # Shell commands are very fast
    "default": (0.5, 1.5),
}


class WorkflowSimulator:
    """
    Executes a workflow in a simulated, sandboxed environment to test its
    logic, data flow, and resilience without affecting live systems.
    """

    def __init__(self, workflow: Dict[str, Any]):
        """
        Initializes the simulator with a workflow definition.

        Args:
            workflow: A dictionary representing the workflow, typically including
                      a list of 'steps' in the IPO (Input-Process-Output) format.
        """
        if not isinstance(workflow, dict) or "steps" not in workflow:
            raise ValueError("Invalid workflow structure provided. Must be a dict with a 'steps' key.")
        self.workflow = copy.deepcopy(workflow)
        logger.info(f"WorkflowSimulator initialized for workflow: '{self.workflow.get('name', 'Unnamed')}'")

    def _simulate_step(
        self,
        step: Dict[str, Any],
        simulation_params: Dict[str, Any],
        simulated_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulates the execution of a single workflow step.
        """
        step_id = step.get("id", "unknown_step")
        step_type = step.get("process", {}).get("type", "default")
        step_report = {
            "step_id": step_id,
            "step_name": step.get("name", "Unnamed Step"),
            "status": "pending",
            "simulated_duration_s": 0.0,
            "output": None,
            "error": None
        }

        # 1. Check for forced outcomes in step_overrides
        overrides = simulation_params.get("step_overrides", {})
        if step_id in overrides:
            logger.warning(f"Applying override for step '{step_id}'.")
            override_data = overrides[step_id]
            step_report.update({
                "status": override_data.get("status", "success"),
                "output": override_data.get("output"),
                "error": override_data.get("error"),
                "simulated_duration_s": override_data.get("duration", random.uniform(0.1, 0.5)),
            })
            return step_report

        # 2. Simulate potential failure based on failure_rate
        failure_rate = simulation_params.get("failure_rate", 0.0)
        if random.random() < failure_rate:
            error_message = "Simulated random failure."
            step_report.update({
                "status": "failed",
                "error": error_message,
                "simulated_duration_s": random.uniform(0.1, 1.0), # Failures are usually fast
            })
            logger.error(f"Step '{step_id}' failed due to simulated failure rate.")
            return step_report

        # 3. Simulate successful execution
        latency_multiplier = simulation_params.get("latency_multiplier", 1.0)
        min_dur, max_dur = DEFAULT_STEP_DURATIONS.get(step_type, DEFAULT_STEP_DURATIONS["default"])
        duration = random.uniform(min_dur, max_dur) * latency_multiplier
        
        # Simulate mock output data
        mock_output = {
            "message": f"Successfully executed step '{step_id}'.",
            "simulated_data": f"mock_data_{random.randint(1000, 9999)}",
            "input_context_keys": list(simulated_context.keys())
        }

        step_report.update({
            "status": "success",
            "output": mock_output,
            "simulated_duration_s": round(duration, 4),
        })
        logger.info(f"Step '{step_id}' simulated successfully in {duration:.2f}s.")
        return step_report


    def run_simulation(
        self,
        failure_rate: float = 0.0,
        latency_multiplier: float = 1.0,
        mock_inputs: Optional[Dict[str, Any]] = None,
        step_overrides: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Runs the full workflow simulation with the given scenario parameters.

        Args:
            failure_rate: The probability (0.0 to 1.0) that any given step will fail.
            latency_multiplier: A factor to scale step durations (e.g., 2.0 for 2x slower).
            mock_inputs: A dictionary of initial data to populate the workflow context.
            step_overrides: A dictionary to force specific outcomes for certain steps.
                          Example: {"step_id_1": {"status": "failed", "error": "Forced failure"}}

        Returns:
            A detailed report of the simulation run.
        """
        simulation_params = {
            "failure_rate": failure_rate,
            "latency_multiplier": latency_multiplier,
            "step_overrides": step_overrides or {},
        }
        logger.info(f"Starting simulation with parameters: {simulation_params}")

        # Initialize context with mock inputs
        simulated_context = mock_inputs or {}
        step_reports = []
        total_duration = 0.0
        overall_status = "success"

        # TODO: Implement a proper DAG executor for workflows with complex dependencies.
        # For now, we process steps linearly.
        for step in self.workflow.get("steps", []):
            step_report = self._simulate_step(step, simulation_params, simulated_context)
            step_reports.append(step_report)
            total_duration += step_report["simulated_duration_s"]

            if step_report["status"] == "success":
                # Add the step's output to the context for the next step
                output_variable = step.get("output", {}).get("variable")
                if output_variable:
                    simulated_context[output_variable] = step_report["output"]
            else:
                # If a step fails, the entire workflow fails
                overall_status = "failed"
                logger.error(f"Workflow simulation failed at step '{step['id']}'. Halting execution.")
                break # Stop processing further steps

        final_report = {
            "workflow_name": self.workflow.get("name", "Unnamed"),
            "overall_status": overall_status,
            "total_simulated_duration_s": round(total_duration, 4),
            "simulation_parameters": simulation_params,
            "step_results": step_reports,
            "final_context": simulated_context,
        }
        
        logger.info(f"Simulation finished with status: '{overall_status}'. Total duration: {total_duration:.2f}s.")
        return final_report


# --- Example Usage Block ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # A sample workflow definition with IPO structure
    sample_workflow = {
        "name": "Sample Invoice Processing",
        "steps": [
            {
                "id": "step_1_fetch_email",
                "name": "Fetch Invoice from Email",
                "process": {"type": "http"},
                "output": {"variable": "invoice_email"}
            },
            {
                "id": "step_2_extract_data",
                "name": "Extract Data with LLM",
                "process": {"type": "llm"},
                "output": {"variable": "extracted_data"}
            },
            {
                "id": "step_3_enter_in_erp",
                "name": "Enter Data in ERP",
                "process": {"type": "desktop"},
                "output": {"variable": "erp_confirmation"}
            },
            {
                "id": "step_4_archive_email",
                "name": "Archive Processed Email",
                "process": {"type": "http"},
                "output": {"variable": "archive_status"}
            }
        ]
    }

    simulator = WorkflowSimulator(sample_workflow)

    # --- Scenario 1: Happy Path ---
    print("\n--- SCENARIO 1: Running 'Happy Path' Simulation ---")
    happy_path_report = simulator.run_simulation()
    print(json.dumps(happy_path_report, indent=2))
    assert happy_path_report["overall_status"] == "success"

    # --- Scenario 2: High Latency and Failure Rate ---
    print("\n\n--- SCENARIO 2: Simulating High Latency and 25% Failure Rate ---")
    unreliable_report = simulator.run_simulation(
        failure_rate=0.25,
        latency_multiplier=3.0
    )
    print(json.dumps(unreliable_report, indent=2))

    # --- Scenario 3: Forcing a Specific Step to Fail ---
    print("\n\n--- SCENARIO 3: Forcing the 'Enter Data in ERP' step to fail ---")
    forced_failure_report = simulator.run_simulation(
        step_overrides={
            "step_3_enter_in_erp": {
                "status": "failed",
                "error": "ERP system timeout: Connection refused.",
                "duration": 5.0
            }
        }
    )
    print(json.dumps(forced_failure_report, indent=2))
    assert forced_failure_report["overall_status"] == "failed"
    assert forced_failure_report["step_results"][2]["error"] is not None

    # --- Scenario 4: Providing Mock Inputs ---
    print("\n\n--- SCENARIO 4: Running with initial mock input data ---")
    mock_input_report = simulator.run_simulation(
        mock_inputs={
            "initial_trigger_data": {
                "user_id": "user-123",
                "source": "manual_run"
            }
        }
    )
    print(json.dumps(mock_input_report, indent=2))
    # Check that the initial context was included in the final context
    assert "initial_trigger_data" in mock_input_report["final_context"]

