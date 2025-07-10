# Argo Rollouts - Progressive Delivery

This directory contains Argo Rollouts configurations for implementing progressive delivery strategies (canary and blue-green deployments) for the AI-powered RPA platform.

## Overview

Argo Rollouts is a Kubernetes controller and set of CRDs that provide advanced deployment capabilities such as blue-green, canary, and experimentation to Kubernetes. It enables gradual traffic shifting, automated analysis, and rollback capabilities.

## Installation

### 1. Install Argo Rollouts Controller

```bash
# Using provided manifests
kubectl apply -f infrastructure/argo-rollouts/install-argo-rollouts.yaml

# Or using official release
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
```

### 2. Install Argo Rollouts CLI (Optional)

```bash
# Linux/WSL
curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64
chmod +x ./kubectl-argo-rollouts-linux-amd64
sudo mv ./kubectl-argo-rollouts-linux-amd64 /usr/local/bin/kubectl-argo-rollouts

# macOS
brew install argoproj/tap/kubectl-argo-rollouts

# Verify installation
kubectl argo rollouts version
```

### 3. Apply Rollout Configurations

```bash
# Apply analysis templates first
kubectl apply -f infrastructure/argo-rollouts/analysis-templates.yaml

# Apply rollout configurations
kubectl apply -f infrastructure/argo-rollouts/ai-engine-rollout.yaml
kubectl apply -f infrastructure/argo-rollouts/blue-green-rollout.yaml
```

## Deployment Strategies

### 1. Canary Deployment (AI Engine API)

**Strategy**: Gradual traffic shifting with automated analysis

**Configuration**: `ai-engine-rollout.yaml`

**Traffic Steps**:
1. **20%** → Pause 10 minutes for manual verification
2. **20%** → Automated analysis (5 minutes)
3. **40%** → Pause 5 minutes
4. **40%** → Second analysis round
5. **60%** → Pause 5 minutes
6. **80%** → Final analysis
7. **100%** → Full promotion

**Analysis Metrics**:
- Success rate > 95%
- 95th percentile latency < 2 seconds
- Workflow failure rate < 5%

**Example Commands**:
```bash
# Watch rollout progress
kubectl argo rollouts get rollout ai-engine-api --watch

# Promote to next step manually
kubectl argo rollouts promote ai-engine-api

# Abort rollout
kubectl argo rollouts abort ai-engine-api

# Set new image
kubectl argo rollouts set image ai-engine-api api=ghcr.io/your-org/ai-engine-api:v2.0.0
```

### 2. Blue-Green Deployment (AI Engine Workers)

**Strategy**: Full environment switch with preview testing

**Configuration**: `blue-green-rollout.yaml`

**Process**:
1. Deploy new version to preview environment
2. Run pre-promotion analysis
3. Manual or automatic promotion
4. Run post-promotion analysis
5. Scale down old version

**Analysis Metrics**:
- Success rate validation
- Resource utilization checks
- Business metrics validation

**Example Commands**:
```bash
# Watch blue-green rollout
kubectl argo rollouts get rollout ai-engine-workers --watch

# Promote preview to active
kubectl argo rollouts promote ai-engine-workers

# Test preview environment
kubectl port-forward svc/ai-engine-workers-preview 8080:80
```

## Analysis Templates

### Core Metrics

#### 1. Success Rate (`success-rate`)
- **Threshold**: > 95% success rate
- **Query**: HTTP 2xx/3xx responses vs total requests
- **Failure Condition**: < 90% success rate

#### 2. Latency P95 (`latency-p95`)
- **Threshold**: < 2000ms (2 seconds)
- **Query**: 95th percentile response time
- **Failure Condition**: > 5000ms (5 seconds)

#### 3. Workflow Failure Rate (`workflow-failure-rate`)
- **Threshold**: < 5% failure rate
- **Query**: Failed workflow executions vs total executions
- **Failure Condition**: > 10% failure rate

### Resource Metrics

#### 4. CPU Usage (`cpu-usage`)
- **Threshold**: < 80% CPU utilization
- **Query**: Container CPU usage vs limits
- **Failure Condition**: > 95% CPU utilization

