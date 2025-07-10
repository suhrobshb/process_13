"""
Secure Code Execution System
=============================

This module provides a secure sandbox for executing dynamically generated code.
It uses multiple layers of security:
1. RestrictedPython for safe code compilation
2. Subprocess isolation for execution
3. Resource limits and timeout controls
4. Static code analysis for malicious patterns
5. Allowlist-based import restrictions
"""

import os
import sys
import ast
import subprocess
import tempfile
import json
import time
import signal
import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from contextlib import contextmanager

try:
    from RestrictedPython import compile_restricted, safe_globals, limited_builtins
    from RestrictedPython.Guards import safe_builtins, safe_iter
    from RestrictedPython.transformer import RestrictingNodeTransformer
    RESTRICTED_PYTHON_AVAILABLE = True
except ImportError:
    RESTRICTED_PYTHON_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ExecutionConfig:
    """Configuration for secure code execution"""
    max_execution_time: int = 30  # seconds
    max_memory_mb: int = 256
    allowed_imports: Set[str] = None
    denied_patterns: List[str] = None
    use_subprocess: bool = True
    use_restricted_python: bool = True
    
    def __post_init__(self):
        if self.allowed_imports is None:
            self.allowed_imports = {
                'logging', 'json', 'time', 'datetime', 'math', 'random',
                'ai_engine.enhanced_runners.desktop_runner',
                'ai_engine.enhanced_runners.browser_runner',
                'ai_engine.workflow_runners'
            }
        
        if self.denied_patterns is None:
            self.denied_patterns = [
                r'__import__\s*\(',
                r'eval\s*\(',
                r'exec\s*\(',
                r'open\s*\(',
                r'file\s*\(',
                r'subprocess\.',
                r'os\.',
                r'sys\.',
                r'importlib\.',
                r'\.system\s*\(',
                r'\.popen\s*\(',
                r'\.spawn\s*\(',
                r'socket\.',
                r'urllib\.',
                r'requests\.',
                r'http\.',
                r'ftp\.',
                r'smtplib\.',
                r'telnetlib\.',
                r'pickle\.',
                r'marshal\.',
                r'ctypes\.',
                r'_?_[a-zA-Z]+_?_',  # Dunder methods/attributes
            ]


class SecurityViolationError(Exception):
    """Raised when code violates security policies"""
    pass


class ExecutionTimeoutError(Exception):
    """Raised when code execution times out"""
    pass


class CodeAnalyzer(ast.NodeVisitor):
    """AST-based static code analyzer for security violations"""
    
    def __init__(self, config: ExecutionConfig):
        self.config = config
        self.violations: List[str] = []
        self.imports: Set[str] = set()
        self.function_calls: Set[str] = set()
        
    def visit_Import(self, node):
        """Check import statements"""
        for alias in node.names:
            self.imports.add(alias.name)
            if alias.name not in self.config.allowed_imports:
                self.violations.append(f"Unauthorized import: {alias.name}")
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Check from-import statements"""
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            self.imports.add(full_name)
            
            # Check if the base module is allowed
            base_allowed = any(
                module.startswith(allowed) or allowed.startswith(module)
                for allowed in self.config.allowed_imports
            )
            
            if not base_allowed:
                self.violations.append(f"Unauthorized import: {full_name}")
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Check function calls"""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            self.function_calls.add(func_name)
            
            # Check for dangerous function calls
            dangerous_functions = {
                'eval', 'exec', 'compile', '__import__', 'open', 'file',
                'input', 'raw_input', 'exit', 'quit'
            }
            
            if func_name in dangerous_functions:
                self.violations.append(f"Dangerous function call: {func_name}")
                
        elif isinstance(node.func, ast.Attribute):
            # Check attribute access like os.system, subprocess.call, etc.
            if isinstance(node.func.value, ast.Name):
                obj_name = node.func.value.id
                attr_name = node.func.attr
                call_name = f"{obj_name}.{attr_name}"
                self.function_calls.add(call_name)
                
                dangerous_calls = {
                    'os.system', 'os.popen', 'os.spawn', 'subprocess.call',
                    'subprocess.run', 'subprocess.Popen', 'sys.exit'
                }
                
                if call_name in dangerous_calls:
                    self.violations.append(f"Dangerous method call: {call_name}")
        
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """Check attribute access"""
        if isinstance(node.value, ast.Name):
            attr_access = f"{node.value.id}.{node.attr}"
            
            # Check for dangerous attribute access
            dangerous_attrs = {
                'sys.modules', 'sys.path', 'os.environ', '__globals__',
                '__locals__', '__builtins__', '__code__'
            }
            
            if attr_access in dangerous_attrs:
                self.violations.append(f"Dangerous attribute access: {attr_access}")
        
        self.generic_visit(node)
    
    def analyze(self, code: str) -> Tuple[bool, List[str]]:
        """Analyze code for security violations"""
        try:
            tree = ast.parse(code)
            self.visit(tree)
            
            # Check for pattern-based violations
            for pattern in self.config.denied_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    self.violations.append(f"Denied pattern found: {pattern}")
            
            return len(self.violations) == 0, self.violations
        except SyntaxError as e:
            return False, [f"Syntax error: {e}"]


