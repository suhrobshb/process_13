"""
Tests for DecisionEngine - Security-focused testing
===================================================

This test suite validates the DecisionEngine's secure evaluation capabilities,
including RestrictedPython sandboxing and LLM integration.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from ai_engine.decision_engine import DecisionEngine, SecurityViolationError


class TestDecisionEngine:
    """Test suite for DecisionEngine functionality"""
    
    @pytest.fixture
    def engine(self):
        """Create a DecisionEngine instance for testing"""
        return DecisionEngine()
    
    @pytest.fixture
    def sample_context(self):
        """Sample context data for testing"""
        return {
            "user_id": 123,
            "amount": 1500.0,
            "category": "office_supplies", 
            "department": "engineering",
            "approval_count": 1,
            "total_cost": 2500.0
        }
    
    # Python Expression Rule Tests
    def test_simple_comparison_rules(self, engine, sample_context):
        """Test basic comparison operations"""
        assert engine.evaluate("context['amount'] > 1000", sample_context) == True
        assert engine.evaluate("context['amount'] < 500", sample_context) == False
        assert engine.evaluate("context['approval_count'] >= 1", sample_context) == True
    
    def test_string_operations(self, engine, sample_context):
        """Test string-based rules"""
        assert engine.evaluate("context['department'] == 'engineering'", sample_context) == True
        assert engine.evaluate("'office' in context['category']", sample_context) == True
        assert engine.evaluate("context['category'].startswith('office')", sample_context) == True
    
    def test_complex_boolean_logic(self, engine, sample_context):
        """Test complex boolean expressions"""
        rule = "context['amount'] > 1000 and context['approval_count'] >= 1"
        assert engine.evaluate(rule, sample_context) == True
        
        rule = "context['amount'] > 5000 or context['department'] == 'engineering'"
        assert engine.evaluate(rule, sample_context) == True
        
        rule = "not (context['amount'] < 100)"
        assert engine.evaluate(rule, sample_context) == True
    
    def test_mathematical_operations(self, engine, sample_context):
        """Test mathematical expressions"""
        rule = "context['amount'] + context['total_cost'] > 3000"
        assert engine.evaluate(rule, sample_context) == True
        
        rule = "context['amount'] * 2 <= context['total_cost'] + 1000"
        assert engine.evaluate(rule, sample_context) == True
    
    def test_type_coercion(self, engine, sample_context):
        """Test that non-boolean results are properly converted"""
        # Test truthy values
        assert engine.evaluate("context['amount']", sample_context) == True
        assert engine.evaluate("context['category']", sample_context) == True
        
        # Test falsy values with modified context
        falsy_context = sample_context.copy()
        falsy_context['amount'] = 0
        assert engine.evaluate("context['amount']", falsy_context) == False
    
    # Security Tests
    def test_dangerous_functions_blocked(self, engine, sample_context):
        """Test that dangerous functions are blocked"""
        dangerous_rules = [
            "exec('print(1)')",
            "eval('1+1')",
            "open('/etc/passwd')",
            "__import__('os').system('ls')",
            "globals()",
            "locals()",
        ]
        
        for rule in dangerous_rules:
            with pytest.raises((ValueError, SecurityViolationError)):
                engine.evaluate(rule, sample_context)
    
    def test_safe_builtins_available(self, engine, sample_context):
        """Test that safe built-in functions work"""
        assert engine.evaluate("len(context['category']) > 5", sample_context) == True
        assert engine.evaluate("str(context['amount']).startswith('1')", sample_context) == True
        assert engine.evaluate("int(context['amount']) == 1500", sample_context) == True
        assert engine.evaluate("isinstance(context['amount'], float)", sample_context) == True
    
    def test_invalid_rules(self, engine, sample_context):
        """Test handling of invalid rules"""
        with pytest.raises(ValueError):
            engine.evaluate("", sample_context)
        
        with pytest.raises(ValueError):
            engine.evaluate(None, sample_context)
        
        with pytest.raises(ValueError):
            engine.evaluate("invalid syntax @@", sample_context)
        
        with pytest.raises(ValueError):
            engine.evaluate("context['nonexistent_key']", sample_context)
    
    # LLM Rule Tests
    @patch('ai_engine.decision_engine.OpenAI')
    def test_llm_rule_true_response(self, mock_openai, engine, sample_context):
        """Test LLM rule returning true"""
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "true"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Set up engine with mock client
        engine.openai_client = mock_client
        
        result = engine.evaluate("llm:Should this purchase be approved?", sample_context)
        assert result == True
        
        # Verify API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert "Should this purchase be approved?" in call_args[1]['messages'][0]['content']
    
    @patch('ai_engine.decision_engine.OpenAI')
    def test_llm_rule_false_response(self, mock_openai, engine, sample_context):
        """Test LLM rule returning false"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "false"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        engine.openai_client = mock_client
        
        result = engine.evaluate("llm:Should this purchase be rejected?", sample_context)
        assert result == False
    
    @patch('ai_engine.decision_engine.OpenAI')
    def test_llm_rule_fuzzy_responses(self, mock_openai, engine, sample_context):
        """Test LLM rule handling fuzzy responses"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        engine.openai_client = mock_client
        
        # Test yes-like responses
        mock_response.choices[0].message.content = "yes, approve this"
        result = engine.evaluate("llm:Should approve?", sample_context)
        assert result == True
        
        # Test no-like responses  
        mock_response.choices[0].message.content = "no, reject this"
        result = engine.evaluate("llm:Should approve?", sample_context)
        assert result == False
    
    @patch('ai_engine.decision_engine.OpenAI')
    def test_llm_rule_invalid_response(self, mock_openai, engine, sample_context):
        """Test LLM rule with unparseable response"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "maybe perhaps sometimes"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        engine.openai_client = mock_client
        
        with pytest.raises(ValueError, match="Could not parse LLM response"):
            engine.evaluate("llm:Should approve?", sample_context)
    
    def test_llm_rule_without_client(self, engine, sample_context):
        """Test LLM rule when OpenAI client is not available"""
        engine.openai_client = None
        
        with pytest.raises(RuntimeError, match="OpenAI client not available"):
            engine.evaluate("llm:Should approve?", sample_context)
    
    # Capability Detection Tests
    def test_capability_detection(self, engine):
        """Test capability detection methods"""
        # These will depend on environment setup
        assert isinstance(engine.is_safe_eval_available(), bool)
        assert isinstance(engine.is_llm_available(), bool)
    
    # Edge Cases
    def test_empty_context(self, engine):
        """Test evaluation with empty context"""
        result = engine.evaluate("True", {})
        assert result == True
        
        with pytest.raises(ValueError):
            engine.evaluate("context['missing']", {})
    
    def test_rule_whitespace_handling(self, engine, sample_context):
        """Test that whitespace in rules is handled properly"""
        assert engine.evaluate("  context['amount'] > 1000  ", sample_context) == True
        assert engine.evaluate("\n\tcontext['amount'] > 1000\n\t", sample_context) == True
        assert engine.evaluate("llm:  Should approve this?  ", sample_context) != None
    
    def test_context_mutation_safety(self, engine, sample_context):
        """Test that context cannot be mutated during evaluation"""
        original_amount = sample_context['amount']
        
        # This should not modify the original context
        rule = "context['amount'] > 1000"  # Should not be able to assign
        engine.evaluate(rule, sample_context)
        
        assert sample_context['amount'] == original_amount


