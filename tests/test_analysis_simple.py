"""
Simple Test Coverage Analysis
============================

Basic analysis of the codebase for test coverage without complex dependencies.
"""

import os
import sys
import json
import glob
import ast

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def analyze_codebase():
    """Analyze the codebase for test coverage"""
    print("=" * 60)
    print("CODEBASE ANALYSIS")
    print("=" * 60)
    
    ai_engine_dir = os.path.join(project_root, "ai_engine")
    test_dir = os.path.join(project_root, "tests")
    
    # Count Python files
    py_files = []
    for root, dirs, files in os.walk(ai_engine_dir):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                py_files.append(os.path.join(root, file))
    
    print("Python Files Found: {}".format(len(py_files)))
    
    # Count functions and classes
    total_functions = 0
    total_classes = 0
    complex_modules = []
    
    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            
            total_functions += len(functions)
            total_classes += len(classes)
            
            complexity = len(functions) + len(classes) * 2
            if complexity > 5:
                relative_path = os.path.relpath(py_file, project_root)
                complex_modules.append((relative_path, complexity, len(functions), len(classes)))
                
        except Exception as e:
            print("Warning: Could not analyze {}".format(py_file))
    
    print("Total Functions: {}".format(total_functions))
    print("Total Classes: {}".format(total_classes))
    
    # Count test files
    test_files = []
    if os.path.exists(test_dir):
        for file in os.listdir(test_dir):
            if file.startswith('test_') and file.endswith('.py'):
                test_files.append(file)
    
    print("Test Files: {}".format(len(test_files)))
    
    # Simple coverage estimate
    coverage_estimate = min(100, (len(test_files) / max(1, len(py_files))) * 100)
    print("Estimated Coverage: {:.1f}%".format(coverage_estimate))
    
    # Show complex modules
    print("\nTop Complex Modules:")
    complex_modules.sort(key=lambda x: x[1], reverse=True)
    for module, complexity, funcs, classes in complex_modules[:10]:
        print("  - {} (complexity: {}, functions: {}, classes: {})".format(
            module, complexity, funcs, classes))
    
    return {
        'total_files': len(py_files),
        'total_functions': total_functions,
        'total_classes': total_classes,
        'test_files': len(test_files),
        'coverage_estimate': coverage_estimate,
        'complex_modules': len(complex_modules)
    }

def run_basic_tests():
    """Run basic import tests"""
    print("\n" + "=" * 60)
    print("BASIC FUNCTIONAL TESTS")
    print("=" * 60)
    
    test_results = {"passed": 0, "failed": 0, "skipped": 0}
    
    # Test 1: Environment validator
    try:
        from ai_engine.utils.env_validator import EnvValidator
        validator = EnvValidator()
        test_results["passed"] += 1
        print("PASSED: Environment validator import")
    except ImportError:
        test_results["skipped"] += 1
        print("SKIPPED: Environment validator not available")
    except Exception as e:
        test_results["failed"] += 1
        print("FAILED: Environment validator error - {}".format(e))
    
    # Test 2: Database configuration
    try:
        from ai_engine.database import DATABASE_URL
        if DATABASE_URL:
            test_results["passed"] += 1
            print("PASSED: Database configuration")
        else:
            test_results["failed"] += 1
            print("FAILED: Database URL not configured")
    except Exception as e:
        test_results["failed"] += 1
        print("FAILED: Database configuration error - {}".format(e))
    
    # Test 3: Main app
    try:
        from ai_engine.main import app
        if app:
            test_results["passed"] += 1
            print("PASSED: Main app import")
        else:
            test_results["failed"] += 1
            print("FAILED: Main app not initialized")
    except Exception as e:
        test_results["failed"] += 1
        print("FAILED: Main app error - {}".format(e))
    
    # Test 4: Workflow models
    try:
        from ai_engine.models.workflow import Workflow
        test_results["passed"] += 1
        print("PASSED: Workflow model import")
    except Exception as e:
        test_results["failed"] += 1
        print("FAILED: Workflow model error - {}".format(e))
    
    # Test 5: Task models
    try:
        from ai_engine.models.task import Task
        test_results["passed"] += 1
        print("PASSED: Task model import")
    except Exception as e:
        test_results["failed"] += 1
        print("FAILED: Task model error - {}".format(e))
    
    total = test_results["passed"] + test_results["failed"] + test_results["skipped"]
    success_rate = (test_results["passed"] / max(1, total)) * 100
    
    print("\nTest Summary:")
    print("  Total: {}".format(total))
    print("  Passed: {}".format(test_results["passed"]))
    print("  Failed: {}".format(test_results["failed"]))
    print("  Skipped: {}".format(test_results["skipped"]))
    print("  Success Rate: {:.1f}%".format(success_rate))
    
    return test_results

