"""
Comprehensive Monitoring and Observability System
================================================

This module provides enterprise-grade monitoring, telemetry, and observability for the RPA platform:
- Performance metrics collection
- Error tracking and alerting
- Distributed tracing
- Custom business metrics
- Health checks and SLA monitoring
- Integration with Prometheus, Grafana, and observability tools

Key Features:
- Real-time metrics and monitoring
- Proactive issue detection
- Performance optimization insights
- Compliance and audit logging
"""

import asyncio
import logging
import json
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from functools import wraps
import traceback
import os

# Telemetry and metrics libraries
try:
    from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server, CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


@dataclass
class MetricEvent:
    """Container for metric events"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str]
    metric_type: str  # counter, gauge, histogram
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class HealthCheck:
    """Health check result"""
    name: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: float
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class MetricsCollector:
    """Centralized metrics collection system"""
    
    def __init__(self):
        self.registry = CollectorRegistry() if PROMETHEUS_AVAILABLE else None
        self.metrics: Dict[str, Any] = {}
        self.events: List[MetricEvent] = []
        self.max_events = 10000  # Keep last 10k events in memory
        self._lock = threading.Lock()
        
        # Initialize core metrics
        self._init_core_metrics()
    
    def _init_core_metrics(self):
        """Initialize core platform metrics"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        # Workflow metrics
        self.workflow_executions_total = Counter(
            'workflow_executions_total',
            'Total number of workflow executions',
            ['workflow_id', 'status', 'user_id'],
            registry=self.registry
        )
        
        self.workflow_execution_duration = Histogram(
            'workflow_execution_duration_seconds',
            'Time spent executing workflows',
            ['workflow_id', 'status'],
            registry=self.registry
        )
        
        # System metrics
        self.active_workflows = Gauge(
            'active_workflows_count',
            'Number of currently active workflows',
            registry=self.registry
        )
        
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'system_memory_usage_percent',
            'System memory usage percentage',
            registry=self.registry
        )
        
        # API metrics
        self.api_requests_total = Counter(
            'api_requests_total',
            'Total number of API requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.api_request_duration = Histogram(
            'api_request_duration_seconds',
            'Time spent processing API requests',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Database metrics
        self.database_connections = Gauge(
            'database_connections_active',
            'Number of active database connections',
            registry=self.registry
        )
        
        self.database_query_duration = Histogram(
            'database_query_duration_seconds',
            'Time spent executing database queries',
            ['operation', 'table'],
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'errors_total',
            'Total number of errors',
            ['error_type', 'component', 'severity'],
            registry=self.registry
        )
        
        # Business metrics
        self.users_active = Gauge(
            'users_active_count',
            'Number of active users',
            registry=self.registry
        )
        
        self.workflows_created_total = Counter(
            'workflows_created_total',
            'Total number of workflows created',
            ['user_id', 'workflow_type'],
            registry=self.registry
        )
    
    def record_event(self, name: str, value: float, labels: Dict[str, str] = None, metric_type: str = "counter"):
        """Record a metric event"""
        with self._lock:
            event = MetricEvent(
                name=name,
                value=value,
                timestamp=datetime.utcnow(),
                labels=labels or {},
                metric_type=metric_type
            )
            
            self.events.append(event)
            
            # Trim events if too many
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        with self._lock:
            return {
                'total_events': len(self.events),
                'recent_events': [event.to_dict() for event in self.events[-100:]],
                'system_info': {
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/').percent if os.path.exists('/') else 0,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }


class PerformanceMonitor:
    """Monitor system and application performance"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.monitoring = False
        self.monitor_thread = None
        self.thresholds = {
            'cpu_warning': 80.0,
            'cpu_critical': 95.0,
            'memory_warning': 80.0,
            'memory_critical': 95.0,
            'disk_warning': 90.0,
            'disk_critical': 98.0,
            'response_time_warning': 2.0,
            'response_time_critical': 5.0
        }
        self.alerts: List[Dict[str, Any]] = []
    
    def start_monitoring(self, interval: int = 30):
        """Start continuous performance monitoring"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logging.info(f"Performance monitoring started with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logging.info("Performance monitoring stopped")
    
    def _monitoring_loop(self, interval: int):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                self._collect_system_metrics()
                self._check_thresholds()
                time.sleep(interval)
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                time.sleep(interval)
    
    def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics.record_event("system.cpu.usage", cpu_percent, metric_type="gauge")
            if PROMETHEUS_AVAILABLE:
                self.metrics.system_cpu_usage.set(cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.metrics.record_event("system.memory.usage", memory.percent, metric_type="gauge")
            self.metrics.record_event("system.memory.available", memory.available, metric_type="gauge")
            if PROMETHEUS_AVAILABLE:
                self.metrics.system_memory_usage.set(memory.percent)
            
            # Disk metrics
            if os.path.exists('/'):
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                self.metrics.record_event("system.disk.usage", disk_percent, metric_type="gauge")
            
            # Network metrics
            network = psutil.net_io_counters()
            self.metrics.record_event("system.network.bytes_sent", network.bytes_sent, metric_type="counter")
            self.metrics.record_event("system.network.bytes_recv", network.bytes_recv, metric_type="counter")
            
            # Process metrics
            process = psutil.Process()
            self.metrics.record_event("process.memory.rss", process.memory_info().rss, metric_type="gauge")
            self.metrics.record_event("process.cpu.percent", process.cpu_percent(), metric_type="gauge")
            
        except Exception as e:
            logging.error(f"Error collecting system metrics: {e}")
    
    def _check_thresholds(self):
        """Check if any metrics exceed thresholds"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            
            # Check CPU thresholds
            if cpu_percent > self.thresholds['cpu_critical']:
                self._create_alert('CPU', 'critical', f'CPU usage at {cpu_percent:.1f}%')
            elif cpu_percent > self.thresholds['cpu_warning']:
                self._create_alert('CPU', 'warning', f'CPU usage at {cpu_percent:.1f}%')
            
            # Check memory thresholds
            if memory_percent > self.thresholds['memory_critical']:
                self._create_alert('Memory', 'critical', f'Memory usage at {memory_percent:.1f}%')
            elif memory_percent > self.thresholds['memory_warning']:
                self._create_alert('Memory', 'warning', f'Memory usage at {memory_percent:.1f}%')
                
        except Exception as e:
            logging.error(f"Error checking thresholds: {e}")
    
    def _create_alert(self, component: str, severity: str, message: str):
        """Create and log an alert"""
        alert = {
            'component': component,
            'severity': severity,
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'resolved': False
        }
        
        self.alerts.append(alert)
        
        # Keep only last 1000 alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
        
        # Log alert
        log_level = logging.CRITICAL if severity == 'critical' else logging.WARNING
        logging.log(log_level, f"ALERT [{severity.upper()}] {component}: {message}")
        
        # Record metric
        if PROMETHEUS_AVAILABLE:
            self.metrics.errors_total.labels(
                error_type='threshold_exceeded',
                component=component.lower(),
                severity=severity
            ).inc()


class DistributedTracing:
    """Distributed tracing for request tracking"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.active_traces: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def trace_operation(self, operation_name: str, **context):
        """Context manager for tracing operations"""
        trace_id = self._generate_trace_id()
        start_time = time.time()
        
        try:
            self._start_trace(trace_id, operation_name, context)
            yield trace_id
        except Exception as e:
            self._record_trace_error(trace_id, str(e))
            raise
        finally:
            duration = time.time() - start_time
            self._end_trace(trace_id, duration)
    
    def _generate_trace_id(self) -> str:
        """Generate unique trace ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _start_trace(self, trace_id: str, operation_name: str, context: Dict[str, Any]):
        """Start a new trace"""
        with self._lock:
            self.active_traces[trace_id] = {
                'operation_name': operation_name,
                'start_time': time.time(),
                'context': context,
                'spans': [],
                'errors': []
            }
    
    def _end_trace(self, trace_id: str, duration: float):
        """End a trace and record metrics"""
        with self._lock:
            if trace_id in self.active_traces:
                trace = self.active_traces.pop(trace_id)
                
                # Record metrics
                self.metrics.record_event(
                    f"trace.{trace['operation_name']}.duration",
                    duration,
                    labels={'trace_id': trace_id},
                    metric_type="histogram"
                )
                
                # Log trace completion
                logging.info(f"Trace completed: {trace['operation_name']} ({duration:.3f}s)")
    
    def _record_trace_error(self, trace_id: str, error: str):
        """Record an error in a trace"""
        with self._lock:
            if trace_id in self.active_traces:
                self.active_traces[trace_id]['errors'].append({
                    'error': error,
                    'timestamp': time.time()
                })


class HealthCheckManager:
    """Manage application health checks"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.health_checks: Dict[str, Callable[[], HealthCheck]] = {}
        self.last_results: Dict[str, HealthCheck] = {}
    
    def register_health_check(self, name: str, check_func: Callable[[], HealthCheck]):
        """Register a health check function"""
        self.health_checks[name] = check_func
        logging.info(f"Registered health check: {name}")
    
    async def run_all_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks"""
        results = {}
        
        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                result.latency_ms = (time.time() - start_time) * 1000
                results[name] = result
                self.last_results[name] = result
                
                # Record metrics
                status_value = 1 if result.status == 'healthy' else 0
                self.metrics.record_event(
                    f"health_check.{name}.status",
                    status_value,
                    labels={'status': result.status},
                    metric_type="gauge"
                )
                
                self.metrics.record_event(
                    f"health_check.{name}.latency",
                    result.latency_ms,
                    metric_type="histogram"
                )
                
            except Exception as e:
                error_result = HealthCheck(
                    name=name,
                    status='unhealthy',
                    latency_ms=0,
                    details={'error': str(e), 'traceback': traceback.format_exc()}
                )
                results[name] = error_result
                self.last_results[name] = error_result
                
                logging.error(f"Health check {name} failed: {e}")
        
        return results
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        if not self.last_results:
            return {'status': 'unknown', 'message': 'No health checks run yet'}
        
        healthy_count = sum(1 for result in self.last_results.values() if result.status == 'healthy')
        total_count = len(self.last_results)
        
        if healthy_count == total_count:
            status = 'healthy'
        elif healthy_count > total_count / 2:
            status = 'degraded'
        else:
            status = 'unhealthy'
        
        return {
            'status': status,
            'healthy_checks': healthy_count,
            'total_checks': total_count,
            'checks': {name: result.status for name, result in self.last_results.items()},
            'timestamp': datetime.utcnow().isoformat()
        }


class TelemetrySystem:
    """Main telemetry and monitoring system"""
    
    def __init__(self, enable_prometheus: bool = True):
        self.metrics_collector = MetricsCollector()
        self.performance_monitor = PerformanceMonitor(self.metrics_collector)
        self.tracing = DistributedTracing(self.metrics_collector)
        self.health_checks = HealthCheckManager(self.metrics_collector)
        
        # Setup structured logging
        self._setup_logging()
        
        # Start Prometheus metrics server if enabled
        if enable_prometheus and PROMETHEUS_AVAILABLE:
            self._start_prometheus_server()
        
        # Register default health checks
        self._register_default_health_checks()
    
    def _setup_logging(self):
        """Setup structured logging"""
        if STRUCTLOG_AVAILABLE:
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
    
    def _start_prometheus_server(self, port: int = 8080):
        """Start Prometheus metrics server"""
        try:
            start_http_server(port, registry=self.metrics_collector.registry)
            logging.info(f"Prometheus metrics server started on port {port}")
        except Exception as e:
            logging.warning(f"Failed to start Prometheus server: {e}")
    
    def _register_default_health_checks(self):
        """Register default system health checks"""
        
        def database_health_check() -> HealthCheck:
            """Check database connectivity"""
            try:
                # Import here to avoid circular dependencies
                from ..database import get_session
                with get_session() as session:
                    session.execute("SELECT 1")
                return HealthCheck(name="database", status="healthy", latency_ms=0)
            except Exception as e:
                return HealthCheck(
                    name="database", 
                    status="unhealthy", 
                    latency_ms=0,
                    details={"error": str(e)}
                )
        
        def system_resources_health_check() -> HealthCheck:
            """Check system resource usage"""
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            
            if cpu_percent > 95 or memory_percent > 95:
                status = "unhealthy"
            elif cpu_percent > 80 or memory_percent > 80:
                status = "degraded"
            else:
                status = "healthy"
            
            return HealthCheck(
                name="system_resources",
                status=status,
                latency_ms=0,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent
                }
            )
        
        self.health_checks.register_health_check("database", database_health_check)
        self.health_checks.register_health_check("system_resources", system_resources_health_check)
    
    def start_monitoring(self):
        """Start all monitoring systems"""
        self.performance_monitor.start_monitoring()
        logging.info("Telemetry system started")
    
    def stop_monitoring(self):
        """Stop all monitoring systems"""
        self.performance_monitor.stop_monitoring()
        logging.info("Telemetry system stopped")
    
    def record_workflow_execution(self, workflow_id: str, user_id: str, duration: float, status: str):
        """Record workflow execution metrics"""
        if PROMETHEUS_AVAILABLE:
            self.metrics_collector.workflow_executions_total.labels(
                workflow_id=workflow_id,
                status=status,
                user_id=user_id
            ).inc()
            
            self.metrics_collector.workflow_execution_duration.labels(
                workflow_id=workflow_id,
                status=status
            ).observe(duration)
        
        self.metrics_collector.record_event(
            "workflow.execution.completed",
            duration,
            labels={
                'workflow_id': workflow_id,
                'user_id': user_id,
                'status': status
            },
            metric_type="histogram"
        )
    
    def record_api_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record API request metrics"""
        if PROMETHEUS_AVAILABLE:
            self.metrics_collector.api_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code)
            ).inc()
            
            self.metrics_collector.api_request_duration.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
        
        self.metrics_collector.record_event(
            "api.request.completed",
            duration,
            labels={
                'method': method,
                'endpoint': endpoint,
                'status_code': str(status_code)
            },
            metric_type="histogram"
        )
    
    def record_error(self, error_type: str, component: str, severity: str = "error", details: Dict[str, Any] = None):
        """Record error occurrence"""
        if PROMETHEUS_AVAILABLE:
            self.metrics_collector.errors_total.labels(
                error_type=error_type,
                component=component,
                severity=severity
            ).inc()
        
        self.metrics_collector.record_event(
            "error.occurred",
            1,
            labels={
                'error_type': error_type,
                'component': component,
                'severity': severity
            },
            metric_type="counter"
        )
        
        # Log error with structured logging
        logging.error(f"Error in {component}: {error_type}", extra={
            'component': component,
            'error_type': error_type,
            'severity': severity,
            'details': details or {}
        })
    
    def get_metrics_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive metrics dashboard data"""
        return {
            'metrics_summary': self.metrics_collector.get_metrics_summary(),
            'health_status': self.health_checks.get_overall_health(),
            'alerts': self.performance_monitor.alerts[-50:],  # Last 50 alerts
            'system_info': {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent if os.path.exists('/') else 0,
                'uptime': time.time() - psutil.boot_time(),
                'active_traces': len(self.tracing.active_traces)
            },
            'timestamp': datetime.utcnow().isoformat()
        }


# Global telemetry instance
telemetry = TelemetrySystem()


# Decorators for easy instrumentation
def monitor_performance(operation_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            with telemetry.tracing.trace_operation(op_name):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    telemetry.metrics_collector.record_event(
                        f"operation.{op_name}.duration",
                        duration,
                        metric_type="histogram"
                    )
                    return result
                except Exception as e:
                    telemetry.record_error(
                        error_type=type(e).__name__,
                        component=func.__module__,
                        details={'function': func.__name__, 'args': str(args)}
                    )
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            with telemetry.tracing.trace_operation(op_name):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    telemetry.metrics_collector.record_event(
                        f"operation.{op_name}.duration",
                        duration,
                        metric_type="histogram"
                    )
                    return result
                except Exception as e:
                    telemetry.record_error(
                        error_type=type(e).__name__,
                        component=func.__module__,
                        details={'function': func.__name__, 'args': str(args)}
                    )
                    raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def monitor_api_endpoint(func):
    """Decorator to monitor API endpoint performance"""
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        start_time = time.time()
        method = request.method
        endpoint = str(request.url.path)
        
        try:
            response = await func(request, *args, **kwargs)
            status_code = response.status_code
            duration = time.time() - start_time
            
            telemetry.record_api_request(method, endpoint, status_code, duration)
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            telemetry.record_api_request(method, endpoint, 500, duration)
            telemetry.record_error(
                error_type=type(e).__name__,
                component="api",
                details={'endpoint': endpoint, 'method': method}
            )
            raise
    
    return wrapper