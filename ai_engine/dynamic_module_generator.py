import os
from typing import Dict, Any

class DynamicModuleGenerator:
    """
    Generate per-user application modules (Python scripts) based on action extra_metadata.
    """

    def generate(self, user_id: str, action_extra_metadata: Dict[str, Any]) -> str:
        """
        Create a new .py module in user_data/{user_id}/application_modules/
        and return its filename.
        """
        # TODO: render a Jinja2 template with action details
        filename = f"{action_extra_metadata['id']}_module.py"
        path = os.path.join("user_data", user_id, "application_modules", filename)
        with open(path, "w") as f:
            f.write("# Auto-generated module stub\n")
            f.write("def run(context):\n    pass\n")
        return filename
