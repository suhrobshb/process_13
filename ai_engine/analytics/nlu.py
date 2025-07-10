"""
Natural Language Understanding (NLU) for Workflow Generation
============================================================

This module is a critical part of the AI Engine's intelligence layer, responsible
for translating human language into machine-executable structured workflows. It
leverages a Large Language Model (LLM) with sophisticated prompting techniques
to understand user intent and generate or modify workflows in the correct
Input-Process-Output (IPO) format.

Key Responsibilities:
-   **Text-to-Workflow Creation**: Parses a user's high-level description of a
    business process (e.g., "Read an invoice from an email, extract the total,
    and enter it into QuickBooks") and generates a valid, structured list of
    workflow steps.
-   **Conversational Workflow Modification**: Takes an existing workflow structure
    and a user's command (e.g., "After the first step, add an approval from the
    manager") and intelligently applies the change, returning the new, complete
    workflow structure.
-   **Structured Output Generation**: Employs advanced prompt engineering,
    including few-shot examples and schema definitions, to guide the LLM into
    producing reliable JSON output.
-   **Validation**: Uses Pydantic models to rigorously validate the structure and
    types of the LLM's output, ensuring that only well-formed workflow data is
    passed to the rest of the system.
-   **Integration with LLM Runners**: Utilizes the platform's core `LLMRunner`
    to remain provider-agnostic (supporting OpenAI, Ollama, etc.).
"""

import json
import logging
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field, ValidationError

# Import the core LLM execution component
from ..enhanced_runners.llm_runner import LLMRunner

# Configure logging
logger = logging.getLogger(__name__)


# --- Pydantic Models for Validating LLM Output ---
# These models define the "contract" that the LLM's JSON output must adhere to.

class StepIO(BaseModel):
    """Validation model for the Input or Output part of a step."""
    description: str = Field(..., description="A human-readable description of the input/output.")
    source: Optional[str] = Field(None, description="The source of the data (e.g., a trigger, a file, a previous step's variable).")
    variable: Optional[str] = Field(None, description="The name of the variable to use or create.")

class StepProcess(BaseModel):
    """Validation model for the Process part of a step."""
    type: str = Field(..., description="The type of runner to use (e.g., 'desktop', 'browser', 'llm').")
    description: str = Field(..., description="A human-readable description of the action being performed.")
    # `actions` or other params will be a dict, so we allow extra fields.
    class Config:
        extra = "allow"

class StepIPO(BaseModel):
    """The complete validation model for a single workflow step."""
    id: str
    name: str
    input: StepIO
    process: StepProcess
    output: StepIO
    metadata: Dict[str, Any] = Field(default_factory=dict)


# --- Advanced LLM Prompts ---

# This prompt guides the LLM to create a new workflow from scratch.
# It includes a schema definition and a "few-shot" example to improve reliability.
CREATE_WORKFLOW_SYSTEM_PROMPT = """
You are an expert AI assistant that translates natural language descriptions of business processes into structured JSON workflows. Your task is to break down the user's request into a series of logical steps.

You MUST respond with ONLY a valid JSON object containing a single key "steps", which is a list of step objects. Do NOT include any explanations or introductory text.

Each step object in the list must follow this exact schema:
{
  "id": "A unique, descriptive snake_case ID for the step.",
  "name": "A short, human-readable title for the step.",
  "input": {
    "description": "Description of what this step needs to start (e.g., 'Receives the invoice PDF from the email trigger').",
    "source": "Optional: Where the input comes from (e.g., 'trigger.file', 'step_1.output.variable')."
  },
  "process": {
    "type": "The runner type (e.g., 'desktop', 'browser', 'llm', 'http', 'shell').",
    "description": "A summary of the action to be performed."
  },
  "output": {
    "description": "Description of what this step produces (e.g., 'The extracted invoice total').",
    "variable": "Optional: The name of the variable to store the output in."
  },
  "metadata": {
    "confidence_score": 0.9,
    "ai_generated": true
  }
}

EXAMPLE:
User Request: "Please create a workflow to open a new customer's invoice from an email, use an LLM to extract the total amount, and then enter that amount into our web portal."

Your JSON Response:
{
  "steps": [
    {
      "id": "open_invoice_from_email",
      "name": "Open Invoice from Email",
      "input": { "description": "Triggered by a new email with an invoice attachment." },
      "process": { "type": "desktop", "description": "Opens the email client and downloads the PDF attachment." },
      "output": { "description": "The invoice PDF file.", "variable": "invoice_pdf_file" }
    },
    {
      "id": "extract_total_amount",
      "name": "Extract Total Amount with LLM",
      "input": { "description": "Receives the invoice PDF.", "source": "open_invoice_from_email.output.invoice_pdf_file" },
      "process": { "type": "llm", "description": "Uses an LLM to perform OCR and extract the total amount from the PDF content." },
      "output": { "description": "The extracted total amount as a number.", "variable": "invoice_total" }
    },
    {
      "id": "enter_amount_in_portal",
      "name": "Enter Amount in Web Portal",
      "input": { "description": "Receives the extracted total amount.", "source": "extract_total_amount.output.invoice_total" },
      "process": { "type": "browser", "description": "Navigates to the web portal, logs in, and enters the invoice total into the correct field." },
      "output": { "description": "Confirmation of successful data entry." }
    }
  ]
}
"""

