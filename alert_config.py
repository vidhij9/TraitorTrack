"""
Alert Configuration System for TraceTrack
Manages alerting channels, recipients, and thresholds
"""

import os
import json
import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class AlertConfig:
    """Centralized alert configuration management"""
    
    def __init__(self):
        # Alert Recipients Configuration
        self.recipients = {
            'email': {
                'critical': [
                    # Add critical alert email recipients here
                    # Example: 'admin@company.com', 'ops-team@company.com'
                ],
                'warning': [
                    # Add warning alert email recipients here
                    # Example: 'tech-lead@company.com'
                ],
                'info': [
                    # Add info alert email recipients here
                    # Example: 'monitoring@company.com'
                ]
            },
            'sms': {
                'critical': [
                    # Add critical alert phone numbers here
                    # Example: '+1234567890'
                ],
                'warning': []
            },
            'webhook': {
                # Add webhook URLs for different alert levels
                'critical': [],  # Example: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
                'warning': [],
                'info': []
            }
        }
        
        # Alert Thresholds Configuration
        self.thresholds = {
            'response_time': {
                'critical': 5.0,  # seconds
                'warning': 2.0    # seconds
            },
            'error_rate': {
                'critical': 0.05,  # 5% error rate
                'warning': 0.02    # 2% error rate
            },
            'concurrent_users': {
                'critical': 2000,  # Maximum expected concurrent users
                'warning': 1500
            },
            'database_connections': {
                'critical': 240,   # Near max pool size
                'warning': 200
            },
            'memory_usage': {
                'critical': 90,    # percentage
                'warning': 80
            },
            'cpu_usage': {
                'critical': 90,    # percentage
                'warning': 75
            },
            'cache_hit_rate': {
                'critical': 0.50,  # Below 50% hit rate is critical
                'warning': 0.70    # Below 70% hit rate is warning
            },
            'queue_size': {
                'critical': 10000,  # Maximum queue size
                'warning': 5000
            }
        }
        
        # Alert Channels Configuration
        self.channels = {
            'email': self._get_email_config(),
            'sms': self._get_sms_config(),
            'webhook': True,  # Enable webhook alerts
            'dashboard': True,  # Show alerts in dashboard
            'log': True  # Log all alerts
        }
        
        # Alert Rate Limiting (prevent alert storms)
        self.rate_limits = {
            'critical': 1,  # Minimum minutes between same critical alerts
            'warning': 5,   # Minimum minutes between same warning alerts
            'info': 15      # Minimum minutes between same info alerts
        }
        
        self.last_alerts = {}  # Track last alert times
        
    def _get_email_config(self):
        """Get email configuration from environment or defaults"""
        return {
            'enabled': os.environ.get('ENABLE_EMAIL_ALERTS', 'false').lower() == 'true',
            'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
            'sender_email': os.environ.get('ALERT_SENDER_EMAIL', 'alerts@tracetrack.com'),
            'sender_password': os.environ.get('ALERT_SENDER_PASSWORD', '')
        }
    
    def _get_sms_config(self):
        """Get SMS configuration (Twilio) from environment"""
        return {
            'enabled': os.environ.get('ENABLE_SMS_ALERTS', 'false').lower() == 'true',
            'account_sid': os.environ.get('TWILIO_ACCOUNT_SID', ''),
            'auth_token': os.environ.get('TWILIO_AUTH_TOKEN', ''),
            'from_number': os.environ.get('TWILIO_FROM_NUMBER', '')
        }
    
    def should_send_alert(self, alert_type: str, alert_key: str) -> bool:
        """Check if alert should be sent based on rate limiting"""
        if alert_key not in self.last_alerts:
            self.last_alerts[alert_key] = {}
        
        last_sent = self.last_alerts[alert_key].get(alert_type)
        if not last_sent:
            return True
        
        minutes_passed = (datetime.utcnow() - last_sent).total_seconds() / 60
        return minutes_passed >= self.rate_limits.get(alert_type, 5)
    
    def mark_alert_sent(self, alert_type: str, alert_key: str):
        """Mark that an alert has been sent"""
        if alert_key not in self.last_alerts:
            self.last_alerts[alert_key] = {}
        self.last_alerts[alert_key][alert_type] = datetime.utcnow()
    
    def send_alert(self, alert_type: str, title: str, message: str, metrics: Optional[Dict] = None):
        """Send alert through configured channels"""
        alert_key = f"{title}_{alert_type}"
        
        # Check rate limiting
        if not self.should_send_alert(alert_type, alert_key):
            logger.debug(f"Alert rate limited: {alert_key}")
            return False
        
        # Log the alert
        if self.channels.get('log'):
            logger.warning(f"ALERT [{alert_type.upper()}]: {title} - {message}")
            if metrics:
                logger.warning(f"Alert metrics: {json.dumps(metrics, default=str)}")
        
        # Send through configured channels
        success = False
        
        # Email alerts
        if self.channels.get('email', {}).get('enabled'):
            success = self._send_email_alert(alert_type, title, message, metrics) or success
        
        # SMS alerts (critical only)
        if alert_type == 'critical' and self.channels.get('sms', {}).get('enabled'):
            success = self._send_sms_alert(title, message) or success
        
        # Webhook alerts
        if self.channels.get('webhook'):
            success = self._send_webhook_alert(alert_type, title, message, metrics) or success
        
        # Mark alert as sent
        if success:
            self.mark_alert_sent(alert_type, alert_key)
        
        return success
    
    def _send_email_alert(self, alert_type: str, title: str, message: str, metrics: Optional[Dict] = None) -> bool:
        """Send email alert"""
        try:
            config = self.channels['email']
            recipients = self.recipients['email'].get(alert_type, [])
            
            if not recipients or not config.get('sender_password'):
                logger.debug(f"Email alerts not configured for {alert_type}")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert_type.upper()}] TraceTrack Alert: {title}"
            msg['From'] = config['sender_email']
            msg['To'] = ', '.join(recipients)
            
            # Create HTML content
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2 style="color: {'#ff0000' if alert_type == 'critical' else '#ff9900'};">
                        {alert_type.upper()} Alert: {title}
                    </h2>
                    <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    <p><strong>Message:</strong> {message}</p>
                    {self._format_metrics_html(metrics) if metrics else ''}
                    <hr>
                    <p style="font-size: 12px; color: #666;">
                        This is an automated alert from TraceTrack monitoring system.
                        <br>To modify alert settings, please contact your system administrator.
                    </p>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
                server.starttls()
                server.login(config['sender_email'], config['sender_password'])
                server.send_message(msg)
            
            logger.info(f"Email alert sent successfully to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def _send_sms_alert(self, title: str, message: str) -> bool:
        """Send SMS alert using Twilio"""
        try:
            config = self.channels['sms']
            recipients = self.recipients['sms'].get('critical', [])
            
            if not recipients or not config.get('auth_token'):
                logger.debug("SMS alerts not configured")
                return False
            
            # Import Twilio client (only if configured)
            from twilio.rest import Client
            
            client = Client(config['account_sid'], config['auth_token'])
            
            # Send to each recipient
            for phone_number in recipients:
                try:
                    message = client.messages.create(
                        body=f"CRITICAL ALERT: {title}\n{message[:140]}",
                        from_=config['from_number'],
                        to=phone_number
                    )
                    logger.info(f"SMS alert sent to {phone_number}")
                except Exception as e:
                    logger.error(f"Failed to send SMS to {phone_number}: {e}")
            
            return True
            
        except ImportError:
            logger.warning("Twilio library not installed for SMS alerts")
            return False
        except Exception as e:
            logger.error(f"Failed to send SMS alert: {e}")
            return False
    
    def _send_webhook_alert(self, alert_type: str, title: str, message: str, metrics: Optional[Dict] = None) -> bool:
        """Send webhook alert (e.g., Slack, Discord, etc.)"""
        try:
            webhooks = self.recipients['webhook'].get(alert_type, [])
            
            if not webhooks:
                logger.debug(f"No webhooks configured for {alert_type}")
                return False
            
            # Prepare payload
            payload = {
                'username': 'TraceTrack Monitoring',
                'icon_emoji': ':warning:' if alert_type == 'warning' else ':rotating_light:',
                'attachments': [{
                    'color': 'danger' if alert_type == 'critical' else 'warning',
                    'title': f"{alert_type.upper()}: {title}",
                    'text': message,
                    'fields': self._format_metrics_webhook(metrics) if metrics else [],
                    'footer': 'TraceTrack Monitoring',
                    'ts': int(datetime.utcnow().timestamp())
                }]
            }
            
            # Send to each webhook
            success = False
            for webhook_url in webhooks:
                try:
                    response = requests.post(webhook_url, json=payload, timeout=5)
                    if response.status_code == 200:
                        logger.info(f"Webhook alert sent successfully")
                        success = True
                except Exception as e:
                    logger.error(f"Failed to send webhook alert: {e}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False
    
    def _format_metrics_html(self, metrics: Dict) -> str:
        """Format metrics for HTML email"""
        if not metrics:
            return ""
        
        html = "<h3>Metrics:</h3><ul>"
        for key, value in metrics.items():
            html += f"<li><strong>{key}:</strong> {value}</li>"
        html += "</ul>"
        return html
    
    def _format_metrics_webhook(self, metrics: Dict) -> List[Dict]:
        """Format metrics for webhook payload"""
        if not metrics:
            return []
        
        fields = []
        for key, value in metrics.items():
            fields.append({
                'title': key.replace('_', ' ').title(),
                'value': str(value),
                'short': True
            })
        return fields
    
    def get_dashboard_config(self) -> Dict:
        """Get configuration for dashboard display"""
        return {
            'thresholds': self.thresholds,
            'channels': {k: v if not isinstance(v, dict) else v.get('enabled', False) 
                        for k, v in self.channels.items()},
            'rate_limits': self.rate_limits,
            'recipients_configured': {
                'email': len(self.recipients['email'].get('critical', [])) > 0,
                'sms': len(self.recipients['sms'].get('critical', [])) > 0,
                'webhook': len(self.recipients['webhook'].get('critical', [])) > 0
            }
        }

# Global alert configuration instance
alert_config = AlertConfig()

def setup_alert_recipients(email_recipients: List[str] = None, 
                          sms_recipients: List[str] = None,
                          webhook_urls: List[str] = None):
    """
    Utility function to set up alert recipients programmatically
    
    Usage:
        setup_alert_recipients(
            email_recipients=['admin@company.com', 'ops@company.com'],
            sms_recipients=['+1234567890'],
            webhook_urls=['https://hooks.slack.com/services/YOUR/WEBHOOK']
        )
    """
    global alert_config
    
    if email_recipients:
        alert_config.recipients['email']['critical'] = email_recipients
        alert_config.recipients['email']['warning'] = email_recipients[:1]  # First recipient for warnings
        logger.info(f"Configured {len(email_recipients)} email recipients")
    
    if sms_recipients:
        alert_config.recipients['sms']['critical'] = sms_recipients
        logger.info(f"Configured {len(sms_recipients)} SMS recipients")
    
    if webhook_urls:
        alert_config.recipients['webhook']['critical'] = webhook_urls
        alert_config.recipients['webhook']['warning'] = webhook_urls
        logger.info(f"Configured {len(webhook_urls)} webhook URLs")

# Example configuration (uncomment and modify as needed):
# setup_alert_recipients(
#     email_recipients=['admin@tracetrack.com'],
#     sms_recipients=['+1234567890'],
#     webhook_urls=['https://hooks.slack.com/services/YOUR/WEBHOOK']
# )