"""
Test Coverage Reporter and CI Integration
=========================================

Comprehensive test coverage reporting and CI/CD integration setup.
"""

import os
import sys
import json
import subprocess
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class TestCoverageReporter:
    """Generates comprehensive test coverage reports"""
    
    def __init__(self):
        self.project_root = project_root
        self.coverage_data = {
            "timestamp": datetime.now().isoformat(),
            "backend": {
                "total_files": 0,
                "tested_files": 0,
                "coverage_percentage": 0.0,
                "test_files": [],
                "untested_files": []
            },
            "frontend": {
                "total_files": 0,
                "tested_files": 0,
                "coverage_percentage": 0.0,
                "test_files": [],
                "untested_files": []
            },
            "integration": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "success_rate": 0.0
            },
            "recommendations": []
        }
    
    def analyze_backend_coverage(self):
        """Analyze backend test coverage"""
        print("Analyzing Backend Test Coverage...")
        
        ai_engine_dir = os.path.join(self.project_root, "ai_engine")
        tests_dir = os.path.join(self.project_root, "tests")
        
        # Count Python files
        py_files = []
        for root, dirs, files in os.walk(ai_engine_dir):
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    py_files.append(os.path.relpath(os.path.join(root, file), self.project_root))
        
        # Count test files
        test_files = []
        for root, dirs, files in os.walk(tests_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(os.path.relpath(os.path.join(root, file), self.project_root))
        
        # Analyze which files have tests
        tested_files = []
        untested_files = []
        
        for py_file in py_files:
            module_name = os.path.basename(py_file).replace('.py', '')
            has_test = any(module_name in test_file for test_file in test_files)
            
            if has_test:
                tested_files.append(py_file)
            else:
                untested_files.append(py_file)
        
        coverage_percentage = (len(tested_files) / len(py_files)) * 100 if py_files else 0
        
        self.coverage_data["backend"] = {
            "total_files": len(py_files),
            "tested_files": len(tested_files),
            "coverage_percentage": round(coverage_percentage, 2),
            "test_files": test_files,
            "untested_files": untested_files[:10]  # Top 10 untested files
        }
        
        print("  - Total backend files: {}".format(len(py_files)))
        print("  - Files with tests: {}".format(len(tested_files)))
        print("  - Coverage: {:.1f}%".format(coverage_percentage))
    
    def analyze_frontend_coverage(self):
        """Analyze frontend test coverage"""
        print("Analyzing Frontend Test Coverage...")
        
        frontend_dir = os.path.join(self.project_root, "dashboard_ui_v2", "src")
        
        if not os.path.exists(frontend_dir):
            print("  - Frontend directory not found")
            return
        
        # Count source files
        source_files = []
        test_files = []
        
        for root, dirs, files in os.walk(frontend_dir):
            for file in files:
                if file.endswith(('.ts', '.tsx', '.js', '.jsx')):
                    file_path = os.path.relpath(os.path.join(root, file), self.project_root)
                    
                    if '__tests__' in file_path or '.test.' in file or '.spec.' in file:
                        test_files.append(file_path)
                    else:
                        source_files.append(file_path)
        
        # Analyze test coverage
        tested_files = []
        untested_files = []
        
        for source_file in source_files:
            # Check if there's a corresponding test file
            base_name = os.path.basename(source_file).split('.')[0]
            has_test = any(base_name in test_file for test_file in test_files)
            
            if has_test:
                tested_files.append(source_file)
            else:
                untested_files.append(source_file)
        
        coverage_percentage = (len(tested_files) / len(source_files)) * 100 if source_files else 0
        
        self.coverage_data["frontend"] = {
            "total_files": len(source_files),
            "tested_files": len(tested_files),
            "coverage_percentage": round(coverage_percentage, 2),
            "test_files": test_files,
            "untested_files": untested_files[:10]  # Top 10 untested files
        }
        
        print("  - Total frontend files: {}".format(len(source_files)))
        print("  - Files with tests: {}".format(len(tested_files)))
        print("  - Coverage: {:.1f}%".format(coverage_percentage))
    
    def analyze_integration_coverage(self):
        """Analyze integration test coverage"""
        print("Analyzing Integration Test Coverage...")
        
        # Read integration test results if available
        integration_report_path = os.path.join(self.project_root, "integration_test_report.json")
        
        if os.path.exists(integration_report_path):
            with open(integration_report_path, 'r') as f:
                integration_data = json.load(f)
            
            summary = integration_data.get("summary", {})
            total_tests = summary.get("total_passed", 0) + summary.get("total_failed", 0)
            passed_tests = summary.get("total_passed", 0)
            success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            
            self.coverage_data["integration"] = {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": summary.get("total_failed", 0),
                "success_rate": round(success_rate, 2)
            }
            
            print("  - Total integration tests: {}".format(total_tests))
            print("  - Passed: {}".format(passed_tests))
            print("  - Success rate: {:.1f}%".format(success_rate))
        else:
            print("  - No integration test results found")
    
    def generate_recommendations(self):
        """Generate testing recommendations"""
        recommendations = []
        
        backend_coverage = self.coverage_data["backend"]["coverage_percentage"]
        frontend_coverage = self.coverage_data["frontend"]["coverage_percentage"]
        integration_success = self.coverage_data["integration"]["success_rate"]
        
        # Backend recommendations
        if backend_coverage < 70:
            recommendations.append({
                "category": "Backend Testing",
                "priority": "High",
                "description": "Increase backend test coverage to at least 70% (currently {:.1f}%)".format(backend_coverage),
                "action": "Add unit tests for {} untested modules".format(len(self.coverage_data["backend"]["untested_files"]))
            })
        
        # Frontend recommendations
        if frontend_coverage < 60:
            recommendations.append({
                "category": "Frontend Testing", 
                "priority": "High",
                "description": "Increase frontend test coverage to at least 60% (currently {:.1f}%)".format(frontend_coverage),
                "action": "Add component tests for React components"
            })
        
        # Integration recommendations
        if integration_success < 95:
            recommendations.append({
                "category": "Integration Testing",
                "priority": "Medium",
                "description": "Improve integration test success rate (currently {:.1f}%)".format(integration_success),
                "action": "Fix failing integration tests and add more end-to-end scenarios"
            })
        
        # General recommendations
        recommendations.extend([
            {
                "category": "CI/CD",
                "priority": "Medium",
                "description": "Set up automated testing in CI/CD pipeline",
                "action": "Configure GitHub Actions or similar CI system"
            },
            {
                "category": "Code Quality",
                "priority": "Medium", 
                "description": "Add code quality checks and linting",
                "action": "Configure ESLint, Prettier, and pre-commit hooks"
            },
            {
                "category": "Performance Testing",
                "priority": "Low",
                "description": "Add performance and load testing",
                "action": "Implement Lighthouse CI and load testing with tools like Artillery"
            }
        ])
        
        self.coverage_data["recommendations"] = recommendations
    
    def generate_report(self):
        """Generate comprehensive coverage report"""
        print("\nGENERATING COMPREHENSIVE TEST COVERAGE REPORT")
        print("=" * 60)
        
        self.analyze_backend_coverage()
        self.analyze_frontend_coverage()
        self.analyze_integration_coverage()
        self.generate_recommendations()
        
        # Calculate overall score
        backend_score = min(self.coverage_data["backend"]["coverage_percentage"], 100)
        frontend_score = min(self.coverage_data["frontend"]["coverage_percentage"], 100) 
        integration_score = min(self.coverage_data["integration"]["success_rate"], 100)
        
        overall_score = (backend_score + frontend_score + integration_score) / 3
        
        self.coverage_data["overall_score"] = round(overall_score, 2)
        
        # Print summary
        print("\n" + "=" * 60)
        print("COVERAGE REPORT SUMMARY")
        print("=" * 60)
        print("Backend Coverage: {:.1f}%".format(backend_score))
        print("Frontend Coverage: {:.1f}%".format(frontend_score))
        print("Integration Success: {:.1f}%".format(integration_score))
        print("Overall Score: {:.1f}%".format(overall_score))
        
        # Print recommendations
        print("\n" + "=" * 60)
        print("RECOMMENDATIONS")
        print("=" * 60)
        
        high_priority = [r for r in self.coverage_data["recommendations"] if r["priority"] == "High"]
        medium_priority = [r for r in self.coverage_data["recommendations"] if r["priority"] == "Medium"]
        low_priority = [r for r in self.coverage_data["recommendations"] if r["priority"] == "Low"]
        
        for priority, items in [("HIGH PRIORITY", high_priority), ("MEDIUM PRIORITY", medium_priority), ("LOW PRIORITY", low_priority)]:
            if items:
                print("\n{}:".format(priority))
                for item in items:
                    print("  - [{}] {}".format(item["category"], item["description"]))
                    print("    Action: {}".format(item["action"]))
        
        # Save report
        report_file = os.path.join(self.project_root, "comprehensive_test_coverage_report.json")
        with open(report_file, 'w') as f:
            json.dump(self.coverage_data, f, indent=2)
        
        print("\nComprehensive coverage report saved: {}".format(report_file))
        
        return self.coverage_data


def create_ci_configuration():
    """Create CI/CD configuration files"""
    print("\nCREATING CI/CD CONFIGURATION")
    print("=" * 40)
    
    # GitHub Actions workflow
    github_workflow = """name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: autoops_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run backend tests
      run: |
        python tests/test_comprehensive_fixed.py
        python tests/test_dependency_fixes.py
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/autoops_test
        REDIS_URL: redis://localhost:6379/0
    
    - name: Run integration tests
      run: |
        python tests/test_integration_suite.py

  frontend-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: dashboard_ui_v2/package.json
    
    - name: Install frontend dependencies
      run: |
        cd dashboard_ui_v2
        npm ci
    
    - name: Run frontend tests
      run: |
        cd dashboard_ui_v2
        npm run test:ci
    
    - name: Build frontend
      run: |
        cd dashboard_ui_v2
        npm run build

  coverage-report:
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Generate coverage report
      run: |
        python tests/test_coverage_reporter.py
    
    - name: Upload coverage reports
      uses: actions/upload-artifact@v3
      with:
        name: coverage-reports
        path: |
          comprehensive_test_coverage_report.json
          integration_test_report.json
"""
    
    # Create .github/workflows directory if it doesn't exist
    github_dir = os.path.join(project_root, ".github", "workflows")
    if not os.path.exists(github_dir):
        os.makedirs(github_dir)
    
    workflow_file = os.path.join(github_dir, "ci-cd.yml")
    with open(workflow_file, 'w') as f:
        f.write(github_workflow)
    
    print("Created GitHub Actions workflow: {}".format(workflow_file))
    
    # Pre-commit hooks configuration
    precommit_config = """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3
        
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        
  - repo: local
    hooks:
      - id: python-tests
        name: Python Tests
        entry: python tests/test_comprehensive_fixed.py
        language: system
        pass_filenames: false
        
      - id: frontend-tests
        name: Frontend Tests
        entry: bash -c 'cd dashboard_ui_v2 && npm run test:ci'
        language: system
        pass_filenames: false
"""
    
    precommit_file = os.path.join(project_root, ".pre-commit-config.yaml")
    with open(precommit_file, 'w') as f:
        f.write(precommit_config)
    
    print("Created pre-commit configuration: {}".format(precommit_file))


def main():
    """Main function"""
    print("TEST COVERAGE REPORTING AND CI INTEGRATION")
    print("=" * 60)
    
    # Generate coverage report
    reporter = TestCoverageReporter()
    coverage_data = reporter.generate_report()
    
    # Create CI configuration
    create_ci_configuration()
    
    print("\n" + "=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    print("- Comprehensive test coverage analysis completed")
    print("- CI/CD pipeline configuration created") 
    print("- Pre-commit hooks configured")
    print("- Coverage reports generated")
    
    # Final score assessment
    overall_score = coverage_data.get("overall_score", 0)
    
    if overall_score >= 80:
        grade = "A"
        status = "Excellent"
    elif overall_score >= 70:
        grade = "B"
        status = "Good"
    elif overall_score >= 60:
        grade = "C"
        status = "Acceptable"
    elif overall_score >= 50:
        grade = "D"
        status = "Needs Improvement"
    else:
        grade = "F"
        status = "Critical"
    
    print("\nOVERALL TESTING GRADE: {} ({})".format(grade, status))
    print("Score: {:.1f}/100".format(overall_score))
    
    return coverage_data


if __name__ == "__main__":
    main()