"""
Monitoring and Telemetry Testing Suite
======================================

This test suite validates the monitoring and observability systems:
- Metrics collection and accuracy
- Performance monitoring and alerting
- Health check functionality
- Distributed tracing
- Error tracking and reporting
- System resource monitoring
"""

import pytest
import asyncio
import time
import threading
from unittest.mock import patch, MagicMock
import psutil
from datetime import datetime, timedelta

from ai_engine.monitoring.telemetry import (
    TelemetrySystem,
    MetricsCollector,
    PerformanceMonitor,
    DistributedTracing,
    HealthCheckManager,
    HealthCheck,
    MetricEvent,
    monitor_performance,
    monitor_api_endpoint
)


class TestMetricsCollector:
    """Test metrics collection functionality"""
    
    def test_record_event(self):
        """Test recording metric events"""
        collector = MetricsCollector()
        
        # Record test event
        collector.record_event(
            name="test.metric",
            value=42.0,
            labels={"component": "test"},
            metric_type="counter"
        )
        
        assert len(collector.events) == 1
        event = collector.events[0]
        assert event.name == "test.metric"
        assert event.value == 42.0
        assert event.labels["component"] == "test"
        assert event.metric_type == "counter"
        assert isinstance(event.timestamp, datetime)
    
    def test_event_trimming(self):
        """Test that events are trimmed when max limit is reached"""
        collector = MetricsCollector()
        collector.max_events = 10
        
        # Add more than max events
        for i in range(15):
            collector.record_event(f"test.metric.{i}", float(i))
        
        # Should only keep last 10 events
        assert len(collector.events) == 10
        assert collector.events[0].name == "test.metric.5"
        assert collector.events[-1].name == "test.metric.14"
    
    def test_metrics_summary(self):
        """Test getting metrics summary"""
        collector = MetricsCollector()
        
        # Add some events
        for i in range(5):
            collector.record_event(f"test.metric.{i}", float(i))
        
        summary = collector.get_metrics_summary()
        
        assert summary["total_events"] == 5
        assert len(summary["recent_events"]) == 5
        assert "system_info" in summary
        assert "cpu_percent" in summary["system_info"]
        assert "memory_percent" in summary["system_info"]
    
    def test_thread_safety(self):
        """Test thread safety of metrics collection"""
        collector = MetricsCollector()
        
        def record_metrics(thread_id):
            for i in range(100):
                collector.record_event(f"thread.{thread_id}.metric.{i}", float(i))
        
        # Start multiple threads
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=record_metrics, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have 500 events total (5 threads * 100 events each)
        assert len(collector.events) == 500


class TestPerformanceMonitor:
    """Test performance monitoring functionality"""
    
    def test_monitoring_lifecycle(self):
        """Test starting and stopping monitoring"""
        collector = MetricsCollector()
        monitor = PerformanceMonitor(collector)
        
        assert not monitor.monitoring
        
        # Start monitoring
        monitor.start_monitoring(interval=1)
        assert monitor.monitoring
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()
        
        # Let it run briefly
        time.sleep(2)
        
        # Stop monitoring
        monitor.stop_monitoring()
        assert not monitor.monitoring
    
    def test_threshold_checking(self):
        """Test threshold checking and alerting"""
        collector = MetricsCollector()
        monitor = PerformanceMonitor(collector)
        
        # Set low thresholds for testing
        monitor.thresholds['cpu_warning'] = 1.0
        monitor.thresholds['cpu_critical'] = 2.0
        
        # Mock high CPU usage
        with patch('psutil.cpu_percent', return_value=50.0):
            monitor._check_thresholds()
        
        # Should have created alerts
        assert len(monitor.alerts) > 0
        alert = monitor.alerts[-1]
        assert alert['component'] == 'CPU'
        assert alert['severity'] == 'critical'
    
    def test_system_metrics_collection(self):
        """Test collection of system metrics"""
        collector = MetricsCollector()
        monitor = PerformanceMonitor(collector)
        
        # Collect metrics
        monitor._collect_system_metrics()
        
        # Check that metrics were recorded
        events = collector.events
        metric_names = [event.name for event in events]
        
        expected_metrics = [
            "system.cpu.usage",
            "system.memory.usage",
            "system.memory.available",
            "system.network.bytes_sent",
            "system.network.bytes_recv",
            "process.memory.rss",
            "process.cpu.percent"
        ]
        
        for metric in expected_metrics:
            assert metric in metric_names
    
    def test_alert_creation(self):
        """Test alert creation and management"""
        collector = MetricsCollector()
        monitor = PerformanceMonitor(collector)
        
        # Create test alert
        monitor._create_alert('TestComponent', 'warning', 'Test alert message')
        
        assert len(monitor.alerts) == 1
        alert = monitor.alerts[0]
        assert alert['component'] == 'TestComponent'
        assert alert['severity'] == 'warning'
        assert alert['message'] == 'Test alert message'
        assert alert['resolved'] is False
    
    def test_alert_trimming(self):
        """Test that alerts are trimmed when limit is exceeded"""
        collector = MetricsCollector()
        monitor = PerformanceMonitor(collector)
        
        # Create many alerts
        for i in range(1100):  # More than the 1000 limit
            monitor._create_alert('Test', 'warning', f'Alert {i}')
        
        # Should only keep last 1000 alerts
        assert len(monitor.alerts) == 1000
        assert monitor.alerts[0]['message'] == 'Alert 100'
        assert monitor.alerts[-1]['message'] == 'Alert 1099'


