"""
Enhanced LLM Runner
===================

This module provides a sophisticated runner for interacting with various Large
Language Models (LLMs). It is designed to be a core component of the AI Engine's
intelligence layer, enabling complex reasoning, data extraction, and content
generation tasks within a workflow.

Key Features:
-   **Multi-Provider Support**: A factory-based approach allows seamless switching
    between different LLM providers like OpenAI, Anthropic, and local models
    (e.g., via Ollama).
-   **Advanced Prompt Templating**: Uses Jinja2 to allow dynamic prompts that can
    incorporate outputs from previous workflow steps, enabling complex context-
    passing.
-   **Structured Output**: Can enforce a specific JSON schema on the LLM's output,
    ensuring reliable, machine-readable results for data extraction and chaining.
-   **Context-Aware Execution**: Receives the entire workflow context to make
    informed, context-aware decisions or summaries.
-   **Error Handling & Configuration**: Robustly handles API errors and missing
    configurations (like API keys).
-   **Metrics & Cost Tracking**: Integrates with the platform's monitoring system
    to track request latency and token usage for performance and cost analysis.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from jinja2 import Environment

# Import metrics helpers for instrumentation
from ..metrics_instrumentation import record_llm_request, record_llm_token_usage

# Configure logging
logger = logging.getLogger(__name__)

# --- Abstract Base Class for LLM Providers ---

class BaseLLM(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self, model: str, **kwargs):
        self.model = model
        self.kwargs = kwargs

    @abstractmethod
    def generate(self, prompt: str) -> Dict[str, Any]:
        """
        Generates a response from the LLM.

        Args:
            prompt (str): The fully rendered prompt to send to the model.

        Returns:
            A dictionary containing the generated text and any provider-specific
            metadata (e.g., token usage).
        """
        pass

# --- Concrete LLM Provider Implementations ---

class OpenAIProvider(BaseLLM):
    """LLM provider for OpenAI models (GPT-3.5, GPT-4, etc.)."""

    def __init__(self, model: str, **kwargs):
        super().__init__(model, **kwargs)
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("OpenAI provider requires 'pip install openai'.")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        self.client = OpenAI(api_key=api_key)

    def generate(self, prompt: str) -> Dict[str, Any]:
        logger.info(f"Sending request to OpenAI model: {self.model}")
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **self.kwargs
            )
            content = completion.choices[0].message.content
            usage = completion.usage
            return {
                "text": content,
                "metadata": {
                    "provider": "openai",
                    "model": self.model,
                    "token_usage": {
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "total_tokens": usage.total_tokens,
                    }
                }
            }
        except Exception as e:
            logger.error(f"OpenAI API request failed: {e}", exc_info=True)
            raise

class AnthropicProvider(BaseLLM):
    """LLM provider for Anthropic models (Claude)."""

    def __init__(self, model: str, **kwargs):
        super().__init__(model, **kwargs)
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("Anthropic provider requires 'pip install anthropic'.")

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
        self.client = Anthropic(api_key=api_key)

    def generate(self, prompt: str) -> Dict[str, Any]:
        logger.info(f"Sending request to Anthropic model: {self.model}")
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.kwargs.get("max_tokens", 1024),
                messages=[{"role": "user", "content": prompt}]
            )
            content = message.content[0].text
            return {
                "text": content,
                "metadata": {
                    "provider": "anthropic",
                    "model": self.model,
                    "token_usage": {
                        "input_tokens": message.usage.input_tokens,
                        "output_tokens": message.usage.output_tokens,
                    }
                }
            }
        except Exception as e:
            logger.error(f"Anthropic API request failed: {e}", exc_info=True)
            raise

class OllamaProvider(BaseLLM):
    """
    Provider for open-source LLMs served locally via Ollama.
    Supports models like Llama3, Mistral, etc.
    """

    def __init__(self, model: str, **kwargs):
        super().__init__(model, **kwargs)
        try:
            import requests
        except ImportError:
            raise ImportError("OllamaProvider requires 'pip install requests'.")
        
        self.endpoint = os.getenv("OLLAMA_API_ENDPOINT", "http://localhost:11434/api/generate")
        if not self.endpoint:
            raise ValueError("OLLAMA_API_ENDPOINT environment variable not set.")
        self.requests = requests

    def generate(self, prompt: str) -> Dict[str, Any]:
        logger.info(f"Sending request to Ollama endpoint: {self.endpoint} for model: {self.model}")
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,  # Ensure we get a single, complete response
            **self.kwargs
        }
        try:
            response = self.requests.post(self.endpoint, json=payload, timeout=120) # 2-minute timeout
            response.raise_for_status()
            data = response.json()
            return {
                "text": data.get("response", ""),
                "metadata": {
                    "provider": "ollama",
                    "model": self.model,
                    "response_time_ms": data.get("total_duration", 0) / 1_000_000,
                    "token_usage": {
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                        "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                    }
                }
            }
        except self.requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}", exc_info=True)
            raise

# --- LLM Provider Factory ---

class LLMFactory:
    """Factory to create LLM provider instances."""

    @staticmethod
    def create_provider(provider_name: str, model: str, **kwargs) -> BaseLLM:
        provider_name = provider_name.lower()
        if provider_name == "openai":
            return OpenAIProvider(model, **kwargs)
        elif provider_name == "anthropic":
            return AnthropicProvider(model, **kwargs)
        elif provider_name == "ollama":
            return OllamaProvider(model, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: '{provider_name}'")

# --- Main LLM Runner Class ---

class LLMRunner:
    """
    Executes an LLM-based step in a workflow.
    """

    def __init__(self, step_id: str, params: Dict[str, Any]):
        """
        Initializes the LLM Runner.

        Args:
            step_id (str): A unique identifier for this step.
            params (Dict[str, Any]): Parameters for the step, including:
                - provider (str): The LLM provider (e.g., 'openai', 'ollama').
                - model (str): The specific model to use.
                - prompt_template (str): A Jinja2 template for the prompt.
                - output_schema (Optional[Dict]): A JSON schema for structured output.
                - llm_kwargs (Optional[Dict]): Additional keyword arguments for the LLM API call.
        """
        self.step_id = step_id
        self.provider_name = params.get("provider")
        self.model = params.get("model")
        self.prompt_template_str = params.get("prompt_template")
        self.output_schema = params.get("output_schema")
        self.llm_kwargs = params.get("llm_kwargs", {})

        if not all([self.provider_name, self.model, self.prompt_template_str]):
            raise ValueError("LLMRunner requires 'provider', 'model', and 'prompt_template' parameters.")

        self.jinja_env = Environment()
        self.prompt_template = self.jinja_env.from_string(self.prompt_template_str)

    def _render_prompt(self, context: Dict[str, Any]) -> str:
        """Renders the Jinja2 prompt template with the workflow context."""
        return self.prompt_template.render(context)

    def _parse_structured_output(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """Attempts to parse the LLM's raw output into a structured JSON object."""
        if not self.output_schema:
            return None
        
        logger.info("Attempting to parse LLM output into structured JSON.")
        try:
            # A common pattern is for the LLM to wrap the JSON in markdown backticks
            if "```json" in raw_text:
                json_str = raw_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = raw_text
            
            parsed_json = json.loads(json_str)
            
            # Optional: Validate against a JSON schema if one is provided
            # A library like `jsonschema` could be used here for validation.
            logger.info("Successfully parsed structured output.")
            return parsed_json
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"Failed to parse LLM output as JSON: {e}. Returning raw text.")
            return None

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the LLM step.

        Args:
            context (Dict[str, Any]): The current state of the workflow context.

        Returns:
            A dictionary with the execution result.
        """
        logger.info(f"Executing LLM step: {self.step_id}")
        start_time = time.time()
        
        try:
            # 1. Render the prompt
            rendered_prompt = self._render_prompt(context)
            logger.debug(f"Rendered prompt for step {self.step_id}:\n{rendered_prompt}")

            # 2. Get the LLM provider
            provider = LLMFactory.create_provider(self.provider_name, self.model, **self.llm_kwargs)

            # 3. Generate the response
            response = provider.generate(rendered_prompt)
            duration = time.time() - start_time
            
            raw_text = response.get("text", "")
            metadata = response.get("metadata", {})
            
            # 4. Record metrics for performance and cost tracking
            record_llm_request(self.provider_name, self.model, duration, 'success')
            token_usage = metadata.get("token_usage", {})
            if token_usage:
                record_llm_token_usage(
                    self.provider_name, self.model,
                    token_usage.get("prompt_tokens", 0),
                    token_usage.get("completion_tokens", 0)
                )

            # 5. Parse structured output if schema is provided
            structured_output = self._parse_structured_output(raw_text)

            result = {
                "raw_text": raw_text,
                "structured_output": structured_output,
                "metadata": metadata,
            }
            
            return {
                "success": True,
                "result": result,
                "execution_time_seconds": duration,
            }

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"LLM step '{self.step_id}' failed: {e}", exc_info=True)
            # Record failed request metric
            record_llm_request(self.provider_name, self.model, duration, 'failure')
            return {
                "success": False,
                "error": str(e),
                "execution_time_seconds": duration,
            }

# --- Example Usage ---
if __name__ == "__main__":
    # This block demonstrates how the LLMRunner would be used by the WorkflowEngine.
    # To run this, you need to set the appropriate environment variables.
    # e.g., export OPENAI_API_KEY="your-key"
    
    logging.basicConfig(level=logging.INFO)

    # --- Example 1: OpenAI with context ---
    print("\n--- 1. OpenAI Runner Execution Example ---")
    try:
        llm_step_params = {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "prompt_template": "Summarize the following text in 50 words or less: {{ previous_step.output.text }}",
            "llm_kwargs": {"temperature": 0.7}
        }
        workflow_context = {
            "previous_step": {
                "output": {
                    "text": "The Industrial Revolution was the transition to new manufacturing processes in Europe and the United States, in the period from about 1760 to sometime between 1820 and 1840."
                }
            }
        }
        runner = LLMRunner(step_id="summarize_text_step", params=llm_step_params)
        execution_result = runner.execute(context=workflow_context)
        print(json.dumps(execution_result, indent=2))
    except (ValueError, ImportError) as e:
        print(f"Skipping OpenAI example: {e}")

    # --- Example 2: Ollama with a local model ---
    print("\n--- 2. Ollama (Local LLM) Execution Example ---")
    try:
        # NOTE: This requires an Ollama server running with the 'llama3' model pulled.
        # e.g., `ollama run llama3`
        ollama_params = {
            "provider": "ollama",
            "model": "llama3",
            "prompt_template": "Why is the sky blue?",
        }
        ollama_runner = LLMRunner(step_id="local_qa_step", params=ollama_params)
        ollama_result = ollama_runner.execute(context={})
        print(json.dumps(ollama_result, indent=2))
    except (ValueError, ImportError) as e:
        print(f"Skipping Ollama example: {e}")
    except Exception as e:
        print(f"Ollama example failed. Is the Ollama server running? Error: {e}")


    # --- Example 3: Structured Output with JSON ---
    print("\n--- 3. Structured Output (JSON) Example ---")
    try:
        structured_step_params = {
            "provider": "openai",
            "model": "gpt-4-turbo",
            "prompt_template": "Extract the name, email, and company from this text and provide it as a JSON object: 'Contact John Doe at john.doe@acme.com from Acme Inc.'",
            "output_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "company": {"type": "string"}
                },
                "required": ["name", "email", "company"]
            }
        }
        structured_runner = LLMRunner(step_id="extract_data_step", params=structured_step_params)
        structured_result = structured_runner.execute(context={})
        print(json.dumps(structured_result, indent=2))
    except (ValueError, ImportError) as e:
        print(f"Skipping structured output example: {e}")

