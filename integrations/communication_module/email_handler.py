import smtplib
import os
import logging
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class EmailHandler:
    """
    Complete email handler for sending automated emails via SMTP.
    Supports attachments, HTML content, and multiple providers.
    """

    def __init__(self, 
                 smtp_server: str = None,
                 smtp_port: int = None,
                 username: str = None,
                 password: str = None,
                 use_tls: bool = True,
                 use_ssl: bool = False):
        """
        Initialize email handler with SMTP configuration.
        
        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            username: Email username
            password: Email password or app password
            use_tls: Use STARTTLS (default: True)
            use_ssl: Use SSL connection (default: False)
        """
        # Load from environment variables if not provided
        self.smtp_server = smtp_server or os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '587'))
        self.username = username or os.getenv('SMTP_USERNAME')
        self.password = password or os.getenv('SMTP_PASSWORD')
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        
        # Validate configuration
        if not self.username or not self.password:
            logger.warning("Email handler: SMTP credentials not configured")
            self.configured = False
        else:
            self.configured = True
            logger.info(f"Email handler configured for {self.smtp_server}:{self.smtp_port}")

    def send_email(self, 
                   to: str, 
                   subject: str, 
                   body: str, 
                   attachments: List[str] = None,
                   cc: str = None,
                   bcc: str = None,
                   html_body: str = None,
                   from_email: str = None) -> bool:
        """
        Send an email via SMTP.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Plain text body
            attachments: List of file paths to attach
            cc: CC recipients (comma-separated)
            bcc: BCC recipients (comma-separated)
            html_body: HTML body content (optional)
            from_email: Custom from email (default: username)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.configured:
            logger.error("Email handler not configured with SMTP credentials")
            return False
        
        try:
            # Create message
            if html_body:
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(body, 'plain'))
                msg.attach(MIMEText(html_body, 'html'))
            else:
                msg = MIMEMultipart()
                msg.attach(MIMEText(body, 'plain'))
            
            # Set headers
            msg['From'] = from_email or self.username
            msg['To'] = to
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = cc
            if bcc:
                msg['Bcc'] = bcc
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    if not self._attach_file(msg, file_path):
                        logger.warning(f"Failed to attach file: {file_path}")
            
            # Send email
            return self._send_via_smtp(msg, to, cc, bcc)
            
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return False

    def _attach_file(self, msg: MIMEMultipart, file_path: str) -> bool:
        """Attach a file to the email message"""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"Attachment file not found: {file_path}")
                return False
            
            with open(path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {path.name}'
            )
            
            msg.attach(part)
            return True
            
        except Exception as e:
            logger.error(f"Failed to attach file {file_path}: {e}")
            return False

    def _send_via_smtp(self, msg: MIMEMultipart, to: str, cc: str = None, bcc: str = None) -> bool:
        """Send email via SMTP server"""
        try:
            # Create SMTP connection
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            # Enable TLS if configured
            if self.use_tls and not self.use_ssl:
                server.starttls()
            
            # Login
            server.login(self.username, self.password)
            
            # Prepare recipient list
            recipients = [to]
            if cc:
                recipients.extend([email.strip() for email in cc.split(',')])
            if bcc:
                recipients.extend([email.strip() for email in bcc.split(',')])
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.username, recipients, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {to}")
            return True
            
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            return False

    def send_notification_email(self, 
                               recipient: str, 
                               notification_type: str, 
                               title: str, 
                               message: str, 
                               workflow_id: str = None,
                               execution_id: str = None) -> bool:
        """
        Send a workflow notification email with predefined template.
        
        Args:
            recipient: Email recipient
            notification_type: Type of notification (success, failure, warning)
            title: Notification title
            message: Notification message
            workflow_id: Related workflow ID
            execution_id: Related execution ID
            
        Returns:
            True if sent successfully
        """
        # Create HTML template
        html_body = self._create_notification_html(
            notification_type, title, message, workflow_id, execution_id
        )
        
        # Set subject based on type
        subject_prefix = {
            'success': '✅ Success',
            'failure': '❌ Failure',
            'warning': '⚠️ Warning',
            'info': 'ℹ️ Info'
        }.get(notification_type, 'Notification')
        
        subject = f"{subject_prefix}: {title}"
        
        return self.send_email(
            to=recipient,
            subject=subject,
            body=message,
            html_body=html_body
        )

    def _create_notification_html(self, 
                                 notification_type: str, 
                                 title: str, 
                                 message: str, 
                                 workflow_id: str = None, 
                                 execution_id: str = None) -> str:
        """Create HTML template for notification emails"""
        
        color_map = {
            'success': '#4CAF50',
            'failure': '#F44336',
            'warning': '#FF9800',
            'info': '#2196F3'
        }
        
        color = color_map.get(notification_type, '#666666')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{title}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="border-left: 4px solid {color}; padding-left: 20px; margin-bottom: 20px;">
                <h2 style="color: {color}; margin-top: 0;">{title}</h2>
                <p style="font-size: 16px; margin-bottom: 20px;">{message}</p>
                
                {f'<p><strong>Workflow ID:</strong> {workflow_id}</p>' if workflow_id else ''}
                {f'<p><strong>Execution ID:</strong> {execution_id}</p>' if execution_id else ''}
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                
                <p style="font-size: 14px; color: #666;">
                    This notification was sent by the AI Automation Platform.
                    <br>
                    Timestamp: {os.environ.get('TZ', 'UTC')} {__import__('datetime').datetime.now().isoformat()}
                </p>
            </div>
        </body>
        </html>
        """
        
        return html

    def send_workflow_completion_email(self, 
                                      recipient: str, 
                                      workflow_name: str, 
                                      execution_id: str, 
                                      status: str, 
                                      duration: float = None, 
                                      error_message: str = None) -> bool:
        """Send workflow completion notification"""
        
        if status == 'completed':
            notification_type = 'success'
            title = f"Workflow '{workflow_name}' Completed Successfully"
            message = f"Your workflow has finished executing successfully."
            if duration:
                message += f" Duration: {duration:.2f} seconds."
        else:
            notification_type = 'failure'
            title = f"Workflow '{workflow_name}' Failed"
            message = f"Your workflow execution failed."
            if error_message:
                message += f" Error: {error_message}"
        
        return self.send_notification_email(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            execution_id=execution_id
        )

    def health_check(self) -> Dict[str, Any]:
        """Perform email service health check"""
        if not self.configured:
            return {
                "status": "not_configured",
                "error": "SMTP credentials not provided"
            }
        
        try:
            # Test SMTP connection
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            if self.use_tls and not self.use_ssl:
                server.starttls()
            
            # Test login
            server.login(self.username, self.password)
            server.quit()
            
            return {
                "status": "healthy",
                "smtp_server": self.smtp_server,
                "smtp_port": self.smtp_port,
                "username": self.username
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Singleton instance
_email_handler = None


def get_email_handler() -> EmailHandler:
    """Get singleton email handler instance"""
    global _email_handler
    if _email_handler is None:
        _email_handler = EmailHandler()
    return _email_handler


def is_email_configured() -> bool:
    """Check if email is properly configured"""
    handler = get_email_handler()
    return handler.configured


# Usage examples
if __name__ == "__main__":
    # Test email handler
    handler = get_email_handler()
    
    # Health check
    health = handler.health_check()
    print("Email Health Check:", health)
    
    # Test notification (if configured)
    if handler.configured:
        result = handler.send_notification_email(
            recipient="test@example.com",
            notification_type="info",
            title="Test Notification",
            message="This is a test notification from the AI Automation Platform.",
            workflow_id="test_workflow_123"
        )
        print(f"Test email sent: {result}")
    else:
        print("Email not configured - set SMTP_USERNAME and SMTP_PASSWORD environment variables")
