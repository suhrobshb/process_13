
"""
Smart Automation Discovery & Recommendation Engine
=================================================

This module forms the proactive core of the AI Engine's intelligence layer.
It analyzes historical user activity logs to automatically identify and surface
high-value opportunities for automation.

Key Responsibilities:
-   **Activity Log Analysis**: Ingests and processes detailed event logs,
    including user actions, application context, and timestamps.
-   **Repetitive Pattern Detection**: Uses sequence mining algorithms to find
    recurring patterns of actions that represent automatable tasks.
-   **Time & Frequency Metrics**: Calculates how often each pattern occurs and
    estimates the total time spent by the user performing it.
-   **Priority Scoring**: Ranks automation candidates based on a weighted score
    of frequency and time consumption, ensuring the most impactful suggestions
    are surfaced first.
-   **Suggestion Generation**: Formats the findings into a clear, actionable list
    of "Automation Suggestions" that can be displayed on the user's dashboard.
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# --- Mock Data Store ---
# In a real application, this would connect to a database (e.g., ClickHouse,
# PostgreSQL) or a log aggregation service to fetch real user event logs.

def _get_event_logs(user_id: int, window_days: int = 7) -> List[Dict[str, Any]]:
    """
    Mock function to simulate fetching detailed event logs for a user.
    Each event includes a unique signature and an estimated duration.
    """
    logger.info(f"Fetching mock event logs for user_id={user_id} over the last {window_days} days.")
    # This sequence represents a common, repetitive task
    repetitive_sequence = [
        {"timestamp": datetime.now() - timedelta(hours=25), "signature": "app_open:outlook", "duration_ms": 500},
        {"timestamp": datetime.now() - timedelta(hours=25), "signature": "click:search_bar", "duration_ms": 1200},
        {"timestamp": datetime.now() - timedelta(hours=25), "signature": "type:New Invoice", "duration_ms": 2500},
        {"timestamp": datetime.now() - timedelta(hours=25), "signature": "click:email_subject", "duration_ms": 800},
        {"timestamp": datetime.now() - timedelta(hours=25), "signature": "click:download_attachment", "duration_ms": 1500},
    ]
    
    # A less frequent, but still repetitive task
    other_sequence = [
        {"timestamp": datetime.now() - timedelta(hours=40), "signature": "app_open:crm", "duration_ms": 2000},
        {"timestamp": datetime.now() - timedelta(hours=40), "signature": "click:generate_report", "duration_ms": 3000},
    ]

    # Simulate a log with these patterns repeated, mixed with random noise
    logs = []
    for i in range(10): # Repeat the main sequence 10 times
        logs.extend(repetitive_sequence)
        logs.append({"timestamp": datetime.now(), "signature": f"random_click_{i}", "duration_ms": 300})

    for i in range(3): # Repeat the other sequence 3 times
        logs.extend(other_sequence)
        logs.append({"timestamp": datetime.now(), "signature": f"random_type_{i}", "duration_ms": 500})
        
    return logs

# --- Core Analytics Logic ---

def _find_repetitive_sequences(
    events: List[Dict[str, Any]],
    min_len: int = 3,
    max_len: int = 8
) -> Counter:
    """
    Finds recurring sequences of action "signatures" in the event log.
    Uses a sliding window (n-gram) approach to identify patterns.
    
    Args:
        events: A list of event dictionaries.
        min_len: The minimum length of a sequence to consider a pattern.
        max_len: The maximum length of a sequence.

    Returns:
        A Counter object where keys are tuples of action signatures (the pattern)
        and values are their frequencies.
    """
    signatures = [event['signature'] for event in events]
    sequences = Counter()

    for n in range(min_len, max_len + 1):
        for i in range(len(signatures) - n + 1):
            sequence = tuple(signatures[i:i+n])
            sequences[sequence] += 1
            
    # Filter out sub-sequences that are part of more frequent, longer sequences
    # For example, if ('A', 'B', 'C') appears 10 times, and ('A', 'B') appears 10 times,
    # we prefer the longer, more specific sequence.
    final_sequences = sequences.copy()
    for seq, count in sequences.items():
        for other_seq, other_count in sequences.items():
            if len(seq) < len(other_seq) and count == other_count:
                # Check if seq is a sub-sequence of other_seq
                s_str = ",".join(seq)
                o_str = ",".join(other_seq)
                if s_str in o_str and seq in final_sequences:
                    del final_sequences[seq]
                    
    return final_sequences


def _calculate_pattern_metrics(
    pattern: Tuple[str, ...],
    events: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Calculates the total time spent on a specific recurring pattern.
    
    Args:
        pattern: The sequence of action signatures to measure.
        events: The full list of event logs.

    Returns:
        A dictionary containing the total estimated duration in milliseconds.
    """
    total_duration_ms = 0
    signatures = [event['signature'] for event in events]
    pattern_len = len(pattern)
    
    for i in range(len(signatures) - pattern_len + 1):
        if tuple(signatures[i:i+pattern_len]) == pattern:
            # Sum the durations of the events that make up this occurrence of the pattern
            occurrence_duration = sum(event['duration_ms'] for event in events[i:i+pattern_len])
            total_duration_ms += occurrence_duration
            
    return {"total_duration_ms": total_duration_ms}


