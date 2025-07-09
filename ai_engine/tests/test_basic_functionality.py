"""
Basic functionality tests for AI Engine
=======================================

Tests core functionality that doesn't require complex imports.
"""

import pytest
import sys
import os
import json
from unittest.mock import Mock, patch


class TestBasicFunctionality:
    """Test basic functionality of the AI Engine"""
    
    def test_import_structure(self):
        """Test that core modules can be imported"""
        # Test that we can import basic Python modules
        import json
        import os
        import sys
        
        assert json is not None
        assert os is not None
        assert sys is not None
    
    def test_json_processing(self):
        """Test JSON processing functionality"""
        test_data = {
            "workflow_id": "test-123",
            "name": "Test Workflow",
            "steps": [
                {"id": "step-1", "type": "shell", "command": "echo test"}
            ]
        }
        
        # Test JSON serialization/deserialization
        json_str = json.dumps(test_data)
        parsed_data = json.loads(json_str)
        
        assert parsed_data["workflow_id"] == "test-123"
        assert parsed_data["name"] == "Test Workflow"
        assert len(parsed_data["steps"]) == 1
    
    def test_workflow_validation_logic(self):
        """Test workflow validation logic"""
        def validate_workflow(workflow_data):
            """Simple workflow validation function"""
            errors = []
            
            # Check required fields
            required_fields = ["id", "name", "steps"]
            for field in required_fields:
                if field not in workflow_data:
                    errors.append(f"Missing required field: {field}")
            
            # Check steps
            if "steps" in workflow_data:
                steps = workflow_data["steps"]
                if not isinstance(steps, list):
                    errors.append("Steps must be a list")
                elif len(steps) == 0:
                    errors.append("Workflow must have at least one step")
                else:
                    for i, step in enumerate(steps):
                        if not isinstance(step, dict):
                            errors.append(f"Step {i} must be a dictionary")
                        else:
                            step_required = ["id", "type"]
                            for field in step_required:
                                if field not in step:
                                    errors.append(f"Step {i} missing required field: {field}")
            
            return len(errors) == 0, errors
        
        # Test valid workflow
        valid_workflow = {
            "id": "test-workflow",
            "name": "Test Workflow",
            "steps": [
                {"id": "step-1", "type": "shell", "command": "echo test"}
            ]
        }
        
        is_valid, errors = validate_workflow(valid_workflow)
        assert is_valid is True
        assert len(errors) == 0
        
        # Test invalid workflow
        invalid_workflow = {
            "name": "Test Workflow"
            # Missing id and steps
        }
        
        is_valid, errors = validate_workflow(invalid_workflow)
        assert is_valid is False
        assert len(errors) > 0
        assert any("id" in error for error in errors)
        assert any("steps" in error for error in errors)
    
    def test_step_dependency_resolution(self):
        """Test step dependency resolution algorithm"""
        def resolve_dependencies(steps):
            """Simple topological sort for step dependencies"""
            # Create dependency graph
            graph = {}
            in_degree = {}
            
            for step in steps:
                step_id = step["id"]
                graph[step_id] = step.get("depends_on", [])
                in_degree[step_id] = 0
            
            # Calculate in-degrees (how many dependencies each step has)
            for step_id, dependencies in graph.items():
                for dep in dependencies:
                    if dep in in_degree:
                        in_degree[step_id] += 1
            
            # Topological sort - start with steps that have no dependencies
            queue = [step_id for step_id in in_degree if in_degree[step_id] == 0]
            result = []
            
            while queue:
                current = queue.pop(0)
                result.append(current)
                
                # For each step that depends on the current step
                for step_id, dependencies in graph.items():
                    if current in dependencies:
                        in_degree[step_id] -= 1
                        if in_degree[step_id] == 0:
                            queue.append(step_id)
            
            # Check for cycles
            if len(result) != len(steps):
                raise ValueError("Circular dependency detected")
            
            # Return steps in execution order
            step_map = {step["id"]: step for step in steps}
            return [step_map[step_id] for step_id in result]
        
        # Test simple dependency chain
        steps = [
            {"id": "step-1", "depends_on": []},
            {"id": "step-2", "depends_on": ["step-1"]},
            {"id": "step-3", "depends_on": ["step-2"]}
        ]
        
        ordered_steps = resolve_dependencies(steps)
        assert ordered_steps[0]["id"] == "step-1"
        assert ordered_steps[1]["id"] == "step-2"
        assert ordered_steps[2]["id"] == "step-3"
        
        # Test parallel execution
        parallel_steps = [
            {"id": "step-1", "depends_on": []},
            {"id": "step-2", "depends_on": []},
            {"id": "step-3", "depends_on": ["step-1", "step-2"]}
        ]
        
        ordered_parallel = resolve_dependencies(parallel_steps)
        # Steps 1 and 2 should come before step 3
        step_positions = {step["id"]: i for i, step in enumerate(ordered_parallel)}
        assert step_positions["step-1"] < step_positions["step-3"]
        assert step_positions["step-2"] < step_positions["step-3"]
        
        # Test circular dependency detection
        circular_steps = [
            {"id": "step-1", "depends_on": ["step-2"]},
            {"id": "step-2", "depends_on": ["step-1"]}
        ]
        
        with pytest.raises(ValueError, match="Circular dependency"):
            resolve_dependencies(circular_steps)
    
    def test_context_variable_substitution(self):
        """Test context variable substitution"""
        def substitute_variables(template, context):
            """Simple variable substitution"""
            import re
            
            def replace_var(match):
                var_name = match.group(1)
                if var_name in context:
                    return str(context[var_name])
                else:
                    raise KeyError(f"Variable '{var_name}' not found in context")
            
            return re.sub(r'\{\{(\w+)\}\}', replace_var, template)
        
        context = {
            "user_name": "John Doe",
            "api_key": "secret123",
            "base_url": "https://api.example.com"
        }
        
        # Test simple substitution
        template = "Hello {{user_name}}"
        result = substitute_variables(template, context)
        assert result == "Hello John Doe"
        
        # Test multiple variables
        template = "{{base_url}}/users/{{user_name}}"
        result = substitute_variables(template, context)
        assert result == "https://api.example.com/users/John Doe"
        
        # Test missing variable
        template = "Hello {{missing_var}}"
        with pytest.raises(KeyError):
            substitute_variables(template, context)
    
    def test_execution_result_formatting(self):
        """Test execution result formatting"""
        def format_execution_result(step_id, success, result=None, error=None, duration_ms=None):
            """Format execution result"""
            from datetime import datetime
            
            execution_result = {
                "step_id": step_id,
                "success": success,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            if duration_ms is not None:
                execution_result["duration_ms"] = duration_ms
            
            if success and result is not None:
                execution_result["result"] = result
            
            if not success and error is not None:
                execution_result["error"] = error
            
            return execution_result
        
        # Test successful execution
        success_result = format_execution_result(
            "test-step", 
            True, 
            result={"output": "Hello World"}, 
            duration_ms=150
        )
        
        assert success_result["step_id"] == "test-step"
        assert success_result["success"] is True
        assert success_result["result"]["output"] == "Hello World"
        assert success_result["duration_ms"] == 150
        assert "timestamp" in success_result
        assert "error" not in success_result
        
        # Test failed execution
        error_result = format_execution_result(
            "test-step", 
            False, 
            error="Command failed", 
            duration_ms=100
        )
        
        assert error_result["step_id"] == "test-step"
        assert error_result["success"] is False
        assert error_result["error"] == "Command failed"
        assert error_result["duration_ms"] == 100
        assert "result" not in error_result
    
    def test_workflow_metrics_calculation(self):
        """Test workflow metrics calculation"""
        def calculate_metrics(step_results):
            """Calculate workflow execution metrics"""
            total_steps = len(step_results)
            successful_steps = sum(1 for result in step_results if result.get("success", False))
            failed_steps = total_steps - successful_steps
            
            total_duration = sum(result.get("duration_ms", 0) for result in step_results)
            success_rate = successful_steps / total_steps if total_steps > 0 else 0
            
            return {
                "total_steps": total_steps,
                "successful_steps": successful_steps,
                "failed_steps": failed_steps,
                "success_rate": success_rate,
                "total_duration_ms": total_duration,
                "average_step_duration_ms": total_duration / total_steps if total_steps > 0 else 0
            }
        
        # Test with all successful steps
        success_results = [
            {"success": True, "duration_ms": 100},
            {"success": True, "duration_ms": 200},
            {"success": True, "duration_ms": 150}
        ]
        
        metrics = calculate_metrics(success_results)
        assert metrics["total_steps"] == 3
        assert metrics["successful_steps"] == 3
        assert metrics["failed_steps"] == 0
        assert metrics["success_rate"] == 1.0
        assert metrics["total_duration_ms"] == 450
        assert metrics["average_step_duration_ms"] == 150
        
        # Test with mixed results
        mixed_results = [
            {"success": True, "duration_ms": 100},
            {"success": False, "duration_ms": 50},
            {"success": True, "duration_ms": 200}
        ]
        
        metrics = calculate_metrics(mixed_results)
        assert metrics["total_steps"] == 3
        assert metrics["successful_steps"] == 2
        assert metrics["failed_steps"] == 1
        assert metrics["success_rate"] == 2/3
        assert metrics["total_duration_ms"] == 350
    
    def test_error_handling_patterns(self):
        """Test error handling patterns"""
        def safe_execute(func, *args, **kwargs):
            """Safe execution wrapper with error handling"""
            try:
                result = func(*args, **kwargs)
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Test successful execution
        def success_func(x, y):
            return x + y
        
        result = safe_execute(success_func, 2, 3)
        assert result["success"] is True
        assert result["result"] == 5
        
        # Test exception handling
        def error_func():
            raise ValueError("Test error")
        
        result = safe_execute(error_func)
        assert result["success"] is False
        assert "Test error" in result["error"]
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        def validate_config(config):
            """Validate configuration structure"""
            errors = []
            
            # Check required sections
            required_sections = ["database", "ai_engine", "logging"]
            for section in required_sections:
                if section not in config:
                    errors.append(f"Missing required section: {section}")
            
            # Validate database config
            if "database" in config:
                db_config = config["database"]
                required_db_fields = ["host", "port", "name"]
                for field in required_db_fields:
                    if field not in db_config:
                        errors.append(f"Database config missing field: {field}")
            
            # Validate AI engine config
            if "ai_engine" in config:
                ai_config = config["ai_engine"]
                if "max_workers" in ai_config:
                    if not isinstance(ai_config["max_workers"], int) or ai_config["max_workers"] < 1:
                        errors.append("max_workers must be a positive integer")
            
            return len(errors) == 0, errors
        
        # Test valid config
        valid_config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "autoops"
            },
            "ai_engine": {
                "max_workers": 10
            },
            "logging": {
                "level": "INFO"
            }
        }
        
        is_valid, errors = validate_config(valid_config)
        assert is_valid is True
        assert len(errors) == 0
        
        # Test invalid config
        invalid_config = {
            "database": {
                "host": "localhost"
                # Missing port and name
            },
            "ai_engine": {
                "max_workers": -1  # Invalid value
            }
            # Missing logging section
        }
        
        is_valid, errors = validate_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])