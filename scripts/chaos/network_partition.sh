#!/bin/bash
# Chaos Engineering Script: Network Partition
# ============================================
# This script simulates network partitions between services

set -euo pipefail

# Configuration
NAMESPACE=${NAMESPACE:-"default"}
TARGET_SERVICE=${TARGET_SERVICE:-"ai-engine-api"}
PARTITION_DURATION=${PARTITION_DURATION:-120}  # 2 minutes
DRY_RUN=${DRY_RUN:-false}

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

# Check dependencies
check_dependencies() {
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is required but not installed"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
}

# Create network policy to block traffic
create_network_policy() {
    local policy_name="chaos-network-partition"
    
    cat << EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: $policy_name
  namespace: $NAMESPACE
spec:
  podSelector:
    matchLabels:
      app: $TARGET_SERVICE
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: chaos-test
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: chaos-test
EOF
    
    log "Network policy '$policy_name' created for service '$TARGET_SERVICE'"
}

# Remove network policy
remove_network_policy() {
    local policy_name="chaos-network-partition"
    
    kubectl delete networkpolicy "$policy_name" -n "$NAMESPACE" --ignore-not-found=true
    log "Network policy '$policy_name' removed"
}

# Monitor service health
monitor_service_health() {
    local service_name=$1
    local check_count=0
    local max_checks=10
    
    while [ $check_count -lt $max_checks ]; do
        if kubectl get pods -n "$NAMESPACE" -l "app=$service_name" -o jsonpath='{.items[0].metadata.name}' | xargs -I {} kubectl exec {} -n "$NAMESPACE" -- curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
            return 0
        fi
        
        ((check_count++))
        sleep 5
    done
    
    return 1
}

# Main execution
main() {
    log "Starting network partition chaos experiment"
    log "Target service: $TARGET_SERVICE"
    log "Partition duration: $PARTITION_DURATION seconds"
    log "Namespace: $NAMESPACE"
    
    check_dependencies
    
    if [ "$DRY_RUN" = "true" ]; then
        log "DRY RUN: Would create network partition for $TARGET_SERVICE"
        exit 0
    fi
    
    # Check initial health
    log "Checking initial service health..."
    if ! monitor_service_health "$TARGET_SERVICE"; then
        error "Service $TARGET_SERVICE is not healthy before chaos experiment"
        exit 1
    fi
    success "Service is healthy before chaos experiment"
    
    # Create network partition
    log "Creating network partition..."
    create_network_policy
    
    # Wait for partition to take effect
    sleep 10
    
    # Monitor during partition
    log "Monitoring service behavior during partition..."
    PARTITION_START=$(date +%s)
    
    while [ $(($(date +%s) - PARTITION_START)) -lt $PARTITION_DURATION ]; do
        if monitor_service_health "$TARGET_SERVICE"; then
            warning "Service is still responding during partition (unexpected)"
        else
            log "Service is correctly partitioned"
        fi
        sleep 15
    done
    
    # Remove network partition
    log "Removing network partition..."
    remove_network_policy
    
    # Wait for recovery
    log "Waiting for service recovery..."
    sleep 30
    
    # Check recovery
    RECOVERY_START=$(date +%s)
    MAX_RECOVERY_TIME=180  # 3 minutes
    
    while [ $(($(date +%s) - RECOVERY_START)) -lt $MAX_RECOVERY_TIME ]; do
        if monitor_service_health "$TARGET_SERVICE"; then
            success "Service has recovered after network partition!"
            log "Recovery time: $(($(date +%s) - RECOVERY_START)) seconds"
            exit 0
        fi
        
        log "Waiting for service recovery... ($(($(date +%s) - RECOVERY_START))s elapsed)"
        sleep 10
    done
    
    error "Service did not recover within $MAX_RECOVERY_TIME seconds"
    exit 1
}

# Cleanup on exit
cleanup() {
    log "Cleaning up network policies..."
    remove_network_policy
}

trap cleanup EXIT

main "$@"