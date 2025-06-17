from typing import Any, Dict

class ApprovalHandler:
    """
    Pause execution for user approval, notify via UI/Slack/email.
    """

    def request_approval(self, step_id: str, data: Dict[str, Any]) -> bool:
        """
        Send notification, wait for user response. Return True if approved.
        """
        # TODO: push to notification_handler, block until response
        return True
