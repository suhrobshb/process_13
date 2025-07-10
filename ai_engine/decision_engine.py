import os
import json
import logging
from typing import Dict, Any, Callable, Optional

try:
    from RestrictedPython import compile_restricted
    from RestrictedPython.Guards import safe_builtins
    RESTRICTED_PYTHON_AVAILABLE = True
except ImportError:
    RESTRICTED_PYTHON_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

class DecisionEngine:
    """
    Evaluate dynamic decision rules (Python expressions or LLM-based).
    
    Supports two types of rules:
    1. Python expressions: "context['total'] > 1000"
    2. LLM rules: "llm:Should we approve this purchase order based on the context?"
    """
    
    def __init__(self):
        """Initialize the decision engine with security configurations."""
        self.openai_client = None
        if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
    
    def evaluate(self, rule: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate a decision rule against the given context.
        
        Args:
            rule: Either a Python expression or LLM prompt (prefixed with "llm:")
            context: Dictionary containing variables for evaluation
            
        Returns:
            Boolean result of the rule evaluation
            
        Raises:
            ValueError: If rule is invalid or evaluation fails
        """
        if not rule or not isinstance(rule, str):
            raise ValueError("Rule must be a non-empty string")
        
        rule = rule.strip()
        
        # Handle LLM-based rules
        if rule.startswith("llm:"):
            return self._evaluate_llm_rule(rule[4:].strip(), context)
        
        # Handle Python expression rules
        return self._evaluate_python_rule(rule, context)
    
    def _evaluate_python_rule(self, expression: str, context: Dict[str, Any]) -> bool:
        """
        Safely evaluate a Python expression using RestrictedPython.
        
        Args:
            expression: Python expression to evaluate
            context: Variables available for evaluation
            
        Returns:
            Boolean result of expression evaluation
        """
        if not RESTRICTED_PYTHON_AVAILABLE:
            raise RuntimeError("RestrictedPython not available for safe evaluation")
        
        try:
            # Create safe execution environment
            safe_globals = {
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
                    'min': min,
                    'max': max,
                    'sum': sum,
                    'abs': abs,
                    'round': round,
                    'isinstance': isinstance,
                    'hasattr': hasattr,
                    'getattr': getattr,
                },
                'context': context,
                # Add safe math operations
                'and': lambda a, b: a and b,
                'or': lambda a, b: a or b,
                'not': lambda a: not a,
            }
            
            # Compile the expression with restrictions
            compiled_code = compile_restricted(expression, '<decision_rule>', 'eval')
            if compiled_code is None:
                raise ValueError(f"Failed to compile rule: {expression}")
            
            # Execute and return result
            result = eval(compiled_code, safe_globals)
            
            # Ensure boolean result
            if not isinstance(result, bool):
                result = bool(result)
            
            logger.debug(f"Evaluated rule '{expression}' -> {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to evaluate Python rule '{expression}': {e}")
            raise ValueError(f"Rule evaluation failed: {str(e)}")
    
    def _evaluate_llm_rule(self, prompt: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate a rule using an LLM (Large Language Model).
        
        Args:
            prompt: Natural language prompt for the LLM
            context: Context data to include in the prompt
            
        Returns:
            Boolean decision from the LLM
        """
        if not self.openai_client:
            raise RuntimeError("OpenAI client not available for LLM evaluation")
        
        try:
            # Prepare context for LLM
            context_str = json.dumps(context, indent=2, default=str)
            
            # Create comprehensive prompt
            full_prompt = f"""
You are a decision engine. Based on the context provided, answer the following question with either "true" or "false".

Context:
{context_str}

Question: {prompt}

Important: Respond with ONLY "true" or "false" (lowercase, no quotes).
"""
            
            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": full_prompt}],
                max_tokens=10,
                temperature=0.1  # Low temperature for consistent decisions
            )
            
            result_text = response.choices[0].message.content.strip().lower()
            
            # Parse boolean result
            if result_text == "true":
                result = True
            elif result_text == "false":
                result = False
            else:
                logger.warning(f"LLM returned unexpected response: {result_text}")
                # Try to parse as boolean-like response
                if any(word in result_text for word in ["yes", "approve", "accept", "allow"]):
                    result = True
                elif any(word in result_text for word in ["no", "reject", "deny", "block"]):
                    result = False
                else:
                    raise ValueError(f"Could not parse LLM response as boolean: {result_text}")
            
            logger.info(f"LLM evaluated rule '{prompt}' -> {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to evaluate LLM rule '{prompt}': {e}")
            raise ValueError(f"LLM rule evaluation failed: {str(e)}")
    
    def is_llm_available(self) -> bool:
        """Check if LLM evaluation is available."""
        return self.openai_client is not None
    
    def is_safe_eval_available(self) -> bool:
        """Check if safe Python evaluation is available."""
        return RESTRICTED_PYTHON_AVAILABLE


# Example usage and testing
if __name__ == "__main__":
    # Test the decision engine
    engine = DecisionEngine()
    
    # Test context
    test_context = {
        "user_id": 123,
        "amount": 1500.0,
        "category": "office_supplies",
        "department": "engineering",
        "approval_count": 1
    }
    
    # Test Python expression rules
    try:
        print("Testing Python expression rules:")
        
        # Simple comparisons
        assert engine.evaluate("context['amount'] > 1000", test_context) == True
        assert engine.evaluate("context['amount'] < 500", test_context) == False
        
        # String operations
        assert engine.evaluate("context['department'] == 'engineering'", test_context) == True
        assert engine.evaluate("'office' in context['category']", test_context) == True
        
        # Complex expressions
        assert engine.evaluate("context['amount'] > 1000 and context['approval_count'] >= 1", test_context) == True
        
        print("✅ Python expression tests passed!")
        
    except Exception as e:
        print(f"❌ Python expression tests failed: {e}")
    
    # Test LLM rules (only if OpenAI key is available)
    if engine.is_llm_available():
        try:
            print("\nTesting LLM rules:")
            
            # Test LLM decision
            result = engine.evaluate(
                "llm:Should this purchase be approved based on the amount and department?", 
                test_context
            )
            print(f"LLM decision result: {result}")
            print("✅ LLM rule test completed!")
            
        except Exception as e:
            print(f"❌ LLM rule test failed: {e}")
    else:
        print("⚠️ LLM evaluation not available (missing OpenAI API key)")
    
    print(f"\nCapabilities:")
    print(f"- Safe Python evaluation: {engine.is_safe_eval_available()}")
    print(f"- LLM evaluation: {engine.is_llm_available()}")