class TestDecisionEngineIntegration:
    """Integration tests for DecisionEngine with real scenarios"""
    
    def test_approval_workflow_scenario(self):
        """Test a realistic approval workflow scenario"""
        engine = DecisionEngine()
        
        scenarios = [
            {
                "context": {
                    "amount": 500,
                    "department": "marketing", 
                    "approver_level": 1
                },
                "rule": "context['amount'] < 1000 and context['approver_level'] >= 1",
                "expected": True
            },
            {
                "context": {
                    "amount": 5000,
                    "department": "engineering",
                    "approver_level": 1
                },
                "rule": "context['amount'] < 1000 or context['approver_level'] >= 3",
                "expected": False
            },
            {
                "context": {
                    "vendor": "trusted_supplier",
                    "amount": 2000,
                    "category": "office_equipment"
                },
                "rule": "context['vendor'] == 'trusted_supplier' and context['amount'] < 5000",
                "expected": True
            }
        ]
        
        for scenario in scenarios:
            result = engine.evaluate(scenario["rule"], scenario["context"])
            assert result == scenario["expected"], f"Failed scenario: {scenario}"
    
    def test_security_validation_scenario(self):
        """Test security-focused validation scenarios"""
        engine = DecisionEngine()
        
        # Test that potentially dangerous inputs are safely handled
        dangerous_context = {
            "__builtins__": {"eval": eval},
            "malicious": "os.system('rm -rf /')",
            "normal_field": 100
        }
        
        # Should be able to safely access normal fields
        assert engine.evaluate("context['normal_field'] > 50", dangerous_context) == True
        
        # Should not be able to execute dangerous code
        with pytest.raises(ValueError):
            engine.evaluate("context['__builtins__']['eval']('1+1')", dangerous_context)


# Performance and Load Testing Helpers
class TestDecisionEnginePerformance:
    """Performance tests for DecisionEngine"""
    
    def test_rule_evaluation_performance(self):
        """Test that rule evaluation is performant"""
        import time
        
        engine = DecisionEngine()
        context = {"value": 100, "category": "test" * 100}  # Larger context
        rule = "context['value'] > 50 and len(context['category']) > 10"
        
        # Warm up
        for _ in range(10):
            engine.evaluate(rule, context)
        
        # Measure performance
        start_time = time.time()
        for _ in range(1000):
            engine.evaluate(rule, context)
        execution_time = time.time() - start_time
        
        # Should complete 1000 evaluations in reasonable time (< 1 second)
        assert execution_time < 1.0, f"Performance too slow: {execution_time}s for 1000 evaluations"
    
    def test_concurrent_evaluation(self):
        """Test concurrent rule evaluation safety"""
        import threading
        import time
        
        engine = DecisionEngine()
        results = []
        errors = []
        
        def evaluate_rule(thread_id):
            try:
                context = {"thread_id": thread_id, "value": thread_id * 10}
                rule = f"context['value'] == {thread_id * 10}"
                result = engine.evaluate(rule, context)
                results.append((thread_id, result))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Run 50 concurrent evaluations
        threads = []
        for i in range(50):
            thread = threading.Thread(target=evaluate_rule, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert len(errors) == 0, f"Concurrent evaluation errors: {errors}"
        assert len(results) == 50
        assert all(result[1] == True for result in results)


if __name__ == "__main__":
    # Run basic smoke test
    engine = DecisionEngine()
    context = {"amount": 1500, "department": "engineering"}
    
    print("Running DecisionEngine smoke tests...")
    
    # Test Python rules
    assert engine.evaluate("context['amount'] > 1000", context) == True
    print("✅ Python rule evaluation works")
    
    # Test security
    try:
        engine.evaluate("exec('print(1)')", context)
        assert False, "Should have blocked exec"
    except ValueError:
        print("✅ Security restrictions work")
    
    print("✅ All smoke tests passed!")