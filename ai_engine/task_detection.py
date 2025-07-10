import json
from typing import List, Dict

class TaskDetection:
    """
    Cluster raw event logs into 'tasks' based on simple heuristics.
    Replace this with your real clustering logic.
    """

    def detect_tasks(self, events: List[Dict]) -> List[Dict]:
        clusters: List[Dict] = []
        current: List[Dict] = []
        last_ts = None
        for ev in events:
            if last_ts and ev["timestamp"] - last_ts > 30:
                # split if >30s of idle
                clusters.append({"events": current})
                current = []
            current.append(ev)
            last_ts = ev["timestamp"]
        if current:
            clusters.append({"events": current})
        return clusters
