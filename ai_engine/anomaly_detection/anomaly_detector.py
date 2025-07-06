"""
Predictive Anomaly Detection & Alerting Engine
=============================================

This module provides a sophisticated, stateful anomaly detection system that
monitors workflow execution patterns to proactively identify issues before they
impact users or business processes.

Key Features:
-   **Statistical Baseline Learning**: Automatically learns the "normal" behavior
    for each workflow by calculating rolling statistics for key metrics like
    execution duration and success rate.
-   **Multi-Faceted Anomaly Detection**: Identifies various types of anomalies:
    -   **Duration Spikes**: Detects when a workflow takes significantly longer
        to run than its historical average (using Z-score).
    -   **Failure Rate Increases**: Flags when a workflow's failure rate starts
        trending upwards.
    -   **Sudden Changes**: Catches when a historically stable workflow suddenly
        starts failing, or vice-versa.
-   **Stateful and Persistent**: Maintains a persistent baseline of workflow
    metrics (stored as a JSON file), allowing it to become more accurate over
    time and across application restarts.
-   **Configurable Sensitivity**: Allows for tuning of detection thresholds (e.g.,
    Z-score, window size) to match business requirements.
-   **Proactive Alerting Integration**: Designed to be easily integrated with an
    alerting system (e.g., Slack, PagerDuty) to notify administrators when a
    critical anomaly is detected.
-   **Thread-Safe**: Ensures that baselines can be updated safely from multiple
    concurrent workflow executions (e.g., from multiple Celery workers).

This engine is a crucial component for building a self-healing and resilient
automation platform, moving from reactive problem-solving to proactive issue
prevention.
"""

import os
import json
import math
import logging
import threading
import random
from collections import deque
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# --- Constants ---
BASELINE_PERSISTENCE_PATH = "storage/anomaly_detection/baselines.json"
DEFAULT_WINDOW_SIZE = 50  # Number of recent executions to consider for rolling stats
DEFAULT_Z_SCORE_THRESHOLD = 3.0 # Threshold for duration spikes (3 std deviations)


class AnomalyDetector:
    """
    Monitors workflow executions to detect statistical anomalies.
    """

    def __init__(
        self,
        persistence_path: str = BASELINE_PERSISTENCE_PATH,
        window_size: int = DEFAULT_WINDOW_SIZE,
        z_score_threshold: float = DEFAULT_Z_SCORE_THRESHOLD
    ):
        """
        Initializes the Anomaly Detector.

        Args:
            persistence_path: Path to the JSON file for storing baselines.
            window_size: The number of recent executions to use for calculations.
            z_score_threshold: The standard deviation multiple for duration anomalies.
        """
        self.persistence_path = persistence_path
        self.window_size = window_size
        self.z_score_threshold = z_score_threshold
        
        # In-memory store for workflow baselines.
        # Format: { workflow_id: { 'durations': deque([...]), 'successes': deque([...]) }, ... }
        self.baselines: Dict[str, Dict[str, deque]] = {}
        self._lock = threading.Lock()
        
        self._load_baselines()

    def _load_baselines(self):
        """Loads historical baselines from the persistence file."""
        with self._lock:
            if os.path.exists(self.persistence_path):
                try:
                    with open(self.persistence_path, 'r') as f:
                        # Convert lists from JSON back to deques
                        raw_baselines = json.load(f)
                        for wf_id, data in raw_baselines.items():
                            self.baselines[wf_id] = {
                                'durations': deque(data.get('durations', []), maxlen=self.window_size),
                                'successes': deque(data.get('successes', []), maxlen=self.window_size)
                            }
                    logger.info(f"Successfully loaded anomaly detection baselines from {self.persistence_path}")
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"Failed to load baselines: {e}. Starting fresh.")
            else:
                logger.info("No existing baselines file found. Starting fresh.")

    def _save_baselines(self):
        """Saves the current baselines to the persistence file."""
        with self._lock:
            try:
                os.makedirs(os.path.dirname(self.persistence_path), exist_ok=True)
                # Convert deques to lists for JSON serialization
                serializable_baselines = {
                    wf_id: {k: list(v) for k, v in data.items()}
                    for wf_id, data in self.baselines.items()
                }
                with open(self.persistence_path, 'w') as f:
                    json.dump(serializable_baselines, f, indent=2)
            except IOError as e:
                logger.error(f"Failed to save baselines: {e}")

    def _update_baseline(self, workflow_id: str, duration: float, success: bool):
        """Updates the historical baseline for a given workflow."""
        with self._lock:
            # Ensure the workflow has an entry in the baselines
            if workflow_id not in self.baselines:
                self.baselines[workflow_id] = {
                    'durations': deque(maxlen=self.window_size),
                    'successes': deque(maxlen=self.window_size),
                }
            
            # Add the new data point
            self.baselines[workflow_id]['durations'].append(duration)
            self.baselines[workflow_id]['successes'].append(1 if success else 0)

    def check_for_anomalies(self, workflow_id: str, duration: float, success: bool) -> List[Dict[str, Any]]:
        """
        Checks a new execution record against the historical baseline for anomalies.

        Args:
            workflow_id: The unique identifier of the workflow.
            duration: The duration of the new execution in seconds.
            success: A boolean indicating if the execution was successful.

        Returns:
            A list of anomaly dictionaries. An empty list means no anomalies were detected.
        """
        anomalies = []
        
        with self._lock:
            baseline = self.baselines.get(workflow_id)
            # We need at least a few data points to have a meaningful baseline
            if not baseline or len(baseline['durations']) < 10:
                return []

            # --- 1. Duration Anomaly Check (Z-score) ---
            durations = list(baseline['durations'])
            mean_duration = sum(durations) / len(durations)
            # Standard deviation requires at least 2 points
            if len(durations) > 1:
                std_dev = math.sqrt(sum((x - mean_duration) ** 2 for x in durations) / (len(durations) - 1))
                # Avoid division by zero if all durations are identical
                if std_dev > 0:
                    z_score = (duration - mean_duration) / std_dev
                    if z_score > self.z_score_threshold:
                        anomalies.append({
                            "type": "duration_spike",
                            "severity": "critical",
                            "message": f"Execution duration ({duration:.2f}s) is significantly higher than average ({mean_duration:.2f}s).",
                            "details": {"z_score": z_score, "mean": mean_duration, "std_dev": std_dev}
                        })

            # --- 2. Failure Rate Anomaly Check ---
            successes = list(baseline['successes'])
            historical_success_rate = sum(successes) / len(successes)
            
            if not success and historical_success_rate > 0.95:
                # A stable workflow suddenly failed
                anomalies.append({
                    "type": "sudden_failure",
                    "severity": "critical",
                    "message": f"A workflow with a historical success rate of {historical_success_rate:.0%} has failed.",
                    "details": {"historical_success_rate": historical_success_rate}
                })
            
            # Check if the recent failure rate is increasing
            # Consider the last 10 executions for this check
            if len(successes) >= 10:
                recent_success_rate = sum(successes[-10:]) / 10
                if historical_success_rate - recent_success_rate > 0.25: # More than 25% drop
                     anomalies.append({
                        "type": "increasing_failure_rate",
                        "severity": "warning",
                        "message": f"Recent success rate ({recent_success_rate:.0%}) has dropped significantly from the historical average ({historical_success_rate:.0%}).",
                        "details": {"recent_rate": recent_success_rate, "historical_rate": historical_success_rate}
                    })

        return anomalies

    def update_and_check(self, workflow_id: str, duration: float, success: bool) -> List[Dict[str, Any]]:
        """
        The main public method. It first checks for anomalies against the *existing*
        baseline, then updates the baseline with the new data point.

        Args:
            workflow_id: The ID of the workflow.
            duration: The execution duration.
            success: The execution success status.

        Returns:
            A list of detected anomalies.
        """
        # Convert workflow_id to string to ensure consistent key types
        wf_id_str = str(workflow_id)
        
        # Check for anomalies *before* adding the new data point
        anomalies = self.check_for_anomalies(wf_id_str, duration, success)
        
        # Now, update the baseline with the new data
        self._update_baseline(wf_id_str, duration, success)
        
        # Persist the changes to disk periodically
        # In a real app, this might be done in a separate background thread
        if len(self.baselines.get(wf_id_str, {}).get('durations', [])) % 10 == 0:
            self._save_baselines()
            
        return anomalies


