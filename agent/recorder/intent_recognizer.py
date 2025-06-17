import os
import json
import openai
from typing import Dict, Any

openai.api_key = os.getenv("OPENAI_API_KEY")

class IntentRecognizer:
    """
    Use an LLM to tag each event (or cluster) with a semantic intent.
    """

    def tag_intent(self, context: Dict[str, Any]) -> str:
        prompt = (
            "You are an assistant that reads a user action context "
            "and returns a short intent label.\n"
            f"Context JSON: {json.dumps(context)}\n"
            "Return only the intent label."
        )
        resp = openai.ChatCompletion.create(
            model="gpt-4",  # or your preferred model
            messages=[{"role":"user","content":prompt}],
            max_tokens=10,
            temperature=0.0,
        )
        return resp.choices[0].message.content.strip()
