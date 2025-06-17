import smtplib
from email.message import EmailMessage

class EmailHandler:
    """
    Send and receive automated emails.
    """

    def send_email(self, to: str, subject: str, body: str, attachments: list = None):
        """
        Send an email via SMTP or a transactional API (SendGrid, SES).
        """
        msg = EmailMessage()
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        # TODO: attach files
        # TODO: send via smtplib or API
