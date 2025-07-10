#!/bin/bash
# Code Quality Check Script
# =========================
# Comprehensive script to run all code quality checks locally
# This script mirrors the CI/CD pipeline checks

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run a check and report results
run_check() {
    local check_name="$1"
    local check_command="$2"
    local required="$3"  # true/false
    
    print_status "Running $check_name..."
    
    if eval "$check_command"; then
        print_success "$check_name passed"
        return 0
    else
        if [ "$required" = "true" ]; then
            print_error "$check_name failed (required)"
            return 1
        else
            print_warning "$check_name failed (optional)"
            return 0
        fi
    fi
}

# Initialize counters
total_checks=0
passed_checks=0
failed_checks=0

print_status "Starting comprehensive code quality checks..."
echo "=============================================="

# Check prerequisites
print_status "Checking prerequisites..."

if ! command_exists python3; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

if ! command_exists pip; then
    print_error "pip is required but not installed"
    exit 1
fi

if ! command_exists node; then
    print_error "Node.js is required but not installed"
    exit 1
fi

if ! command_exists npm; then
    print_error "npm is required but not installed"
    exit 1
fi

print_success "All prerequisites are available"

# Install Python dependencies if needed
print_status "Installing Python dependencies..."
pip install -q black isort flake8 mypy bandit safety pre-commit 2>/dev/null || true

# Install pre-commit hooks
print_status "Setting up pre-commit hooks..."
pre-commit install --install-hooks >/dev/null 2>&1 || true

echo ""
echo "=============================================="
print_status "Running Python code quality checks..."
echo "=============================================="

# Python Code Formatting (Black)
total_checks=$((total_checks + 1))
if run_check "Black code formatting" "black --check --diff ai_engine/ tests/ scripts/" true; then
    passed_checks=$((passed_checks + 1))
else
    failed_checks=$((failed_checks + 1))
    print_warning "Run 'black ai_engine/ tests/ scripts/' to fix formatting issues"
fi

# Python Import Sorting (isort)
total_checks=$((total_checks + 1))
if run_check "isort import sorting" "isort --check-only --diff ai_engine/ tests/ scripts/" true; then
    passed_checks=$((passed_checks + 1))
else
    failed_checks=$((failed_checks + 1))
    print_warning "Run 'isort ai_engine/ tests/ scripts/' to fix import sorting"
fi

# Python Linting (Flake8)
total_checks=$((total_checks + 1))
if run_check "Flake8 linting" "flake8 ai_engine/ tests/ scripts/" true; then
    passed_checks=$((passed_checks + 1))
else
    failed_checks=$((failed_checks + 1))
fi

# Python Type Checking (MyPy)
total_checks=$((total_checks + 1))
if run_check "MyPy type checking" "mypy ai_engine/ --ignore-missing-imports" false; then
    passed_checks=$((passed_checks + 1))
else
    failed_checks=$((failed_checks + 1))
fi

# Python Security Scanning (Bandit)
total_checks=$((total_checks + 1))
if run_check "Bandit security scan" "bandit -r ai_engine/ -ll" false; then
    passed_checks=$((passed_checks + 1))
else
    failed_checks=$((failed_checks + 1))
fi

# Python Dependency Security (Safety)
total_checks=$((total_checks + 1))
if run_check "Safety dependency scan" "safety check" false; then
    passed_checks=$((passed_checks + 1))
else
    failed_checks=$((failed_checks + 1))
fi

echo ""
echo "=============================================="
print_status "Running frontend code quality checks..."
echo "=============================================="

# Check if frontend directory exists
if [ -d "dashboard_ui_v2" ]; then
    cd dashboard_ui_v2
    
    # Install frontend dependencies
    print_status "Installing frontend dependencies..."
    npm ci --silent >/dev/null 2>&1 || npm install --silent >/dev/null 2>&1 || true
    
    # Frontend Linting (ESLint)
    total_checks=$((total_checks + 1))
    if run_check "ESLint linting" "npm run lint" true; then
        passed_checks=$((passed_checks + 1))
    else
        failed_checks=$((failed_checks + 1))
        print_warning "Run 'npm run lint -- --fix' to fix some issues automatically"
    fi
    
    # Frontend Type Checking (TypeScript)
    total_checks=$((total_checks + 1))
    if run_check "TypeScript type checking" "npx tsc --noEmit" true; then
        passed_checks=$((passed_checks + 1))
    else
        failed_checks=$((failed_checks + 1))
    fi
    
    # Frontend Formatting (Prettier)
    total_checks=$((total_checks + 1))
    if run_check "Prettier formatting" "npx prettier --check \"src/**/*.{js,jsx,ts,tsx,json,css,md}\"" true; then
        passed_checks=$((passed_checks + 1))
    else
        failed_checks=$((failed_checks + 1))
        print_warning "Run 'npx prettier --write \"src/**/*.{js,jsx,ts,tsx,json,css,md}\"' to fix formatting"
    fi
    
    cd ..
