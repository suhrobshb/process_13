#!/bin/bash
# Chaos Engineering Orchestrator
# ===============================
# This script orchestrates various chaos experiments and collects results

set -euo pipefail

# Configuration
NAMESPACE=${NAMESPACE:-"default"}
EXPERIMENT_DIR="${EXPERIMENT_DIR:-$(dirname "$0")}"
RESULTS_DIR="${RESULTS_DIR:-./chaos_results}"
RUN_ALL=${RUN_ALL:-false}
EXPERIMENT_NAME=${EXPERIMENT_NAME:-""}
DRY_RUN=${DRY_RUN:-false}
SLACK_WEBHOOK=${SLACK_WEBHOOK:-""}

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

# Available experiments
declare -A EXPERIMENTS=(
    ["kill_runner_pod"]="Kill random runner pod to test resilience"
    ["network_partition"]="Create network partition to test service mesh"
    ["cpu_stress"]="Apply CPU stress to test resource limits"
)

# Show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --experiment NAME    Run specific experiment ($(echo "${!EXPERIMENTS[@]}" | tr ' ' '|'))"
    echo "  -a, --all               Run all experiments"
    echo "  -n, --namespace NAME    Kubernetes namespace (default: default)"
    echo "  -d, --dry-run          Show what would be done without executing"
    echo "  -r, --results-dir PATH  Directory to store results (default: ./chaos_results)"
    echo "  -s, --slack-webhook URL Slack webhook for notifications"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Available experiments:"
    for exp in "${!EXPERIMENTS[@]}"; do
        echo "  $exp - ${EXPERIMENTS[$exp]}"
    done
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--experiment)
                EXPERIMENT_NAME="$2"
                shift 2
                ;;
            -a|--all)
                RUN_ALL=true
                shift
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -r|--results-dir)
                RESULTS_DIR="$2"
                shift 2
                ;;
            -s|--slack-webhook)
                SLACK_WEBHOOK="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Send Slack notification
send_slack_notification() {
    local message="$1"
    local color="${2:-good}"
    
    if [ -z "$SLACK_WEBHOOK" ]; then
        return 0
    fi
    
    local payload=$(cat <<EOF
{
    "attachments": [
        {
            "color": "$color",
            "fields": [
                {
                    "title": "Chaos Engineering Report",
                    "value": "$message",
                    "short": false
                }
            ]
        }
    ]
}
EOF
)
    
    curl -X POST -H 'Content-type: application/json' \
         --data "$payload" \
         "$SLACK_WEBHOOK" > /dev/null 2>&1 || true
}

# Create results directory
setup_results_dir() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    RESULTS_DIR="$RESULTS_DIR/chaos_run_$timestamp"
    
    mkdir -p "$RESULTS_DIR"
    log "Results will be stored in: $RESULTS_DIR"
}

# Run single experiment
run_experiment() {
    local exp_name="$1"
    local exp_script="$EXPERIMENT_DIR/${exp_name}.sh"
    local exp_log="$RESULTS_DIR/${exp_name}.log"
    
    if [ ! -f "$exp_script" ]; then
        error "Experiment script not found: $exp_script"
        return 1
    fi
    
    log "Running experiment: $exp_name"
    log "Description: ${EXPERIMENTS[$exp_name]}"
    
    # Make script executable
    chmod +x "$exp_script"
    
    # Run experiment with environment variables
    local start_time=$(date +%s)
    local exit_code=0
    
    if [ "$DRY_RUN" = "true" ]; then
        DRY_RUN=true NAMESPACE="$NAMESPACE" "$exp_script" 2>&1 | tee "$exp_log"
        exit_code=${PIPESTATUS[0]}
    else
        NAMESPACE="$NAMESPACE" "$exp_script" 2>&1 | tee "$exp_log"
        exit_code=${PIPESTATUS[0]}
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Record experiment result
    local result_file="$RESULTS_DIR/${exp_name}_result.json"
    cat > "$result_file" <<EOF
{
    "experiment": "$exp_name",
    "description": "${EXPERIMENTS[$exp_name]}",
    "start_time": "$start_time",
    "end_time": "$end_time",
    "duration_seconds": $duration,
    "exit_code": $exit_code,
    "success": $([ $exit_code -eq 0 ] && echo "true" || echo "false"),
    "log_file": "$exp_log",
    "namespace": "$NAMESPACE",
    "dry_run": $DRY_RUN
}
EOF
    
    if [ $exit_code -eq 0 ]; then
        success "Experiment $exp_name completed successfully in ${duration}s"
        return 0
    else
        error "Experiment $exp_name failed with exit code $exit_code"
        return 1
    fi
}

