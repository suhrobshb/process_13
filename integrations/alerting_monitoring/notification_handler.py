class NotificationHandler:
    """
    Push notifications to Slack, Teams, or email.
    """

    def send_slack(self, channel: str, message: str):
        # TODO: integrate with slack_sdk
        pass

    def send_email(self, to: str, subject: str, body: str):
        # TODO: delegate to EmailHandler
        pass
