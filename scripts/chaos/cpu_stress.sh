#!/bin/bash
# Chaos Engineering Script: CPU Stress Test
# ==========================================
# This script simulates high CPU load to test system behavior under stress

set -euo pipefail

# Configuration
NAMESPACE=${NAMESPACE:-"default"}
TARGET_SERVICE=${TARGET_SERVICE:-"ai-engine-api"}
STRESS_DURATION=${STRESS_DURATION:-300}  # 5 minutes
CPU_CORES=${CPU_CORES:-2}
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

# Get target pod
get_target_pod() {
    local pod_name
    pod_name=$(kubectl get pods -n "$NAMESPACE" -l "app=$TARGET_SERVICE" -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$pod_name" ]; then
        error "No pods found for service $TARGET_SERVICE"
        exit 1
    fi
    
    echo "$pod_name"
}

# Start CPU stress
start_cpu_stress() {
    local pod_name=$1
    
    log "Starting CPU stress test on pod: $pod_name"
    
    # Install stress-ng if not available
    kubectl exec "$pod_name" -n "$NAMESPACE" -- sh -c "
        if ! command -v stress-ng &> /dev/null; then
            apt-get update -qq && apt-get install -y -qq stress-ng
        fi
    " 2>/dev/null || true
    
    # Start stress test in background
    kubectl exec "$pod_name" -n "$NAMESPACE" -- sh -c "
        nohup stress-ng --cpu $CPU_CORES --timeout ${STRESS_DURATION}s > /tmp/stress.log 2>&1 &
        echo \$! > /tmp/stress.pid
    " &
    
    log "CPU stress test started with $CPU_CORES cores for $STRESS_DURATION seconds"
}

# Stop CPU stress
stop_cpu_stress() {
    local pod_name=$1
    
    log "Stopping CPU stress test on pod: $pod_name"
    
    kubectl exec "$pod_name" -n "$NAMESPACE" -- sh -c "
        if [ -f /tmp/stress.pid ]; then
            kill \$(cat /tmp/stress.pid) 2>/dev/null || true
            rm -f /tmp/stress.pid
        fi
        pkill -f stress-ng || true
    " 2>/dev/null || true
    
    log "CPU stress test stopped"
}

# Monitor system metrics
monitor_metrics() {
    local pod_name=$1
    local duration=$2
    
    log "Monitoring system metrics for $duration seconds..."
    
    local start_time=$(date +%s)
    local metrics_log="/tmp/chaos_metrics.log"
    
    echo "timestamp,cpu_usage,memory_usage,response_time" > "$metrics_log"
    
    while [ $(($(date +%s) - start_time)) -lt $duration ]; do
        # Get CPU and memory usage
        local cpu_usage=$(kubectl top pod "$pod_name" -n "$NAMESPACE" --no-headers | awk '{print $2}' | sed 's/m//' 2>/dev/null || echo "0")
        local memory_usage=$(kubectl top pod "$pod_name" -n "$NAMESPACE" --no-headers | awk '{print $3}' | sed 's/Mi//' 2>/dev/null || echo "0")
        
        # Test API response time
        local response_time=$(kubectl exec "$pod_name" -n "$NAMESPACE" -- sh -c "
            start=\$(date +%s%3N)
            curl -s -f http://localhost:8000/health > /dev/null 2>&1
            end=\$(date +%s%3N)
            echo \$((end - start))
        " 2>/dev/null || echo "999999")
        
        echo "$(date +%s),$cpu_usage,$memory_usage,$response_time" >> "$metrics_log"
        
        log "CPU: ${cpu_usage}m, Memory: ${memory_usage}Mi, Response: ${response_time}ms"
        sleep 10
    done
    
    log "Metrics saved to $metrics_log"
}

# Check system health
check_system_health() {
    local pod_name=$1
    
    # Check if pod is still running
    local pod_status=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.status.phase}')
    if [ "$pod_status" != "Running" ]; then
        warning "Pod is not in Running state: $pod_status"
        return 1
    fi
    
    # Check API health
    if kubectl exec "$pod_name" -n "$NAMESPACE" -- curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Main execution
main() {
    log "Starting CPU stress chaos experiment"
    log "Target service: $TARGET_SERVICE"
    log "Stress duration: $STRESS_DURATION seconds"
    log "CPU cores: $CPU_CORES"
    log "Namespace: $NAMESPACE"
    
    check_dependencies
    
    local target_pod
    target_pod=$(get_target_pod)
    
    if [ "$DRY_RUN" = "true" ]; then
        log "DRY RUN: Would stress $CPU_CORES CPU cores on pod $target_pod"
        exit 0
    fi
    
    # Check initial health
    log "Checking initial system health..."
    if ! check_system_health "$target_pod"; then
        error "System is not healthy before chaos experiment"
        exit 1
    fi
    success "System is healthy before chaos experiment"
    
    # Start CPU stress
    start_cpu_stress "$target_pod"
    
    # Monitor during stress
    monitor_metrics "$target_pod" "$STRESS_DURATION" &
    MONITOR_PID=$!
    
    # Check system health during stress
    local check_interval=30
    local health_checks=0
    local failed_checks=0
    
    for ((i=0; i<STRESS_DURATION; i+=check_interval)); do
        sleep $check_interval
        
        if check_system_health "$target_pod"; then
            log "System health check passed"
        else
            warning "System health check failed"
            ((failed_checks++))
        fi
        
        ((health_checks++))
    done
    
    # Stop monitoring
    kill $MONITOR_PID 2>/dev/null || true
    
    # Stop CPU stress
    stop_cpu_stress "$target_pod"
    
    # Wait for recovery
    log "Waiting for system recovery..."
    sleep 30
    
    # Check final health
    if check_system_health "$target_pod"; then
        success "System has recovered after CPU stress test!"
        log "Health check results: $((health_checks - failed_checks))/$health_checks passed"
        
        if [ $failed_checks -eq 0 ]; then
            success "System maintained full availability during stress test!"
        else
            warning "System experienced $failed_checks/$health_checks health check failures"
        fi
    else
        error "System did not recover after CPU stress test"
        exit 1
    fi
}

# Cleanup on exit
cleanup() {
    log "Cleaning up CPU stress processes..."
    local target_pod
    target_pod=$(get_target_pod 2>/dev/null)
    
    if [ -n "$target_pod" ]; then
        stop_cpu_stress "$target_pod"
    fi
}

trap cleanup EXIT

main "$@"