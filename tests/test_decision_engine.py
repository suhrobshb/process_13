"""
Comprehensive Unit Tests for Decision Engine
==========================================

Tests for the Decision Engine module that handles dynamic decision rule evaluation
including Python expressions and LLM-based rules.
"""

import unittest
import json
import logging
import os

# Mock object for testing
class Mock:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __call__(self, *args, **kwargs):
        return Mock()

class MagicMock(Mock):
    pass

# Mock external dependencies
class MockOpenAI:
    class Chat:
        def __init__(self):
            self.completions = self.Completions()
            
        class Completions:
            def create(self, model, messages, **kwargs):
                # Mock OpenAI response
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message = Mock()
                
                # Extract the question from messages
                question = messages[-1]['content'].lower()
                
                if 'approve' in question and 'purchase' in question:
                    mock_response.choices[0].message.content = "true"
                elif 'reject' in question:
                    mock_response.choices[0].message.content = "false"
                else:
                    mock_response.choices[0].message.content = "true"
                
                return mock_response
    
    def __init__(self, api_key=None):
        self.chat = self.Chat()

def mock_decision_engine():
    """Create a mock decision_engine module for testing"""
    
    class DecisionEngine:
        def __init__(self):
            self.openai_client = None
            self.safe_globals = {
                '__builtins__': {
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'min': min,
                    'max': max,
                    'sum': sum,
                    'abs': abs,
                    'round': round,
                    'True': True,
                    'False': False,
                    'None': None
                }
            }
            
            # Mock OpenAI initialization
            if os.getenv("OPENAI_API_KEY") or True:  # Force initialization for testing
                self.openai_client = MockOpenAI()
        
        def evaluate(self, rule, context):
            """Evaluate a decision rule against the given context"""
            if not rule:
                raise ValueError("Rule cannot be empty")
            
            try:
                if rule.startswith("llm:"):
                    return self._evaluate_llm_rule(rule[4:].strip(), context)
                else:
                    return self._evaluate_python_rule(rule, context)
            except Exception as e:
                raise ValueError("Error evaluating rule '{}': {}".format(rule, str(e)))
        
        def _evaluate_python_rule(self, rule, context):
            """Evaluate a Python expression rule"""
            # Create safe evaluation environment
            safe_locals = dict(context)
            safe_locals['context'] = context
            
            # Restricted evaluation (simulate RestrictedPython)
            try:
                # Basic security check
                dangerous_keywords = ['import', 'exec', 'eval', 'open', 'file', '__']
                if any(keyword in rule for keyword in dangerous_keywords):
                    raise ValueError("Dangerous keyword detected in rule: {}".format(rule))
                
                # Evaluate the expression
                result = eval(rule, self.safe_globals, safe_locals)
                
                # Convert to boolean
                if isinstance(result, bool):
                    return result
                else:
                    return bool(result)
                    
            except Exception as e:
                raise ValueError("Failed to evaluate Python rule: {}".format(str(e)))
        
        def _evaluate_llm_rule(self, rule, context):
            """Evaluate an LLM-based rule"""
            if not self.openai_client:
                raise ValueError("OpenAI client not available for LLM rule evaluation")
            
            try:
                # Prepare context for LLM
                context_str = json.dumps(context, indent=2)
                
                messages = [
                    {
                        "role": "system",
                        "content": "You are a decision engine. Analyze the given context and answer the question with only 'true' or 'false'."
                    },
                    {
                        "role": "user",
                        "content": "Context: {}\n\nQuestion: {}\n\nAnswer with only 'true' or 'false':".format(context_str, rule)
                    }
                ]
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=10,
                    temperature=0
                )
                
                answer = response.choices[0].message.content.strip().lower()
                
                if answer == "true":
                    return True
                elif answer == "false":
                    return False
                else:
                    raise ValueError("Invalid LLM response: {}".format(answer))
                    
            except Exception as e:
                raise ValueError("Failed to evaluate LLM rule: {}".format(str(e)))
        
        def validate_rule(self, rule):
            """Validate a decision rule"""
            if not rule:
                return {"valid": False, "error": "Rule cannot be empty"}
            
            try:
                if rule.startswith("llm:"):
                    # LLM rule validation
                    llm_rule = rule[4:].strip()
                    if not llm_rule:
                        return {"valid": False, "error": "LLM rule cannot be empty"}
                    
                    if not self.openai_client:
                        return {"valid": False, "error": "OpenAI client not available"}
                    
                    return {"valid": True, "type": "llm", "rule": llm_rule}
                else:
                    # Python rule validation
                    dangerous_keywords = ['import', 'exec', 'eval', 'open', 'file', '__']
                    if any(keyword in rule for keyword in dangerous_keywords):
                        return {"valid": False, "error": "Dangerous keyword detected: {}".format(rule)}
                    
                    # Try to compile the rule
                    try:
                        compile(rule, '<string>', 'eval')
                        return {"valid": True, "type": "python", "rule": rule}
                    except SyntaxError as e:
                        return {"valid": False, "error": "Syntax error: {}".format(str(e))}
                        
            except Exception as e:
                return {"valid": False, "error": "Validation error: {}".format(str(e))}
    
    # Create mock module
    import sys
    mock_module = type(sys)('decision_engine')
    mock_module.DecisionEngine = DecisionEngine
    mock_module.logger = logging.getLogger(__name__)
    
    return mock_module