# Generate summary report
generate_summary() {
    local summary_file="$RESULTS_DIR/summary.json"
    local total_experiments=0
    local successful_experiments=0
    local failed_experiments=0
    
    log "Generating summary report..."
    
    echo "{" > "$summary_file"
    echo "  \"chaos_run\": {" >> "$summary_file"
    echo "    \"timestamp\": \"$(date -Iseconds)\"," >> "$summary_file"
    echo "    \"namespace\": \"$NAMESPACE\"," >> "$summary_file"
    echo "    \"dry_run\": $DRY_RUN," >> "$summary_file"
    echo "    \"results_dir\": \"$RESULTS_DIR\"" >> "$summary_file"
    echo "  }," >> "$summary_file"
    echo "  \"experiments\": [" >> "$summary_file"
    
    local first=true
    for result_file in "$RESULTS_DIR"/*_result.json; do
        if [ -f "$result_file" ]; then
            if [ "$first" = true ]; then
                first=false
            else
                echo "," >> "$summary_file"
            fi
            
            cat "$result_file" >> "$summary_file"
            
            # Count experiments
            ((total_experiments++))
            if jq -r '.success' "$result_file" | grep -q "true"; then
                ((successful_experiments++))
            else
                ((failed_experiments++))
            fi
        fi
    done
    
    echo "" >> "$summary_file"
    echo "  ]," >> "$summary_file"
    echo "  \"summary\": {" >> "$summary_file"
    echo "    \"total_experiments\": $total_experiments," >> "$summary_file"
    echo "    \"successful_experiments\": $successful_experiments," >> "$summary_file"
    echo "    \"failed_experiments\": $failed_experiments," >> "$summary_file"
    echo "    \"success_rate\": $(echo "scale=2; $successful_experiments * 100 / $total_experiments" | bc -l 2>/dev/null || echo "0")" >> "$summary_file"
    echo "  }" >> "$summary_file"
    echo "}" >> "$summary_file"
    
    log "Summary report generated: $summary_file"
    
    # Display summary
    echo ""
    echo "=========================================="
    echo "         CHAOS ENGINEERING SUMMARY"
    echo "=========================================="
    echo "Total Experiments: $total_experiments"
    echo "Successful: $successful_experiments"
    echo "Failed: $failed_experiments"
    echo "Success Rate: $(echo "scale=1; $successful_experiments * 100 / $total_experiments" | bc -l 2>/dev/null || echo "0")%"
    echo "Results Directory: $RESULTS_DIR"
    echo "=========================================="
    
    # Send Slack notification
    if [ "$failed_experiments" -eq 0 ]; then
        send_slack_notification "✅ All chaos experiments passed! ($successful_experiments/$total_experiments)" "good"
    else
        send_slack_notification "⚠️ Some chaos experiments failed! ($successful_experiments/$total_experiments successful)" "warning"
    fi
}

# Main execution
main() {
    log "Starting chaos engineering orchestrator"
    
    parse_args "$@"
    
    # Validate arguments
    if [ "$RUN_ALL" = false ] && [ -z "$EXPERIMENT_NAME" ]; then
        error "Must specify either --all or --experiment"
        show_usage
        exit 1
    fi
    
    if [ -n "$EXPERIMENT_NAME" ] && [ -z "${EXPERIMENTS[$EXPERIMENT_NAME]:-}" ]; then
        error "Unknown experiment: $EXPERIMENT_NAME"
        show_usage
        exit 1
    fi
    
    setup_results_dir
    
    # Run experiments
    local overall_success=true
    
    if [ "$RUN_ALL" = true ]; then
        log "Running all chaos experiments..."
        for exp_name in "${!EXPERIMENTS[@]}"; do
            if ! run_experiment "$exp_name"; then
                overall_success=false
            fi
            echo ""
        done
    else
        run_experiment "$EXPERIMENT_NAME"
        overall_success=$?
    fi
    
    generate_summary
    
    if [ "$overall_success" = true ]; then
        success "All chaos experiments completed successfully!"
        exit 0
    else
        error "Some chaos experiments failed. Check the results for details."
        exit 1
    fi
}

# Check dependencies
check_dependencies() {
    local missing_deps=()
    
    for cmd in kubectl jq bc; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        exit 1
    fi
}

check_dependencies
main "$@"