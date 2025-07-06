"""
Prometheus Metrics Instrumentation for AI Engine
===============================================

This module defines a comprehensive set of Prometheus metrics to provide deep
observability into the AI Engine's performance and behavior. These metrics are
designed to be consumed by a Prometheus server and visualized in dashboards
(e.g., with Grafana).

The metrics cover:
-   High-level workflow execution statistics (counts, durations, statuses).
-   Granular, step-level performance to identify bottlenecks.
-   LLM interaction monitoring for performance and cost tracking.
-   System resource and load monitoring (e.g., active workers, queue sizes).

Helper functions are provided to make it easy to instrument the core application
logic (e.g., the WorkflowEngine, runners) by simply calling a function.
"""

from prometheus_client import Counter, Histogram, Gauge

# --- 1. Workflow Execution Metrics ---
# These metrics provide a high-level overview of the platform's automation activity.

WORKFLOW_EXECUTIONS_TOTAL = Counter(
    'workflow_executions_total',
    'Total number of workflow executions initiated, completed, or failed.',
    ['workflow_name', 'status']  # Labels: status='started'|'completed'|'failed'
)

WORKFLOW_DURATION_SECONDS = Histogram(
    'workflow_duration_seconds',
    'Histogram of the total time taken for a workflow to complete.',
    ['workflow_name']
)

# --- 2. Step-Level Metrics ---
# These metrics provide granular insight into the performance of individual steps
# within a workflow, helping to pinpoint bottlenecks or frequently failing actions.

WORKFLOW_STEP_DURATION_SECONDS = Histogram(
    'workflow_step_duration_seconds',
    'Histogram of execution durations for individual workflow steps.',
    ['workflow_name', 'step_name', 'step_type']
)

# --- 3. LLM Interaction Metrics ---
# Critical for monitoring the performance, cost, and reliability of integrations
# with third-party Large Language Models.

LLM_REQUESTS_TOTAL = Counter(
    'llm_requests_total',
    'Total number of API requests made to LLM providers.',
    ['provider', 'model', 'status']  # e.g., provider='openai', status='success'
)

LLM_RESPONSE_TIME_SECONDS = Histogram(
    'llm_response_time_seconds',
    'Histogram of response times from LLM providers.',
    ['provider', 'model']
)

LLM_TOKEN_USAGE_TOTAL = Counter(
    'llm_token_usage_total',
    'Total number of tokens processed by LLMs, categorized by type.',
    ['provider', 'model', 'token_type']  # e.g., token_type='prompt'|'completion'
)

# --- 4. Resource and System Load Metrics ---
# Gauges to monitor the current state of system resources and task queues.

ACTIVE_CELERY_WORKERS = Gauge(
    'active_celery_workers',
    'Number of currently active Celery workers processing tasks.'
)

TASKS_IN_QUEUE = Gauge(
    'tasks_in_queue_total',
    'Number of tasks currently waiting in the message broker queue (e.g., Redis).'
)

# --- Helper Functions for Easy Instrumentation ---
# These functions abstract the Prometheus client logic, making it easy to
# record metrics from anywhere in the application.

def record_workflow_start(workflow_name: str):
    """To be called when a workflow execution begins."""
    WORKFLOW_EXECUTIONS_TOTAL.labels(workflow_name=workflow_name, status='started').inc()

def record_workflow_end(workflow_name: str, duration_seconds: float, status: str):
    """To be called when a workflow execution finishes (completes or fails)."""
    WORKFLOW_EXECUTIONS_TOTAL.labels(workflow_name=workflow_name, status=status).inc()
    if status == 'completed':
        WORKFLOW_DURATION_SECONDS.labels(workflow_name=workflow_name).observe(duration_seconds)

def record_step_execution(workflow_name: str, step_name: str, step_type: str, duration_seconds: float, status: str):
    """To be called after each individual workflow step is executed."""
    if status == 'completed':
        WORKFLOW_STEP_DURATION_SECONDS.labels(
            workflow_name=workflow_name,
            step_name=step_name,
            step_type=step_type
        ).observe(duration_seconds)
    # Note: A counter for step executions could be added here if needed,
    # but it can often be derived from the histogram's '_count' metric.

def record_llm_request(provider: str, model: str, duration_seconds: float, status: str):
    """To be called after an LLM API request."""
    LLM_REQUESTS_TOTAL.labels(provider=provider, model=model, status=status).inc()
    if status == 'success':
        LLM_RESPONSE_TIME_SECONDS.labels(provider=provider, model=model).observe(duration_seconds)

def record_llm_token_usage(provider: str, model: str, prompt_tokens: int, completion_tokens: int):
    """To be called with token usage data from an LLM response."""
    LLM_TOKEN_USAGE_TOTAL.labels(provider=provider, model=model, token_type='prompt').inc(prompt_tokens)
    LLM_TOKEN_USAGE_TOTAL.labels(provider=provider, model=model, token_type='completion').inc(completion_tokens)

def update_active_workers(count: int):
    """To be called periodically or via signals to update the active worker count."""
    ACTIVE_WORKERS.set(count)

def update_tasks_in_queue(count: int):
    """To be called periodically to update the number of tasks in the queue."""
    TASKS_IN_QUEUE.set(count)

# --- Integration Example ---
#
# To integrate these metrics into the main FastAPI application, you would use
# a library like `prometheus-fastapi-instrumentator`.
#
# In `ai_engine/main.py`:
#
# from fastapi import FastAPI
# from prometheus_fastapi_instrumentator import Instrumentator
#
# app = FastAPI()
#
# @app.on_event("startup")
# async def startup():
#     # This exposes default metrics like http_requests_total and a /metrics endpoint
#     Instrumentator().instrument(app).expose(app)
#
# Now, from within your application logic (e.g., in `workflow_engine.py`),
# you can import and use the helper functions from this file:
#
# from .metrics_instrumentation import record_workflow_start, record_workflow_end
#
# class WorkflowEngine:
#     def run(self):
#         start_time = time.time()
#         record_workflow_start(self.workflow.name)
#         try:
#             # ... execute workflow ...
#             duration = time.time() - start_time
#             record_workflow_end(self.workflow.name, duration, 'completed')
#         except Exception:
#             duration = time.time() - start_time
#             record_workflow_end(self.workflow.name, duration, 'failed')
#
