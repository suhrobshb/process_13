# OPA Gatekeeper Policies

This directory contains Open Policy Agent (OPA) Gatekeeper policies for enforcing security and governance rules in the Kubernetes cluster.

## Overview

Gatekeeper is a validating admission webhook that enforces policies written in Rego (OPA's native query language). These policies help ensure security compliance, resource governance, and operational best practices.

## Installation

### 1. Install Gatekeeper

Use the official Gatekeeper installation:

```bash
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.14/deploy/gatekeeper.yaml
```

Or use the local installation file:

```bash
kubectl apply -f infrastructure/gatekeeper/install-gatekeeper.yaml
```

### 2. Apply Constraint Templates and Constraints

```bash
# Apply all policies
kubectl apply -f infrastructure/gatekeeper/

# Or apply individually
kubectl apply -f infrastructure/gatekeeper/no-privileged-containers.yaml
kubectl apply -f infrastructure/gatekeeper/require-resource-limits.yaml
kubectl apply -f infrastructure/gatekeeper/block-host-namespace.yaml
kubectl apply -f infrastructure/gatekeeper/require-security-context.yaml
kubectl apply -f infrastructure/gatekeeper/allowed-registries.yaml
```

## Available Policies

### 1. No Privileged Containers (`no-privileged-containers.yaml`)

**Purpose**: Prevents the creation of privileged containers.

**What it blocks**:
- Containers with `securityContext.privileged: true`
- Init containers with privileged access

**Exemptions**: System containers like pause containers

**Example violation**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
spec:
  containers:
  - name: app
    image: nginx
    securityContext:
      privileged: true  # ❌ This will be blocked
```

### 2. Require Resource Limits (`require-resource-limits.yaml`)

**Purpose**: Ensures all containers have CPU and memory limits defined.

**What it enforces**:
- CPU limits must be specified
- Memory limits must be specified
- Applies to both containers and init containers

**Example violation**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
spec:
  containers:
  - name: app
    image: nginx
    # ❌ Missing resources.limits
```

**Correct configuration**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: good-pod
spec:
  containers:
  - name: app
    image: nginx
    resources:
      limits:
        cpu: "500m"
        memory: "512Mi"
      requests:
        cpu: "100m"
        memory: "128Mi"
```

### 3. Block Host Namespace (`block-host-namespace.yaml`)

**Purpose**: Prevents containers from using host namespaces.

**What it blocks**:
- `hostNetwork: true`
- `hostIPC: true`
- `hostPID: true`

**Example violation**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
spec:
  hostNetwork: true  # ❌ This will be blocked
  containers:
  - name: app
    image: nginx
```

### 4. Require Security Context (`require-security-context.yaml`)

**Purpose**: Enforces secure container configurations.

**What it enforces**:
- Containers must run as non-root user
- Privilege escalation must be disabled
- Optional: Read-only root filesystem

**Example violation**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
spec:
  containers:
  - name: app
    image: nginx
    securityContext:
      runAsNonRoot: false  # ❌ This will be blocked
```

**Correct configuration**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: good-pod
spec:
  containers:
  - name: app
    image: nginx
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
```

### 5. Allowed Registries (`allowed-registries.yaml`)

**Purpose**: Restricts container images to approved registries.

**What it enforces**:
- Images must come from whitelisted registries
- Helps prevent supply chain attacks
- Ensures image provenance

**Allowed registries** (default configuration):
- `registry.k8s.io/*` - Official Kubernetes images
- `ghcr.io/*` - GitHub Container Registry
- `quay.io/*` - Red Hat Quay
- `gcr.io/*` - Google Container Registry
- `*.dkr.ecr.*.amazonaws.com/*` - AWS ECR
- `*.azurecr.io/*` - Azure Container Registry

**Example violation**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
spec:
  containers:
  - name: app
    image: untrusted-registry.com/malicious:latest  # ❌ This will be blocked
```

## Configuration

### Exempting Namespaces

All policies exclude system namespaces by default:
- `kube-system`
- `gatekeeper-system`

To exempt additional namespaces, modify the `excludedNamespaces` field:

```yaml
spec:
  match:
    - excludedNamespaces: ["kube-system", "gatekeeper-system", "monitoring"]
```

### Exempting Images

Some policies support image exemptions:

```yaml
parameters:
  exemptImages:
    - "registry.k8s.io/pause:*"
    - "your-special-image:*"
```

### Customizing Resource Requirements

Modify the required resources in `require-resource-limits.yaml`:

```yaml
parameters:
  limits: ["cpu", "memory", "ephemeral-storage"]  # Add storage limits
```

### Adding Trusted Registries

Update the `allowed-registries.yaml` policy:

```yaml
parameters:
  repos:
    - "your-company-registry.com/*"
    - "trusted-vendor.io/*"
```

## Monitoring and Troubleshooting

### Check Policy Status

```bash
# List constraint templates
kubectl get constrainttemplates

# List constraints
kubectl get constraints

# Check specific constraint status
kubectl describe k8srequirednonprivileged no-privileged-containers
```

### View Violations

```bash
# Check Gatekeeper audit logs
kubectl logs -n gatekeeper-system deployment/gatekeeper-controller-manager

# View violation events
kubectl get events --field-selector reason=FailedCreate
```

### Test Policies

Create test resources to verify policies are working:

```bash
# This should be blocked by the privileged container policy
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: test-privileged
spec:
  containers:
  - name: test
    image: nginx
    securityContext:
      privileged: true
EOF
```

### Disable Enforcement

To temporarily disable a constraint without deleting it:

```yaml
apiVersion: config.gatekeeper.sh/v1alpha1
kind: K8sRequiredNonPrivileged
metadata:
  name: no-privileged-containers
spec:
  enforcementAction: dryrun  # or "warn" for warnings only
```

## Policy Development

### Creating New Policies

1. Create a `ConstraintTemplate` with Rego policy
2. Create a `Constraint` that uses the template
3. Test with sample resources
4. Deploy to cluster

### Rego Policy Structure

```rego
package policy_name

import rego.v1

violation[{"msg": msg}] if {
    # Condition that triggers violation
    input.review.object.spec.someField == "badValue"
    msg := "This is not allowed"
}
```

### Testing Policies

Use OPA CLI to test policies locally:

```bash
# Install OPA CLI
curl -L -o opa https://openpolicyagent.org/downloads/v0.57.0/opa_linux_amd64_static
chmod +x opa

# Test policy
opa test policy.rego test_data.json
```

## Integration with CI/CD

### Pre-commit Hook

Add policy validation to pre-commit hooks:

```yaml
- repo: local
  hooks:
  - id: gatekeeper-conftest
    name: Gatekeeper Policy Check
    entry: conftest verify --policy infrastructure/gatekeeper/
    language: system
    files: '\.yaml$'
```

### GitHub Actions

```yaml
name: Policy Check
on: [push, pull_request]

jobs:
  policy-check:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Install Conftest
      run: |
        wget https://github.com/open-policy-agent/conftest/releases/download/v0.46.0/conftest_0.46.0_Linux_x86_64.tar.gz
        tar xzf conftest_0.46.0_Linux_x86_64.tar.gz
        sudo mv conftest /usr/local/bin
    
    - name: Test Policies
      run: |
        conftest verify --policy infrastructure/gatekeeper/ k8s/*.yaml
```

## Best Practices

### 1. Gradual Rollout

- Start with `enforcementAction: dryrun`
- Monitor violations and adjust policies
- Switch to `enforcementAction: deny` when ready

### 2. Documentation

- Document each policy's purpose and scope
- Provide examples of compliant configurations
- Maintain exemption justifications

### 3. Monitoring

- Set up alerts for policy violations
- Regular audit of exemptions
- Review and update policies periodically

### 4. Testing

- Test policies in staging before production
- Validate with realistic workloads
- Maintain test cases for each policy

## Common Issues

### 1. Policy Not Enforced

**Symptoms**: Resources are created despite violating policies

**Solutions**:
- Check if enforcement action is set to `deny`
- Verify constraint is properly configured
- Check namespace exclusions

### 2. Legitimate Resources Blocked

**Symptoms**: Valid workloads are blocked by policies

**Solutions**:
- Add appropriate exemptions
- Adjust policy parameters
- Consider namespace-specific policies

### 3. Performance Impact

**Symptoms**: Slow resource creation/updates

**Solutions**:
- Optimize Rego policies
- Use more specific resource selectors
- Consider async validation for large resources

## Security Considerations

1. **Policy Tampering**: Protect Gatekeeper namespace with RBAC
2. **Bypass Attempts**: Monitor for attempts to disable policies
3. **Performance DoS**: Set resource limits on Gatekeeper pods
4. **Policy Updates**: Use GitOps for policy changes

## Reference

- [OPA Gatekeeper Documentation](https://open-policy-agent.github.io/gatekeeper/)
- [Rego Language Reference](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)