def analyze_frontend():
    """Analyze frontend components"""
    print("\n" + "=" * 60)
    print("FRONTEND ANALYSIS")
    print("=" * 60)
    
    frontend_dir = os.path.join(project_root, "dashboard_ui_v2")
    
    if not os.path.exists(frontend_dir):
        print("Frontend directory not found")
        return
    
    # Count files
    js_files = []
    ts_files = []
    test_files = []
    
    for root, dirs, files in os.walk(frontend_dir):
        for file in files:
            if file.endswith('.js') or file.endswith('.jsx'):
                js_files.append(file)
            elif file.endswith('.ts') or file.endswith('.tsx'):
                ts_files.append(file)
            elif '.test.' in file or '.spec.' in file:
                test_files.append(file)
    
    print("JavaScript files: {}".format(len(js_files)))
    print("TypeScript files: {}".format(len(ts_files)))
    print("Test files: {}".format(len(test_files)))
    
    total_source = len(js_files) + len(ts_files)
    if total_source > 0:
        frontend_coverage = (len(test_files) / total_source) * 100
        print("Frontend test coverage: {:.1f}%".format(frontend_coverage))
    
    # Check package.json
    package_file = os.path.join(frontend_dir, "package.json")
    if os.path.exists(package_file):
        try:
            with open(package_file, 'r') as f:
                package_data = json.load(f)
            print("Package: {}".format(package_data.get('name', 'unknown')))
            print("Dependencies: {}".format(len(package_data.get('dependencies', {}))))
        except Exception as e:
            print("Error reading package.json: {}".format(e))

def main():
    """Main analysis function"""
    print("COMPREHENSIVE TEST AND COVERAGE ANALYSIS")
    print("=" * 60)
    
    # Analyze codebase
    analysis = analyze_codebase()
    
    # Run basic tests
    test_results = run_basic_tests()
    
    # Analyze frontend
    analyze_frontend()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    print("Backend Files: {}".format(analysis['total_files']))
    print("Backend Functions: {}".format(analysis['total_functions']))
    print("Backend Classes: {}".format(analysis['total_classes']))
    print("Test Files: {}".format(analysis['test_files']))
    print("Backend Coverage: {:.1f}%".format(analysis['coverage_estimate']))
    print("Complex Modules: {}".format(analysis['complex_modules']))
    
    success_rate = (test_results["passed"] / max(1, sum(test_results.values()))) * 100
    print("Functional Test Success: {:.1f}%".format(success_rate))
    
    # Save report
    report = {
        "timestamp": "2025-01-10",
        "backend_files": analysis['total_files'],
        "backend_functions": analysis['total_functions'],
        "backend_classes": analysis['total_classes'],
        "test_files": analysis['test_files'],
        "backend_coverage": analysis['coverage_estimate'],
        "complex_modules": analysis['complex_modules'],
        "functional_test_success": success_rate
    }
    
    report_file = os.path.join(project_root, "test_coverage_report.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print("\nReport saved to: {}".format(report_file))
    
    # Recommendations
    print("\nRecommendations:")
    if analysis['coverage_estimate'] < 70:
        print("  - Increase test coverage (currently {:.1f}%)".format(analysis['coverage_estimate']))
    if analysis['complex_modules'] > 10:
        print("  - Add tests for {} complex modules".format(analysis['complex_modules']))
    if success_rate < 100:
        print("  - Fix {} failing functional tests".format(test_results["failed"]))
    
    return report

if __name__ == "__main__":
    main()