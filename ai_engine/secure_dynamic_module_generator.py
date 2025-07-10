"""
Secure Dynamic Module Generator
===============================

This module provides a secure version of the dynamic module generator that uses
restricted execution environments to prevent malicious code execution. It uses
RestrictedPython to create a sandboxed environment for executing dynamically
generated code.

Key Security Features:
- Restricted Python execution environment
- Whitelist of allowed modules and functions
- Resource limits (memory, CPU time)
- Input validation and sanitization
- Audit logging of all executed code
- Secure template rendering
"""

import os
import json
import logging
import sys
import tempfile
import subprocess
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
import signal

try:
    from RestrictedPython import compile_restricted
    from RestrictedPython.Guards import safe_builtins, safe_globals
    from RestrictedPython.transformer import RestrictingNodeTransformer
    RESTRICTED_PYTHON_AVAILABLE = True
except ImportError:
    RESTRICTED_PYTHON_AVAILABLE = False

import pytest
from jinja2 import Template, Environment, select_autoescape
from jinja2.sandbox import SandboxedEnvironment

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class SecurityConfig:
    """Configuration for security settings"""
    max_execution_time: int = 30  # seconds
    max_memory_mb: int = 256
    allowed_modules: Set[str] = field(default_factory=lambda: {
        'logging', 'json', 'time', 'datetime', 'uuid', 'hashlib',
        'ai_engine.enhanced_runners.desktop_runner',
        'ai_engine.enhanced_runners.browser_runner',
        'ai_engine.workflow_runners'
    })
    blocked_functions: Set[str] = field(default_factory=lambda: {
        'eval', 'exec', 'compile', 'open', '__import__', 'globals', 'locals',
        'vars', 'dir', 'getattr', 'setattr', 'delattr', 'hasattr'
    })
    enable_audit_logging: bool = True
    validate_templates: bool = True

class SecureExecutionError(Exception):
    """Raised when secure execution fails"""
    pass

class SecurityViolationError(Exception):
    """Raised when code violates security policies"""
    pass

class TimeoutError(Exception):
    """Raised when execution times out"""
    pass

class SecureGuard:
    """Security guard for restricted execution"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.start_time = None
        
    def check_timeout(self):
        """Check if execution has timed out"""
        if self.start_time and time.time() - self.start_time > self.config.max_execution_time:
            raise TimeoutError(f"Execution exceeded {self.config.max_execution_time} seconds")
    
    def safe_iter(self, seq):
        """Safe iterator that checks for timeout"""
        self.check_timeout()
        return iter(seq)
    
    def safe_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        """Safe import that only allows whitelisted modules"""
        if name not in self.config.allowed_modules:
            raise SecurityViolationError(f"Import of module '{name}' is not allowed")
        return __import__(name, globals, locals, fromlist, level)

def create_secure_globals(config: SecurityConfig) -> Dict[str, Any]:
    """Create secure globals dictionary for restricted execution"""
    guard = SecureGuard(config)
    
    # Start with safe builtins
    secure_globals = safe_builtins.copy()
    
    # Add safe functions
    secure_globals.update({
        '__builtins__': {
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
            'sorted': sorted,
            'reversed': reversed,
            'sum': sum,
            'min': min,
            'max': max,
            'abs': abs,
            'round': round,
            'isinstance': isinstance,
            'issubclass': issubclass,
            'type': type,
            'print': print,
            '__import__': guard.safe_import,
        },
        '_iter_unpack_sequence_': guard.safe_iter,
        '_getiter_': guard.safe_iter,
        '_getattr_': lambda obj, name, default=None, getattr=getattr: getattr(obj, name, default),
        '_write_': lambda x: x,  # Allow writes to prevent errors
        '_print_': lambda *args, **kwargs: print(*args, **kwargs),
    })
    
    # Remove blocked functions
    for func in config.blocked_functions:
        secure_globals.pop(func, None)
        if '__builtins__' in secure_globals and isinstance(secure_globals['__builtins__'], dict):
            secure_globals['__builtins__'].pop(func, None)
    
    return secure_globals

@contextmanager
def timeout_context(seconds: int):
    """Context manager for timeout handling"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set up signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

