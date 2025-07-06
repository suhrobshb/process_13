from .worker_app import celery_app
from .models.task import Task
from .models.workflow import Workflow
from .models.execution import Execution
from .database import get_session
from datetime import datetime
from croniter import croniter
import os
import zipfile
import json
import tempfile
import shutil
from .task_detection import TaskDetection
from .workflow_engine import execute_workflow_by_id

# --------------------------------------------------------------------------- #
# Metrics & Timing
# --------------------------------------------------------------------------- #
import time
from .metrics_instrumentation import (
    record_step_execution,
    record_workflow_start,
    record_workflow_end,
)

@celery_app.task
def process_task(self, task_id: int):
    """
    1. Mark as 'processing'
    2. Unzip the recording
    3. Parse events.json
    4. Cluster via TaskDetection
    5. Update Task.extra_metadata with clusters
    6. Mark as 'completed'
    """
    start_ts = time.time()
    record_step_execution(  # metrics: mark step start
        workflow_name="__recording_pipeline__",
        step_name="process_task",
        step_type="system",
        duration_seconds=0,
        status="started",
    )

    with get_session() as session:
        task = session.get(Task, task_id)
        if not task:
            return

        # 1) status → processing
        task.status = "processing"
        session.add(task)
        session.commit()

        # 2) locate & unzip
        base = os.path.join("storage/users", str(task.user_id), "recordings")
        zip_path = os.path.join(base, task.filename)
        extract_dir = tempfile.mkdtemp(prefix="rec_")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)
            # 3) parse events.json
            events_file = os.path.join(extract_dir, "events.json")
            with open(events_file, 'r') as f:
                events = json.load(f)

            # 4) cluster
            detector = TaskDetection()
            clusters = detector.detect_tasks(events)

            # 5) store in extra_metadata
            task.extra_metadata = {"clusters": clusters}
            session.add(task)
            session.commit()

            # OPTIONAL: save clusters to disk
            out_path = os.path.join(base, f"{task.id}_clusters.json")
            with open(out_path, "w") as f:
                json.dump(clusters, f, indent=2)

        except Exception as e:
            task.status = "failed"
            task.extra_metadata = {"error": str(e)}
            session.add(task)
            session.commit()
            # Metrics – failure
            record_step_execution(
                workflow_name="__recording_pipeline__",
                step_name="process_task",
                step_type="system",
                duration_seconds=time.time() - start_ts,
                status="failed",
            )
            # Retry with exponential back-off, up to 3 attempts
            raise self.retry(
                exc=e,
                countdown=2 ** self.request.retries * 60,
                max_retries=3,
            )
        else:
            # 6) complete
            task.status = "completed"
            session.add(task)
            session.commit()
            # Metrics – success
            record_step_execution(
                workflow_name="__recording_pipeline__",
                step_name="process_task",
                step_type="system",
                duration_seconds=time.time() - start_ts,
                status="completed",
            )
        finally:
            shutil.rmtree(extract_dir)

@celery_app.task
def execute_workflow(self, workflow_id: int):
    """
    Execute a workflow using the new WorkflowEngine.

    This delegates the heavy-lifting to `execute_workflow_by_id`, which
    handles creation of the Execution record, step dispatch, approvals,
    result collection, and status updates.
    """
    record_workflow_start(f"wf_{workflow_id}")
    start = time.time()
    try:
        result = execute_workflow_by_id(workflow_id)
        record_workflow_end(f"wf_{workflow_id}", time.time() - start, "completed")
        return result
    except Exception as e:
        record_workflow_end(f"wf_{workflow_id}", time.time() - start, "failed")
        # Retry with exponential back-off (1,2,4 minutes)
        raise self.retry(
            exc=e,
            countdown=2 ** self.request.retries * 60,
            max_retries=3,
        )

@celery_app.task
def enqueue_scheduled_workflows():
    """
    Scan workflows with time-based triggers and enqueue executions
    when their cron expression matches the current time.
    """
    now = datetime.utcnow()
    with get_session() as session:
        workflows = session.query(Workflow).filter(Workflow.status == "active").all()
        for wf in workflows:
            for trig in wf.triggers:
                if trig["type"] == "cron":
                    try:
                        base = croniter(trig["expr"], wf.updated_at)
                        next_run = base.get_next(datetime)
                        # Allow 1-minute window to enqueue
                        if next_run <= now < next_run.replace(second=next_run.second + 60):
                            execute_workflow.delay(wf.id)
                    except Exception as e:
                        print(f"Error processing trigger for workflow {wf.id}: {str(e)}") 