else
    print_warning "Frontend directory 'dashboard_ui_v2' not found, skipping frontend checks"
fi

echo ""
echo "=============================================="
print_status "Running additional quality checks..."
echo "=============================================="

# Check for large files
total_checks=$((total_checks + 1))
if run_check "Large file check" "find . -name '*.py' -o -name '*.js' -o -name '*.ts' | xargs wc -l | awk '\$1 > 1000 {print \$2\" has \"\$1\" lines (>1000)\"} END {if (NR == 0) exit 0; else exit 1}'" false; then
    passed_checks=$((passed_checks + 1))
else
    failed_checks=$((failed_checks + 1))
fi

# Check for TODO/FIXME comments
total_checks=$((total_checks + 1))
todo_count=$(find ai_engine/ tests/ -name "*.py" -exec grep -l "TODO\|FIXME\|XXX" {} \; 2>/dev/null | wc -l)
if [ "$todo_count" -eq 0 ]; then
    print_success "No TODO/FIXME comments found"
    passed_checks=$((passed_checks + 1))
else
    print_warning "Found $todo_count files with TODO/FIXME comments"
    failed_checks=$((failed_checks + 1))
fi

# Check for print statements in Python code (should use logging)
total_checks=$((total_checks + 1))
print_count=$(find ai_engine/ -name "*.py" -exec grep -l "print(" {} \; 2>/dev/null | wc -l)
if [ "$print_count" -eq 0 ]; then
    print_success "No print statements found in production code"
    passed_checks=$((passed_checks + 1))
else
    print_warning "Found $print_count files with print statements (should use logging)"
    failed_checks=$((failed_checks + 1))
fi

# Check for console.log in frontend code
if [ -d "dashboard_ui_v2/src" ]; then
    total_checks=$((total_checks + 1))
    console_count=$(find dashboard_ui_v2/src -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" | xargs grep -l "console\." 2>/dev/null | wc -l)
    if [ "$console_count" -eq 0 ]; then
        print_success "No console statements found in frontend code"
        passed_checks=$((passed_checks + 1))
    else
        print_warning "Found $console_count files with console statements"
        failed_checks=$((failed_checks + 1))
    fi
fi

# Run pre-commit on all files
total_checks=$((total_checks + 1))
if run_check "Pre-commit hooks" "pre-commit run --all-files" false; then
    passed_checks=$((passed_checks + 1))
else
    failed_checks=$((failed_checks + 1))
fi

echo ""
echo "=============================================="
print_status "Quality check summary"
echo "=============================================="

echo "Total checks: $total_checks"
echo "Passed: $passed_checks"
echo "Failed: $failed_checks"

# Calculate percentage
if [ "$total_checks" -gt 0 ]; then
    percentage=$((passed_checks * 100 / total_checks))
    echo "Success rate: $percentage%"
    
    if [ "$percentage" -ge 90 ]; then
        print_success "Excellent code quality! ($percentage% passed)"
        exit_code=0
    elif [ "$percentage" -ge 75 ]; then
        print_warning "Good code quality, but room for improvement ($percentage% passed)"
        exit_code=0
    elif [ "$percentage" -ge 50 ]; then
        print_warning "Code quality needs improvement ($percentage% passed)"
        exit_code=1
    else
        print_error "Poor code quality ($percentage% passed)"
        exit_code=1
    fi
else
    print_error "No checks were run"
    exit_code=1
fi

echo ""
echo "=============================================="
print_status "Recommendations"
echo "=============================================="

if [ "$failed_checks" -gt 0 ]; then
    echo "To improve code quality:"
    echo "1. Run individual tools to fix specific issues:"
    echo "   - black ai_engine/ tests/ scripts/  # Fix formatting"
    echo "   - isort ai_engine/ tests/ scripts/  # Fix imports"
    echo "   - cd dashboard_ui_v2 && npm run lint -- --fix  # Fix ESLint issues"
    echo ""
    echo "2. Set up pre-commit hooks to catch issues early:"
    echo "   - pre-commit install"
    echo "   - pre-commit run --all-files"
    echo ""
    echo "3. Configure your IDE/editor to:"
    echo "   - Format code on save (Black, Prettier)"
    echo "   - Show linting errors inline"
    echo "   - Use type checking"
fi

print_status "Quality check completed!"
exit $exit_code