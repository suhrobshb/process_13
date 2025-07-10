"""
Test Coverage Analysis and Functional Testing
============================================

Analyzes the codebase for test coverage and runs functional tests.
"""

import os
import sys
import importlib
import inspect
try:
    from pathlib import Path
except ImportError:
    # Python 2 compatibility
    import os
    class Path:
        def __init__(self, path):
            self.path = str(path)
        def __str__(self):
            return self.path
        def __truediv__(self, other):
            return Path(os.path.join(self.path, str(other)))
        def exists(self):
            return os.path.exists(self.path)
        def relative_to(self, other):
            return Path(os.path.relpath(self.path, str(other)))
        def rglob(self, pattern):
            import glob
            return [Path(p) for p in glob.glob(os.path.join(self.path, "**", pattern), recursive=True)]
        def glob(self, pattern):
            import glob
            return [Path(p) for p in glob.glob(os.path.join(self.path, pattern))]
        @property
        def stem(self):
            return os.path.splitext(os.path.basename(self.path))[0]
        @property
        def name(self):
            return os.path.basename(self.path)
        parent = property(lambda self: Path(os.path.dirname(self.path)))
try:
    from unittest.mock import Mock, patch
except ImportError:
    try:
        from mock import Mock, patch
    except ImportError:
        # Simple mock implementations
        class Mock:
            def __init__(self, *args, **kwargs):
                pass
            def __call__(self, *args, **kwargs):
                return self
            def __getattr__(self, name):
                return Mock()
            def return_value(self, val):
                return val
        
        class patch:
            def __init__(self, target, return_value=None):
                self.target = target
                self.return_value = return_value
            def __enter__(self):
                return Mock()
            def __exit__(self, *args):
                pass
import json
try:
    from typing import Dict, List, Any
except ImportError:
    # Python 2 compatibility
    Dict = dict
    List = list
    Any = object

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class CodebaseAnalyzer:
    """Analyzes the codebase for testing opportunities"""
    
    def __init__(self):
        self.project_root = project_root
        self.ai_engine_dir = Path(os.path.join(str(self.project_root), "ai_engine"))
        self.test_dir = Path(os.path.join(str(self.project_root), "tests"))
        
        self.analysis = {
            "total_python_files": 0,
            "total_functions": 0,
            "total_classes": 0,
            "tested_modules": 0,
            "coverage_estimate": 0.0,
            "modules": {},
            "test_files": {},
            "missing_tests": []
        }
    
    def analyze_codebase(self):
        """Analyze the entire codebase"""
        print("Analyzing codebase for test coverage...")
        
        # Analyze source code
        self._analyze_source_files()
        
        # Analyze test files
        self._analyze_test_files()
        
        # Calculate coverage estimates
        self._calculate_coverage()
        
        return self.analysis
    
    def _analyze_source_files(self):
        """Analyze source Python files"""
        for py_file in self.ai_engine_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
                
            try:
                module_info = self._analyze_module(py_file)
                if module_info:
                    self.analysis["modules"][str(py_file.relative_to(self.project_root))] = module_info
                    self.analysis["total_python_files"] += 1
                    self.analysis["total_functions"] += module_info["function_count"]
                    self.analysis["total_classes"] += module_info["class_count"]
                    
            except Exception as e:
                print("WARNING: Could not analyze {}: {}".format(py_file, e))
    
    def _analyze_module(self, py_file):
        """Analyze a single Python module"""
        try:
            # Read file content
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count functions and classes using AST
            import ast
            tree = ast.parse(content)
            
            functions = []
            classes = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "args": len(node.args.args)
                    })
                elif isinstance(node, ast.ClassDef):
                    class_methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            class_methods.append(item.name)
                    
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": class_methods
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    else:
                        imports.append(node.module)
            
            return {
                "file_path": str(py_file),
                "lines_of_code": len(content.split('\n')),
                "function_count": len(functions),
                "class_count": len(classes),
                "functions": functions,
                "classes": classes,
                "imports": list(set(filter(None, imports))),
                "complexity_score": len(functions) + len(classes) * 2
            }
            
        except Exception as e:
            return None
    
    def _analyze_test_files(self):
        """Analyze existing test files"""
        if not self.test_dir.exists():
            return
            
        for test_file in self.test_dir.glob("test_*.py"):
            try:
                module_info = self._analyze_module(test_file)
                if module_info:
                    self.analysis["test_files"][str(test_file.relative_to(self.project_root))] = module_info
                    
            except Exception as e:
                print("WARNING: Could not analyze test file {}: {}".format(test_file, e))
    
    def _calculate_coverage(self):
        """Calculate estimated test coverage"""
        total_modules = len(self.analysis["modules"])
        test_coverage_hints = 0
        
        # Check which modules might have tests
        for module_path, module_info in self.analysis["modules"].items():
            module_name = Path(module_path).stem
            
            # Check if there are test files that might cover this module
            has_test = any(
                module_name in test_path or 
                any(func["name"].replace("test_", "") in module_name for func in test_info.get("functions", []))
                for test_path, test_info in self.analysis["test_files"].items()
            )
            
            if has_test:
                test_coverage_hints += 1
        
        # Estimate coverage
        if total_modules > 0:
            self.analysis["coverage_estimate"] = (test_coverage_hints / total_modules) * 100
            self.analysis["tested_modules"] = test_coverage_hints
        
        # Identify modules without tests
        for module_path, module_info in self.analysis["modules"].items():
            module_name = Path(module_path).stem
            
            has_specific_test = any(
                module_name in test_path for test_path in self.analysis["test_files"].keys()
            )
            
            if not has_specific_test and module_info["complexity_score"] > 3:
                self.analysis["missing_tests"].append({
                    "module": module_path,
                    "complexity": module_info["complexity_score"],
                    "functions": module_info["function_count"],
                    "classes": module_info["class_count"]
                })
    
    def print_analysis(self):
        """Print detailed analysis"""
        analysis = self.analysis
        
        print("\n" + "=" * 60)
        print("CODEBASE ANALYSIS REPORT")
        print("=" * 60)
        
        print("Overall Statistics:")
        print("   - Python files: {}".format(analysis['total_python_files']))
        print("   - Total functions: {}".format(analysis['total_functions']))
        print("   - Total classes: {}".format(analysis['total_classes']))
        print("   - Test files: {}".format(len(analysis['test_files'])))
        print("   - Estimated coverage: {:.1f}%".format(analysis['coverage_estimate']))
        
        print("\nCoverage Analysis:")
        print("   - Modules with tests: {}/{}".format(analysis['tested_modules'], len(analysis['modules'])))
        print("   - Missing test coverage: {} modules".format(len(analysis['missing_tests'])))
        
        if analysis['missing_tests']:
            print("\nModules needing tests (complexity > 3):")
            for module in sorted(analysis['missing_tests'], key=lambda x: x['complexity'], reverse=True)[:10]:
                print("   - {} (complexity: {}, functions: {}, classes: {})".format(
                    module['module'], module['complexity'], module['functions'], module['classes']))
        
        print("\nTop Complex Modules:")
        complex_modules = [(path, info) for path, info in analysis['modules'].items()]
        complex_modules.sort(key=lambda x: x[1]['complexity_score'], reverse=True)
        
        for path, info in complex_modules[:5]:
            print("   - {} (complexity: {}, functions: {}, classes: {})".format(
                path, info['complexity_score'], info['function_count'], info['class_count']))
        
        print("\nExisting Test Files:")
        for test_path, test_info in analysis['test_files'].items():
            print("   - {} ({} tests)".format(test_path, test_info['function_count']))