def _calculate_priority_score(frequency: int, total_time_ms: float) -> float:
    """
    Calculates a priority score to rank automation suggestions.
    The score is higher for tasks that are both frequent and time-consuming.
    
    Args:
        frequency: How many times the pattern occurred.
        total_time_ms: The total time spent on all occurrences.

    Returns:
        A float representing the priority score.
    """
    # Weight time spent more heavily than raw frequency
    time_weight = 1.0
    frequency_weight = 0.5
    
    # Normalize time to seconds to keep score in a reasonable range
    score = (total_time_ms / 1000) * time_weight + frequency * frequency_weight
    return round(score, 2)


# --- Public Orchestration Function ---

def get_automation_suggestions(user_id: int, top_n: int = 5) -> List[Dict[str, Any]]:
    """
    Analyzes user activity and returns a ranked list of automation suggestions.

    This is the main public function for this module. It orchestrates the
    process of fetching logs, finding patterns, and scoring them.

    Args:
        user_id: The ID of the user to analyze.
        top_n: The number of top suggestions to return.

    Returns:
        A list of suggestion dictionaries, sorted by priority. Each dictionary
        contains the suggested workflow, frequency, estimated time saved, and score.
    """
    logger.info(f"Generating automation suggestions for user_id={user_id}")
    
    # 1. Fetch logs
    logs = _get_event_logs(user_id)
    if not logs:
        return []

    # 2. Find all repetitive sequences
    frequent_patterns = _find_repetitive_sequences(logs)
    
    suggestions = []
    for pattern, frequency in frequent_patterns.items():
        # Ignore patterns that only occurred once
        if frequency <= 1:
            continue
            
        # 3. Calculate metrics for each pattern
        metrics = _calculate_pattern_metrics(pattern, logs)
        total_duration_ms = metrics["total_duration_ms"]
        
        # 4. Calculate priority score
        score = _calculate_priority_score(frequency, total_duration_ms)
        
        # 5. Format the suggestion
        suggestion_title = " -> ".join(pattern).replace("_", " ").title()
        time_saved_str = f"{total_duration_ms / 1000:.1f} seconds"
        
        suggestions.append({
            "title": f"Automate: {suggestion_title}",
            "workflow_pattern": list(pattern),
            "frequency": frequency,
            "estimated_time_saved_ms": total_duration_ms,
            "estimated_time_saved_str": time_saved_str,
            "priority_score": score,
        })
        
    # 6. Sort by priority score and return the top N
    sorted_suggestions = sorted(suggestions, key=lambda x: x['priority_score'], reverse=True)
    
    logger.info(f"Generated {len(sorted_suggestions)} potential automation suggestions.")
    return sorted_suggestions[:top_n]


# --- Example Usage ---
if __name__ == "__main__":
    print("--- Running Smart Automation Discovery Demo ---")
    user_id_to_analyze = 123
    
    top_suggestions = get_automation_suggestions(user_id_to_analyze)
    
    if not top_suggestions:
        print("\nNo significant repetitive tasks found to suggest for automation.")
    else:
        print(f"\nTop {len(top_suggestions)} Automation Suggestions for User {user_id_to_analyze}:")
        for i, suggestion in enumerate(top_suggestions):
            print(f"\n{i+1}. Suggestion: {suggestion['title']}")
            print(f"   - Priority Score: {suggestion['priority_score']}")
            print(f"   - Performed: {suggestion['frequency']} times")
            print(f"   - Est. Total Time Spent: {suggestion['estimated_time_saved_str']}")
            print(f"   - Action Sequence: {suggestion['workflow_pattern']}")

```