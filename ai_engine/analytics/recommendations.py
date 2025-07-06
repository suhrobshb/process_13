"""
Adaptive Workflow Improvement & Recommendations Engine
======================================================

This module provides a sophisticated analytics engine that moves beyond simple
execution and proactively helps users improve their automations. It analyzes
the historical performance patterns of workflows to identify bottlenecks,
reliability issues, and optimization opportunities.

Key Features:
-   **Performance Pattern Analysis**: Ingests historical execution data for a
    workflow, including the status and duration of each individual step.
-   **Reliability Analysis**: Identifies steps within a workflow that have a high
    failure rate, suggesting they may be brittle and require attention.
-   **Efficiency Analysis**: Pinpoints steps that are significant time sinks or
    bottlenecks in the automation process.
-   **Actionable Recommendations**: Translates raw analytical findings into clear,
    human-readable recommendations, each with a category (e.g., 'reliability',
    'efficiency') and a severity level.
-   **Data-Driven Suggestions**: The recommendations are based on statistical
    analysis of past performance, providing objective evidence for improvement.
-   **Extensible Design**: The engine is built with a modular structure, making it
    easy to add new types of analysis and recommendations in the future (e.g.,
    cost optimization, security hardening).

This engine empowers users and administrators to continuously improve their
automations, ensuring they remain robust, efficient, and valuable over time.
"""

import logging
from collections import defaultdict
from typing import List, Dict, Any
import random
import statistics

# Configure logging
logger = logging.getLogger(__name__)

# --- Mock Data Store ---
# In a real application, this function would query the `executions` and
# `execution_step_results` tables from the database for a given workflow_id.