class FunctionalTester:
    """Runs functional tests on core components"""
    
    def __init__(self):
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "test_details": []
        }
    
    def run_functional_tests(self):
        """Run functional tests on importable modules"""
        print("\nRunning Functional Tests...")
        
        test_methods = [
            self.test_environment_validation,
            self.test_redis_client_mock,
            self.test_email_handler_mock,
            self.test_circuit_breaker_logic,
            self.test_database_configuration,
            self.test_workflow_components,
            self.test_api_structure,
            self.test_security_components,
            self.test_monitoring_components
        ]
        
        for test_method in test_methods:
            self.run_test(test_method)
        
        return self.test_results
    
    def run_test(self, test_method):
        """Run a single test method"""
        test_name = test_method.__name__
        self.test_results["total_tests"] += 1
        
        try:
            result = test_method()
            if result.get("skipped"):
                self.test_results["skipped_tests"] += 1
                print("  SKIPPED {}: {}".format(test_name, result.get('reason', 'Skipped')))
            else:
                self.test_results["passed_tests"] += 1
                print("  PASSED {}".format(test_name))
            
            self.test_results["test_details"].append({
                "name": test_name,
                "status": "skipped" if result.get("skipped") else "passed",
                "details": result
            })
            
        except Exception as e:
            self.test_results["failed_tests"] += 1
            print("  FAILED {}: {}".format(test_name, str(e)))
            
            self.test_results["test_details"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e)
            })
    
    def test_environment_validation(self):
        """Test environment validation functionality"""
        try:
            from ai_engine.utils.env_validator import EnvValidator, validate_environment
            
            validator = EnvValidator()
            results = validate_environment()
            
            assert isinstance(results, dict)
            assert "valid" in results
            assert "errors" in results
            
            return {"status": "Environment validation works"}
            
        except ImportError:
            return {"skipped": True, "reason": "Environment validator not available"}
    
    def test_redis_client_mock(self):
        """Test Redis client with mocking"""
        with patch('redis.Redis') as mock_redis:
            mock_instance = Mock()
            mock_instance.ping.return_value = True
            mock_redis.return_value = mock_instance
            
            try:
                from ai_engine.utils.redis_client import RedisClient
                
                client = RedisClient()
                assert client._connected == True
                
                return {"status": "Redis client logic works"}
                
            except ImportError:
                return {"skipped": True, "reason": "Redis client not available"}
    
    def test_email_handler_mock(self):
        """Test email handler with mocking"""
        with patch('smtplib.SMTP'):
            try:
                from integrations.communication_module.email_handler import EmailHandler
                
                # Test without config
                handler = EmailHandler()
                assert hasattr(handler, 'configured')
                
                # Test with config
                handler = EmailHandler(
                    smtp_server="test.com",
                    smtp_port=587,
                    username="test@test.com",
                    password="test_pass"
                )
                assert handler.configured == True
                
                return {"status": "Email handler logic works"}
                
            except ImportError:
                return {"skipped": True, "reason": "Email handler not available"}
    
    def test_circuit_breaker_logic(self):
        """Test circuit breaker logic"""
        try:
            from ai_engine.utils.circuit_breaker import CircuitBreaker, CircuitBreakerManager
            
            # Test basic circuit breaker
            breaker = CircuitBreaker("test", max_failures=2, reset_timeout=1)
            assert breaker.state == "closed"
            
            # Test failure tracking
            breaker.record_failure()
            breaker.record_failure()
            assert breaker.state == "open"
            
            # Test manager
            manager = CircuitBreakerManager()
            test_func = lambda: "success"
            result = manager.call("test_service", test_func)
            assert result == "success"
            
            return {"status": "Circuit breaker logic works"}
            
        except ImportError:
            return {"skipped": True, "reason": "Circuit breaker not available"}
    
    def test_database_configuration(self):
        """Test database configuration"""
        try:
            from ai_engine.database import DATABASE_URL, engine
            
            assert isinstance(DATABASE_URL, str)
            assert len(DATABASE_URL) > 0
            assert engine is not None
            
            return {"status": "Database configuration works"}
            
        except ImportError:
            return {"skipped": True, "reason": "Database configuration not available"}
    
    def test_workflow_components(self):
        """Test workflow-related components"""
        try:
            # Test workflow models
            from ai_engine.models.workflow import Workflow
            from ai_engine.models.execution import Execution
            
            assert Workflow is not None
            assert Execution is not None
            
            return {"status": "Workflow components available"}
            
        except ImportError:
            return {"skipped": True, "reason": "Workflow components not available"}
    
    def test_api_structure(self):
        """Test API application structure"""
        try:
            # Test that FastAPI app can be imported
            from ai_engine.main import app
            
            assert app is not None
            assert hasattr(app, 'routes')
            assert len(app.routes) > 0
            
            return {"status": "API structure works", "routes": len(app.routes)}
            
        except ImportError as e:
            return {"skipped": True, "reason": "API not available: {}".format(e)}
    
    def test_security_components(self):
        """Test security-related components"""
        try:
            from ai_engine.utils.secrets_manager import SecretsManager
            
            # Test basic initialization
            manager = SecretsManager()
            assert manager is not None
            
            return {"status": "Security components available"}
            
        except ImportError:
            return {"skipped": True, "reason": "Security components not available"}
    
    def test_monitoring_components(self):
        """Test monitoring and metrics components"""
        try:
            from ai_engine.metrics_instrumentation import MetricsInstrumentation
            
            metrics = MetricsInstrumentation()
            assert metrics is not None
            
            return {"status": "Monitoring components available"}
            
        except ImportError:
            return {"skipped": True, "reason": "Monitoring components not available"}
    
    def print_results(self):
        """Print test results summary"""
        results = self.test_results
        
        print("\n" + "=" * 60)
        print("FUNCTIONAL TEST RESULTS")
        print("=" * 60)
        
        total = results["total_tests"]
        passed = results["passed_tests"]
        failed = results["failed_tests"]
        skipped = results["skipped_tests"]
        
        print("Test Summary:")
        print("   - Total tests: {}".format(total))
        print("   - Passed: {}".format(passed))
        print("   - Failed: {}".format(failed))
        print("   - Skipped: {}".format(skipped))
        
        if total > 0:
            success_rate = (passed / total) * 100
            print("   - Success rate: {:.1f}%".format(success_rate))
        
        if failed > 0:
            print("\nFailed Tests:")
            for test in results["test_details"]:
                if test["status"] == "failed":
                    print("   - {}: {}".format(test['name'], test.get('error', 'Unknown error')))