# This prompt guides the LLM to modify an existing workflow.
MODIFY_WORKFLOW_SYSTEM_PROMPT = """
You are an expert AI assistant that modifies existing structured JSON workflows based on a user's natural language command.

The user will provide the current workflow as a JSON object and a command for how to change it. Your task is to apply the change and return the ENTIRE, NEW, VALID JSON object for the modified workflow.

You MUST respond with ONLY the complete, valid JSON object containing the "steps" list. Do NOT include any other text.

Follow the same schema for each step object as defined previously. When applying the change, you can add, remove, or modify steps in the list. Ensure all step IDs remain unique.
"""


# --- Core Logic ---

async def _call_llm_for_workflow_structure(prompt: str) -> Optional[List[Dict[str, Any]]]:
    """
    A helper function to call the LLM, parse its response, and validate it.
    """
    logger.info("Calling LLM to generate/modify workflow structure...")
    raw_text = ""
    try:
        # For this complex task, we might prefer a more powerful model.
        # This could be configured via environment variables.
        llm_params = {
            "provider": "openai",
            "model": "gpt-4-turbo",
            "prompt_template": prompt,
            "llm_kwargs": {"response_format": {"type": "json_object"}}
        }
        runner = LLMRunner(step_id="nlu_workflow_generation", params=llm_params)
        
        # The context is empty as the full instruction is in the prompt template itself.
        result = runner.execute(context={})

        if not result.get("success"):
            raise RuntimeError(f"LLM execution failed: {result.get('error')}")

        raw_text = result["result"]["raw_text"]
        
        # Parse the JSON response
        data = json.loads(raw_text)
        
        if "steps" not in data or not isinstance(data["steps"], list):
            raise ValueError("LLM response is missing the required 'steps' list.")

        # Validate each step in the list using Pydantic
        validated_steps = [StepIPO.model_validate(step).model_dump() for step in data["steps"]]
        
        logger.info(f"Successfully generated and validated {len(validated_steps)} workflow steps.")
        return validated_steps

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}\nRaw response: {raw_text}")
        return None
    except ValidationError as e:
        logger.error(f"LLM output failed Pydantic validation: {e}\nRaw response: {raw_text}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during NLU processing: {e}", exc_info=True)
        return None


async def nlu_to_workflow(text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Translates a natural language description into a structured workflow.

    Args:
        text: The user's description of the process.

    Returns:
        A list of step dictionaries in the validated IPO format, or None on failure.
    """
    logger.info(f"Attempting to convert text to workflow: '{text[:100]}...'")
    full_prompt = f"{CREATE_WORKFLOW_SYSTEM_PROMPT}\n\nUser Request: \"{text}\""
    return await _call_llm_for_workflow_structure(full_prompt)


async def apply_nlu_modification_to_workflow(
    original_steps: List[Dict[str, Any]],
    modification_instruction: str
) -> Optional[List[Dict[str, Any]]]:
    """
    Applies a natural language modification to an existing workflow.

    Args:
        original_steps: The current list of steps in the workflow.
        modification_instruction: The user's command for what to change.

    Returns:
        The new, complete list of steps if successful, otherwise None.
    """
    logger.info(f"Attempting to modify workflow with instruction: '{modification_instruction}'")
    
    original_steps_json = json.dumps({"steps": original_steps}, indent=2)
    
    # Construct the prompt with the full context
    full_prompt = (
        f"{MODIFY_WORKFLOW_SYSTEM_PROMPT}\n\n"
        f"Here is the current workflow JSON:\n{original_steps_json}\n\n"
        f"Now, apply this modification: \"{modification_instruction}\"\n\n"
        "Return the new, complete JSON for the entire workflow."
    )
    
    return await _call_llm_for_workflow_structure(full_prompt)


# --- Example Usage ---
if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def demo():
        # --- Demo 1: Create a new workflow from text ---
        print("\n--- DEMO 1: Creating a new workflow from natural language ---")
        create_text = "I need to check my email for a new sales report, download the attached CSV, then upload that CSV to our company's data warehouse via an HTTP POST request."
        
        new_steps = await nlu_to_workflow(create_text)
        
        if new_steps:
            print("✅ Successfully generated workflow:")
            print(json.dumps(new_steps, indent=2))
        else:
            print("❌ Failed to generate workflow.")

        # --- Demo 2: Modify an existing workflow ---
        print("\n\n--- DEMO 2: Modifying an existing workflow with natural language ---")
        if new_steps:
            modify_instruction = "Actually, before uploading to the data warehouse, add a step to use an LLM to summarize the CSV content first."
            
            modified_steps = await apply_nlu_modification_to_workflow(new_steps, modify_instruction)
            
            if modified_steps:
                print("✅ Successfully modified workflow:")
                print(json.dumps(modified_steps, indent=2))
            else:
                print("❌ Failed to modify workflow.")
        else:
            print("Skipping modification demo because creation failed.")

    # Run the async demo
    asyncio.run(demo())