def _get_workflow_execution_history(workflow_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Mock function to simulate fetching detailed execution history for a workflow.
    
    This data is intentionally crafted to contain patterns that the analysis
    functions can detect.
    """
    logger.info(f"Fetching mock execution history for workflow_id={workflow_id}")
    
    history = []
    for i in range(limit):
        # --- Simulate a step that is brittle and often fails ---
        login_step_fails = random.random() < 0.30  # 30% failure rate
        login_step_result = {
            "step_id": "step_1_login",
            "name": "Login to Web Portal",
            "status": "failed" if login_step_fails else "completed",
            "duration_seconds": random.uniform(5.0, 8.0)
        }
        
        # --- Simulate a step that is a major time bottleneck ---
        report_step_duration = random.uniform(60.0, 90.0)
        report_step_result = {
            "step_id": "step_2_generate_report",
            "name": "Generate Report via UI",
            "status": "completed",
            "duration_seconds": report_step_duration
        }
        
        # --- Simulate a normal, healthy step ---
        save_step_result = {
            "step_id": "step_3_save_file",
            "name": "Save Report to Disk",
            "status": "completed",
            "duration_seconds": random.uniform(1.0, 2.0)
        }
        
        # An execution only completes if all its steps complete
        is_overall_success = not login_step_fails
        
        execution_record = {
            "execution_id": f"exec_{i}",
            "status": "completed" if is_overall_success else "failed",
            "step_results": [login_step_result, report_step_result, save_step_result]
        }
        history.append(execution_record)
        
    return history

# --- Analysis Functions ---

def _find_frequently_failing_steps(
    execution_history: List[Dict[str, Any]],
    failure_threshold: float = 0.20
) -> List[Dict[str, Any]]:
    """
    Analyzes execution history to find steps with a high failure rate.
    """
    step_stats = defaultdict(lambda: {"failures": 0, "total": 0})
    
    for execution in execution_history:
        for step in execution.get("step_results", []):
            step_id = step["step_id"]
            step_stats[step_id]["total"] += 1
            if step["status"] == "failed":
                step_stats[step_id]["failures"] += 1
            # Store name for easy access later
            step_stats[step_id]["name"] = step["name"]

    failing_steps = []
    for step_id, stats in step_stats.items():
        if stats["total"] > 0:
            failure_rate = stats["failures"] / stats["total"]
            if failure_rate >= failure_threshold:
                failing_steps.append({
                    "step_id": step_id,
                    "name": stats["name"],
                    "failure_rate": failure_rate,
                    "total_runs": stats["total"]
                })
    
    return failing_steps

def _find_inefficient_steps(
    execution_history: List[Dict[str, Any]],
    std_dev_threshold: float = 2.0
) -> List[Dict[str, Any]]:
    """
    Analyzes execution history to find steps that are performance bottlenecks.
    Identifies steps whose average duration is significantly above the mean for the workflow.
    """
    step_durations = defaultdict(list)
    
    for execution in execution_history:
        if execution["status"] == "completed": # Only consider successful runs for duration analysis
            for step in execution.get("step_results", []):
                step_durations[step["step_id"]].append(step["duration_seconds"])

    if not step_durations:
        return []

    avg_step_durations = {
        step_id: statistics.mean(durations)
        for step_id, durations in step_durations.items() if durations
    }
    
    # Calculate the overall average and standard deviation of step durations
    all_avg_durations = list(avg_step_durations.values())
    if len(all_avg_durations) < 2:
        return [] # Not enough data for statistical comparison
        
    overall_mean = statistics.mean(all_avg_durations)
    overall_std_dev = statistics.stdev(all_avg_durations)

    inefficient_steps = []
    for step_id, avg_duration in avg_step_durations.items():
        if overall_std_dev > 0:
            z_score = (avg_duration - overall_mean) / overall_std_dev
            if z_score > std_dev_threshold:
                inefficient_steps.append({
                    "step_id": step_id,
                    "name": f"Step '{step_id}'", # A real implementation would fetch the name
                    "average_duration": avg_duration,
                    "workflow_average_duration": overall_mean,
                    "z_score": z_score
                })

    return inefficient_steps


# --- Public Orchestration Function ---

def get_improvement_recommendations(workflow_id: int, user: Any = None) -> List[Dict[str, Any]]:
    """
    Orchestrates the analysis of a workflow's history and generates a list of
    actionable improvement recommendations.

    Args:
        workflow_id: The ID of the workflow to analyze.
        user: The user object, for future permission checks.

    Returns:
        A list of recommendation dictionaries.
    """
    logger.info(f"Generating improvement recommendations for workflow_id={workflow_id}")
    
    # In a real app, you might add permission checks here using the `user` object.
    
    # 1. Fetch the data
    history = _get_workflow_execution_history(workflow_id)
    if not history:
        return []

    recommendations = []

    # 2. Run reliability analysis
    failing_steps = _find_frequently_failing_steps(history)
    for step in failing_steps:
        recommendations.append({
            "recommendation_id": f"reliability_{step['step_id']}",
            "title": f"Improve Reliability of Step: '{step['name']}'",
            "description": f"This step has a failure rate of {step['failure_rate']:.0%}. Consider adding more robust error handling, increasing timeouts, or using a more resilient selector (e.g., vision-based) to improve its stability.",
            "category": "reliability",
            "severity": "high" if step['failure_rate'] > 0.5 else "medium",
        })

    # 3. Run efficiency analysis
    inefficient_steps = _find_inefficient_steps(history)
    for step in inefficient_steps:
        recommendations.append({
            "recommendation_id": f"efficiency_{step['step_id']}",
            "title": f"Optimize Performance of Step: '{step['name']}'",
            "description": f"This step's average execution time ({step['average_duration']:.1f}s) is a significant bottleneck. Investigate if it can be replaced with a direct API call or a more efficient background process.",
            "category": "efficiency",
            "severity": "medium",
        })
        
    # 4. (Future) Add other analyzers here, e.g., for cost or security.

    logger.info(f"Generated {len(recommendations)} improvement recommendations for workflow_id={workflow_id}")
    return recommendations


# --- Example Usage ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("--- Running Workflow Improvement Recommendations Demo ---")
    
    demo_workflow_id = 42
    recommendations = get_improvement_recommendations(demo_workflow_id)
    
    if not recommendations:
        print("\n✅ No improvement recommendations found. The workflow is performing well!")
    else:
        print(f"\n🔥 Found {len(recommendations)} Improvement Recommendations for Workflow {demo_workflow_id}:")
        for rec in recommendations:
            print("\n-------------------------------------------------")
            print(f"  Title: {rec['title']}")
            print(f"  Severity: {rec['severity'].upper()} | Category: {rec['category'].title()}")
            print(f"  Suggestion: {rec['description']}")
            print("-------------------------------------------------")
