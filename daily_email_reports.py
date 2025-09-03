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
    """Manages daily consolidated email report for all billers"""
    
    def __init__(self, db, app):
        self.db = db
        self.app = app
        self.is_running = False
        self.report_time = "22:00"  # 10 PM daily
        self.admin_emails = []  # Will be populated with admin emails
        
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
    
    def get_consolidated_daily_report(self, date: datetime) -> Dict[str, Any]:
        """Get consolidated report data for all billers"""
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        try:
            # Get all billers and their activity for today with parent bag details
            result = self.db.session.execute(text("""
                WITH biller_bills AS (
                    SELECT 
                        u.id as user_id,
                        u.username,
                        u.email,
                        b.id as bill_id,
                        b.bill_id as bill_number,
                        b.destination,
                        b.parent_bag_count,
                        b.total_weight_kg,
                        b.status,
                        b.created_at,
                        COUNT(DISTINCT bb.bag_id) as linked_bags
                    FROM "user" u
                    LEFT JOIN bill b ON b.created_by_id = u.id 
                        AND b.created_at >= :start_date 
                        AND b.created_at < :end_date
                    LEFT JOIN bill_bag bb ON bb.bill_id = b.id
                    WHERE u.role = 'biller'
                    GROUP BY u.id, u.username, u.email, b.id, b.bill_id, 
                             b.destination, b.parent_bag_count, b.total_weight_kg, 
                             b.status, b.created_at
                ),
                parent_bags AS (
                    SELECT 
                        bb.bill_id,
                        bag.qr_id as parent_qr,
                        bag.child_count,
                        bag.weight_kg
                    FROM bill_bag bb
                    JOIN bag ON bag.id = bb.bag_id
                    JOIN bill b ON b.id = bb.bill_id
                    WHERE b.created_at >= :start_date 
                        AND b.created_at < :end_date
                        AND bag.type = 'parent'
                    ORDER BY bag.qr_id
                ),
                summary_stats AS (
                    SELECT 
                        COUNT(DISTINCT b.id) as total_bills,
                        COUNT(DISTINCT bb.bag_id) as total_bags,
                        SUM(b.total_weight_kg) as total_weight,
                        COUNT(DISTINCT b.created_by_id) as active_billers
                    FROM bill b
                    LEFT JOIN bill_bag bb ON bb.bill_id = b.id
                    WHERE b.created_at >= :start_date 
                        AND b.created_at < :end_date
                )
                SELECT 
                    json_agg(DISTINCT jsonb_build_object(
                        'user_id', bb.user_id,
                        'username', bb.username,
                        'email', bb.email,
                        'bill_id', bb.bill_id,
                        'bill_number', bb.bill_number,
                        'destination', bb.destination,
                        'parent_bag_count', bb.parent_bag_count,
                        'total_weight_kg', bb.total_weight_kg,
                        'status', bb.status,
                        'created_at', bb.created_at,
                        'linked_bags', bb.linked_bags
                    )) as biller_bills,
                    json_agg(DISTINCT jsonb_build_object(
                        'bill_id', pb.bill_id,
                        'parent_qr', pb.parent_qr,
                        'child_count', pb.child_count,
                        'weight_kg', pb.weight_kg
                    )) FILTER (WHERE pb.bill_id IS NOT NULL) as parent_bags,
                    (SELECT row_to_json(ss) FROM summary_stats ss) as summary
                FROM biller_bills bb
                LEFT JOIN parent_bags pb ON pb.bill_id = bb.bill_id
            """), {
                'start_date': start_date,
                'end_date': end_date
            }).fetchone()
            
            if result:
                import json
                biller_bills = json.loads(result.biller_bills) if result.biller_bills else []
                parent_bags = json.loads(result.parent_bags) if result.parent_bags else []
                summary = json.loads(result.summary) if result.summary else {}
                
                # Organize data by biller
                billers_data = {}
                for bill in biller_bills:
                    if bill and bill.get('username'):
                        username = bill['username']
                        if username not in billers_data:
                            billers_data[username] = {
                                'user_id': bill['user_id'],
                                'username': username,
                                'email': bill.get('email'),
                                'bills': []
                            }
                        if bill.get('bill_id'):
                            # Add parent bags to this bill
                            bill['parent_bags'] = [pb for pb in parent_bags if pb.get('bill_id') == bill['bill_id']]
                            billers_data[username]['bills'].append(bill)
                
                return {
                    'billers': list(billers_data.values()),
                    'summary': summary,
                    'report_date': date.strftime('%B %d, %Y'),
                    'parent_bags': parent_bags
                }
            
            return {
                'billers': [],
                'summary': {},
                'report_date': date.strftime('%B %d, %Y'),
                'parent_bags': []
            }
            
        except Exception as e:
            logger.error(f"Error generating consolidated report: {e}")
            return {
                'billers': [],
                'summary': {},
                'report_date': date.strftime('%B %d, %Y'),
                'parent_bags': []
            }
    
    def generate_consolidated_report_html(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML for consolidated daily report"""
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
                .container { max-width: 900px; margin: 0 auto; background: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 8px 8px 0 0; margin: -30px -30px 20px -30px; text-align: center; }
                h1 { margin: 0; font-size: 28px; }
                h2 { color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; margin-top: 30px; }
                h3 { color: #666; margin-top: 20px; }
                .subtitle { opacity: 0.9; margin-top: 5px; font-size: 18px; }
                .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
                .summary-box { background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 3px solid #667eea; text-align: center; }
                .summary-label { color: #666; font-size: 12px; text-transform: uppercase; }
                .summary-value { font-size: 24px; font-weight: bold; color: #333; margin-top: 5px; }
                .biller-section { margin: 30px 0; padding: 20px; background: #fafafa; border-radius: 8px; }
                .biller-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
                .biller-name { font-size: 20px; font-weight: bold; color: #333; }
                .biller-stats { color: #666; }
                .bill-table { width: 100%; border-collapse: collapse; margin-top: 15px; background: white; }
                .bill-table th { background: #667eea; color: white; padding: 10px; text-align: left; font-size: 12px; text-transform: uppercase; }
                .bill-table td { padding: 10px; border-bottom: 1px solid #eee; }
                .parent-bags { margin-top: 10px; padding: 8px; background: #e8f4f8; border-radius: 4px; }
                .parent-bag-item { display: inline-block; background: white; padding: 4px 8px; margin: 2px; border-radius: 3px; font-size: 12px; border: 1px solid #ddd; }
                .status-badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
                .status-completed { background: #d4edda; color: #155724; }
                .status-active { background: #fff3cd; color: #856404; }
                .status-pending { background: #d1ecf1; color: #0c5460; }
                .no-activity { text-align: center; padding: 20px; color: #999; }
                .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Daily Consolidated Biller Report</h1>
                    <div class="subtitle">{{ report_date }}</div>
                </div>
                
                {% if summary and summary.total_bills %}
                <div class="summary-grid">
                    <div class="summary-box">
                        <div class="summary-label">Total Bills</div>
                        <div class="summary-value">{{ summary.total_bills or 0 }}</div>
                    </div>
                    <div class="summary-box">
                        <div class="summary-label">Total Bags</div>
                        <div class="summary-value">{{ summary.total_bags or 0 }}</div>
                    </div>
                    <div class="summary-box">
                        <div class="summary-label">Total Weight</div>
                        <div class="summary-value">{{ "%.1f"|format(summary.total_weight or 0) }} kg</div>
                    </div>
                    <div class="summary-box">
                        <div class="summary-label">Active Billers</div>
                        <div class="summary-value">{{ summary.active_billers or 0 }}</div>
                    </div>
                </div>
                {% endif %}
                
                <h2>Biller Activity Details</h2>
                
                {% if billers %}
                    {% for biller in billers %}
                    <div class="biller-section">
                        <div class="biller-header">
                            <div class="biller-name">{{ biller.username }}</div>
                            <div class="biller-stats">{{ biller.bills|length }} bill(s) created today</div>
                        </div>
                        
                        {% if biller.bills %}
                        <table class="bill-table">
                            <thead>
                                <tr>
                                    <th>Bill ID</th>
                                    <th>Destination</th>
                                    <th>Bags</th>
                                    <th>Weight</th>
                                    <th>Status</th>
                                    <th>Parent Bags</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for bill in biller.bills %}
                                <tr>
                                    <td><strong>{{ bill.bill_number }}</strong></td>
                                    <td>{{ bill.destination or 'N/A' }}</td>
                                    <td>{{ bill.linked_bags }}/{{ bill.parent_bag_count }}</td>
                                    <td>{{ "%.1f"|format(bill.total_weight_kg or 0) }} kg</td>
                                    <td>
                                        <span class="status-badge status-{{ bill.status }}">
                                            {{ bill.status|upper }}
                                        </span>
                                    </td>
                                    <td>
                                        {% if bill.parent_bags %}
                                        <div class="parent-bags">
                                            {% for bag in bill.parent_bags %}
                                            <span class="parent-bag-item">
                                                {{ bag.parent_qr }} ({{ bag.child_count }} children, {{ "%.1f"|format(bag.weight_kg or 0) }}kg)
                                            </span>
                                            {% endfor %}
                                        </div>
                                        {% else %}
                                        <em style="color: #999;">No bags attached</em>
                                        {% endif %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                        {% else %}
                        <div class="no-activity">No bills created today</div>
                        {% endif %}
                    </div>
                    {% endfor %}
                {% else %}
                <div class="no-activity">
                    <h3>No Activity Today</h3>
                    <p>No bills were created by any billers today.</p>
                </div>
                {% endif %}
                
                <div class="footer">
                    <p><strong>{{ company_name }}</strong> - Daily Consolidated Report</p>
                    <p>Generated on {{ report_date }} at 10:00 PM</p>
                    <p style="margin-top: 10px; font-size: 10px;">This report includes all bills created today with their associated parent bags and details.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        from jinja2 import Template
        tmpl = Template(template)
        
        return tmpl.render(
            company_name=COMPANY_NAME,
            **report_data
        )
    
    def send_daily_reports(self):
        """Send consolidated daily report to admins"""
        with self.app.app_context():
            logger.info("Starting consolidated daily report generation...")
            
            today = datetime.now()
            
            try:
                # Get admin email addresses
                admins = self.db.session.execute(text("""
                    SELECT id, username, email 
                    FROM "user" 
                    WHERE role = 'admin' 
                        AND email IS NOT NULL 
                        AND email != ''
                """)).fetchall()
                
                if not admins:
                    logger.warning("No admin emails found for consolidated report")
                    return
                
                # Generate consolidated report
                report_data = self.get_consolidated_daily_report(today)
                
                if not report_data.get('billers'):
                    logger.info("No biller activity today, skipping report")
                    return
                
                # Generate HTML
                html_content = self.generate_consolidated_report_html(report_data)
                
                # Send to all admins
                subject = f"Daily Consolidated Biller Report - {today.strftime('%B %d, %Y')}"
                success_count = 0
                
                for admin in admins:
                    if self.send_email(admin.email, subject, html_content):
                        success_count += 1
                        logger.info(f"Consolidated report sent to {admin.username} ({admin.email})")
                    else:
                        logger.warning(f"Failed to send consolidated report to {admin.username}")
                
                logger.info(f"Consolidated daily report sent to {success_count}/{len(admins)} admins")
                
            except Exception as e:
                logger.error(f"Error in consolidated daily report generation: {e}")
    
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
        
        logger.info(f"✅ Daily consolidated report scheduled for {self.report_time} every day")
    
    def send_test_report(self, user_id: int = None):
        """Send a test consolidated report to admin"""
        with self.app.app_context():
            try:
                # Get admin to send test report to
                if user_id:
                    user = self.db.session.execute(text("""
                        SELECT id, username, email 
                        FROM "user" 
                        WHERE id = :user_id AND role = 'admin'
                    """), {'user_id': user_id}).fetchone()
                else:
                    # Get first admin
                    user = self.db.session.execute(text("""
                        SELECT id, username, email 
                        FROM "user" 
                        WHERE role = 'admin' AND email IS NOT NULL
                        LIMIT 1
                    """)).fetchone()
                
                if not user or not user.email:
                    return False, "No admin user found or no email configured"
                
                # Generate consolidated report
                report_data = self.get_consolidated_daily_report(datetime.now())
                
                # Generate HTML
                html_content = self.generate_consolidated_report_html(report_data)
                subject = f"TEST: Daily Consolidated Report - {datetime.now().strftime('%B %d, %Y')}"
                
                if self.send_email(user.email, subject, html_content):
                    return True, f"Test consolidated report sent to {user.email}"
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
    from flask_wtf import csrf
    
    @app.route('/api/test_consolidated_report', methods=['POST'])
    @csrf.exempt
    def send_test_consolidated_report():
        """Send a test consolidated report to admin"""
        from flask import jsonify, request
        
        if not report_system:
            return jsonify({'success': False, 'message': 'Report system not initialized'})
        
        user_id = request.args.get('user_id', type=int)
        success, message = report_system.send_test_report(user_id)
        return jsonify({'success': success, 'message': message})
    
    logger.info("✅ Daily email report system initialized")
    return report_system