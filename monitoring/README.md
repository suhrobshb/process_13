# Synthetic Canary Monitoring

This directory contains the synthetic canary monitoring system for the AI Automation Platform. The system provides continuous health monitoring through automated synthetic workflows that simulate real user scenarios.

## Overview

The canary monitoring system consists of:

1. **Synthetic Canary Workflows** - Automated tests that run continuously
2. **Canary Dashboard** - Web interface for monitoring results
3. **Orchestrator** - Manages canary execution and scheduling
4. **Alerting System** - Sends notifications when issues are detected

## Components

### Canary Workflows

- **API Health Canary** - Monitors core API endpoints
- **Workflow Execution Canary** - Tests end-to-end workflow execution
- **Database Canary** - Monitors database connectivity and performance
- **Authentication Canary** - Tests authentication system

### Monitoring Dashboard

- Real-time health status
- Success rate metrics
- Response time trends
- Recent execution results
- Manual canary execution

## Quick Start

### Local Development

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Start the main application**:
```bash
python main.py
```

3. **Run canaries once**:
```bash
python monitoring/synthetic_canary_workflows.py --once
```

4. **Start canary dashboard**:
```bash
python monitoring/canary_dashboard.py
```

5. **Access dashboard**: http://localhost:8001

### Docker Deployment

1. **Start all services**:
```bash
docker-compose -f monitoring/docker-compose.canary.yml up -d
```

2. **Access services**:
   - Main Application: http://localhost:8000
   - Canary Dashboard: http://localhost:8001
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000
   - Alertmanager: http://localhost:9093

## Configuration

### Environment Variables

- `CANARY_BASE_URL` - Base URL for the application (default: http://localhost:8000)
- `CANARY_AUTH_TOKEN` - Authentication token for API access
- `CANARY_SCHEDULE_INTERVAL` - Interval between canary runs (default: 5 minutes)
- `CANARY_RESULTS_RETENTION` - How long to keep results (default: 7 days)

### Canary Configuration

Edit `synthetic_canary_workflows.py` to customize:

- Canary frequency
- Timeout values
- Expected response times
- Alert thresholds

## Canary Types

### 1. API Health Canary

**Purpose**: Monitor API endpoint availability and performance

**Endpoints Tested**:
- `/health` - Basic health check
- `/api/workflows` - Workflow listing
- `/api/metrics` - System metrics

**Success Criteria**:
- HTTP 200 response
- Response time < 2 seconds
- Valid JSON response

### 2. Workflow Execution Canary

**Purpose**: Test complete workflow lifecycle

**Test Steps**:
1. Create test workflow
2. Execute workflow
3. Monitor execution status
4. Verify completion
5. Clean up resources

**Success Criteria**:
- Workflow creation successful
- Execution completes within 2 minutes
- Final status is "completed"

### 3. Database Canary

**Purpose**: Monitor database connectivity and performance

**Test Operations**:
- Read operation (list workflows)
- Write operation (create test workflow)
- Delete operation (cleanup)

**Success Criteria**:
- All operations succeed
- Response time < 1 second
- Data consistency maintained

### 4. Authentication Canary

**Purpose**: Test authentication system

**Test Cases**:
- Valid token access
- Invalid token rejection
- Token expiration handling

**Success Criteria**:
- Authorized requests succeed
- Unauthorized requests fail with 401/403
- Token validation works correctly

## Metrics and Alerting

### Key Metrics

- **Availability**: Percentage of successful canary executions
- **Response Time**: Average response time across all canaries
- **Error Rate**: Percentage of failed executions
- **Coverage**: Number of different canary types executed

### Alert Conditions

- **Critical**: Success rate < 70% over 15 minutes
- **Warning**: Success rate < 90% over 30 minutes
- **Info**: Individual canary failure

### Alert Channels

- **Email**: Critical and warning alerts
- **Slack**: All alerts including info
- **PagerDuty**: Critical alerts only
- **Webhook**: Custom integrations

## Dashboard Features

### Real-time Metrics

- System health status
- Success rate over time
- Response time trends
- Recent execution results

### Interactive Features

- Manual canary execution
- Drill-down into specific failures
- Historical data analysis
- Export results to CSV

### Visualizations

- Success rate timeline
- Response time distribution
- Failure categorization
- Geographic performance (if applicable)

## Troubleshooting

### Common Issues

1. **Canaries Not Running**
   - Check application is running
   - Verify network connectivity
   - Check authentication token

2. **High Failure Rate**
   - Check application logs
   - Monitor system resources
   - Verify database connectivity

3. **Dashboard Not Loading**
   - Check dashboard service status
   - Verify port availability
   - Check results directory permissions

### Debug Commands

```bash
# Check canary status
python monitoring/synthetic_canary_workflows.py --once

# View recent results
ls -la monitoring/canary_results/

# Check dashboard health
curl http://localhost:8001/api/health

# View canary logs
docker logs canary-orchestrator
```

## Integration

### CI/CD Integration

Add canary checks to your CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run Canary Tests
  run: |
    python monitoring/synthetic_canary_workflows.py --once
    if [ $? -ne 0 ]; then
      echo "Canary tests failed"
      exit 1
    fi
```

### Monitoring Integration

The system integrates with:

- **Prometheus** - Metrics collection
- **Grafana** - Visualization
- **Alertmanager** - Alert routing
- **Custom webhooks** - External integrations

### API Integration

Access canary data via REST API:

```bash
# Get current health status
curl http://localhost:8001/api/health

# Get recent results
curl http://localhost:8001/api/results

# Trigger canary execution
curl -X POST http://localhost:8001/api/run-canaries
```

## Development

### Adding New Canaries

1. Create new class inheriting from `CanaryWorkflow`
2. Implement `_execute_workflow` method
3. Add to orchestrator's canary list
4. Update dashboard if needed

Example:

```python
class CustomCanary(CanaryWorkflow):
    def __init__(self):
        super().__init__("custom_canary", "Custom Test", "Description")
    
    async def _execute_workflow(self, context):
        # Implement custom test logic
        return {"custom_metric": 123}
```

### Testing

Run tests for canary system:

```bash
# Unit tests
pytest tests/test_canary_workflows.py

# Integration tests
pytest tests/test_canary_integration.py

# Performance tests
python monitoring/synthetic_canary_workflows.py --once --verbose
```

## Production Deployment

### Recommended Setup

1. **High Availability**
   - Deploy canary orchestrator on multiple nodes
   - Use load balancer for dashboard
   - Implement failover mechanisms

2. **Monitoring**
   - Set up comprehensive alerting
   - Monitor canary system itself
   - Regular health checks

3. **Security**
   - Use HTTPS for all communications
   - Implement proper authentication
   - Regular security audits

### Scaling Considerations

- **Frequency**: Adjust based on system load
- **Timeout**: Set appropriate timeouts
- **Retention**: Configure data retention policies
- **Resources**: Monitor resource usage

## Best Practices

1. **Canary Design**
   - Keep canaries simple and focused
   - Test critical user journeys
   - Avoid impacting production data

2. **Monitoring**
   - Set realistic thresholds
   - Implement gradual alerting
   - Regular review of metrics

3. **Maintenance**
   - Regular canary updates
   - Monitor for false positives
   - Keep documentation current

## Support

For issues or questions:

1. Check the troubleshooting guide
2. Review application logs
3. Contact the platform team
4. Create an issue in the repository

---

**Last Updated**: 2025-01-10  
**Version**: 1.0.0