def run_frontend_analysis():
    """Analyze frontend components"""
    print("\nFrontend Analysis...")
    
    frontend_dir = Path(os.path.join(str(project_root), "dashboard_ui_v2"))
    
    if not frontend_dir.exists():
        print("   WARNING: Frontend directory not found")
        return
    
    # Check package.json
    package_json = Path(os.path.join(str(frontend_dir), "package.json"))
    if package_json.exists():
        try:
            with open(package_json) as f:
                package_data = json.load(f)
            
            print("   - Package: {}".format(package_data.get('name', 'unknown')))
            print("   - Version: {}".format(package_data.get('version', 'unknown')))
            
            deps = package_data.get('dependencies', {})
            dev_deps = package_data.get('devDependencies', {})
            
            print("   - Dependencies: {}".format(len(deps)))
            print("   - Dev Dependencies: {}".format(len(dev_deps)))
            
            # Check for key frontend tech
            if 'react' in deps:
                print("   - React: {}".format(deps['react']))
            if 'next' in deps:
                print("   - Next.js: {}".format(deps['next']))
            if 'typescript' in deps or 'typescript' in dev_deps:
                print("   - TypeScript: Yes")
            
        except Exception as e:
            print("   - Error reading package.json: {}".format(e))
    
    # Check for TypeScript files
    ts_files = list(frontend_dir.rglob("*.ts")) + list(frontend_dir.rglob("*.tsx"))
    js_files = list(frontend_dir.rglob("*.js")) + list(frontend_dir.rglob("*.jsx"))
    
    print("   - TypeScript files: {}".format(len(ts_files)))
    print("   - JavaScript files: {}".format(len(js_files)))
    
    # Check for test files
    test_files = list(frontend_dir.rglob("*.test.*")) + list(frontend_dir.rglob("*.spec.*"))
    print("   - Test files: {}".format(len(test_files)))
    
    if len(ts_files) + len(js_files) > 0:
        test_coverage = len(test_files) / (len(ts_files) + len(js_files)) * 100
        print("   - Estimated test coverage: {:.1f}%".format(test_coverage))