class TestDistributedTracing:
    """Test distributed tracing functionality"""
    
    def test_trace_operation_context_manager(self):
        """Test tracing operations with context manager"""
        collector = MetricsCollector()
        tracing = DistributedTracing(collector)
        
        with tracing.trace_operation("test_operation", user_id="123") as trace_id:
            assert trace_id is not None
            assert trace_id in tracing.active_traces
            
            trace = tracing.active_traces[trace_id]
            assert trace['operation_name'] == "test_operation"
            assert trace['context']['user_id'] == "123"
            
            time.sleep(0.1)  # Simulate work
        
        # Trace should be completed and removed from active traces
        assert trace_id not in tracing.active_traces
        
        # Should have recorded duration metric
        events = collector.events
        duration_events = [e for e in events if "duration" in e.name]
        assert len(duration_events) > 0
    
    def test_trace_error_handling(self):
        """Test error handling in traces"""
        collector = MetricsCollector()
        tracing = DistributedTracing(collector)
        
        try:
            with tracing.trace_operation("error_operation") as trace_id:
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected
        
        # Trace should still be completed
        assert trace_id not in tracing.active_traces
    
    def test_trace_id_generation(self):
        """Test trace ID generation"""
        collector = MetricsCollector()
        tracing = DistributedTracing(collector)
        
        trace_ids = set()
        for _ in range(100):
            trace_id = tracing._generate_trace_id()
            trace_ids.add(trace_id)
        
        # All trace IDs should be unique
        assert len(trace_ids) == 100


class TestHealthCheckManager:
    """Test health check management"""
    
    def test_register_health_check(self):
        """Test registering health checks"""
        collector = MetricsCollector()
        health_manager = HealthCheckManager(collector)
        
        def test_check():
            return HealthCheck(name="test", status="healthy", latency_ms=10.0)
        
        health_manager.register_health_check("test_check", test_check)
        
        assert "test_check" in health_manager.health_checks
    
    @pytest.mark.asyncio
    async def test_run_health_checks(self):
        """Test running health checks"""
        collector = MetricsCollector()
        health_manager = HealthCheckManager(collector)
        
        def healthy_check():
            return HealthCheck(name="healthy", status="healthy", latency_ms=5.0)
        
        def unhealthy_check():
            return HealthCheck(name="unhealthy", status="unhealthy", latency_ms=100.0)
        
        def failing_check():
            raise Exception("Check failed")
        
        health_manager.register_health_check("healthy", healthy_check)
        health_manager.register_health_check("unhealthy", unhealthy_check)
        health_manager.register_health_check("failing", failing_check)
        
        results = await health_manager.run_all_health_checks()
        
        assert len(results) == 3
        assert results["healthy"].status == "healthy"
        assert results["unhealthy"].status == "unhealthy"
        assert results["failing"].status == "unhealthy"  # Exception converted to unhealthy
        
        # Check that metrics were recorded
        events = collector.events
        health_events = [e for e in events if "health_check" in e.name]
        assert len(health_events) > 0
    
    @pytest.mark.asyncio
    async def test_async_health_check(self):
        """Test async health check functions"""
        collector = MetricsCollector()
        health_manager = HealthCheckManager(collector)
        
        async def async_check():
            await asyncio.sleep(0.1)  # Simulate async work
            return HealthCheck(name="async", status="healthy", latency_ms=100.0)
        
        health_manager.register_health_check("async_check", async_check)
        
        results = await health_manager.run_all_health_checks()
        
        assert "async_check" in results
        assert results["async_check"].status == "healthy"
        assert results["async_check"].latency_ms > 100  # Should have actual latency
    
    def test_overall_health_status(self):
        """Test overall health status calculation"""
        collector = MetricsCollector()
        health_manager = HealthCheckManager(collector)
        
        # No health checks run yet
        status = health_manager.get_overall_health()
        assert status['status'] == 'unknown'
        
        # Add some results
        health_manager.last_results = {
            'check1': HealthCheck(name="check1", status="healthy", latency_ms=10),
            'check2': HealthCheck(name="check2", status="healthy", latency_ms=15),
            'check3': HealthCheck(name="check3", status="unhealthy", latency_ms=100)
        }
        
        status = health_manager.get_overall_health()
        assert status['status'] == 'degraded'  # 2/3 healthy = degraded
        assert status['healthy_checks'] == 2
        assert status['total_checks'] == 3


