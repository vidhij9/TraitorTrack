"""
Daily Email Reporting System for Billers
Sends comprehensive daily activity reports to all billers
"""

import os
import logging
from datetime import datetime, timedelta, time
from typing import List, Dict, Any
import threading
import schedule
from sqlalchemy import text
from flask import render_template_string

logger = logging.getLogger(__name__)

# Email configuration
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@tracetrack.com')
COMPANY_NAME = "TraceTrack"

class DailyReportSystem:
    """Manages daily email reports for billers"""
    
    def __init__(self, db, app):
        self.db = db
        self.app = app
        self.is_running = False
        self.report_time = "18:00"  # 6 PM daily
        
    def get_biller_daily_stats(self, user_id: int, date: datetime) -> Dict[str, Any]:
        """Get comprehensive daily statistics for a biller"""
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        try:
            # Get all statistics in a single optimized query
            result = self.db.session.execute(text("""
                WITH daily_stats AS (
                    -- Bills created today
                    SELECT 
                        COUNT(DISTINCT b.id) as bills_created,
                        COUNT(DISTINCT bb.bag_id) as bags_linked,
                        SUM(b.total_weight_kg) as total_weight,
                        COUNT(DISTINCT CASE WHEN b.status = 'completed' THEN b.id END) as bills_completed
                    FROM bill b
                    LEFT JOIN bill_bag bb ON bb.bill_id = b.id
                    WHERE b.created_by_id = :user_id
                        AND b.created_at >= :start_date
                        AND b.created_at < :end_date
                ),
                scan_stats AS (
                    -- Scanning activity
                    SELECT 
                        COUNT(*) as total_scans,
                        COUNT(DISTINCT parent_bag_id) as parent_bags_scanned,
                        COUNT(DISTINCT child_bag_id) as child_bags_scanned
                    FROM scan
                    WHERE user_id = :user_id
                        AND timestamp >= :start_date
                        AND timestamp < :end_date
                ),
                bill_details AS (
                    -- Detailed bill information
                    SELECT 
                        b.bill_id,
                        b.destination,
                        b.parent_bag_count,
                        COUNT(DISTINCT bb.bag_id) as linked_bags,
                        b.total_weight_kg,
                        b.status,
                        b.created_at
                    FROM bill b
                    LEFT JOIN bill_bag bb ON bb.bill_id = b.id
                    WHERE b.created_by_id = :user_id
                        AND b.created_at >= :start_date
                        AND b.created_at < :end_date
                    GROUP BY b.id, b.bill_id, b.destination, b.parent_bag_count, 
                             b.total_weight_kg, b.status, b.created_at
                    ORDER BY b.created_at DESC
                )
                SELECT 
                    ds.bills_created,
                    ds.bags_linked,
                    ds.total_weight,
                    ds.bills_completed,
                    ss.total_scans,
                    ss.parent_bags_scanned,
                    ss.child_bags_scanned,
                    (SELECT json_agg(row_to_json(bd)) FROM bill_details bd) as bill_details
                FROM daily_stats ds, scan_stats ss
            """), {
                'user_id': user_id,
                'start_date': start_date,
                'end_date': end_date
            }).fetchone()
            
            if result:
                import json
                bill_details = json.loads(result.bill_details) if result.bill_details else []
                
                return {
                    'bills_created': result.bills_created or 0,
                    'bags_linked': result.bags_linked or 0,
                    'total_weight': float(result.total_weight or 0),
                    'bills_completed': result.bills_completed or 0,
                    'total_scans': result.total_scans or 0,
                    'parent_bags_scanned': result.parent_bags_scanned or 0,
                    'child_bags_scanned': result.child_bags_scanned or 0,
                    'bill_details': bill_details,
                    'report_date': date.strftime('%B %d, %Y')
                }
            
            return self._empty_stats(date)
            
        except Exception as e:
            logger.error(f"Error getting biller stats for user {user_id}: {e}")
            return self._empty_stats(date)
    
    def _empty_stats(self, date: datetime) -> Dict[str, Any]:
        """Return empty statistics structure"""
        return {
            'bills_created': 0,
            'bags_linked': 0,
            'total_weight': 0.0,
            'bills_completed': 0,
            'total_scans': 0,
            'parent_bags_scanned': 0,
            'child_bags_scanned': 0,
            'bill_details': [],
            'report_date': date.strftime('%B %d, %Y')
        }
    
    def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email using SendGrid"""
        if not SENDGRID_API_KEY:
            logger.warning("SendGrid API key not configured")
            return False
        
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            
            message = Mail(
                from_email=Email(FROM_EMAIL, COMPANY_NAME),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = sg.send(message)
            logger.info(f"Email sent to {to_email}: Status {response.status_code}")
            return response.status_code in [200, 201, 202]
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def generate_report_html(self, user_name: str, stats: Dict[str, Any]) -> str:
        """Generate HTML email report"""
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
                .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; margin: -30px -30px 20px -30px; text-align: center; }
                h1 { margin: 0; font-size: 24px; }
                .subtitle { opacity: 0.9; margin-top: 5px; }
                .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }
                .stat-box { background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 3px solid #667eea; }
                .stat-label { color: #666; font-size: 12px; text-transform: uppercase; }
                .stat-value { font-size: 24px; font-weight: bold; color: #333; margin-top: 5px; }
                .bill-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                .bill-table th { background: #f8f9fa; padding: 10px; text-align: left; font-size: 12px; text-transform: uppercase; color: #666; }
                .bill-table td { padding: 10px; border-bottom: 1px solid #eee; }
                .status-badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
                .status-completed { background: #d4edda; color: #155724; }
                .status-active { background: #fff3cd; color: #856404; }
                .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #666; font-size: 12px; }
                .empty-state { text-align: center; padding: 40px; color: #999; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Daily Activity Report</h1>
                    <div class="subtitle">{{ user_name }} - {{ report_date }}</div>
                </div>
                
                {% if bills_created > 0 or total_scans > 0 %}
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-label">Bills Created</div>
                        <div class="stat-value">{{ bills_created }}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Bills Completed</div>
                        <div class="stat-value">{{ bills_completed }}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Bags Linked</div>
                        <div class="stat-value">{{ bags_linked }}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Total Weight</div>
                        <div class="stat-value">{{ "%.1f"|format(total_weight) }} kg</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Parent Bags Scanned</div>
                        <div class="stat-value">{{ parent_bags_scanned }}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Child Bags Scanned</div>
                        <div class="stat-value">{{ child_bags_scanned }}</div>
                    </div>
                </div>
                
                {% if bill_details %}
                <h3 style="margin-top: 30px; color: #333;">📋 Bill Details</h3>
                <table class="bill-table">
                    <thead>
                        <tr>
                            <th>Bill ID</th>
                            <th>Destination</th>
                            <th>Bags</th>
                            <th>Weight</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for bill in bill_details %}
                        <tr>
                            <td><strong>{{ bill.bill_id }}</strong></td>
                            <td>{{ bill.destination or 'N/A' }}</td>
                            <td>{{ bill.linked_bags }}/{{ bill.parent_bag_count }}</td>
                            <td>{{ "%.1f"|format(bill.total_weight_kg or 0) }} kg</td>
                            <td>
                                <span class="status-badge status-{{ bill.status }}">
                                    {{ bill.status|upper }}
                                </span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% endif %}
                
                {% else %}
                <div class="empty-state">
                    <h3>No Activity Today</h3>
                    <p>You haven't created any bills or performed any scans today.</p>
                </div>
                {% endif %}
                
                <div class="footer">
                    <p>This is an automated report from {{ company_name }}</p>
                    <p>Report generated on {{ report_date }}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        from jinja2 import Template
        tmpl = Template(template)
        
        return tmpl.render(
            user_name=user_name,
            company_name=COMPANY_NAME,
            **stats
        )
    
    def send_daily_reports(self):
        """Send daily reports to all billers"""
        with self.app.app_context():
            logger.info("Starting daily report generation...")
            
            today = datetime.now()
            
            try:
                # Get all billers
                billers = self.db.session.execute(text("""
                    SELECT id, username, email 
                    FROM "user" 
                    WHERE role = 'biller' 
                        AND email IS NOT NULL 
                        AND email != ''
                """)).fetchall()
                
                logger.info(f"Found {len(billers)} billers to send reports to")
                
                success_count = 0
                for biller in billers:
                    try:
                        # Get biller's daily statistics
                        stats = self.get_biller_daily_stats(biller.id, today)
                        
                        # Generate HTML report
                        html_content = self.generate_report_html(biller.username, stats)
                        
                        # Send email
                        subject = f"Daily Activity Report - {today.strftime('%B %d, %Y')}"
                        if self.send_email(biller.email, subject, html_content):
                            success_count += 1
                            logger.info(f"Report sent to {biller.username} ({biller.email})")
                        else:
                            logger.warning(f"Failed to send report to {biller.username}")
                            
                    except Exception as e:
                        logger.error(f"Error processing report for {biller.username}: {e}")
                
                logger.info(f"Daily reports sent: {success_count}/{len(billers)} successful")
                
            except Exception as e:
                logger.error(f"Error in daily report generation: {e}")
    
    def schedule_daily_reports(self):
        """Schedule daily report sending"""
        schedule.every().day.at(self.report_time).do(self.send_daily_reports)
        
        def run_schedule():
            while self.is_running:
                schedule.run_pending()
                import time
                time.sleep(60)  # Check every minute
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=run_schedule, daemon=True)
        self.scheduler_thread.start()
        
        logger.info(f"✅ Daily reports scheduled for {self.report_time} every day")
    
    def send_test_report(self, user_id: int):
        """Send a test report to a specific user"""
        with self.app.app_context():
            try:
                user = self.db.session.execute(text("""
                    SELECT id, username, email 
                    FROM "user" 
                    WHERE id = :user_id
                """), {'user_id': user_id}).fetchone()
                
                if not user or not user.email:
                    return False, "User not found or no email configured"
                
                # Get today's stats
                stats = self.get_biller_daily_stats(user_id, datetime.now())
                
                # Generate and send report
                html_content = self.generate_report_html(user.username, stats)
                subject = f"Test Report - {datetime.now().strftime('%B %d, %Y')}"
                
                if self.send_email(user.email, subject, html_content):
                    return True, f"Test report sent to {user.email}"
                else:
                    return False, "Failed to send email"
                    
            except Exception as e:
                logger.error(f"Error sending test report: {e}")
                return False, str(e)
    
    def stop(self):
        """Stop the scheduler"""
        self.is_running = False
        if hasattr(self, 'scheduler_thread'):
            self.scheduler_thread.join(timeout=2)

# Global instance
report_system = None

def init_daily_reports(app, db):
    """Initialize the daily report system"""
    global report_system
    
    if not SENDGRID_API_KEY:
        logger.warning("Daily reports disabled - SendGrid API key not configured")
        return None
    
    report_system = DailyReportSystem(db, app)
    report_system.schedule_daily_reports()
    
    # Register test endpoint
    @app.route('/api/test_daily_report/<int:user_id>', methods=['POST'])
    def send_test_daily_report(user_id):
        """Send a test daily report to a specific user"""
        from flask import jsonify
        
        if not report_system:
            return jsonify({'success': False, 'message': 'Report system not initialized'})
        
        success, message = report_system.send_test_report(user_id)
        return jsonify({'success': success, 'message': message})
    
    logger.info("✅ Daily email report system initialized")
    return report_system