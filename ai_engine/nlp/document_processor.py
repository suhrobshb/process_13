"""
Advanced NLP for Document & Email Processing
============================================

This module provides a sophisticated Natural Language Processing (NLP) engine
designed to understand, categorize, and extract structured information from
unstructured text sources like documents, emails, and OCR outputs.

It serves as a powerful extension to the AI Engine's capabilities, turning raw
text into actionable, structured data that can be used in downstream automation
steps.

Key Features:
-   **Document Classification**: Intelligently categorizes documents into predefined
    types (e.g., 'invoice', 'contract', 'purchase_order', 'report') using an LLM.
-   **Structured Information Extraction**: Extracts specific data points (like
    invoice numbers, dates, totals, party names) from text based on a user-defined
    JSON schema, ensuring reliable and machine-readable output.
-   **Intelligent Summarization**: Generates concise, context-aware summaries of
    long documents, with options to control length and focus.
-   **Multi-Format Text Extraction**: Includes utility functions to extract raw
    text from various file formats (e.g., .txt, .pdf), making the processor
    versatile.
-   **LLM-Powered**: Leverages the existing `LLMRunner` to remain provider-agnostic
    (supporting OpenAI, Ollama, Anthropic, etc.) and to benefit from centralized
    metrics and configuration.
-   **Robust and Extensible**: Designed with clear functions and prompts, making
    it easy to add new NLP tasks or refine existing ones.

This engine is crucial for automating processes that involve handling documents,
such as invoice processing, contract analysis, and customer support email triage.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# Import the core LLM execution component from our existing infrastructure
from ..enhanced_runners.llm_runner import LLMRunner

# Configure logging
logger = logging.getLogger(__name__)

# --- Text Extraction Utilities ---

def extract_text_from_document(file_path: Union[str, Path]) -> str:
    """
    Extracts raw text content from a file, supporting various formats.

    Args:
        file_path: The path to the document file.

    Returns:
        The extracted text content as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        NotImplementedError: If the file format is not supported or required
                             libraries are not installed.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"No such file: {path}")

    extension = path.suffix.lower()

    if extension == ".txt":
        return path.read_text(encoding='utf-8')
    
    elif extension == ".pdf":
        try:
            # To enable PDF support, install the pypdf library:
            # pip install pypdf
            from pypdf import PdfReader
            reader = PdfReader(path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except ImportError:
            raise NotImplementedError(
                "PDF processing requires the 'pypdf' library. Please install it using 'pip install pypdf'."
            )
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {path}: {e}")
            raise
    
    # Placeholder for image-based OCR
    elif extension in [".png", ".jpg", ".jpeg", ".tiff"]:
        raise NotImplementedError(
            "Image processing (OCR) is not implemented in this function. Use the vision_utils module for OCR."
        )

    else:
        raise NotImplementedError(f"Unsupported file format: {extension}")


# --- Core Document Processor Class ---

class DocumentProcessor:
    """
    An NLP engine that classifies, extracts, and summarizes document content.
    """

    def __init__(
        self,
        document_content: Optional[str] = None,
        file_path: Optional[Union[str, Path]] = None
    ):
        """
        Initializes the processor with document content.

        Args:
            document_content: The raw text content of the document.
            file_path: The path to the document file. If provided, content will
                       be extracted from this file.
        
        Raises:
            ValueError: If neither document_content nor file_path is provided.
        """
        if file_path:
            self.content = extract_text_from_document(file_path)
        elif document_content:
            self.content = document_content
        else:
            raise ValueError("Either 'document_content' or 'file_path' must be provided.")
        
        if not self.content.strip():
            logger.warning("Document content is empty or contains only whitespace.")

    async def _run_nlp_task(self, prompt: str) -> Dict[str, Any]:
        """A helper to run a specific NLP task using the LLMRunner."""
        # Use a powerful model for these complex NLP tasks
        llm_params = {
            "provider": os.getenv("NLP_LLM_PROVIDER", "openai"),
            "model": os.getenv("NLP_LLM_MODEL", "gpt-4-turbo"),
            "prompt_template": prompt,
            "llm_kwargs": {"temperature": 0.1} # Low temperature for factual tasks
        }
        runner = LLMRunner(step_id="nlp_document_processing", params=llm_params)
        result = runner.execute(context={}) # Context is in the prompt
        
        if not result.get("success"):
            raise RuntimeError(f"NLP task failed: {result.get('error')}")
        
        return result["result"]

    async def classify_document(self, categories: List[str]) -> str:
        """
        Classifies the document into one of the provided categories.

        Args:
            categories: A list of possible document types (e.g., ['invoice', 'contract']).

        Returns:
            The most likely category as a string.
        """
        logger.info(f"Classifying document into one of categories: {categories}")
        
        prompt = f"""
        Analyze the following document and classify it into one of these exact categories: {json.dumps(categories)}.
        Respond with ONLY the single category name as a JSON string.

        Document Content:
        ---
        {self.content[:4000]}
        ---

        Your JSON response:
        """
        
        result = await self._run_nlp_task(prompt)
        try:
            # The LLM is asked to return a JSON string, e.g., "\"invoice\""
            parsed_category = json.loads(result["raw_text"])
            if parsed_category in categories:
                return parsed_category
            else:
                logger.warning(f"LLM returned an invalid category '{parsed_category}'. Falling back to 'unknown'.")
                return "unknown"
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse LLM classification response. Falling back to 'unknown'.")
            return "unknown"

    async def extract_information(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts structured information from the document based on a JSON schema.

        Args:
            schema: A dictionary defining the desired JSON structure with descriptions
                    for each field. Example:
                    {
                        "invoice_id": "The unique invoice number",
                        "due_date": "The payment due date in YYYY-MM-DD format",
                        "total_amount": "The total amount due as a float"
                    }

        Returns:
            A dictionary containing the extracted data.
        """
        logger.info("Extracting structured information based on schema.")
        schema_str = json.dumps(schema, indent=2)

        prompt = f"""
        You are an expert data entry assistant. Analyze the following document and extract the required information.
        Respond with ONLY a valid JSON object that strictly follows the provided schema. If a value is not found, use null.

        Schema to fill:
        ---
        {schema_str}
        ---

        Document Content:
        ---
        {self.content[:8000]}
        ---

        Your JSON response:
        """
        
        result = await self._run_nlp_task(prompt)
        try:
            # The LLM should return a complete JSON object string
            extracted_data = json.loads(result["raw_text"])
            return extracted_data
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM extraction response as JSON. Returning empty dict.")
            return {}

    async def summarize(self, length: str = "medium", focus: Optional[str] = None) -> str:
        """
        Generates a summary of the document.

        Args:
            length: The desired length of the summary ('short', 'medium', 'long').
            focus: An optional topic to focus the summary on (e.g., "financial obligations").

        Returns:
            The summary text.
        """
        logger.info(f"Generating a '{length}' summary. Focus: {focus or 'general'}")
        
        length_instructions = {
            "short": "one or two sentences",
            "medium": "one paragraph",
            "long": "three detailed paragraphs"
        }
        
        focus_instruction = f"Pay special attention to details related to {focus}." if focus else ""

        prompt = f"""
        Generate a {length_instructions.get(length, 'one paragraph')} summary of the following document.
        {focus_instruction}

        Document Content:
        ---
        {self.content[:8000]}
        ---

        Summary:
        """
        
        result = await self._run_nlp_task(prompt)
        return result["raw_text"].strip()


# --- Example Usage ---
if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Mock document content
    mock_invoice_text = """
    INVOICE
    Quantum Solutions Inc.
    123 Cyber Way, Neo City, 90210

    Bill To:
    Hyperion Corp.
    456 Data Drive
    Tech Valley, 12345

    Invoice #: INV-2025-001
    Date: 2025-07-15
    Due Date: 2025-08-14

    Description        | Qty | Unit Price | Total
    -------------------------------------------------
    AI Consulting      | 10  | $200.00    | $2000.00
    Cloud Server Costs | 1   | $500.00    | $500.00
    -------------------------------------------------
    Subtotal: $2500.00
    Tax (8%): $200.00
    TOTAL: $2700.00

    Please remit payment within 30 days.
    """

    async def demo():
        print("--- NLP Document Processor Demo ---")
        
        # Initialize the processor with the mock text
        processor = DocumentProcessor(document_content=mock_invoice_text)

        # --- 1. Classify the Document ---
        print("\n1. Classifying document...")
        categories = ["invoice", "contract", "report", "memo"]
        doc_type = await processor.classify_document(categories)
        print(f"   ✅ Document classified as: '{doc_type}'")

        # --- 2. Extract Structured Information ---
        print("\n2. Extracting structured information...")
        extraction_schema = {
            "invoice_number": "The unique invoice identifier (e.g., INV-2025-001)",
            "issuer_name": "The name of the company that sent the invoice",
            "client_name": "The name of the company being billed",
            "due_date": "The payment due date in YYYY-MM-DD format",
            "total_amount": "The final total amount due as a float"
        }
        extracted_info = await processor.extract_information(schema=extraction_schema)
        print("   ✅ Extracted Information:")
        print(json.dumps(extracted_info, indent=4))

        # --- 3. Generate a Summary ---
        print("\n3. Generating a summary...")
        summary = await processor.summarize(length="short", focus="payment details")
        print(f"   ✅ Focused Summary: {summary}")

    # Run the async demo
    # Ensure OPENAI_API_KEY (or another provider's key) is set in your environment
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  WARNING: OPENAI_API_KEY environment variable not set. This demo will fail.")
        print("   Please set it to run the example usage.")
    else:
        asyncio.run(demo())
