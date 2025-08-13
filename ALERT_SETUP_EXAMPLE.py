#!/usr/bin/env python3
"""
Example Alert Configuration Setup for TraceTrack
Run this script to configure your alert recipients and thresholds
"""

from alert_config import setup_alert_recipients, alert_config

def configure_production_alerts():
    """
    Configure alert recipients for production deployment
    Replace with your actual contact information
    """
    
    # Configure alert recipients
    setup_alert_recipients(
        # Email recipients for different alert levels
        email_recipients=[
            'admin@yourcompany.com',          # Primary admin
            'ops-team@yourcompany.com',       # Operations team
            'tech-lead@yourcompany.com'       # Technical lead
        ],
        
        # SMS recipients for critical alerts only
        sms_recipients=[
            '+1234567890',  # Primary on-call number
            '+0987654321'   # Backup on-call number
        ],
        
        # Webhook URLs for Slack/Discord/Teams integration
        webhook_urls=[
            'https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
            # 'https://discord.com/api/webhooks/YOUR/WEBHOOK/URL'
        ]
    )
    
    print("✓ Alert recipients configured")
    print(f"✓ Email alerts: {len(alert_config.recipients['email']['critical'])} recipients")
    print(f"✓ SMS alerts: {len(alert_config.recipients['sms']['critical'])} recipients")
    print(f"✓ Webhook alerts: {len(alert_config.recipients['webhook']['critical'])} webhooks")

def set_environment_variables():
    """
    Display required environment variables for alert channels
    """
    print("\n" + "="*60)
    print("REQUIRED ENVIRONMENT VARIABLES")
    print("="*60)
    
    print("\n📧 For Email Alerts:")
    print("ENABLE_EMAIL_ALERTS=true")
    print("SMTP_SERVER=smtp.gmail.com")
    print("SMTP_PORT=587")
    print("ALERT_SENDER_EMAIL=alerts@yourcompany.com")
    print("ALERT_SENDER_PASSWORD=your_app_password")
    
    print("\n📱 For SMS Alerts (Twilio):")
    print("ENABLE_SMS_ALERTS=true")
    print("TWILIO_ACCOUNT_SID=your_account_sid")
    print("TWILIO_AUTH_TOKEN=your_auth_token")
    print("TWILIO_FROM_NUMBER=+1234567890")
    
    print("\n🔗 Webhook alerts are configured directly in the code above")

def test_alert_system():
    """
    Send a test alert to verify configuration
    """
    print("\n" + "="*60)
    print("TESTING ALERT SYSTEM")
    print("="*60)
    
    # Send test alerts
    alert_config.send_alert(
        'info', 
        'Test Alert', 
        'This is a test alert to verify your configuration is working correctly.',
        {'test_metric': 'success', 'timestamp': '2025-08-13'}
    )
    
    alert_config.send_alert(
        'warning',
        'Test Warning Alert',
        'This is a test warning alert.',
        {'warning_level': 'medium'}
    )
    
    print("✓ Test alerts sent")
    print("Check your configured channels for test messages")

def display_current_thresholds():
    """
    Display current alert thresholds
    """
    print("\n" + "="*60)
    print("CURRENT ALERT THRESHOLDS")
    print("="*60)
    
    for metric, thresholds in alert_config.thresholds.items():
        if isinstance(thresholds, dict):
            print(f"\n{metric.replace('_', ' ').title()}:")
            for level, value in thresholds.items():
                print(f"  {level}: {value}")
        else:
            print(f"{metric.replace('_', ' ').title()}: {thresholds}")

if __name__ == "__main__":
    print("TraceTrack Alert Configuration Setup")
    print("="*60)
    
    print("\n1. Configuring alert recipients...")
    configure_production_alerts()
    
    print("\n2. Environment variables needed...")
    set_environment_variables()
    
    print("\n3. Current alert thresholds...")
    display_current_thresholds()
    
    print("\n4. Testing alert system...")
    try:
        test_alert_system()
    except Exception as e:
        print(f"⚠ Alert test failed: {e}")
        print("This is normal if environment variables are not set yet")
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. Set the environment variables shown above")
    print("2. Update the email/phone/webhook URLs in this script")
    print("3. Run this script again to test alerts")
    print("4. Access the analytics dashboard at /analytics/dashboard")
    print("5. Monitor system health and adjust thresholds as needed")
    print("\nFor more details, see MONITORING_GUIDE.md")