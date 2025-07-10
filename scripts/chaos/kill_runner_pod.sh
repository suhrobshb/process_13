#!/bin/bash
# Chaos Engineering Script: Kill Random Runner Pod
# ================================================
# This script simulates sudden pod failures to test system resilience

set -euo pipefail

# Configuration
NAMESPACE=${NAMESPACE:-"default"}
LABEL_SELECTOR=${LABEL_SELECTOR:-"app=ai-engine-runner"}
DRY_RUN=${DRY_RUN:-false}
CHAOS_DURATION=${CHAOS_DURATION:-300}  # 5 minutes
RECOVERY_WAIT=${RECOVERY_WAIT:-30}     # 30 seconds

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    error "kubectl is required but not installed"
    exit 1
fi

# Check if we can connect to the cluster
if ! kubectl cluster-info &> /dev/null; then
    error "Cannot connect to Kubernetes cluster"
    exit 1
fi

# Get list of runner pods
log "Fetching runner pods with label selector: $LABEL_SELECTOR"
PODS=$(kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR" -o jsonpath='{.items[*].metadata.name}')

if [ -z "$PODS" ]; then
    warning "No runner pods found with label selector: $LABEL_SELECTOR"
    exit 0
fi

# Convert to array
PODS_ARRAY=($PODS)
POD_COUNT=${#PODS_ARRAY[@]}

log "Found $POD_COUNT runner pods: ${PODS_ARRAY[*]}"

# Select random pod
RANDOM_INDEX=$((RANDOM % POD_COUNT))
TARGET_POD=${PODS_ARRAY[$RANDOM_INDEX]}

log "Selected target pod: $TARGET_POD"

# Check pod status before chaos
POD_STATUS=$(kubectl get pod "$TARGET_POD" -n "$NAMESPACE" -o jsonpath='{.status.phase}')
log "Current pod status: $POD_STATUS"

if [ "$POD_STATUS" != "Running" ]; then
    warning "Pod $TARGET_POD is not in Running state. Skipping chaos experiment."
    exit 0
fi

# Get workflow executions before chaos
ACTIVE_EXECUTIONS=$(kubectl get pods -n "$NAMESPACE" -l "app=ai-engine-api" -o jsonpath='{.items[0].metadata.name}' | xargs -I {} kubectl exec {} -n "$NAMESPACE" -- curl -s http://localhost:8000/api/executions?status=running | jq -r '.[] | .id' 2>/dev/null | wc -l || echo "0")
log "Active workflow executions before chaos: $ACTIVE_EXECUTIONS"

if [ "$DRY_RUN" = "true" ]; then
    log "DRY RUN: Would kill pod $TARGET_POD"
    exit 0
fi

# Execute chaos - kill the pod
log "Executing chaos: Killing pod $TARGET_POD"
kubectl delete pod "$TARGET_POD" -n "$NAMESPACE" --force --grace-period=0

success "Pod $TARGET_POD has been killed"

# Monitor recovery
log "Monitoring system recovery for $CHAOS_DURATION seconds..."

START_TIME=$(date +%s)
RECOVERY_CONFIRMED=false

while [ $(($(date +%s) - START_TIME)) -lt $CHAOS_DURATION ]; do
    sleep "$RECOVERY_WAIT"
    
    # Check if new pod is running
    NEW_PODS=$(kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR" --field-selector=status.phase=Running -o jsonpath='{.items[*].metadata.name}')
    NEW_POD_COUNT=$(echo "$NEW_PODS" | wc -w)
    
    log "Current running pods: $NEW_POD_COUNT"
    
    if [ "$NEW_POD_COUNT" -ge "$POD_COUNT" ]; then
        # Check if API is responsive
        API_POD=$(kubectl get pods -n "$NAMESPACE" -l "app=ai-engine-api" -o jsonpath='{.items[0].metadata.name}')
        if kubectl exec "$API_POD" -n "$NAMESPACE" -- curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
            success "System has recovered! API is responsive and pods are running."
            RECOVERY_CONFIRMED=true
            break
        fi
    fi
    
    log "Waiting for recovery... ($(($(date +%s) - START_TIME))s elapsed)"
done

# Final status check
if [ "$RECOVERY_CONFIRMED" = "true" ]; then
    # Check if workflow executions are still processing
    FINAL_EXECUTIONS=$(kubectl get pods -n "$NAMESPACE" -l "app=ai-engine-api" -o jsonpath='{.items[0].metadata.name}' | xargs -I {} kubectl exec {} -n "$NAMESPACE" -- curl -s http://localhost:8000/api/executions?status=running | jq -r '.[] | .id' 2>/dev/null | wc -l || echo "0")
    
    success "Chaos experiment completed successfully!"
    log "Recovery metrics:"
    log "  - Recovery time: $(($(date +%s) - START_TIME)) seconds"
    log "  - Active executions before: $ACTIVE_EXECUTIONS"
    log "  - Active executions after: $FINAL_EXECUTIONS"
    log "  - Pod count maintained: $NEW_POD_COUNT/$POD_COUNT"
    
    if [ "$FINAL_EXECUTIONS" -ge "$ACTIVE_EXECUTIONS" ]; then
        success "Workflow executions maintained during chaos!"
    else
        warning "Some workflow executions may have been disrupted"
    fi
else
    error "System did not recover within $CHAOS_DURATION seconds"
    log "Current pod status:"
    kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR"
    exit 1
fi