def main():
    """Main analysis function"""
    print("COMPREHENSIVE TEST AND COVERAGE ANALYSIS")
    print("=" * 60)
    
    # Analyze codebase
    analyzer = CodebaseAnalyzer()
    analysis = analyzer.analyze_codebase()
    analyzer.print_analysis()
    
    # Run functional tests
    tester = FunctionalTester()
    test_results = tester.run_functional_tests()
    tester.print_results()
    
    # Analyze frontend
    run_frontend_analysis()
    
    # Overall summary
    print("\n" + "=" * 60)
    print("OVERALL ASSESSMENT")
    print("=" * 60)
    
    backend_coverage = analysis["coverage_estimate"]
    test_success_rate = (test_results["passed_tests"] / test_results["total_tests"]) * 100 if test_results["total_tests"] > 0 else 0
    
    print("Backend Coverage Estimate: {:.1f}%".format(backend_coverage))
    print("Functional Test Success: {:.1f}%".format(test_success_rate))
    print("Total Python Files: {}".format(analysis['total_python_files']))
    print("Total Functions: {}".format(analysis['total_functions']))
    print("Total Classes: {}".format(analysis['total_classes']))
    print("Test Files: {}".format(len(analysis['test_files'])))
    
    # Recommendations
    print("\nRecommendations:")
    
    if backend_coverage < 70:
        print("   - Increase backend test coverage (currently {:.1f}%)".format(backend_coverage))
    
    if test_success_rate < 100:
        print("   - Fix failing functional tests ({} failed)".format(test_results['failed_tests']))
    
    if len(analysis['missing_tests']) > 5:
        print("   - Add unit tests for {} complex modules".format(len(analysis['missing_tests'])))
    
    if analysis['total_functions'] > 200:
        print("   - Consider breaking down large modules ({} functions)".format(analysis['total_functions']))
    
    # Generate test coverage report
    coverage_report = {
        "timestamp": "2025-01-10",
        "backend_coverage_estimate": backend_coverage,
        "functional_test_success_rate": test_success_rate,
        "total_files": analysis['total_python_files'],
        "total_functions": analysis['total_functions'],
        "total_classes": analysis['total_classes'],
        "test_files": len(analysis['test_files']),
        "missing_tests": len(analysis['missing_tests']),
        "recommendations": []
    }
    
    # Save report
    report_file = Path(os.path.join(str(project_root), "test_coverage_report.json"))
    with open(report_file, 'w') as f:
        json.dump(coverage_report, f, indent=2)
    
    print("\nFull report saved to: {}".format(report_file))
    
    return coverage_report


if __name__ == "__main__":
    main()