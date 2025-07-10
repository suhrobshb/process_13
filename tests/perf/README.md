# Performance Testing

This directory contains comprehensive performance testing tools for the AI Automation Platform using Locust.

## Files

- `locustfile.py` - Main Locust configuration with user scenarios
- `performance_test.py` - Automated test runner with multiple scenarios
- `results/` - Directory for storing test results and reports

## Quick Start

### Prerequisites

```bash
pip install locust
```

### Basic Usage

1. **Run smoke test** (quick validation):
```bash
python tests/perf/performance_test.py --scenarios smoke
```

2. **Run stress test** (1000+ concurrent users):
```bash
python tests/perf/performance_test.py --scenarios stress
```

3. **Run all scenarios**:
```bash
python tests/perf/performance_test.py
```

### Direct Locust Usage

```bash
# Interactive web interface
locust -f tests/perf/locustfile.py --web-port 8089

# Headless mode with 1000 users
locust -f tests/perf/locustfile.py --headless -u 1000 -r 50 -t 20m
```

## Test Scenarios

### Smoke Test
- **Users**: 10
- **Duration**: 2 minutes
- **Purpose**: Quick validation that the system can handle basic load

### Normal Load
- **Users**: 100
- **Duration**: 10 minutes  
- **Purpose**: Simulate typical operational load

### Peak Load
- **Users**: 500
- **Duration**: 15 minutes
- **Purpose**: Test system behavior during peak usage

### Stress Test
- **Users**: 1000
- **Duration**: 20 minutes
- **Purpose**: Validate system stability under high load

### Spike Test
- **Users**: 2000
- **Duration**: 5 minutes
- **Purpose**: Test system response to sudden traffic spikes

## User Types

### WorkflowUser (Primary Load)
- Creates and executes workflows
- Monitors execution status
- Manages workflow lifecycle
- **Weight**: 10 (most common user type)

### AdminUser (System Management)
- Performs administrative tasks
- Monitors system health
- Manages user analytics
- **Weight**: 1 (fewer admin users)

### WebSocketUser (Real-time Features)
- Connects to WebSocket endpoints
- Receives real-time updates
- **Weight**: 2 (some users use real-time features)

## Key Performance Metrics

### Response Times
- **Target**: < 2 seconds for 95% of requests
- **Maximum**: < 5 seconds for 99% of requests

### Throughput
- **Normal Load**: 50+ requests/second
- **Peak Load**: 200+ requests/second

### Failure Rate
- **Normal Load**: < 1%
- **Peak Load**: < 5%
- **Stress Test**: < 15%

### Concurrent Executions
- **Target**: 1000+ concurrent workflow executions
- **Maximum**: System should gracefully handle overload

## Test Scenarios Details

### Workflow Creation Test
- Creates workflows with various step types
- Tests different automation runners (browser, desktop, LLM)
- Validates workflow configuration

### Execution Monitoring Test
- Executes workflows and monitors status
- Tests real-time status updates
- Validates completion notifications

### API Load Test
- Tests all REST API endpoints
- Validates authentication and authorization
- Tests data consistency under load

### Database Performance Test
- Tests database query performance
- Validates connection pooling
- Tests transaction handling

## Performance Thresholds

### Response Time SLAs
| Endpoint | Target | Maximum |
|----------|---------|---------|
| `/api/workflows` | < 500ms | < 2s |
| `/api/executions` | < 1s | < 5s |
| `/api/metrics` | < 200ms | < 1s |
| `/health` | < 100ms | < 500ms |

### System Resource Limits
- **CPU**: < 80% average utilization
- **Memory**: < 4GB per instance
- **Database**: < 1000 active connections
- **Queue**: < 10,000 pending tasks

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure the application is running on the correct port
   - Check firewall settings

2. **High Failure Rate**
   - Check application logs for errors
   - Monitor database performance
   - Verify system resources

3. **Slow Response Times**
   - Check database query performance
   - Monitor network latency
   - Review application profiling

### Performance Optimization

1. **Database Optimization**
   - Add appropriate indexes
   - Optimize query patterns
   - Configure connection pooling

2. **Application Optimization**
   - Enable caching where appropriate
   - Optimize hot code paths
   - Configure async processing

3. **Infrastructure Optimization**
   - Scale horizontally if needed
   - Optimize container resources
   - Configure load balancing

## Reporting

Test results are automatically saved to `tests/perf/results/` directory:

- JSON files with detailed metrics
- Markdown reports with analysis
- Performance trend data

### Sample Report Structure
```
# Performance Test Report
## Test Summary
- Scenario results table
- Key metrics overview

## Detailed Results
- Per-scenario analysis
- Performance metrics
- Issues and recommendations

## Trend Analysis
- Historical performance data
- Regression detection
```

## Integration with CI/CD

Performance tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Run Performance Tests
  run: |
    python tests/perf/performance_test.py --scenarios smoke normal
    
- name: Archive Performance Results
  uses: actions/upload-artifact@v3
  with:
    name: performance-results
    path: tests/perf/results/
```

## Advanced Usage

### Custom Scenarios
You can create custom test scenarios by modifying `locustfile.py`:

```python
class CustomUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def custom_task(self):
        # Your custom test logic
        pass
```

### Environment-Specific Testing
Use environment variables to configure tests:

```bash
export LOCUST_HOST=https://staging.example.com
export LOCUST_USERS=500
export LOCUST_SPAWN_RATE=25
python tests/perf/performance_test.py
```

### Continuous Performance Testing
Set up automated performance testing:

```bash
# Run daily performance tests
crontab -e
0 2 * * * cd /path/to/project && python tests/perf/performance_test.py --scenarios normal >> /var/log/perf_tests.log 2>&1
```