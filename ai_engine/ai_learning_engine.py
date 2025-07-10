"""
AI Learning Engine
==================

This module is the "brain" of the AI Engine. It takes the raw, low-level event
data captured by the Recording Agent and transforms it into a high-level,
structured, and intelligent workflow.

The core responsibilities of this engine are:
1.  **Event Clustering**: Grouping raw events (clicks, keystrokes) into meaningful,
    high-level actions (e.g., "Login to Salesforce", "Fill out Invoice Form").
2.  **Intent Recognition**: Using an LLM to analyze clustered actions and generate
    human-readable titles and descriptions for the action step boxes.
3.  **Pattern Detection**: Identifying common automation patterns like loops (e.g.,
    processing rows in a spreadsheet) and conditional logic (e.g., handling an
    error message).
4.  **Confidence Scoring**: Calculating a confidence score for its interpretation
    of each action, highlighting areas that might require user review or
    re-recording.
5.  **Workflow Generation**: Producing a structured output (a graph of nodes and
    edges) that can be executed by the Workflow Engine or visualized in the UI.

This engine is designed to be application-agnostic, learning the user's specific
processes without needing pre-built integrations for every tool they use.
"""

import logging
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Callable

# Configure logging
logger = logging.getLogger(__name__)

# --- Mock LLM for demonstration purposes ---
# In a real implementation, this would be a client for OpenAI, Anthropic, etc.
class MockLLM:
    def generate(self, prompt: str) -> str:
        """Simulates an LLM generating a response."""
        logger.info(f"Simulating LLM call with prompt: '{prompt[:100]}...'")
        time.sleep(0.1) # Simulate network latency
        if "summarize the following actions" in prompt.lower():
            if "outlook" in prompt.lower() and "email" in prompt.lower():
                return "Check for New Load Request Emails in Outlook"
            elif "tms pro" in prompt.lower() and "search" in prompt.lower():
                return "Search for Available Drivers in TMS Pro"
            else:
                return "Perform User Action"
        elif "what is the business goal" in prompt.lower():
            return "The user is processing a new customer order."
        return "Generated LLM Response"

# --- Main Learning Engine Class ---