#### 5. Memory Usage (`memory-usage`)
- **Threshold**: < 85% memory utilization
- **Query**: Container memory usage vs limits
- **Failure Condition**: > 95% memory utilization

### Business Metrics

#### 6. Error Budget (`error-budget`)
- **Threshold**: Based on SLO (default 99%)
- **Query**: Combined availability of API and workflows
- **Failure Condition**: < 95% availability

#### 7. Automation Success Rate (`automation-success-rate`)
- **Threshold**: > 98% automation success
- **Query**: Successful automation tasks vs total tasks
- **Failure Condition**: < 95% success rate

## Monitoring and Observability

### Rollout Status

```bash
# List all rollouts
kubectl argo rollouts list

# Get detailed rollout status
kubectl argo rollouts get rollout <rollout-name>

# Watch rollout progress in real-time
kubectl argo rollouts get rollout <rollout-name> --watch

# Get rollout history
kubectl argo rollouts history rollout <rollout-name>
```

### Analysis Results

```bash
# List analysis runs
kubectl get analysisruns

# Get analysis details
kubectl describe analysisrun <analysis-run-name>

# View analysis logs
kubectl logs -l app=argo-rollouts -n argo-rollouts
```

### Metrics and Dashboards

Monitor rollouts through:
- **Prometheus Metrics**: Available at `:8090/metrics`
- **Grafana Dashboards**: Import official Argo Rollouts dashboard
- **Kubernetes Events**: Standard Kubernetes events for rollout activities

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Deploy with Argo Rollouts
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup kubectl
      # Configure kubectl access
      
    - name: Install Argo Rollouts CLI
      run: |
        curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64
        chmod +x kubectl-argo-rollouts-linux-amd64
        sudo mv kubectl-argo-rollouts-linux-amd64 /usr/local/bin/kubectl-argo-rollouts
    
    - name: Update rollout image
      run: |
        kubectl argo rollouts set image ai-engine-api \
          api=ghcr.io/${{ github.repository }}/ai-engine-api:${{ github.sha }}
    
    - name: Wait for rollout completion
      run: |
        kubectl argo rollouts get rollout ai-engine-api --watch \
          --timeout=1800s  # 30 minutes timeout
```

### ArgoCD Integration

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ai-engine-rollouts
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/ai-engine
    targetRevision: HEAD
    path: infrastructure/argo-rollouts
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

## Configuration Customization

### Traffic Routing

#### NGINX Ingress Controller

```yaml
spec:
  strategy:
    canary:
      trafficRouting:
        nginx:
          stableIngress: ai-engine-api-stable
          annotationPrefix: nginx.ingress.kubernetes.io
```

#### Istio Service Mesh

```yaml
spec:
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: ai-engine-api-vs
            routes:
            - primary
```

#### AWS ALB

```yaml
spec:
  strategy:
    canary:
      trafficRouting:
        alb:
          ingress: ai-engine-api-ingress
          servicePort: 80
```

### Analysis Configuration

#### Custom Prometheus Queries

```yaml
metrics:
- name: custom-metric
  successCondition: result[0] >= 0.99
  provider:
    prometheus:
      address: http://prometheus.monitoring.svc.cluster.local:9090
      query: |
        sum(rate(custom_metric_total{service="{{args.service-name}}"}[5m])) /
        sum(rate(requests_total{service="{{args.service-name}}"}[5m]))
```

#### Web-based Health Checks

```yaml
metrics:
- name: health-check
  successCondition: result == "1"
  provider:
    web:
      url: http://{{args.service-name}}/health
      jsonPath: $.status
      timeoutSeconds: 10
```

### Notification Integration

#### Slack Notifications

```yaml
# Add to analysis template
metadata:
  annotations:
    notifications.argoproj.io/subscribe.on-analysis-run-failed.slack: ai-engineering-alerts
    notifications.argoproj.io/subscribe.on-analysis-run-error.slack: ai-engineering-alerts