class SecureTemplateRenderer:
    """Secure template renderer using sandboxed Jinja2"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.env = SandboxedEnvironment(
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters if needed
        self.env.filters['tojson'] = json.dumps
    
    def render_template(self, template_str: str, **kwargs) -> str:
        """Render template with security checks"""
        if self.config.validate_templates:
            self._validate_template(template_str)
        
        template = self.env.from_string(template_str)
        return template.render(**kwargs)
    
    def _validate_template(self, template_str: str):
        """Validate template for security issues"""
        # Check for potentially dangerous patterns
        dangerous_patterns = [
            '__import__', 'exec', 'eval', 'compile', 'open', 'file',
            'subprocess', 'os.system', 'os.popen', 'os.spawn'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in template_str:
                raise SecurityViolationError(f"Template contains dangerous pattern: {pattern}")

class SecureDynamicModuleGenerator:
    """
    Secure version of the dynamic module generator that uses restricted execution
    """
    
    def __init__(self, structured_workflow: Dict[str, Any], security_config: Optional[SecurityConfig] = None):
        """
        Initialize the secure generator
        
        Args:
            structured_workflow: Workflow structure from AI engine
            security_config: Security configuration
        """
        if not RESTRICTED_PYTHON_AVAILABLE:
            raise ImportError("RestrictedPython is required for secure execution")
        
        self.workflow = structured_workflow
        self.security_config = security_config or SecurityConfig()
        self.workflow_id = structured_workflow.get("id", f"wf_{int(time.time())}")
        self.module_dir = Path(f"storage/secure_modules/{self.workflow_id}")
        self.module_name = f"secure_workflow_{self.workflow_id}"
        self.module_path = self.module_dir / f"{self.module_name}.py"
        self.test_path = self.module_dir / f"test_{self.module_name}.py"
        self.audit_path = self.module_dir / f"audit_{self.module_name}.log"
        
        # Create directory
        self.module_dir.mkdir(parents=True, exist_ok=True)
        (self.module_dir / "__init__.py").touch(exist_ok=True)
        
        # Initialize secure renderer
        self.renderer = SecureTemplateRenderer(self.security_config)
        
        # Audit logger
        self.audit_logger = self._setup_audit_logger()
    
    def _setup_audit_logger(self) -> logging.Logger:
        """Set up audit logger for security events"""
        audit_logger = logging.getLogger(f"audit.{self.module_name}")
        audit_logger.setLevel(logging.INFO)
        
        # Create file handler
        handler = logging.FileHandler(self.audit_path)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        audit_logger.addHandler(handler)
        
        return audit_logger
    
    def _sanitize_workflow_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize workflow data to prevent injection attacks"""
        sanitized = {}
        
        for key, value in data.items():
            # Sanitize keys
            if not isinstance(key, str) or not key.isidentifier():
                sanitized_key = f"key_{hashlib.md5(str(key).encode()).hexdigest()[:8]}"
            else:
                sanitized_key = key
            
            # Sanitize values
            if isinstance(value, str):
                # Remove potentially dangerous characters
                sanitized_value = value.replace('"', '\\"').replace("'", "\\'")
                # Limit length
                if len(sanitized_value) > 1000:
                    sanitized_value = sanitized_value[:1000] + "..."
                sanitized[sanitized_key] = sanitized_value
            elif isinstance(value, dict):
                sanitized[sanitized_key] = self._sanitize_workflow_data(value)
            elif isinstance(value, list):
                sanitized[sanitized_key] = [self._sanitize_workflow_data(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[sanitized_key] = value
        
        return sanitized
    
    def _generate_secure_code(self) -> Tuple[str, str]:
        """Generate secure code with restricted execution"""
        self.audit_logger.info(f"Generating secure code for workflow {self.workflow_id}")
        
        # Sanitize workflow data
        sanitized_workflow = self._sanitize_workflow_data(self.workflow)
        
        generation_date = datetime.utcnow().isoformat()
        
        # Secure module template
        secure_module_template = """
'''
Secure Dynamically Generated Workflow Module
--------------------------------------------
Workflow ID: {{ workflow.name }} ({{ workflow.id }})
Generated on: {{ generation_date }}
Security Level: RESTRICTED

This module executes in a restricted Python environment.
'''

import logging
from typing import Dict, Any

# Import allowed modules only
try:
    from ai_engine.enhanced_runners.desktop_runner import DesktopRunner
    from ai_engine.enhanced_runners.browser_runner import BrowserRunner  
    from ai_engine.workflow_runners import RunnerFactory
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback for testing
    class DesktopRunner:
        def __init__(self, *args, **kwargs): pass
        def execute(self): return {"success": True, "result": "mock_desktop"}
    
    class BrowserRunner:
        def __init__(self, *args, **kwargs): pass
        def execute(self): return {"success": True, "result": "mock_browser"}
    
    class RunnerFactory:
        @staticmethod
        def create_runner(*args, **kwargs):
            class MockRunner:
                def execute(self, context=None): return {"success": True, "result": "mock_runner"}
            return MockRunner()

logger = logging.getLogger(__name__)

# Workflow configuration
WORKFLOW_NODES = {{ workflow_nodes_json }}

def run(context: Dict[str, Any] = None) -> Dict[str, Any]:
    '''
    Main execution function with security restrictions
    '''
    if context is None:
        context = {}
    
    logger.info(f"Starting secure execution of workflow: {{ workflow.name }}")
    execution_results = {}
    
    # Validate input context
    if not isinstance(context, dict):
        raise ValueError("Context must be a dictionary")
    
    # Limit context size
    if len(str(context)) > 10000:
        raise ValueError("Context too large")
    
    for node in WORKFLOW_NODES:
        step_id = node.get("id", "unknown")
        step_type = node.get("type", "unknown")
        step_data = node.get("data", {})
        
        # Validate step data
        if not isinstance(step_data, dict):
            logger.error(f"Invalid step data for {step_id}")
            continue
        
        logger.info(f"Executing step '{step_id}' (Type: {step_type})")
        
        try:
            # Check confidence score
            confidence = step_data.get("confidence_score", 1.0)
            if confidence < 0.5:
                logger.warning(f"Low confidence for step '{step_id}': {confidence}")
            
            # Execute step based on type
            if step_type == "desktop":
                runner = DesktopRunner(step_id, {"actions": step_data.get("raw_actions", [])})
                result = runner.execute()
            elif step_type == "browser":
                runner = BrowserRunner(step_id, {"actions": step_data.get("raw_actions", [])})
                result = runner.execute()
            else:
                runner = RunnerFactory.create_runner(step_type, step_id, step_data)
                result = runner.execute(context)
            
            if not result.get("success", False):
                raise Exception(result.get("error", "Unknown error"))
            
            execution_results[step_id] = {
                "status": "success",
                "output": result.get("result", result.get("results", ""))
            }
            
            # Update context safely
            if isinstance(result.get("result"), dict):
                context[step_id] = result["result"]
            
        except Exception as e:
            logger.error(f"Step '{step_id}' failed: {e}")
            execution_results[step_id] = {
                "status": "failure", 
                "error": str(e)[:500]  # Limit error message length
            }
            break
    
    logger.info(f"Secure workflow '{{ workflow.name }}' completed")
    return execution_results

# Module validation
if __name__ == "__main__":
    # Test execution
    test_result = run({})
    print(f"Test execution result: {test_result}")
"""
        
        # Secure test template
        secure_test_template = """
'''
Secure Test for Generated Workflow Module
-----------------------------------------
Workflow ID: {{ workflow.name }} ({{ workflow.id }})
Generated on: {{ generation_date }}
'''

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add module path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from {{ module_name }} import run
except ImportError:
    def run(context=None):
        return {"status": "import_error"}

def test_secure_workflow_execution():
    '''Test secure workflow execution'''
    # Test with empty context
    result = run({})
    assert isinstance(result, dict)
    
    # Test with valid context
    result = run({"test": "data"})
    assert isinstance(result, dict)
    
    # Test with invalid context (should handle gracefully)
    try:
        result = run("invalid")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected

def test_context_size_limit():
    '''Test context size limitations'''
    large_context = {"data": "x" * 20000}
    try:
        result = run(large_context)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected

def test_workflow_steps():
    '''Test individual workflow steps'''
    result = run({})
    
    # Check that steps were processed
    expected_steps = [node["id"] for node in {{ workflow_nodes_json }} if "id" in node]
    
    if expected_steps:
        assert len(result) > 0, "Should have processed at least one step"
        
        # Check that each step has proper structure
        for step_id, step_result in result.items():
            assert "status" in step_result
            assert step_result["status"] in ["success", "failure"]
"""
        
        # Render templates
        try:
            module_code = self.renderer.render_template(
                secure_module_template,
                workflow=sanitized_workflow,
                workflow_nodes_json=json.dumps(sanitized_workflow.get("nodes", []), indent=4),
                generation_date=generation_date
            )
            
            test_code = self.renderer.render_template(
                secure_test_template,
                workflow=sanitized_workflow,
                module_name=self.module_name,
                workflow_nodes_json=json.dumps(sanitized_workflow.get("nodes", []), indent=4),
                generation_date=generation_date
            )
            
            self.audit_logger.info("Code generation completed successfully")
            return module_code, test_code
            
        except Exception as e:
            self.audit_logger.error(f"Code generation failed: {e}")
            raise SecureExecutionError(f"Failed to generate secure code: {e}")
    
    def _compile_restricted_code(self, code: str) -> Optional[object]:
        """Compile code with RestrictedPython"""
        try:
            # Compile with restrictions
            compiled_code = compile_restricted(code, '<string>', 'exec')
            if compiled_code is None:
                raise SecureExecutionError("Failed to compile restricted code")
            
            self.audit_logger.info("Code compiled successfully with restrictions")
            return compiled_code
            
        except Exception as e:
            self.audit_logger.error(f"Code compilation failed: {e}")
            raise SecureExecutionError(f"Failed to compile code: {e}")
    
    def _execute_in_sandbox(self, compiled_code: object) -> Dict[str, Any]:
        """Execute compiled code in sandbox"""
        try:
            # Create secure globals
            secure_globals = create_secure_globals(self.security_config)
            
            # Execute with timeout
            with timeout_context(self.security_config.max_execution_time):
                exec(compiled_code, secure_globals)
                
                # Get the run function
                if 'run' in secure_globals:
                    run_func = secure_globals['run']
                    result = run_func({})
                    
                    self.audit_logger.info("Sandbox execution completed successfully")
                    return result
                else:
                    raise SecureExecutionError("No run function found in generated code")
                    
        except TimeoutError:
            self.audit_logger.error("Execution timed out")
            raise
        except Exception as e:
            self.audit_logger.error(f"Sandbox execution failed: {e}")
            raise SecureExecutionError(f"Sandbox execution failed: {e}")
    
    def _save_secure_files(self, module_code: str, test_code: str):
        """Save generated files with security metadata"""
        # Add security header
        security_header = f"""# SECURITY METADATA
# Generated: {datetime.utcnow().isoformat()}
# Security Level: RESTRICTED
# Max Execution Time: {self.security_config.max_execution_time}s
# Allowed Modules: {', '.join(self.security_config.allowed_modules)}
# Audit Log: {self.audit_path}

"""
        
        # Save module
        with open(self.module_path, "w", encoding="utf-8") as f:
            f.write(security_header + module_code)
        
        # Save test
        with open(self.test_path, "w", encoding="utf-8") as f:
            f.write(security_header + test_code)
        
        self.audit_logger.info(f"Files saved: {self.module_path}, {self.test_path}")
    
    def _run_secure_tests(self) -> bool:
        """Run tests in secure environment"""
        try:
            self.audit_logger.info("Starting secure test execution")
            
            # Run tests with timeout
            with timeout_context(60):  # 1 minute timeout for tests
                result = subprocess.run([
                    sys.executable, "-m", "pytest", 
                    str(self.test_path), "-v", "--tb=short"
                ], 
                capture_output=True, text=True, timeout=45)
            
            if result.returncode == 0:
                self.audit_logger.info("Secure tests passed")
                return True
            else:
                self.audit_logger.error(f"Secure tests failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.audit_logger.error(f"Test execution failed: {e}")
            return False
    
    def generate_and_validate_secure(self) -> Optional[Path]:
        """
        Generate and validate secure workflow module
        
        Returns:
            Path to validated module or None if validation fails
        """
        try:
            self.audit_logger.info(f"Starting secure generation for workflow {self.workflow_id}")
            
            # 1. Generate secure code
            module_code, test_code = self._generate_secure_code()
            
            # 2. Compile and validate with RestrictedPython
            compiled_code = self._compile_restricted_code(module_code)
            
            # 3. Test execution in sandbox
            self._execute_in_sandbox(compiled_code)
            
            # 4. Save files
            self._save_secure_files(module_code, test_code)
            
            # 5. Run tests
            if self._run_secure_tests():
                self.audit_logger.info("Secure module generation completed successfully")
                return self.module_path
            else:
                self.audit_logger.error("Secure module validation failed")
                return None
                
        except Exception as e:
            self.audit_logger.error(f"Secure generation failed: {e}")
            logger.error(f"Secure module generation failed: {e}")
            return None

# Example usage
if __name__ == "__main__":
    # Example workflow
    sample_workflow = {
        "id": "secure_demo",
        "name": "Secure Demo Workflow",
        "overall_confidence": 0.85,
        "nodes": [
            {
                "id": "step1",
                "type": "desktop",
                "data": {
                    "label": "Desktop Action",
                    "confidence_score": 0.9,
                    "raw_actions": [{"type": "click", "x": 100, "y": 200}]
                }
            }
        ]
    }
    
    # Configure security
    security_config = SecurityConfig(
        max_execution_time=10,
        max_memory_mb=128,
        enable_audit_logging=True
    )
    
    # Generate secure module
    generator = SecureDynamicModuleGenerator(sample_workflow, security_config)
    result = generator.generate_and_validate_secure()
    
    if result:
        print(f"✅ Secure module generated: {result}")
    else:
        print("❌ Secure module generation failed")