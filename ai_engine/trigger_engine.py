import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from celery import Celery
from croniter import croniter
from datetime import datetime

from .database import get_session
from .models.workflow import Workflow

# Import your execute_workflow task
from .tasks import execute_workflow

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "autoops_triggers",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

class FileWatcherHandler(FileSystemEventHandler):
    def __init__(self, workflow_id: int, pattern: str):
        self.workflow_id = workflow_id
        self.pattern = pattern

    def on_created(self, event):
        if self.pattern in event.src_path:
            execute_workflow.delay(self.workflow_id)

class TriggerEngine:
    """
    Watches for file events and cron schedules to enqueue workflows.
    """

    def __init__(self):
        self.observer = Observer()
        self._cron_thread = threading.Thread(target=self._cron_loop, daemon=True)

    def start(self):
        self._setup_file_watchers()
        self.observer.start()
        self._cron_thread.start()
        print("[TriggerEngine] Started file watchers & cron scanner")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

    def _setup_file_watchers(self):
        """Schedule watchers for all file-based triggers."""
        with get_session() as session:
            workflows = session.exec(
                Workflow.select().where(Workflow.status == "active")
            ).all()
            for wf in workflows:
                for trig in wf.triggers:
                    if trig.get("type") == "file":
                        path = trig.get("path")
                        pattern = trig.get("pattern", "")
                        handler = FileWatcherHandler(wf.id, pattern)
                        self.observer.schedule(handler, path, recursive=False)

    def _cron_loop(self):
        """Every 60s, scan cron triggers and enqueue."""
        while True:
            now = datetime.utcnow()
            with get_session() as session:
                workflows = session.exec(
                    Workflow.select().where(Workflow.status == "active")
                ).all()
                for wf in workflows:
                    for trig in wf.triggers:
                        ttype = trig.get("type")
                        if ttype == "cron":
                            expr = trig.get("expr")
                            base = croniter(expr, wf.updated_at)
                            next_run = base.get_next(datetime)
                            if next_run <= now < next_run.replace(second=next_run.second + 60):
                                execute_workflow.delay(wf.id)
                        elif ttype == "composite":
                            results = []
                            for sub in trig["triggers"]:
                                if sub["type"] == "cron":
                                    base = croniter(sub["expr"], wf.updated_at)
                                    nr = base.get_next(datetime)
                                    results.append(nr <= now < nr.replace(second=nr.second + 60))
                            mode = trig.get("mode", "or")
                            if (mode=="and" and all(results)) or (mode=="or" and any(results)):
                                execute_workflow.delay(wf.id)
            time.sleep(60)