class TestTelemetrySystem:
    """Test complete telemetry system"""
    
    def test_telemetry_initialization(self):
        """Test telemetry system initialization"""
        telemetry = TelemetrySystem(enable_prometheus=False)
        
        assert telemetry.metrics_collector is not None
        assert telemetry.performance_monitor is not None
        assert telemetry.tracing is not None
        assert telemetry.health_checks is not None
    
    def test_workflow_execution_recording(self):
        """Test recording workflow execution metrics"""
        telemetry = TelemetrySystem(enable_prometheus=False)
        
        telemetry.record_workflow_execution(
            workflow_id="wf123",
            user_id="user456",
            duration=2.5,
            status="completed"
        )
        
        events = telemetry.metrics_collector.events
        workflow_events = [e for e in events if "workflow.execution" in e.name]
        assert len(workflow_events) > 0
        
        event = workflow_events[0]
        assert event.value == 2.5
        assert event.labels['workflow_id'] == "wf123"
        assert event.labels['user_id'] == "user456"
        assert event.labels['status'] == "completed"
    
    def test_api_request_recording(self):
        """Test recording API request metrics"""
        telemetry = TelemetrySystem(enable_prometheus=False)
        
        telemetry.record_api_request(
            method="GET",
            endpoint="/workflows",
            status_code=200,
            duration=0.5
        )
        
        events = telemetry.metrics_collector.events
        api_events = [e for e in events if "api.request" in e.name]
        assert len(api_events) > 0
        
        event = api_events[0]
        assert event.value == 0.5
        assert event.labels['method'] == "GET"
        assert event.labels['endpoint'] == "/workflows"
        assert event.labels['status_code'] == "200"
    
    def test_error_recording(self):
        """Test recording error metrics"""
        telemetry = TelemetrySystem(enable_prometheus=False)
        
        telemetry.record_error(
            error_type="ValueError",
            component="workflow_engine",
            severity="error",
            details={"function": "execute_workflow"}
        )
        
        events = telemetry.metrics_collector.events
        error_events = [e for e in events if "error.occurred" in e.name]
        assert len(error_events) > 0
        
        event = error_events[0]
        assert event.value == 1
        assert event.labels['error_type'] == "ValueError"
        assert event.labels['component'] == "workflow_engine"
        assert event.labels['severity'] == "error"
    
    def test_metrics_dashboard(self):
        """Test metrics dashboard data"""
        telemetry = TelemetrySystem(enable_prometheus=False)
        
        # Record some test data
        telemetry.record_workflow_execution("wf1", "user1", 1.0, "completed")
        telemetry.record_api_request("POST", "/workflows", 201, 0.3)
        
        dashboard = telemetry.get_metrics_dashboard()
        
        assert "metrics_summary" in dashboard
        assert "health_status" in dashboard
        assert "alerts" in dashboard
        assert "system_info" in dashboard
        assert "timestamp" in dashboard
        
        # Check system info
        system_info = dashboard["system_info"]
        assert "cpu_percent" in system_info
        assert "memory_percent" in system_info
        assert "uptime" in system_info


