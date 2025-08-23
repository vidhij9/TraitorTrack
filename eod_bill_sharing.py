#!/usr/bin/env python3
"""
End of Day (EOD) Bill Summary Sharing System
Sends daily bill summaries to billers (their own) and admins (all summaries)
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import current_app
from models import db, User, Bill, BillBag
from cache_utils import format_datetime_ist
import logging

# Configure logging
logger = logging.getLogger(__name__)

class EODBillSharing:
    """Handles EOD bill summary generation and sharing"""
    
    def __init__(self):
        self.smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_user = os.environ.get('SMTP_USER', 'noreply@tracetrack.com')
        self.smtp_pass = os.environ.get('SMTP_PASSWORD', '')
        self.from_email = os.environ.get('FROM_EMAIL', 'TraceTrack System <noreply@tracetrack.com>')
        
    def generate_biller_summary(self, user_id, date_from=None, date_to=None):
        """Generate bill summary for a specific biller"""
        if not date_from:
            date_from = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not date_to:
            date_to = date_from + timedelta(days=1)
        
        # Get user's bills for the period
        bills = Bill.query.filter(
            Bill.created_by_id == user_id,
            Bill.created_at >= date_from,
            Bill.created_at < date_to
        ).all()
        
        summary = {
            'total_bills': len(bills),
            'completed_bills': 0,
            'pending_bills': 0,
            'total_parent_bags': 0,
            'total_child_bags': 0,
            'total_weight_kg': 0,
            'bills': []
        }
        
        for bill in bills:
            parent_count = BillBag.query.filter_by(bill_id=bill.id).count()
            
            # Determine status
            if bill.status == 'completed':
                summary['completed_bills'] += 1
                status = 'Completed'
            elif parent_count > 0:
                status = 'In Progress'
            else:
                summary['pending_bills'] += 1
                status = 'Pending'
            
            summary['total_parent_bags'] += parent_count
            summary['total_child_bags'] += bill.total_child_bags or 0
            summary['total_weight_kg'] += bill.total_weight_kg or 0
            
            summary['bills'].append({
                'bill_id': bill.bill_id,
                'created_at': format_datetime_ist(bill.created_at),
                'status': status,
                'parent_bags': parent_count,
                'child_bags': bill.total_child_bags or 0,
                'weight_kg': bill.total_weight_kg or 0
            })
        
        return summary
    
    def generate_admin_summary(self, date_from=None, date_to=None):
        """Generate comprehensive summary for admins (all users)"""
        if not date_from:
            date_from = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not date_to:
            date_to = date_from + timedelta(days=1)
        
        # Get all billers
        billers = User.query.filter(User.role == 'biller').all()
        
        admin_summary = {
            'report_date': format_datetime_ist(date_from, 'date'),
            'total_billers': len(billers),
            'overall_stats': {
                'total_bills': 0,
                'completed_bills': 0,
                'pending_bills': 0,
                'total_parent_bags': 0,
                'total_child_bags': 0,
                'total_weight_kg': 0
            },
            'biller_summaries': []
        }
        
        # Generate summary for each biller
        for biller in billers:
            biller_summary = self.generate_biller_summary(biller.id, date_from, date_to)
            
            # Update overall stats
            admin_summary['overall_stats']['total_bills'] += biller_summary['total_bills']
            admin_summary['overall_stats']['completed_bills'] += biller_summary['completed_bills']
            admin_summary['overall_stats']['pending_bills'] += biller_summary['pending_bills']
            admin_summary['overall_stats']['total_parent_bags'] += biller_summary['total_parent_bags']
            admin_summary['overall_stats']['total_child_bags'] += biller_summary['total_child_bags']
            admin_summary['overall_stats']['total_weight_kg'] += biller_summary['total_weight_kg']
            
            # Add biller summary
            if biller_summary['total_bills'] > 0:  # Only include billers with activity
                admin_summary['biller_summaries'].append({
                    'username': biller.username,
                    'email': biller.email,
                    'summary': biller_summary
                })
        
        return admin_summary
    
    def format_biller_email(self, username, summary):
        """Format bill summary email for a biller"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h2 {{ color: #2c3e50; }}
                .stats {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background: #3498db; color: white; padding: 10px; text-align: left; }}
                td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                .completed {{ color: #27ae60; font-weight: bold; }}
                .pending {{ color: #e67e22; font-weight: bold; }}
                .progress {{ color: #3498db; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h2>Daily Bill Summary for {username}</h2>
            <p>Date: {format_datetime_ist(datetime.now(), 'date')}</p>
            
            <div class="stats">
                <h3>Summary Statistics</h3>
                <ul>
                    <li><strong>Total Bills Created:</strong> {summary['total_bills']}</li>
                    <li><strong>Completed Bills:</strong> <span class="completed">{summary['completed_bills']}</span></li>
                    <li><strong>Pending Bills:</strong> <span class="pending">{summary['pending_bills']}</span></li>
                    <li><strong>Total Parent Bags:</strong> {summary['total_parent_bags']}</li>
                    <li><strong>Total Child Bags:</strong> {summary['total_child_bags']}</li>
                    <li><strong>Total Weight:</strong> {summary['total_weight_kg']:.2f} KG</li>
                </ul>
            </div>
        """
        
        if summary['bills']:
            html += """
            <h3>Bill Details</h3>
            <table>
                <tr>
                    <th>Bill ID</th>
                    <th>Created At</th>
                    <th>Status</th>
                    <th>Parent Bags</th>
                    <th>Child Bags</th>
                    <th>Weight (KG)</th>
                </tr>
            """
            
            for bill in summary['bills']:
                status_class = 'completed' if bill['status'] == 'Completed' else 'pending' if bill['status'] == 'Pending' else 'progress'
                html += f"""
                <tr>
                    <td>{bill['bill_id']}</td>
                    <td>{bill['created_at']}</td>
                    <td class="{status_class}">{bill['status']}</td>
                    <td>{bill['parent_bags']}</td>
                    <td>{bill['child_bags']}</td>
                    <td>{bill['weight_kg']:.2f}</td>
                </tr>
                """
            
            html += "</table>"
        else:
            html += "<p><em>No bills created today.</em></p>"
        
        html += """
            <hr>
            <p style="color: #7f8c8d; font-size: 12px;">
                This is an automated EOD summary from TraceTrack System.<br>
                For any queries, please contact your administrator.
            </p>
        </body>
        </html>
        """
        
        return html
    
    def format_admin_email(self, summary):
        """Format comprehensive summary email for admins"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h2 {{ color: #2c3e50; }}
                .overall {{ background: #ecf0f1; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                .biller-section {{ background: #f8f9fa; padding: 15px; margin: 15px 0; border-left: 4px solid #3498db; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th {{ background: #34495e; color: white; padding: 8px; text-align: left; }}
                td {{ padding: 6px; border-bottom: 1px solid #ddd; }}
                .highlight {{ font-weight: bold; color: #2c3e50; }}
            </style>
        </head>
        <body>
            <h2>Admin EOD Summary - All Billers</h2>
            <p>Report Date: {summary['report_date']}</p>
            
            <div class="overall">
                <h3>Overall Statistics</h3>
                <ul>
                    <li><strong>Total Active Billers:</strong> {summary['total_billers']}</li>
                    <li><strong>Total Bills:</strong> {summary['overall_stats']['total_bills']}</li>
                    <li><strong>Completed:</strong> {summary['overall_stats']['completed_bills']}</li>
                    <li><strong>Pending:</strong> {summary['overall_stats']['pending_bills']}</li>
                    <li><strong>Total Parent Bags:</strong> {summary['overall_stats']['total_parent_bags']}</li>
                    <li><strong>Total Child Bags:</strong> {summary['overall_stats']['total_child_bags']}</li>
                    <li><strong>Total Weight:</strong> {summary['overall_stats']['total_weight_kg']:.2f} KG</li>
                </ul>
            </div>
            
            <h3>Individual Biller Summaries</h3>
        """
        
        if summary['biller_summaries']:
            for biller_data in summary['biller_summaries']:
                biller_summary = biller_data['summary']
                html += f"""
                <div class="biller-section">
                    <h4 class="highlight">{biller_data['username']}</h4>
                    <p>Email: {biller_data['email']}</p>
                    <ul>
                        <li>Bills Created: {biller_summary['total_bills']}</li>
                        <li>Completed: {biller_summary['completed_bills']}</li>
                        <li>Pending: {biller_summary['pending_bills']}</li>
                        <li>Parent Bags: {biller_summary['total_parent_bags']}</li>
                        <li>Child Bags: {biller_summary['total_child_bags']}</li>
                        <li>Weight: {biller_summary['total_weight_kg']:.2f} KG</li>
                    </ul>
                """
                
                if biller_summary['bills']:
                    html += """
                    <table>
                        <tr>
                            <th>Bill ID</th>
                            <th>Status</th>
                            <th>Parent</th>
                            <th>Child</th>
                            <th>Weight</th>
                        </tr>
                    """
                    for bill in biller_summary['bills'][:5]:  # Show first 5 bills
                        html += f"""
                        <tr>
                            <td>{bill['bill_id']}</td>
                            <td>{bill['status']}</td>
                            <td>{bill['parent_bags']}</td>
                            <td>{bill['child_bags']}</td>
                            <td>{bill['weight_kg']:.2f}</td>
                        </tr>
                        """
                    if len(biller_summary['bills']) > 5:
                        html += f"""
                        <tr>
                            <td colspan="5" style="text-align:center; font-style:italic;">
                                ... and {len(biller_summary['bills']) - 5} more bills
                            </td>
                        </tr>
                        """
                    html += "</table>"
                
                html += "</div>"
        else:
            html += "<p><em>No billing activity today from any biller.</em></p>"
        
        html += """
            <hr>
            <p style="color: #7f8c8d; font-size: 12px;">
                This is an automated admin EOD summary from TraceTrack System.<br>
                Generated at: """ + format_datetime_ist(datetime.now()) + """
            </p>
        </body>
        </html>
        """
        
        return html
    
    def send_email(self, to_email, subject, html_content):
        """Send email using SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            if self.smtp_pass:  # Only send if SMTP is configured
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
                logger.info(f"EOD summary sent to {to_email}")
                return True
            else:
                logger.warning(f"SMTP not configured, skipping email to {to_email}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_eod_summaries(self, date_from=None, date_to=None):
        """Main function to send EOD summaries to all users"""
        results = {
            'billers_sent': [],
            'billers_failed': [],
            'admins_sent': [],
            'admins_failed': [],
            'total_processed': 0
        }
        
        try:
            # Send individual summaries to billers
            billers = User.query.filter(User.role == 'biller').all()
            
            for biller in billers:
                if not biller.email:
                    logger.warning(f"Biller {biller.username} has no email address")
                    results['billers_failed'].append(biller.username)
                    continue
                
                # Generate and send biller summary
                summary = self.generate_biller_summary(biller.id, date_from, date_to)
                
                if summary['total_bills'] > 0:  # Only send if there's activity
                    subject = f"EOD Bill Summary - {format_datetime_ist(datetime.now(), 'date')}"
                    html = self.format_biller_email(biller.username, summary)
                    
                    if self.send_email(biller.email, subject, html):
                        results['billers_sent'].append(biller.username)
                    else:
                        results['billers_failed'].append(biller.username)
                
                results['total_processed'] += 1
            
            # Send comprehensive summary to admins
            admins = User.query.filter(User.role == 'admin').all()
            admin_summary = self.generate_admin_summary(date_from, date_to)
            
            for admin in admins:
                if not admin.email:
                    logger.warning(f"Admin {admin.username} has no email address")
                    results['admins_failed'].append(admin.username)
                    continue
                
                subject = f"Admin EOD Summary - All Billers - {admin_summary['report_date']}"
                html = self.format_admin_email(admin_summary)
                
                if self.send_email(admin.email, subject, html):
                    results['admins_sent'].append(admin.username)
                else:
                    results['admins_failed'].append(admin.username)
            
            logger.info(f"EOD summaries sent: {len(results['billers_sent'])} billers, {len(results['admins_sent'])} admins")
            
        except Exception as e:
            logger.error(f"Error in send_eod_summaries: {str(e)}")
        
        return results

# Create global instance
eod_sharing = EODBillSharing()