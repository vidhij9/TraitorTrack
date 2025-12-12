"""
Email Notification System for TraitorTrack
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
- Optional FROM_EMAIL (defaults to vidhi.jn39@gmail.com)
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
    """Email configuration with feature flags for cost control"""
    API_KEY = os.environ.get('SENDGRID_API_KEY')
    FROM_EMAIL = os.environ.get('FROM_EMAIL', 'vidhi.jn39@gmail.com')
    FROM_NAME = os.environ.get('FROM_NAME', 'TraitorTrack')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'vidhi.jn39@gmail.com')
    
    # Feature flags for email notifications (set to 'false' to disable)
    WELCOME_EMAILS_ENABLED = os.environ.get('ENABLE_WELCOME_EMAILS', 'true').lower() == 'true'
    BILL_NOTIFICATION_EMAILS_ENABLED = os.environ.get('ENABLE_BILL_EMAILS', 'false').lower() == 'true'
    PASSWORD_RESET_EMAILS_ENABLED = os.environ.get('ENABLE_PASSWORD_RESET_EMAILS', 'true').lower() == 'true'
    ADMIN_ALERT_EMAILS_ENABLED = os.environ.get('ENABLE_ADMIN_ALERT_EMAILS', 'true').lower() == 'true'
    
    @staticmethod
    def is_configured() -> bool:
        """Check if email is properly configured"""
        return bool(EmailConfig.API_KEY and SENDGRID_AVAILABLE)
    
    @staticmethod
    def is_feature_enabled(feature: str) -> bool:
        """Check if a specific email feature is enabled.
        
        Args:
            feature: One of 'welcome', 'bill', 'password_reset', 'admin_alert'
        
        Returns:
            True if the feature is enabled AND email is configured
        """
        if not EmailConfig.is_configured():
            return False
        
        feature_map = {
            'welcome': EmailConfig.WELCOME_EMAILS_ENABLED,
            'bill': EmailConfig.BILL_NOTIFICATION_EMAILS_ENABLED,
            'password_reset': EmailConfig.PASSWORD_RESET_EMAILS_ENABLED,
            'admin_alert': EmailConfig.ADMIN_ALERT_EMAILS_ENABLED
        }
        return feature_map.get(feature, False)


class EmailTemplate:
    """Email template manager"""
    
    @staticmethod
    def welcome_email(username: str, email: str) -> Tuple[str, str]:
        """
        Generate welcome email for new users.
        
        Returns:
            Tuple of (subject, html_content)
        """
        subject = "Welcome to TraitorTrack"
        
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
                    <h1>Welcome to TraitorTrack</h1>
                </div>
                <div class="content">
                    <p>Hello {username},</p>
                    <p>Thank you for joining TraitorTrack! Your account has been successfully created.</p>
                    <p><strong>Username:</strong> {username}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p>You can now log in and start managing your warehouse operations.</p>
                    <p>If you have any questions, please contact your administrator.</p>
                </div>
                <div class="footer">
                    <p>© {datetime.now().year} TraitorTrack. All rights reserved.</p>
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
        subject = "TraitorTrack Password Reset Request"
        
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
                    <p>We received a request to reset your TraitorTrack password.</p>
                    <p>Click the button below to reset your password:</p>
                    <p><a href="{reset_link}" class="button">Reset Password</a></p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p><code>{reset_link}</code></p>
                    <p class="warning">If you did not request this reset, please ignore this email and contact your administrator immediately.</p>
                    <p>This link will expire in 1 hour for security reasons.</p>
                </div>
                <div class="footer">
                    <p>© {datetime.now().year} TraitorTrack. All rights reserved.</p>
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
                    <p>A new bill has been created in TraitorTrack:</p>
                    <div class="info-box">
                        <p><strong>Bill ID:</strong> {bill_id}</p>
                        <p><strong>Parent Bags:</strong> {parent_bags}</p>
                        <p><strong>Created By:</strong> {created_by}</p>
                        <p><strong>Created At:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                    <p>You can view and manage this bill in the TraitorTrack system.</p>
                </div>
                <div class="footer">
                    <p>© {datetime.now().year} TraitorTrack. All rights reserved.</p>
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
        subject = f"TraitorTrack Alert: {title}"
        
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
                    <p>© {datetime.now().year} TraitorTrack. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, html_content
    
    @staticmethod
    def eod_bill_summary(report_date: str, eod_data: Dict) -> Tuple[str, str]:
        """
        Generate End of Day (EOD) bill summary email.
        
        Args:
            report_date: Date of the report (formatted string)
            eod_data: Dictionary containing EOD summary data
            
        Returns:
            Tuple of (subject, html_content)
        """
        subject = f"TraitorTrack EOD Bill Summary - {report_date}"
        
        # Build bills by status section
        status_rows = ""
        for status, count in eod_data.get('bills_by_status', {}).items():
            status_rows += f"<tr><td style='padding: 8px; border: 1px solid #ddd;'>{status.title()}</td><td style='padding: 8px; border: 1px solid #ddd; text-align: right;'>{count}</td></tr>"
        
        if not status_rows:
            status_rows = "<tr><td colspan='2' style='padding: 8px; border: 1px solid #ddd; text-align: center; color: #999;'>No bills created today</td></tr>"
        
        # Build bills by user section
        user_rows = ""
        for username, count in eod_data.get('bills_by_user', {}).items():
            user_rows += f"<tr><td style='padding: 8px; border: 1px solid #ddd;'>{username}</td><td style='padding: 8px; border: 1px solid #ddd; text-align: right;'>{count}</td></tr>"
        
        if not user_rows:
            user_rows = "<tr><td colspan='2' style='padding: 8px; border: 1px solid #ddd; text-align: center; color: #999;'>No bills created today</td></tr>"
        
        # Build detailed bills table
        detail_rows = ""
        for bill in eod_data.get('detailed_bills', []):
            detail_rows += f"""
            <tr>
                <td style='padding: 8px; border: 1px solid #ddd;'>{bill.get('bill_id', 'N/A')}</td>
                <td style='padding: 8px; border: 1px solid #ddd;'>{bill.get('created_by', 'Unknown')}</td>
                <td style='padding: 8px; border: 1px solid #ddd;'>{bill.get('status', 'N/A').title()}</td>
                <td style='padding: 8px; border: 1px solid #ddd; text-align: right;'>{bill.get('parent_bags', 0)}</td>
                <td style='padding: 8px; border: 1px solid #ddd; text-align: right;'>{bill.get('child_bags', 0)}</td>
                <td style='padding: 8px; border: 1px solid #ddd; text-align: right;'>{bill.get('weight_kg', 0):.2f}</td>
            </tr>
            """
        
        if not detail_rows:
            detail_rows = "<tr><td colspan='6' style='padding: 8px; border: 1px solid #ddd; text-align: center; color: #999;'>No bills created today</td></tr>"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #1976D2; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .summary-box {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0; }}
                .stat-card {{ background: #E3F2FD; padding: 15px; border-radius: 8px; border-left: 4px solid #1976D2; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #1976D2; margin: 5px 0; }}
                .stat-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
                .section-title {{ color: #1976D2; border-bottom: 2px solid #1976D2; padding-bottom: 8px; margin: 20px 0 15px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; background: white; }}
                th {{ background: #1976D2; color: white; padding: 12px 8px; text-align: left; font-weight: 600; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                @media only screen and (max-width: 600px) {{
                    .stats-grid {{ grid-template-columns: 1fr; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 End of Day Bill Summary</h1>
                    <p style="margin: 5px 0; font-size: 16px;">{report_date}</p>
                </div>
                <div class="content">
                    <div class="summary-box">
                        <h2 style="margin-top: 0; color: #1976D2;">Overview</h2>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <div class="stat-label">Total Bills</div>
                                <div class="stat-value">{eod_data.get('total_bills', 0)}</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">Parent Bags</div>
                                <div class="stat-value">{eod_data.get('total_parent_bags', 0)}</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">Child Bags</div>
                                <div class="stat-value">{eod_data.get('total_child_bags', 0)}</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">Total Weight (kg)</div>
                                <div class="stat-value">{eod_data.get('total_weight_kg', 0):.2f}</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="summary-box">
                        <h3 class="section-title">Bills by Status</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Status</th>
                                    <th style="text-align: right;">Count</th>
                                </tr>
                            </thead>
                            <tbody>
                                {status_rows}
                            </tbody>
                        </table>
                    </div>
                    
                    <div class="summary-box">
                        <h3 class="section-title">Bills by User</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th style="text-align: right;">Bills Created</th>
                                </tr>
                            </thead>
                            <tbody>
                                {user_rows}
                            </tbody>
                        </table>
                    </div>
                    
                    <div class="summary-box">
                        <h3 class="section-title">Detailed Bill List</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Bill ID</th>
                                    <th>Created By</th>
                                    <th>Status</th>
                                    <th style="text-align: right;">Parent Bags</th>
                                    <th style="text-align: right;">Child Bags</th>
                                    <th style="text-align: right;">Weight (kg)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {detail_rows}
                            </tbody>
                        </table>
                    </div>
                    
                    <p style="margin-top: 20px; padding: 15px; background: #FFF3E0; border-left: 4px solid #FF9800; border-radius: 4px;">
                        <strong>Note:</strong> This is an automated End of Day summary report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
                    </p>
                </div>
                <div class="footer">
                    <p>© {datetime.now().year} TraitorTrack. All rights reserved.</p>
                    <p style="color: #999; font-size: 11px;">This is an automated email. Please do not reply.</p>
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
            
            # Create email message - type: ignore for SendGrid library types
            message = Mail(  # type: ignore[misc]
                from_email=Email(from_email, from_name),  # type: ignore[misc]
                to_emails=To(to_email),  # type: ignore[misc]
                subject=subject,
                html_content=Content("text/html", html_content)  # type: ignore[misc]
            )
            
            # Send email
            sg = SendGridAPIClient(EmailConfig.API_KEY)  # type: ignore[misc]
            response = sg.send(message)
            
            # SendGrid response has status_code attribute
            status = getattr(response, 'status_code', None)
            if status and 200 <= status < 300:
                logger.info(f"Email sent successfully to {to_email}: {subject}")
                return True, None
            else:
                error_body = getattr(response, 'body', 'Unknown error')
                logger.error(f"SendGrid error: {status} - {error_body}")
                return False, f"SendGrid error: {status}"
        
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
        """Send welcome email to new user.
        
        Respects ENABLE_WELCOME_EMAILS feature flag for cost control.
        """
        if not EmailConfig.is_feature_enabled('welcome'):
            logger.debug(f"Welcome email skipped for {email} - feature disabled")
            return True, None  # Return success to avoid error handling in caller
        
        subject, html_content = EmailTemplate.welcome_email(username, email)
        return EmailService.send_email(email, subject, html_content)
    
    @staticmethod
    def send_password_reset_email(username: str, email: str, reset_link: str) -> Tuple[bool, Optional[str]]:
        """
        Send password reset email.
        
        SECURITY: Accepts None values for anti-enumeration. When username/email is None,
        still makes SendGrid API call with synthetic data to ensure constant-time behavior.
        """
        # SECURITY: For anti-enumeration, use fake data but still call SendGrid API
        if username is None or email is None:
            username = "fake_user"
            email = "noreply@example.com"  # Will fail but takes same time as real attempts
            reset_link = "https://example.com/reset/fake"
            
        subject, html_content = EmailTemplate.password_reset(username, reset_link)
        return EmailService.send_email(email, subject, html_content)
    
    @staticmethod
    def send_bill_notification(bill_id: str, parent_bags: int, created_by: str, 
                               admin_emails: List[str]) -> Tuple[int, int, List[str]]:
        """Send bill creation notification to admins.
        
        Respects ENABLE_BILL_EMAILS feature flag for cost control.
        Bill emails are disabled by default to reduce costs.
        """
        if not EmailConfig.is_feature_enabled('bill'):
            logger.debug(f"Bill notification skipped for {bill_id} - feature disabled")
            return 0, 0, []  # Return success with no emails sent
        
        subject, html_content = EmailTemplate.bill_created(bill_id, parent_bags, created_by)
        
        recipients = [(email, subject, html_content) for email in admin_emails]
        return EmailService.send_batch_emails(recipients)
    
    @staticmethod
    def send_admin_alert(title: str, message: str, details: Optional[Dict] = None, 
                        admin_emails: Optional[List[str]] = None) -> Tuple[int, int, List[str]]:
        """Send alert notification to admins.
        
        Respects ENABLE_ADMIN_ALERT_EMAILS feature flag.
        """
        if not EmailConfig.is_feature_enabled('admin_alert'):
            logger.debug(f"Admin alert skipped: {title} - feature disabled")
            return 0, 0, []  # Return success with no emails sent
        
        subject, html_content = EmailTemplate.admin_alert(title, message, details)
        
        # Use configured admin email if not provided
        if not admin_emails:
            admin_emails = [EmailConfig.ADMIN_EMAIL]
        
        recipients = [(email, subject, html_content) for email in admin_emails]
        return EmailService.send_batch_emails(recipients)
    
    @staticmethod
    def send_eod_summary(recipient_emails: List[str], report_date: str, eod_data: Dict) -> Tuple[int, int, List[str]]:
        """
        Send End of Day bill summary to recipients.
        
        Args:
            recipient_emails: List of email addresses to send to
            report_date: Date of the report (formatted string)
            eod_data: Dictionary containing EOD summary data
            
        Returns:
            Tuple of (sent_count, failed_count, error_messages)
        """
        if not EmailConfig.is_configured():
            logger.error("SendGrid not configured - cannot send EOD summary")
            return 0, len(recipient_emails), ["Email service not configured"]
        
        if not recipient_emails:
            logger.warning("No recipients provided for EOD summary")
            return 0, 0, ["No recipients provided"]
        
        try:
            # Generate email content from template
            subject, html_content = EmailTemplate.eod_bill_summary(report_date, eod_data)
            
            # Create recipients list for batch sending
            recipients = [(email, subject, html_content) for email in recipient_emails]
            
            # Send emails in batch
            sent, failed, errors = EmailService.send_batch_emails(recipients)
            
            logger.info(f"EOD summary sent: {sent} successful, {failed} failed to {len(recipient_emails)} recipients")
            return sent, failed, errors
        
        except Exception as e:
            logger.error(f"Error sending EOD summary: {str(e)}")
            return 0, len(recipient_emails), [f"Error generating email: {str(e)}"]


# Convenience function for pool monitoring and other alert systems
def send_admin_alert_email(subject: str, message: str, details: Optional[Dict] = None, 
                           admin_emails: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    """
    Send alert email to admins (convenience wrapper for EmailService.send_admin_alert)
    
    Args:
        subject: Email subject (will be used as title)
        message: HTML message content
        details: Optional dictionary of additional details
        admin_emails: Optional list of admin emails (uses config default if not provided)
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        sent, failed, errors = EmailService.send_admin_alert(subject, message, details, admin_emails)
        if sent > 0:
            return True, None
        else:
            return False, ', '.join(errors) if errors else "No emails sent"
    except Exception as e:
        logger.error(f"Error in send_admin_alert_email: {e}")
        return False, str(e)
