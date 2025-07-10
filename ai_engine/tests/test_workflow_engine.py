"""
Unit tests for workflow_engine.py
=================================

Tests for the core workflow execution engine, including:
- Workflow execution logic
- Step processing and ordering
- Error handling and recovery
- Context management
- Parallel execution capabilities
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from workflow_engine import WorkflowEngine
from models.workflow import Workflow
from models.execution import Execution


class TestWorkflowEngine:
    """Test suite for WorkflowEngine class"""
    
    @pytest.fixture
    def engine(self):
        """Create a WorkflowEngine instance for testing"""
        return WorkflowEngine()
    
    @pytest.fixture
    def sample_workflow(self):
        """Create a sample workflow for testing"""
        return {
            "id": "test-workflow-123",
            "name": "Test Workflow",
            "version": "1.0.0",
            "steps": [
                {
                    "id": "step-1",
                    "name": "Initial Step",
                    "type": "shell",
                    "params": {
                        "command": "echo 'Hello World'"
                    },
                    "depends_on": []
                },
                {
                    "id": "step-2", 
                    "name": "Second Step",
                    "type": "http",
                    "params": {
                        "url": "https://api.example.com/data",
                        "method": "GET"
                    },
                    "depends_on": ["step-1"]
                }
            ],
            "metadata": {
                "created_at": "2024-01-01T00:00:00Z",
                "created_by": "test-user"
            }
        }
    
    def test_workflow_engine_initialization(self, engine):
        """Test WorkflowEngine initializes correctly"""
        assert engine is not None
        assert hasattr(engine, 'execute_workflow')
        assert hasattr(engine, 'validate_workflow')
    
    def test_workflow_validation_success(self, engine, sample_workflow):
        """Test workflow validation with valid workflow"""
        is_valid, errors = engine.validate_workflow(sample_workflow)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_workflow_validation_missing_required_fields(self, engine):
        """Test workflow validation with missing required fields"""
        invalid_workflow = {
            "name": "Test Workflow"
            # Missing id, steps, etc.
        }
        
        is_valid, errors = engine.validate_workflow(invalid_workflow)
        assert is_valid is False
        assert len(errors) > 0
        assert any("id" in error for error in errors)
        assert any("steps" in error for error in errors)
    
    def test_workflow_validation_circular_dependencies(self, engine):
        """Test workflow validation detects circular dependencies"""
        circular_workflow = {
            "id": "circular-test",
            "name": "Circular Test",
            "version": "1.0.0",
            "steps": [
                {
                    "id": "step-1",
                    "name": "Step 1",
                    "type": "shell",
                    "params": {"command": "echo 'test'"},
                    "depends_on": ["step-2"]
                },
                {
                    "id": "step-2",
                    "name": "Step 2", 
                    "type": "shell",
                    "params": {"command": "echo 'test'"},
                    "depends_on": ["step-1"]
                }
            ]
        }
        
        is_valid, errors = engine.validate_workflow(circular_workflow)
        assert is_valid is False
        assert any("circular" in error.lower() for error in errors)
    
    @pytest.mark.asyncio
    async def test_workflow_execution_success(self, engine, sample_workflow):
        """Test successful workflow execution"""
        # Mock the step runners to return successful results
        with patch('workflow_engine.get_runner') as mock_get_runner:
            mock_runner = Mock()
            mock_runner.execute.return_value = {
                "success": True,
                "result": {"output": "Hello World"},
                "duration_ms": 100
            }
            mock_get_runner.return_value = mock_runner
            
            result = await engine.execute_workflow(sample_workflow)
            
            assert result["success"] is True
            assert result["workflow_id"] == "test-workflow-123"
            assert len(result["step_results"]) == 2
            assert all(step["success"] for step in result["step_results"])
    
    @pytest.mark.asyncio
    async def test_workflow_execution_step_failure(self, engine, sample_workflow):
        """Test workflow execution with step failure"""
        with patch('workflow_engine.get_runner') as mock_get_runner:
            mock_runner = Mock()
            # First call succeeds, second fails
            mock_runner.execute.side_effect = [
                {"success": True, "result": {"output": "Hello World"}, "duration_ms": 100},
                {"success": False, "error": "HTTP request failed", "duration_ms": 200}
            ]
            mock_get_runner.return_value = mock_runner
            
            result = await engine.execute_workflow(sample_workflow)
            
            assert result["success"] is False
            assert len(result["step_results"]) == 2
            assert result["step_results"][0]["success"] is True
            assert result["step_results"][1]["success"] is False
            assert "HTTP request failed" in result["step_results"][1]["error"]
    
    def test_step_dependency_resolution(self, engine, sample_workflow):
        """Test that step dependencies are resolved correctly"""
        ordered_steps = engine._resolve_step_dependencies(sample_workflow["steps"])
        
        # First step should have no dependencies
        assert ordered_steps[0]["id"] == "step-1"
        assert len(ordered_steps[0]["depends_on"]) == 0
        
        # Second step should depend on first
        assert ordered_steps[1]["id"] == "step-2"
        assert "step-1" in ordered_steps[1]["depends_on"]
    
    def test_step_dependency_resolution_complex(self, engine):
        """Test dependency resolution with complex dependency graph"""
        complex_steps = [
            {"id": "step-1", "depends_on": []},
            {"id": "step-2", "depends_on": ["step-1"]},
            {"id": "step-3", "depends_on": ["step-1"]},
            {"id": "step-4", "depends_on": ["step-2", "step-3"]},
            {"id": "step-5", "depends_on": ["step-4"]}
        ]
        
        ordered_steps = engine._resolve_step_dependencies(complex_steps)
        
        # Verify ordering respects dependencies
        step_positions = {step["id"]: i for i, step in enumerate(ordered_steps)}
        
        assert step_positions["step-1"] < step_positions["step-2"]
        assert step_positions["step-1"] < step_positions["step-3"]
        assert step_positions["step-2"] < step_positions["step-4"]
        assert step_positions["step-3"] < step_positions["step-4"]
        assert step_positions["step-4"] < step_positions["step-5"]
    
    def test_context_variable_substitution(self, engine):
        """Test that context variables are properly substituted"""
        context = {
            "user_name": "John Doe",
            "api_key": "secret-key-123",
            "base_url": "https://api.example.com"
        }
        
        step_params = {
            "url": "{{base_url}}/users/{{user_name}}",
            "headers": {
                "Authorization": "Bearer {{api_key}}"
            },
            "greeting": "Hello {{user_name}}!"
        }
        
        substituted = engine._substitute_context_variables(step_params, context)
        
        assert substituted["url"] == "https://api.example.com/users/John Doe"
        assert substituted["headers"]["Authorization"] == "Bearer secret-key-123"
        assert substituted["greeting"] == "Hello John Doe!"
    
    def test_context_variable_substitution_missing_vars(self, engine):
        """Test context variable substitution with missing variables"""
        context = {"user_name": "John Doe"}
        
        step_params = {
            "url": "{{base_url}}/users/{{user_name}}",
            "api_key": "{{missing_key}}"
        }
        
        # Should raise an error for missing variables
        with pytest.raises(KeyError):
            engine._substitute_context_variables(step_params, context)
    
    @pytest.mark.asyncio
    async def test_parallel_step_execution(self, engine):
        """Test parallel execution of independent steps"""
        parallel_workflow = {
            "id": "parallel-test",
            "name": "Parallel Test",
            "version": "1.0.0",
            "steps": [
                {
                    "id": "step-1",
                    "name": "Step 1",
                    "type": "shell",
                    "params": {"command": "echo 'step1'"},
                    "depends_on": []
                },
                {
                    "id": "step-2",
                    "name": "Step 2",
                    "type": "shell", 
                    "params": {"command": "echo 'step2'"},
                    "depends_on": []
                },
                {
                    "id": "step-3",
                    "name": "Step 3",
                    "type": "shell",
                    "params": {"command": "echo 'step3'"},
                    "depends_on": ["step-1", "step-2"]
                }
            ]
        }
        
        with patch('workflow_engine.get_runner') as mock_get_runner:
            mock_runner = Mock()
            mock_runner.execute.return_value = {
                "success": True,
                "result": {"output": "test"},
                "duration_ms": 100
            }
            mock_get_runner.return_value = mock_runner
            
            result = await engine.execute_workflow(parallel_workflow)
            
            assert result["success"] is True
            assert len(result["step_results"]) == 3
            # Steps 1 and 2 should be executed in parallel
            # Step 3 should wait for both to complete
    
    def test_workflow_timeout_handling(self, engine, sample_workflow):
        """Test workflow timeout handling"""
        # Add timeout to workflow
        sample_workflow["timeout"] = 1  # 1 second timeout
        
        with patch('workflow_engine.get_runner') as mock_get_runner:
            mock_runner = Mock()
            # Simulate long-running step
            mock_runner.execute.return_value = {
                "success": True,
                "result": {"output": "test"},
                "duration_ms": 2000  # 2 seconds
            }
            mock_get_runner.return_value = mock_runner
            
            # Should handle timeout gracefully
            result = asyncio.run(engine.execute_workflow(sample_workflow))
            
            # Workflow should fail due to timeout
            assert result["success"] is False
            assert "timeout" in result.get("error", "").lower()
    
    def test_workflow_error_recovery(self, engine):
        """Test error recovery and retry mechanisms"""
        retry_workflow = {
            "id": "retry-test",
            "name": "Retry Test",
            "version": "1.0.0",
            "steps": [
                {
                    "id": "step-1",
                    "name": "Retry Step",
                    "type": "http",
                    "params": {
                        "url": "https://api.example.com/data",
                        "method": "GET",
                        "retry": {
                            "max_attempts": 3,
                            "delay": 1,
                            "backoff": "exponential"
                        }
                    },
                    "depends_on": []
                }
            ]
        }
        
        with patch('workflow_engine.get_runner') as mock_get_runner:
            mock_runner = Mock()
            # Fail first two attempts, succeed on third
            mock_runner.execute.side_effect = [
                {"success": False, "error": "Connection failed"},
                {"success": False, "error": "Connection failed"},
                {"success": True, "result": {"data": "success"}, "duration_ms": 100}
            ]
            mock_get_runner.return_value = mock_runner
            
            result = asyncio.run(engine.execute_workflow(retry_workflow))
            
            assert result["success"] is True
            assert mock_runner.execute.call_count == 3  # 3 attempts total
    
    def test_workflow_metrics_collection(self, engine, sample_workflow):
        """Test that workflow execution metrics are collected"""
        with patch('workflow_engine.get_runner') as mock_get_runner:
            mock_runner = Mock()
            mock_runner.execute.return_value = {
                "success": True,
                "result": {"output": "test"},
                "duration_ms": 150
            }
            mock_get_runner.return_value = mock_runner
            
            result = asyncio.run(engine.execute_workflow(sample_workflow))
            
            # Check that metrics are included in result
            assert "metrics" in result
            assert "total_duration_ms" in result["metrics"]
            assert "steps_executed" in result["metrics"]
            assert "success_rate" in result["metrics"]
            assert result["metrics"]["steps_executed"] == 2
            assert result["metrics"]["success_rate"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])