class AILearningEngine:
    """
    Analyzes raw recordings to produce structured, intelligent workflows.
    """

    def __init__(
        self,
        recording_data: List[Dict[str, Any]],
        business_context: Optional[str] = None,
        *,
        stream_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initializes the learning engine with a user's recording.

        Args:
            recording_data (List[Dict[str, Any]]): A list of event dictionaries
                captured by the recording agent.
            business_context (Optional[str]): An optional hint from the user about
                the overall goal of the process (e.g., "monthly financial reporting").
            stream_callback (Optional[Callable]):  A callable that will be invoked
                every time a new action-step node is generated.  This enables
                real-time streaming (e.g., over WebSocket) to the frontend.
        """
        self.raw_events = sorted(recording_data, key=lambda x: x.get('timestamp', 0))
        self.business_context = business_context
        self.stream_callback = stream_callback
        self.llm = MockLLM()
        logger.info(f"AILearningEngine initialized with {len(self.raw_events)} events.")

    # ------------------------------------------------------------------#
    #  Real-time streaming helper                                       #
    # ------------------------------------------------------------------#
    def _stream_node(self, node: Dict[str, Any]) -> None:
        """
        Sends an incrementally generated workflow node to the supplied
        ``stream_callback`` (if any).  Failures are logged but do not halt
        processing.
        """
        if not self.stream_callback:
            return
        try:
            # The event structure is important for the frontend to handle different real-time updates
            event_to_stream = {
                "event": "action_step_generated",
                "payload": node
            }
            self.stream_callback(event_to_stream)
            logger.debug("Streamed node %s to client", node.get("id"))
        except Exception as exc:  # noqa: broad-except
            # Streaming errors should never break offline learning
            logger.warning("Failed to stream node %s: %s", node.get("id"), exc)

    def _cluster_events_into_actions(self) -> List[List[Dict[str, Any]]]:
        """
        Groups a linear sequence of raw events into high-level action clusters.

        This is a key step where the AI identifies logical breaks in user activity.
        Clustering can be based on:
        - Time gaps between events (a long pause often indicates a new step).
        - Changes in the active application window.
        - Repetitive sequences (indicating a loop).
        - Interaction with specific UI elements (e.g., a "Save" button often ends a step).

        Returns:
            A list of action clusters, where each cluster is a list of raw events.
        """
        logger.info("Clustering raw events into high-level actions...")
        if not self.raw_events:
            return []

        clusters = []
        current_cluster = [self.raw_events[0]]
        last_event_time = self.raw_events[0].get('timestamp', 0)
        last_window = self.raw_events[0].get('title', '')

        # Time gap threshold in seconds to start a new cluster
        TIME_THRESHOLD = 3.0

        for event in self.raw_events[1:]:
            current_event_time = event.get('timestamp', 0)
            current_window = event.get('title', last_window) # Use last window if not present
            
            time_gap = current_event_time - last_event_time
            window_changed = current_window and last_window and current_window != last_window

            # Start a new cluster if there's a significant pause or window change
            if time_gap > TIME_THRESHOLD or window_changed:
                if current_cluster:
                    clusters.append(current_cluster)
                current_cluster = []

            current_cluster.append(event)
            last_event_time = current_event_time
            last_window = current_window

        if current_cluster:
            clusters.append(current_cluster)
        
        logger.info(f"Identified {len(clusters)} distinct action clusters.")
        return clusters

    def _get_action_summary_with_llm(self, action_cluster: List[Dict[str, Any]]) -> Tuple[str, str]:
        """
        Uses an LLM to generate a human-readable title and description for a cluster of actions.

        Args:
            action_cluster (List[Dict[str, Any]]): A list of raw events forming one action.

        Returns:
            A tuple containing the (title, description).
        """
        # Create a simplified summary of the events for the LLM prompt
        event_summary = []
        for event in action_cluster[:10]: # Limit to first 10 events for brevity
            summary = f"- Type: {event.get('type')}"
            if 'details' in event:
                summary += f", Details: {json.dumps(event['details'])}"
            event_summary.append(summary)
        
        prompt = f"""
        Analyze the following sequence of user actions and provide a concise, human-readable
        business-level summary.

        User Actions:
        {chr(10).join(event_summary)}

        Based on these actions, what is the most likely business task being performed?
        Respond with a short title (e.g., "Log into System", "Fill out Customer Form").
        """
        
        title = self.llm.generate(prompt)
        description = f"This step involves {len(action_cluster)} recorded actions, including clicks and keyboard inputs, to achieve the goal of '{title}'."
        
        return title, description

    def _calculate_confidence_score(self, action_cluster: List[Dict[str, Any]]) -> float:
        """
        Calculates a confidence score (0.0 to 1.0) for the AI's interpretation of an action.

        Confidence is based on factors like:
        - Clarity of action patterns (e.g., login forms are easy to recognize).
        - Presence of error messages or unexpected pop-ups.
        - Consistency of the actions.
        """
        # A simplified scoring model for demonstration
        score = 0.85  # Start with a base confidence
        
        # Penalize for potential signs of user uncertainty or errors
        for event in action_cluster:
            if event.get('type') == 'key' and event.get('key') == 'Key.backspace':
                score -= 0.05 # User made a typing mistake
            if event.get('type') == 'click' and event.get('details', {}).get('element_text', '').lower() in ['cancel', 'close']:
                score -= 0.1 # User may have cancelled an action
        
        # Boost score for clear, common patterns
        if any("login" in event.get('title', '').lower() for event in action_cluster):
            score += 0.1
        if any("submit" in event.get('details', {}).get('element_text', '').lower() for event in action_cluster):
            score += 0.05

        return max(0.0, min(1.0, score)) # Clamp score between 0 and 1

    def analyze_and_generate_workflow(self) -> Dict[str, Any]:
        """
        The main method that orchestrates the entire learning and generation process.

        Returns:
            A dictionary representing the structured workflow, including nodes,
            edges, and metadata like confidence scores.
        """
        logger.info("Starting workflow generation process...")
        
        action_clusters = self._cluster_events_into_actions()
        
        workflow_nodes = []
        workflow_edges = []
        last_node_id = None

        for i, cluster in enumerate(action_clusters):
            node_id = f"action_step_{i+1}"
            
            # Use LLM to get a business-friendly summary
            title, description = self._get_action_summary_with_llm(cluster)
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(cluster)
            
            # Create the node using the new explicit IPO structure
            node = {
                "id": node_id,
                "name": title,
                "input": {
                    "source": "previous_step.output" if last_node_id else "manual_trigger",
                    "description": f"Receives data from '{last_node_id}'." if last_node_id else "This is the first step, initiated by a trigger."
                },
                "process": {
                    "type": "desktop",  # Default to desktop runner for replaying raw events
                    "description": description,
                    "actions": cluster  # The raw events to be replayed
                },
                "output": {
                    "variable": f"{node_id}_output",
                    "description": f"The result of the '{title}' action."
                },
                "metadata": {
                    "confidence_score": round(confidence, 2),
                    "ai_generated": True,
                    "type": "desktop" # For the visual editor's node type
                }
            }
            workflow_nodes.append(node)
            
            # Create a simple linear connection to the previous node
            if last_node_id:
                workflow_edges.append({
                    "id": f"edge_{last_node_id}_to_{node_id}",
                    "source": last_node_id,
                    "target": node_id
                })

            # --- Real-time streaming of this node ---------------------#
            self._stream_node(node)

            last_node_id = node_id

        overall_confidence = sum(n['metadata']['confidence_score'] for n in workflow_nodes) / len(workflow_nodes) if workflow_nodes else 0
        
        final_workflow = {
            "name": f"Learned Workflow - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "description": f"Automatically generated from a recording. Business context: {self.business_context or 'Not provided'}",
            "overall_confidence": round(overall_confidence, 2),
            "steps": workflow_nodes, # Using 'steps' to align with the IPO model
            "nodes": [], # Keep these for visual editor if needed, but steps is primary
            "edges": workflow_edges
        }
        
        logger.info(f"Workflow generation complete. Overall confidence: {final_workflow['overall_confidence']:.2f}")
        return final_workflow

# --- Example Usage ---
if __name__ == "__main__":
    # Simulate raw recording data from the agent
    sample_recording_data = [
        {'timestamp': 1672531201.0, 'type': 'window_change', 'title': 'Inbox - user@company.com - Outlook'},
        {'timestamp': 1672531202.0, 'type': 'click', 'details': {'x': 250, 'y': 300, 'element_text': 'Email: New PO #12345'}},
        {'timestamp': 1672531203.0, 'type': 'double_click', 'details': {'x': 400, 'y': 500, 'element_text': 'po_12345.pdf'}},
        {'timestamp': 1672531207.0, 'type': 'window_change', 'title': 'po_12345.pdf - Adobe Reader'},
        {'timestamp': 1672531208.0, 'type': 'hotkey', 'details': {'keys': ['ctrl', 'c']}},
        {'timestamp': 1672531212.0, 'type': 'window_change', 'title': 'Customer Portal - Google Chrome'},
        {'timestamp': 1672531213.0, 'type': 'fill', 'details': {'selector': '#po_number', 'text': '12345'}},
        {'timestamp': 1672531214.0, 'type': 'click', 'details': {'selector': 'button#submit-po'}}
    ]
    
    print("--- Running AI Learning Engine Demo ---")
    
    # Instantiate the engine with the sample data
    learning_engine = AILearningEngine(sample_recording_data, business_context="Processing a new purchase order")
    
    # Generate the structured workflow
    structured_workflow = learning_engine.analyze_and_generate_workflow()
    
    # Print the result
    print("\n--- Generated Workflow Structure (with IPO) ---")
    print(json.dumps(structured_workflow, indent=2))
    
    print("\n--- Demo Complete ---")
    print("The raw recording has been analyzed and converted into a structured, executable workflow.")