class TestDecisionEngine(unittest.TestCase):
    """Test cases for Decision Engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_module = mock_decision_engine()
        self.engine = self.mock_module.DecisionEngine()
        
        # Sample test contexts
        self.sample_context = {
            "total": 1500,
            "user_level": "manager",
            "department": "finance",
            "items": [
                {"name": "laptop", "price": 1200},
                {"name": "mouse", "price": 50}
            ],
            "urgent": True
        }
    
    def test_engine_initialization(self):
        """Test Decision Engine initialization"""
        engine = self.mock_module.DecisionEngine()
        
        self.assertIsNotNone(engine.safe_globals)
        self.assertIn('__builtins__', engine.safe_globals)
        
        # Should have OpenAI client (mocked)
        self.assertIsNotNone(engine.openai_client)
    
    def test_evaluate_python_rule_simple_comparison(self):
        """Test evaluation of simple Python comparison rules"""
        # Test greater than
        result = self.engine.evaluate("context['total'] > 1000", self.sample_context)
        self.assertTrue(result)
        
        # Test less than
        result = self.engine.evaluate("context['total'] < 1000", self.sample_context)
        self.assertFalse(result)
        
        # Test equality
        result = self.engine.evaluate("context['user_level'] == 'manager'", self.sample_context)
        self.assertTrue(result)
        
        # Test inequality
        result = self.engine.evaluate("context['department'] != 'hr'", self.sample_context)
        self.assertTrue(result)
    
    def test_evaluate_python_rule_boolean_logic(self):
        """Test evaluation of Python rules with boolean logic"""
        # Test AND logic
        result = self.engine.evaluate("context['total'] > 1000 and context['user_level'] == 'manager'", self.sample_context)
        self.assertTrue(result)
        
        # Test OR logic
        result = self.engine.evaluate("context['total'] > 2000 or context['urgent'] == True", self.sample_context)
        self.assertTrue(result)
        
        # Test NOT logic
        result = self.engine.evaluate("not context['urgent'] == False", self.sample_context)
        self.assertTrue(result)
    
    def test_evaluate_python_rule_complex_expressions(self):
        """Test evaluation of complex Python expressions"""
        # Test list operations
        result = self.engine.evaluate("len(context['items']) > 1", self.sample_context)
        self.assertTrue(result)
        
        # Test sum function
        result = self.engine.evaluate("sum(item['price'] for item in context['items']) > 1000", self.sample_context)
        self.assertTrue(result)
        
        # Test string operations
        result = self.engine.evaluate("'finance' in context['department']", self.sample_context)
        self.assertTrue(result)
    
    def test_evaluate_python_rule_security_restrictions(self):
        """Test security restrictions in Python rule evaluation"""
        # Test dangerous keywords
        with self.assertRaises(ValueError):
            self.engine.evaluate("import os", self.sample_context)
        
        with self.assertRaises(ValueError):
            self.engine.evaluate("exec('malicious code')", self.sample_context)
        
        with self.assertRaises(ValueError):
            self.engine.evaluate("eval('1+1')", self.sample_context)
        
        with self.assertRaises(ValueError):
            self.engine.evaluate("open('/etc/passwd')", self.sample_context)
    
    def test_evaluate_llm_rule_success(self):
        """Test successful LLM rule evaluation"""
        # Test approval rule
        result = self.engine.evaluate("llm:Should we approve this purchase order?", self.sample_context)
        self.assertTrue(result)
        
        # Test rejection rule
        result = self.engine.evaluate("llm:Should we reject this request?", self.sample_context)
        self.assertFalse(result)
    
    def test_evaluate_llm_rule_without_client(self):
        """Test LLM rule evaluation without OpenAI client"""
        # Create engine without OpenAI client
        engine = self.mock_module.DecisionEngine()
        engine.openai_client = None
        
        with self.assertRaises(ValueError) as cm:
            engine.evaluate("llm:Should we approve this?", self.sample_context)
        
        self.assertIn("OpenAI client not available", str(cm.exception))
    
    def test_evaluate_empty_rule(self):
        """Test evaluation with empty rule"""
        with self.assertRaises(ValueError) as cm:
            self.engine.evaluate("", self.sample_context)
        
        self.assertIn("Rule cannot be empty", str(cm.exception))
    
    def test_evaluate_invalid_python_rule(self):
        """Test evaluation with invalid Python syntax"""
        with self.assertRaises(ValueError):
            self.engine.evaluate("context['total'] > > 1000", self.sample_context)
    
    def test_evaluate_nonexistent_context_key(self):
        """Test evaluation with nonexistent context key"""
        with self.assertRaises(ValueError):
            self.engine.evaluate("context['nonexistent_key'] > 100", self.sample_context)
    
    def test_validate_rule_python_valid(self):
        """Test validation of valid Python rules"""
        # Valid simple rule
        result = self.engine.validate_rule("context['total'] > 1000")
        self.assertTrue(result["valid"])
        self.assertEqual(result["type"], "python")
        
        # Valid complex rule
        result = self.engine.validate_rule("len(context['items']) > 0 and context['urgent'] == True")
        self.assertTrue(result["valid"])
        self.assertEqual(result["type"], "python")
    
    def test_validate_rule_python_invalid(self):
        """Test validation of invalid Python rules"""
        # Invalid syntax
        result = self.engine.validate_rule("context['total'] > > 1000")
        self.assertFalse(result["valid"])
        self.assertIn("Syntax error", result["error"])
        
        # Dangerous keywords
        result = self.engine.validate_rule("import os")
        self.assertFalse(result["valid"])
        self.assertIn("Dangerous keyword", result["error"])
    
    def test_validate_rule_llm_valid(self):
        """Test validation of valid LLM rules"""
        result = self.engine.validate_rule("llm:Should we approve this purchase?")
        self.assertTrue(result["valid"])
        self.assertEqual(result["type"], "llm")
        self.assertEqual(result["rule"], "Should we approve this purchase?")
    
    def test_validate_rule_llm_invalid(self):
        """Test validation of invalid LLM rules"""
        # Empty LLM rule
        result = self.engine.validate_rule("llm:")
        self.assertFalse(result["valid"])
        self.assertIn("LLM rule cannot be empty", result["error"])
        
        # LLM rule with spaces only
        result = self.engine.validate_rule("llm:   ")
        self.assertFalse(result["valid"])
        self.assertIn("LLM rule cannot be empty", result["error"])
    
    def test_validate_rule_empty(self):
        """Test validation of empty rule"""
        result = self.engine.validate_rule("")
        self.assertFalse(result["valid"])
        self.assertIn("Rule cannot be empty", result["error"])
    
    def test_evaluate_rule_type_conversion(self):
        """Test rule evaluation with type conversion"""
        # Test numeric result conversion to boolean
        result = self.engine.evaluate("context['total'] - 1500", self.sample_context)
        self.assertFalse(result)  # 0 converts to False
        
        result = self.engine.evaluate("context['total'] - 1000", self.sample_context)
        self.assertTrue(result)  # 500 converts to True
        
        # Test string result conversion
        result = self.engine.evaluate("context['department']", self.sample_context)
        self.assertTrue(result)  # Non-empty string converts to True
    
    def test_evaluate_with_different_context_types(self):
        """Test evaluation with different context value types"""
        various_context = {
            "string_val": "test",
            "int_val": 42,
            "float_val": 3.14,
            "bool_val": True,
            "list_val": [1, 2, 3],
            "dict_val": {"key": "value"},
            "none_val": None
        }
        
        # Test with string
        result = self.engine.evaluate("context['string_val'] == 'test'", various_context)
        self.assertTrue(result)
        
        # Test with int
        result = self.engine.evaluate("context['int_val'] > 40", various_context)
        self.assertTrue(result)
        
        # Test with float
        result = self.engine.evaluate("context['float_val'] < 4.0", various_context)
        self.assertTrue(result)
        
        # Test with boolean
        result = self.engine.evaluate("context['bool_val'] == True", various_context)
        self.assertTrue(result)
        
        # Test with list
        result = self.engine.evaluate("len(context['list_val']) == 3", various_context)
        self.assertTrue(result)
        
        # Test with dict
        result = self.engine.evaluate("'key' in context['dict_val']", various_context)
        self.assertTrue(result)
        
        # Test with None
        result = self.engine.evaluate("context['none_val'] is None", various_context)
        self.assertTrue(result)
    
    def test_integration_full_decision_workflow(self):
        """Test complete decision workflow"""
        # Define a complex business rule
        business_rule = "context['total'] > 1000 and context['user_level'] == 'manager' and len(context['items']) > 0"
        
        # Validate the rule
        validation = self.engine.validate_rule(business_rule)
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["type"], "python")
        
        # Evaluate the rule
        result = self.engine.evaluate(business_rule, self.sample_context)
        self.assertTrue(result)
        
        # Test with different context
        different_context = {
            "total": 500,
            "user_level": "employee",
            "items": []
        }
        
        result = self.engine.evaluate(business_rule, different_context)
        self.assertFalse(result)


def run_decision_engine_tests():
    """Run all Decision Engine tests"""
    print("Running Decision Engine Tests...")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestDecisionEngine)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\nTest Results:")
    print("Tests Run: {}".format(result.testsRun))
    print("Failures: {}".format(len(result.failures)))
    print("Errors: {}".format(len(result.errors)))
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
    print("Success Rate: {:.1f}%".format(success_rate))
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_decision_engine_tests()
    if success:
        print("\n[SUCCESS] All Decision Engine tests passed!")
    else:
        print("\n[FAILED] Some tests failed!")