class TestMonitoringDecorators:
    """Test monitoring decorators"""
    
    def test_monitor_performance_decorator_sync(self):
        """Test performance monitoring decorator for sync functions"""
        collector = MetricsCollector()
        
        # Mock the global telemetry
        with patch('ai_engine.monitoring.telemetry.telemetry') as mock_telemetry:
            mock_telemetry.tracing.trace_operation.return_value.__enter__ = MagicMock()
            mock_telemetry.tracing.trace_operation.return_value.__exit__ = MagicMock()
            mock_telemetry.metrics_collector = collector
            
            @monitor_performance("test_operation")
            def test_function(x, y):
                time.sleep(0.1)
                return x + y
            
            result = test_function(1, 2)
            assert result == 3
            
            # Check that metrics were recorded
            events = collector.events
            duration_events = [e for e in events if "duration" in e.name]
            assert len(duration_events) > 0
    
    @pytest.mark.asyncio
    async def test_monitor_performance_decorator_async(self):
        """Test performance monitoring decorator for async functions"""
        collector = MetricsCollector()
        
        # Mock the global telemetry
        with patch('ai_engine.monitoring.telemetry.telemetry') as mock_telemetry:
            mock_telemetry.tracing.trace_operation.return_value.__enter__ = MagicMock()
            mock_telemetry.tracing.trace_operation.return_value.__exit__ = MagicMock()
            mock_telemetry.metrics_collector = collector
            
            @monitor_performance("async_test_operation")
            async def async_test_function(x, y):
                await asyncio.sleep(0.1)
                return x * y
            
            result = await async_test_function(3, 4)
            assert result == 12
            
            # Check that metrics were recorded
            events = collector.events
            duration_events = [e for e in events if "duration" in e.name]
            assert len(duration_events) > 0
    
    def test_monitor_performance_decorator_error_handling(self):
        """Test error handling in performance monitoring decorator"""
        collector = MetricsCollector()
        
        with patch('ai_engine.monitoring.telemetry.telemetry') as mock_telemetry:
            mock_telemetry.tracing.trace_operation.return_value.__enter__ = MagicMock()
            mock_telemetry.tracing.trace_operation.return_value.__exit__ = MagicMock()
            mock_telemetry.metrics_collector = collector
            mock_telemetry.record_error = MagicMock()
            
            @monitor_performance("error_operation")
            def error_function():
                raise ValueError("Test error")
            
            with pytest.raises(ValueError):
                error_function()
            
            # Check that error was recorded
            mock_telemetry.record_error.assert_called_once()


class TestHealthCheckIntegration:
    """Test health check integration"""
    
    @pytest.mark.asyncio
    async def test_default_health_checks(self):
        """Test default health checks are registered and work"""
        telemetry = TelemetrySystem(enable_prometheus=False)
        
        # Run all health checks
        results = await telemetry.health_checks.run_all_health_checks()
        
        # Should have default health checks
        assert "database" in results or "system_resources" in results
        
        # Check system resources health check
        if "system_resources" in results:
            result = results["system_resources"]
            assert result.status in ["healthy", "degraded", "unhealthy"]
            assert "cpu_percent" in result.details
            assert "memory_percent" in result.details
    
    @pytest.mark.asyncio
    async def test_custom_health_check_registration(self):
        """Test registering and running custom health checks"""
        telemetry = TelemetrySystem(enable_prometheus=False)
        
        def custom_check():
            return HealthCheck(
                name="custom",
                status="healthy",
                latency_ms=25.0,
                details={"custom_metric": 42}
            )
        
        telemetry.health_checks.register_health_check("custom", custom_check)
        
        results = await telemetry.health_checks.run_all_health_checks()
        
        assert "custom" in results
        assert results["custom"].status == "healthy"
        assert results["custom"].details["custom_metric"] == 42


class TestMetricsAccuracy:
    """Test metrics accuracy and consistency"""
    
    def test_timing_accuracy(self):
        """Test that timing metrics are accurate"""
        collector = MetricsCollector()
        
        start_time = time.time()
        time.sleep(0.1)  # Sleep for 100ms
        end_time = time.time()
        
        actual_duration = end_time - start_time
        collector.record_event("timing.test", actual_duration, metric_type="histogram")
        
        event = collector.events[0]
        # Should be approximately 0.1 seconds (within 20ms tolerance)
        assert abs(event.value - 0.1) < 0.02
    
    def test_counter_accuracy(self):
        """Test that counter metrics accumulate correctly"""
        collector = MetricsCollector()
        
        # Record multiple counter events
        for i in range(10):
            collector.record_event("counter.test", 1, metric_type="counter")
        
        counter_events = [e for e in collector.events if e.name == "counter.test"]
        assert len(counter_events) == 10
        
        # Sum should be 10
        total = sum(e.value for e in counter_events)
        assert total == 10.0
    
    def test_gauge_accuracy(self):
        """Test that gauge metrics reflect current values"""
        collector = MetricsCollector()
        
        # Record gauge values
        values = [10.0, 20.0, 15.0, 25.0]
        for value in values:
            collector.record_event("gauge.test", value, metric_type="gauge")
        
        gauge_events = [e for e in collector.events if e.name == "gauge.test"]
        assert len(gauge_events) == 4
        
        # Last value should be 25.0
        assert gauge_events[-1].value == 25.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])