# --- Global Singleton Instance ---
anomaly_detector = AnomalyDetector()


# --- Example Usage ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Clean up previous demo runs
    if os.path.exists(BASELINE_PERSISTENCE_PATH):
        os.remove(BASELINE_PERSISTENCE_PATH)
    
    demo_detector = AnomalyDetector()
    WORKFLOW_ID = "wf_invoice_processing"

    print("--- Anomaly Detector Demo ---")
    print("1. Establishing a baseline with normal executions...")
    
    # Simulate 20 normal, successful executions
    for i in range(20):
        # Simulate normal duration with slight variance
        normal_duration = random.uniform(9.5, 10.5)
        anomalies = demo_detector.update_and_check(WORKFLOW_ID, normal_duration, True)
        if i > 10: # Don't check for anomalies until we have a decent baseline
            print(f"  Run {i+1}: Duration={normal_duration:.2f}s, Success=True. Anomalies: {len(anomalies)}")

    print("\nBaseline established. Current stats:")
    baseline_data = demo_detector.baselines[WORKFLOW_ID]
    mean_dur = sum(baseline_data['durations']) / len(baseline_data['durations'])
    print(f"  - Average Duration: {mean_dur:.2f}s")
    print(f"  - Success Rate: {sum(baseline_data['successes']) / len(baseline_data['successes']):.0%}")

    # --- 2. Simulate an anomalous execution ---
    print("\n2. Simulating an anomalous execution (duration spike)...")
    anomalous_duration = 35.0 # More than 3 standard deviations away
    anomalies = demo_detector.update_and_check(WORKFLOW_ID, anomalous_duration, True)
    
    if anomalies:
        print(f"  🚨 ANOMALY DETECTED:")
        for anomaly in anomalies:
            print(f"     - Type: {anomaly['type']}")
            print(f"     - Severity: {anomaly['severity']}")
            print(f"     - Message: {anomaly['message']}")
    else:
        print("  No anomaly detected.")

    # --- 3. Simulate another anomalous execution ---
    print("\n3. Simulating an anomalous execution (sudden failure)...")
    anomalies = demo_detector.update_and_check(WORKFLOW_ID, 10.1, False)
    
    if anomalies:
        print(f"  🚨 ANOMALY DETECTED:")
        for anomaly in anomalies:
            print(f"     - Type: {anomaly['type']}")
            print(f"     - Severity: {anomaly['severity']}")
            print(f"     - Message: {anomaly['message']}")
    else:
        print("  No anomaly detected.")
        
    # --- 4. Save the final baselines ---
    demo_detector._save_baselines()
    print(f"\nFinal baselines saved to '{demo_detector.persistence_path}'")
