import yaml
from typing import Dict, Any

class WorkflowSerializer:
    """
    Convert in-memory workflow definitions to/from YAML.
    """

    def to_yaml(self, workflow: Dict[str, Any]) -> str:
        return yaml.safe_dump(workflow)

    def from_yaml(self, yaml_str: str) -> Dict[str, Any]:
        return yaml.safe_load(yaml_str)