class SecureExecutor:
    """Secure code executor with multiple security layers"""
    
    def __init__(self, config: ExecutionConfig = None):
        self.config = config or ExecutionConfig()
        self.analyzer = CodeAnalyzer(self.config)
        
        if not RESTRICTED_PYTHON_AVAILABLE and self.config.use_restricted_python:
            logger.warning("RestrictedPython not available, falling back to basic security")
            self.config.use_restricted_python = False
    
    def _create_safe_globals(self) -> Dict[str, Any]:
        """Create a safe globals dictionary for code execution"""
        safe_globals_dict = {
            '__builtins__': {
                # Safe builtins only
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'sorted': sorted,
                'reversed': reversed,
                'any': any,
                'all': all,
                'isinstance': isinstance,
                'issubclass': issubclass,
                'hasattr': hasattr,
                'getattr': getattr,
                'setattr': setattr,
                'print': print,  # Allow print for debugging
            }
        }
        
        # Add safe modules
        import json
        import time
        import datetime
        import math
        import logging
        
        safe_globals_dict.update({
            'json': json,
            'time': time,
            'datetime': datetime,
            'math': math,
            'logging': logging,
        })
        
        return safe_globals_dict
    
    def _validate_code(self, code: str) -> None:
        """Validate code for security violations"""
        # 1. Static analysis
        is_safe, violations = self.analyzer.analyze(code)
        if not is_safe:
            raise SecurityViolationError(f"Code security violations: {violations}")
        
        # 2. Size limits
        if len(code) > 100000:  # 100KB limit
            raise SecurityViolationError("Code size exceeds maximum allowed")
        
        # 3. Line count limits
        lines = code.split('\n')
        if len(lines) > 1000:
            raise SecurityViolationError("Code line count exceeds maximum allowed")
        
        # 4. Basic pattern checks
        dangerous_keywords = ['eval', 'exec', '__import__', 'compile']
        for keyword in dangerous_keywords:
            if keyword in code:
                logger.warning(f"Potentially dangerous keyword found: {keyword}")
    
    def _compile_restricted(self, code: str, filename: str = '<dynamic>') -> Any:
        """Compile code using RestrictedPython"""
        if not RESTRICTED_PYTHON_AVAILABLE:
            # Fallback to regular compilation with validation
            self._validate_code(code)
            return compile(code, filename, 'exec')
        
        # Use RestrictedPython for safe compilation
        compiled = compile_restricted(code, filename, 'exec')
        if compiled is None:
            raise SecurityViolationError("Code compilation failed - potential security violation")
        
        return compiled
    
    def _execute_in_subprocess(self, code: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute code in an isolated subprocess"""
        context = context or {}
        
        # Create temporary files for communication
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as code_file:
            code_file.write(code)
            code_file_path = code_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as input_file:
            json.dump(context, input_file)
            input_file_path = input_file.name
        
        output_file_path = tempfile.mktemp(suffix='.json')
        
        try:
            # Create wrapper script
            wrapper_script = f'''
import sys
import json
import signal
import resource
import traceback

# Set resource limits
resource.setrlimit(resource.RLIMIT_AS, ({self.config.max_memory_mb * 1024 * 1024}, -1))
resource.setrlimit(resource.RLIMIT_CPU, ({self.config.max_execution_time}, -1))

def timeout_handler(signum, frame):
    raise TimeoutError("Execution timeout")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm({self.config.max_execution_time})

try:
    # Load input context
    with open("{input_file_path}", "r") as f:
        context = json.load(f)
    
    # Load and execute code
    with open("{code_file_path}", "r") as f:
        code_content = f.read()
    
    # Create restricted globals
    restricted_globals = {{
        "__builtins__": {{
            "len": len, "str": str, "int": int, "float": float, "bool": bool,
            "list": list, "dict": dict, "tuple": tuple, "set": set,
            "range": range, "enumerate": enumerate, "zip": zip,
            "print": print, "isinstance": isinstance, "hasattr": hasattr
        }},
        "json": __import__("json"),
        "time": __import__("time"),
        "datetime": __import__("datetime"),
        "math": __import__("math"),
        "logging": __import__("logging"),
    }}
    
    # Execute code
    exec(compile(code_content, "{code_file_path}", "exec"), restricted_globals, context)
    
    # Get result from context (assuming the code modifies context)
    result = {{"success": True, "context": context, "error": None}}
    
except Exception as e:
    result = {{"success": False, "context": {{}}, "error": str(e), "traceback": traceback.format_exc()}}

finally:
    signal.alarm(0)  # Cancel alarm
    
    # Write result
    with open("{output_file_path}", "w") as f:
        json.dump(result, f)
'''
            
            # Execute wrapper script
            process = subprocess.Popen(
                [sys.executable, '-c', wrapper_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=tempfile.gettempdir()
            )
            
            try:
                stdout, stderr = process.communicate(timeout=self.config.max_execution_time + 5)
                
                # Read result
                if os.path.exists(output_file_path):
                    with open(output_file_path, 'r') as f:
                        result = json.load(f)
                else:
                    result = {
                        "success": False,
                        "context": {},
                        "error": "No output produced",
                        "stderr": stderr.decode() if stderr else ""
                    }
                
            except subprocess.TimeoutExpired:
                process.kill()
                raise ExecutionTimeoutError(f"Code execution timed out after {self.config.max_execution_time} seconds")
            
        finally:
            # Cleanup temporary files
            for temp_file in [code_file_path, input_file_path, output_file_path]:
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass
        
        return result
    
    def _execute_restricted(self, code: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute code using RestrictedPython in the current process"""
        context = context or {}
        
        try:
            # Compile with restrictions
            compiled_code = self._compile_restricted(code)
            
            # Create safe execution environment
            safe_globals = self._create_safe_globals()
            safe_locals = context.copy()
            
            # Execute with timeout
            start_time = time.time()
            exec(compiled_code, safe_globals, safe_locals)
            execution_time = time.time() - start_time
            
            if execution_time > self.config.max_execution_time:
                raise ExecutionTimeoutError(f"Execution time {execution_time:.2f}s exceeded limit")
            
            return {
                "success": True,
                "context": safe_locals,
                "error": None,
                "execution_time": execution_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "context": {},
                "error": str(e),
                "execution_time": time.time() - start_time if 'start_time' in locals() else 0
            }
    
    def execute(self, code: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute code securely with configured security measures
        
        Args:
            code: Python code to execute
            context: Initial context dictionary
            
        Returns:
            Dictionary with execution results
        """
        logger.info("Starting secure code execution")
        
        # Validate code first
        self._validate_code(code)
        
        # Choose execution method
        if self.config.use_subprocess:
            logger.info("Executing code in isolated subprocess")
            return self._execute_in_subprocess(code, context)
        else:
            logger.info("Executing code with RestrictedPython")
            return self._execute_restricted(code, context)
    
    def test_code(self, code: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Test code with multiple test cases
        
        Args:
            code: Code to test
            test_cases: List of test case dictionaries with 'input' and 'expected' keys
            
        Returns:
            Dictionary with test results
        """
        results = {
            "total_tests": len(test_cases),
            "passed": 0,
            "failed": 0,
            "errors": [],
            "test_results": []
        }
        
        for i, test_case in enumerate(test_cases):
            try:
                input_context = test_case.get('input', {})
                expected = test_case.get('expected', {})
                
                result = self.execute(code, input_context.copy())
                
                if result['success']:
                    # Check if output matches expected
                    output_context = result['context']
                    passed = all(
                        output_context.get(key) == value
                        for key, value in expected.items()
                    )
                    
                    if passed:
                        results["passed"] += 1
                        results["test_results"].append({
                            "test_id": i,
                            "status": "passed",
                            "input": input_context,
                            "output": output_context,
                            "expected": expected
                        })
                    else:
                        results["failed"] += 1
                        results["test_results"].append({
                            "test_id": i,
                            "status": "failed",
                            "input": input_context,
                            "output": output_context,
                            "expected": expected,
                            "error": "Output did not match expected results"
                        })
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Test {i}: {result['error']}")
                    results["test_results"].append({
                        "test_id": i,
                        "status": "error",
                        "input": input_context,
                        "expected": expected,
                        "error": result['error']
                    })
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Test {i}: {str(e)}")
                results["test_results"].append({
                    "test_id": i,
                    "status": "error",
                    "input": test_case.get('input', {}),
                    "expected": test_case.get('expected', {}),
                    "error": str(e)
                })
        
        results["success_rate"] = results["passed"] / results["total_tests"] if results["total_tests"] > 0 else 0
        
        return results


# Convenience functions
def execute_secure(code: str, context: Dict[str, Any] = None, config: ExecutionConfig = None) -> Dict[str, Any]:
    """Execute code securely with default configuration"""
    executor = SecureExecutor(config)
    return executor.execute(code, context)


def validate_code_security(code: str, config: ExecutionConfig = None) -> Tuple[bool, List[str]]:
    """Validate code for security violations without executing it"""
    config = config or ExecutionConfig()
    analyzer = CodeAnalyzer(config)
    return analyzer.analyze(code)


# Example usage
if __name__ == "__main__":
    # Test the secure executor
    test_code = '''
# Safe code example
result = sum(range(10))
message = f"The sum is: {result}"
output = {"result": result, "message": message}
'''
    
    executor = SecureExecutor()
    result = executor.execute(test_code)
    print("Execution result:", result)
    
    # Test security validation
    malicious_code = '''
import os
os.system("rm -rf /")  # This should be blocked
'''
    
    is_safe, violations = validate_code_security(malicious_code)
    print(f"Is malicious code safe: {is_safe}")
    print(f"Violations: {violations}")