```

## Troubleshooting

### Common Issues

#### 1. Rollout Stuck in Progressing State

**Symptoms**: Rollout doesn't progress beyond a certain step

**Solutions**:
```bash
# Check rollout events
kubectl describe rollout <rollout-name>

# Check replica set status
kubectl get rs -l app=<app-name>

# Check analysis run status
kubectl get analysisruns
kubectl describe analysisrun <analysis-run-name>
```

#### 2. Analysis Failures

**Symptoms**: Analysis consistently fails

**Solutions**:
- Verify Prometheus queries return valid data
- Check metric thresholds are realistic
- Validate service discovery and labels
- Test queries manually in Prometheus UI

```bash
# Test Prometheus query manually
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=your_metric_query'
```

#### 3. Traffic Routing Issues

**Symptoms**: Traffic not splitting correctly

**Solutions**:
- Verify ingress controller supports traffic splitting
- Check service selector labels match pods
- Validate ingress annotations

```bash
# Check service endpoints
kubectl get endpoints <service-name>

# Verify ingress status
kubectl describe ingress <ingress-name>
```

### Debugging Commands

```bash
# Get rollout logs
kubectl logs -l app.kubernetes.io/name=argo-rollouts -n argo-rollouts

# Describe rollout status
kubectl describe rollout <rollout-name>

# Check analysis run details
kubectl get analysisrun -o wide
kubectl logs <analysis-run-pod-name>

# View rollout events
kubectl get events --field-selector involvedObject.name=<rollout-name>
```

## Best Practices

### 1. Gradual Rollout Strategy

- Start with small traffic percentages (5-10%)
- Include manual approval gates for critical deployments
- Implement comprehensive analysis metrics
- Plan for quick rollback scenarios

### 2. Analysis Configuration

- Use multiple metrics to validate deployment health
- Set realistic thresholds based on baseline performance
- Include both technical and business metrics
- Configure appropriate failure limits to avoid false positives

### 3. Traffic Management

- Ensure load balancer supports traffic splitting
- Test traffic routing in staging environment
- Monitor traffic distribution during deployments
- Have backup traffic routing strategies

### 4. Monitoring and Alerting

- Set up alerts for failed rollouts
- Monitor rollout duration and success rates
- Track analysis metric trends over time
- Implement notification channels for stakeholders

### 5. Disaster Recovery

- Test rollback procedures regularly
- Document emergency rollback processes
- Maintain previous version availability
- Plan for infrastructure-level failures

## Security Considerations

### 1. RBAC Configuration

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: rollout-manager
rules:
- apiGroups: ["argoproj.io"]
  resources: ["rollouts", "analysisruns"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
```

### 2. Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: argo-rollouts-netpol
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: argo-rollouts
  policyTypes:
  - Ingress
  - Egress
```

### 3. Secret Management

- Use Kubernetes secrets for sensitive configuration
- Implement secret rotation procedures
- Avoid storing credentials in rollout manifests
- Use service accounts with minimal required permissions

## Performance Optimization

### 1. Resource Limits

```yaml
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 256Mi
```

### 2. Analysis Optimization

- Optimize Prometheus queries for performance
- Use appropriate query intervals
- Limit analysis duration for faster feedback
- Cache frequently used metrics

### 3. Scaling Considerations

- Plan for increased load during canary phases
- Configure HPA for automatic scaling
- Monitor resource utilization during rollouts
- Consider cluster capacity for blue-green deployments

## Integration Examples

### With Flagger

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: ai-engine-api
spec:
  provider: nginx
  targetRef:
    apiVersion: argoproj.io/v1alpha1
    kind: Rollout
    name: ai-engine-api
```

### With Prometheus Operator

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: argo-rollouts
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: argo-rollouts-metrics
  endpoints:
  - port: metrics
```

## Reference

- [Argo Rollouts Documentation](https://argo-rollouts.readthedocs.io/)
- [Progressive Delivery Best Practices](https://www.weave.works/blog/progressive-delivery-best-practices)
- [Kubernetes Deployment Strategies](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#strategy)
- [Prometheus Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)