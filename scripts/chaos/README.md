# Chaos Engineering Scripts

This directory contains chaos engineering scripts designed to test the resilience and reliability of the AI-powered RPA platform.

## Overview

Chaos engineering is the practice of intentionally introducing failures and stress into a system to discover weaknesses and improve reliability. These scripts help validate that the platform can handle various failure scenarios gracefully.

## Available Experiments

### 1. Kill Runner Pod (`kill_runner_pod.sh`)
- **Purpose**: Tests pod failure resilience
- **What it does**: Randomly kills a runner pod to simulate sudden failures
- **Tests**: Pod recovery, service continuity, workflow execution resilience
- **Duration**: 5 minutes monitoring

### 2. Network Partition (`network_partition.sh`)
- **Purpose**: Tests network isolation scenarios
- **What it does**: Creates network policies to isolate services
- **Tests**: Service mesh resilience, API gateway behavior, circuit breaker patterns
- **Duration**: 2 minutes partition

### 3. CPU Stress (`cpu_stress.sh`)
- **Purpose**: Tests resource exhaustion scenarios
- **What it does**: Applies high CPU load to test resource limits
- **Tests**: Resource management, auto-scaling, performance degradation
- **Duration**: 5 minutes stress test

## Usage

### Run Individual Experiments

```bash
# Kill a random runner pod
./chaos_runner.sh --experiment kill_runner_pod

# Create network partition
./chaos_runner.sh --experiment network_partition

# Apply CPU stress
./chaos_runner.sh --experiment cpu_stress
```

### Run All Experiments

```bash
# Run all chaos experiments
./chaos_runner.sh --all
```

### Advanced Usage

```bash
# Dry run to see what would happen
./chaos_runner.sh --all --dry-run

# Run in specific namespace
./chaos_runner.sh --all --namespace production

# Store results in custom directory
./chaos_runner.sh --all --results-dir /path/to/results

# Send notifications to Slack
./chaos_runner.sh --all --slack-webhook https://hooks.slack.com/...
```

## Configuration

### Environment Variables

- `NAMESPACE`: Kubernetes namespace (default: `default`)
- `DRY_RUN`: Show what would be done without executing (default: `false`)
- `CHAOS_DURATION`: Duration for experiments in seconds
- `SLACK_WEBHOOK`: Slack webhook URL for notifications

### Prerequisites

- `kubectl` configured and connected to cluster
- `jq` for JSON processing
- `bc` for calculations
- Appropriate RBAC permissions

## Results and Reporting

### Output Structure

```
chaos_results/
├── chaos_run_20240710_120000/
│   ├── kill_runner_pod.log
│   ├── kill_runner_pod_result.json
│   ├── network_partition.log
│   ├── network_partition_result.json
│   ├── cpu_stress.log
│   ├── cpu_stress_result.json
│   └── summary.json
```

### Result JSON Format

```json
{
  "experiment": "kill_runner_pod",
  "description": "Kill random runner pod to test resilience",
  "start_time": "1720612800",
  "end_time": "1720613100",
  "duration_seconds": 300,
  "exit_code": 0,
  "success": true,
  "log_file": "/path/to/kill_runner_pod.log",
  "namespace": "default",
  "dry_run": false
}
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Chaos Engineering Tests

on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2 AM

jobs:
  chaos-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup kubectl
        run: |
          # Configure kubectl for staging cluster
          
      - name: Run chaos experiments
        run: |
          cd scripts/chaos
          ./chaos_runner.sh --all --namespace staging
```

### Kubernetes CronJob Example

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: chaos-experiments
spec:
  schedule: "0 2 * * 1"  # Weekly
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: chaos-runner
            image: ai-engine/chaos-runner:latest
            command:
            - /bin/bash
            - -c
            - |
              cd /chaos
              ./chaos_runner.sh --all --namespace staging
```

## Safety and Best Practices

### 1. Environment Isolation
- Always run chaos experiments in non-production environments first
- Use separate namespaces for chaos testing
- Implement proper RBAC to limit blast radius

### 2. Monitoring and Alerting
- Monitor system metrics during experiments
- Set up alerts for unusual behavior
- Have rollback procedures ready

### 3. Gradual Rollout
- Start with low-impact experiments
- Gradually increase complexity and duration
- Document learnings and improvements

### 4. Business Hours
- Schedule experiments during low-traffic periods
- Avoid running during critical business operations
- Coordinate with stakeholders

## Experiment Development

### Adding New Experiments

1. Create a new script file: `scripts/chaos/new_experiment.sh`
2. Follow the existing script patterns
3. Add the experiment to the `EXPERIMENTS` array in `chaos_runner.sh`
4. Update this README

### Script Template

```bash
#!/bin/bash
# Chaos Engineering Script: [Experiment Name]
# Description: [What this experiment does]

set -euo pipefail

# Configuration
NAMESPACE=${NAMESPACE:-"default"}
DRY_RUN=${DRY_RUN:-false}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Main experiment logic
main() {
    log "Starting [experiment name] chaos experiment"
    
    # Check prerequisites
    # Execute experiment
    # Monitor results
    # Cleanup
    
    log "Experiment completed"
}

# Cleanup function
cleanup() {
    log "Cleaning up..."
    # Cleanup code
}

trap cleanup EXIT
main "$@"
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Ensure scripts are executable: `chmod +x scripts/chaos/*.sh`
   - Check RBAC permissions for the service account

2. **Network Policy Not Applied**
   - Verify network policy controller is installed
   - Check if CNI supports network policies

3. **Resource Constraints**
   - Ensure sufficient resources for stress tests
   - Check resource quotas and limits

### Debug Mode

Run experiments with debug logging:

```bash
set -x  # Enable debug mode
./chaos_runner.sh --experiment kill_runner_pod
```

## Contributing

1. Follow the existing script patterns
2. Add comprehensive logging
3. Include proper error handling and cleanup
4. Update documentation
5. Test in staging environment first