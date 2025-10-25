"""
Email Notification System for TraceTrack
Provides SendGrid-based email notifications with templates

FEATURES:
- Welcome emails for new users
- Password reset notifications
- Bill creation notifications
- Alert notifications for admins
- Batch email support
- Template system
- Error handling and logging

CONFIGURATION:
- Requires SENDGRID_API_KEY environment variable
- Optional FROM_EMAIL (defaults to noreply@tracetrack.app)
- Optional ADMIN_EMAIL for admin notifications
"""
import os
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import SendGrid
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logger.warning("SendGrid not available - email notifications disabled")


class EmailConfig:
    """Email configuration"""
    API_KEY = os.environ.get('SENDGRID_API_KEY')
    FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@tracetrack.app')
    FROM_NAME = os.environ.get('FROM_NAME', 'TraceTrack')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@tracetrack.app')
    
    @staticmethod
    def is_configured() -> bool:
        """Check if email is properly configured"""
        return bool(EmailConfig.API_KEY and SENDGRID_AVAILABLE)


class EmailTemplate:
    """Email template manager"""
    
    @staticmethod
    def welcome_email(username: str, email: str) -> Tuple[str, str]:
        """
        Generate welcome email for new users.
        
        Returns:
            Tuple of (subject, html_content)
        """
        subject = "Welcome to TraceTrack"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to TraceTrack</h1>
                </div>
                <div class="content">
                    <p>Hello {username},</p>
                    <p>Thank you for joining TraceTrack! Your account has been successfully created.</p>
                    <p><strong>Username:</strong> {username}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p>You can now log in and start managing your warehouse operations.</p>
                    <p>If you have any questions, please contact your administrator.</p>
                </div>
                <div class="footer">
                    <p>© {datetime.now().year} TraceTrack. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, html_content
    
    @staticmethod
    def password_reset(username: str, reset_link: str) -> Tuple[str, str]:
        """
        Generate password reset email.
        
        Returns:
            Tuple of (subject, html_content)
        """
        subject = "TraceTrack Password Reset Request"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #FF9800; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #FF9800; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .warning {{ color: #d32f2f; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hello {username},</p>
                    <p>We received a request to reset your TraceTrack password.</p>
                    <p>Click the button below to reset your password:</p>
                    <p><a href="{reset_link}" class="button">Reset Password</a></p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p><code>{reset_link}</code></p>
                    <p class="warning">If you did not request this reset, please ignore this email and contact your administrator immediately.</p>
                    <p>This link will expire in 1 hour for security reasons.</p>
                </div>
                <div class="footer">
                    <p>© {datetime.now().year} TraceTrack. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, html_content
    
    @staticmethod
    def bill_created(bill_id: str, parent_bags: int, created_by: str) -> Tuple[str, str]:
        """
        Generate bill creation notification.
        
        Returns:
            Tuple of (subject, html_content)
        """
        subject = f"New Bill Created: {bill_id}"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2196F3; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .info-box {{ background: white; padding: 15px; margin: 15px 0; border-left: 4px solid #2196F3; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>New Bill Created</h1>
                </div>
                <div class="content">
                    <p>A new bill has been created in TraceTrack:</p>
                    <div class="info-box">
                        <p><strong>Bill ID:</strong> {bill_id}</p>
                        <p><strong>Parent Bags:</strong> {parent_bags}</p>
                        <p><strong>Created By:</strong> {created_by}</p>
                        <p><strong>Created At:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                    <p>You can view and manage this bill in the TraceTrack system.</p>
                </div>
                <div class="footer">
                    <p>© {datetime.now().year} TraceTrack. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, html_content
    
    @staticmethod
    def admin_alert(title: str, message: str, details: Optional[Dict] = None) -> Tuple[str, str]:
        """
        Generate admin alert notification.
        
        Returns:
            Tuple of (subject, html_content)
        """
        subject = f"TraceTrack Alert: {title}"
        
        details_html = ""
        if details:
            details_html = "<div class='details'><h3>Details:</h3><ul>"
            for key, value in details.items():
                details_html += f"<li><strong>{key}:</strong> {value}</li>"
            details_html += "</ul></div>"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #f44336; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .alert-box {{ background: #ffebee; padding: 15px; margin: 15px 0; border-left: 4px solid #f44336; }}
                .details {{ background: white; padding: 15px; margin: 15px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>System Alert</h1>
                </div>
                <div class="content">
                    <div class="alert-box">
                        <h2>{title}</h2>
                        <p>{message}</p>
                    </div>
                    {details_html}
                    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    <p>Please review and take appropriate action if necessary.</p>
                </div>
                <div class="footer">
                    <p>© {datetime.now().year} TraceTrack. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, html_content


class EmailService:
    """SendGrid email service"""
    
    @staticmethod
    def send_email(to_email: str, subject: str, html_content: str, 
                   from_email: Optional[str] = None, from_name: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Send an email using SendGrid.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            from_email: Sender email (optional, uses config default)
            from_name: Sender name (optional, uses config default)
            
        Returns:
            Tuple of (success, error_message)
        """
        if not EmailConfig.is_configured():
            logger.error("SendGrid not configured - cannot send email")
            return False, "Email service not configured"
        
        try:
            # Use defaults if not provided
            from_email = from_email or EmailConfig.FROM_EMAIL
            from_name = from_name or EmailConfig.FROM_NAME
            
            # Create email message
            message = Mail(
                from_email=Email(from_email, from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            # Send email
            sg = SendGridAPIClient(EmailConfig.API_KEY)
            response = sg.send(message)
            
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Email sent successfully to {to_email}: {subject}")
                return True, None
            else:
                logger.error(f"SendGrid error: {response.status_code} - {response.body}")
                return False, f"SendGrid error: {response.status_code}"
        
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def send_batch_emails(recipients: List[Tuple[str, str, str]]) -> Tuple[int, int, List[str]]:
        """
        Send multiple emails in batch.
        
        Args:
            recipients: List of (email, subject, html_content) tuples
            
        Returns:
            Tuple of (sent_count, failed_count, error_messages)
        """
        sent = 0
        failed = 0
        errors = []
        
        for email, subject, html_content in recipients:
            success, error = EmailService.send_email(email, subject, html_content)
            if success:
                sent += 1
            else:
                failed += 1
                errors.append(f"{email}: {error}")
        
        return sent, failed, errors
    
    @staticmethod
    def send_welcome_email(username: str, email: str) -> Tuple[bool, Optional[str]]:
        """Send welcome email to new user"""
        subject, html_content = EmailTemplate.welcome_email(username, email)
        return EmailService.send_email(email, subject, html_content)
    
    @staticmethod
    def send_password_reset_email(username: str, email: str, reset_link: str) -> Tuple[bool, Optional[str]]:
        """Send password reset email"""
        subject, html_content = EmailTemplate.password_reset(username, reset_link)
        return EmailService.send_email(email, subject, html_content)
    
    @staticmethod
    def send_bill_notification(bill_id: str, parent_bags: int, created_by: str, 
                               admin_emails: List[str]) -> Tuple[int, int, List[str]]:
        """Send bill creation notification to admins"""
        subject, html_content = EmailTemplate.bill_created(bill_id, parent_bags, created_by)
        
        recipients = [(email, subject, html_content) for email in admin_emails]
        return EmailService.send_batch_emails(recipients)
    
    @staticmethod
    def send_admin_alert(title: str, message: str, details: Optional[Dict] = None, 
                        admin_emails: Optional[List[str]] = None) -> Tuple[int, int, List[str]]:
        """Send alert notification to admins"""
        subject, html_content = EmailTemplate.admin_alert(title, message, details)
        
        # Use configured admin email if not provided
        if not admin_emails:
            admin_emails = [EmailConfig.ADMIN_EMAIL]
        
        recipients = [(email, subject, html_content) for email in admin_emails]
        return EmailService.send_batch_emails(recipients)
