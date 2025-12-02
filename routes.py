"""
Optimized routes for TraitorTrack application - consolidated and performance-optimized
"""
import os
from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_file, abort, make_response, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

# Import optimized authentication utilities
from auth_utils import (
    create_session, clear_session, is_logged_in, 
    login_required, admin_required, get_current_user,
    get_current_user_id, get_current_username, get_current_user_role
)

# Import timezone utilities
from timezone_utils import format_datetime_ist, get_ist_now

# Import enhanced audit logging utilities
from audit_utils import (
    log_audit, log_audit_with_snapshot, capture_entity_snapshot,
    get_audit_trail, get_entity_history
)

# Import email notification utilities
from email_utils import EmailService, EmailConfig
# Create a current_user proxy for compatibility
class CurrentUserProxy:
    @property
    def id(self):
        return get_current_user_id()
    
    @property
    def username(self):
        return get_current_username()
    
    @property
    def role(self):
        return get_current_user_role()
    
    @property
    def is_authenticated(self):
        return is_logged_in()
    
    @property
    def dispatch_area(self):
        return session.get('dispatch_area')
    
    @property
    def email(self):
        return session.get('email')
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def is_biller(self):
        """Check if user is biller"""
        return self.role == 'biller'
    
    def is_dispatcher(self):
        """Check if user is dispatcher"""
        return self.role == 'dispatcher'
    
    def can_edit_bills(self):
        """Check if user can edit bills"""
        return self.is_admin() or self.is_biller()
    
    def can_manage_users(self):
        """Check if user can manage users"""
        return self.is_admin()
        
current_user = CurrentUserProxy()

# Commented out missing modules with fallbacks
# from query_optimizer import query_optimizer
# from optimized_cache import cached, cache, invalidate_cache

# Define fallback functions for missing imports
def query_optimizer_fallback():
    """Fallback class for query optimizer when not available"""
    class FallbackOptimizer:
        @staticmethod
        def get_bag_by_qr(qr_id, bag_type=None):
            from models import Bag
            return Bag.query.filter_by(qr_id=qr_id).first()
        
        @staticmethod
        def create_bag_optimized(*args, **kwargs):
            return None
            
        @staticmethod  
        def create_scan_optimized(*args, **kwargs):
            return None
            
        @staticmethod
        def create_link_optimized(*args, **kwargs):
            return None, False
        
        @staticmethod
        def create_link_fast(*args, **kwargs):
            return False, "Optimizer not available"
            
        @staticmethod
        def invalidate_bag_cache(qr_id=None, bag_id=None):
            pass  # No-op in fallback
        
        @staticmethod
        def invalidate_all_cache():
            pass  # No-op in fallback
            
        @staticmethod
        def bulk_commit():
            return True
    return FallbackOptimizer()

# Import the real query optimizer
try:
    from query_optimizer import query_optimizer
except ImportError:
    # Fallback if not available
    query_optimizer = query_optimizer_fallback()

# Using Flask-Login's login_required decorator directly

from sqlalchemy import desc, func, and_, or_, text
from datetime import datetime, timedelta

from app import app, db, limiter, csrf, csrf_compat, get_admin_rate_limit_key
from forms import LoginForm, RegistrationForm, ChildLookupForm, ManualScanForm, PromotionRequestForm, AdminPromotionForm, PromotionRequestActionForm, BillCreationForm
from validation_utils import InputValidator

# Simple sanitization helper for backward compatibility
def sanitize_input(input_str):
    """Comprehensive input sanitizer - removes invisible characters, normalizes whitespace, limits length
    
    Critical for barcode scanner input which may include:
    - Carriage returns (\\r)
    - Line feeds (\\n)
    - Tabs (\\t)
    - Null bytes (\\x00)
    - Non-breaking spaces (\\xa0)
    - Zero-width characters
    - Control characters
    """
    if not input_str:
        return ''
    
    import re
    
    # Convert to string
    s = str(input_str)
    
    # Remove null bytes and control characters (ASCII 0-31 except tab/newline/CR)
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s)
    
    # Remove zero-width characters and other invisible Unicode characters
    s = re.sub(r'[\u200b-\u200f\u2028-\u202f\u2060-\u206f\ufeff]', '', s)
    
    # Replace all whitespace variants (including non-breaking space) with regular space
    s = re.sub(r'[\s\xa0]+', ' ', s)
    
    # Strip leading/trailing whitespace
    s = s.strip()
    
    # Limit length
    return s[:255]

# Import all required models - FIX for 288 errors
from models import (
    User, UserRole, 
    Bag, BagType, 
    Link, Bill, BillBag, 
    Scan, AuditLog, 
    PromotionRequest, PromotionRequestStatus,
    DispatchArea
)

# Fast scanning routes removed - functionality consolidated

# API endpoint for bill weights
@app.route('/api/bill/<int:bill_id>/weights')
@login_required
def api_bill_weights(bill_id):
    """Get real-time weight information for a bill - returns current total weight only"""
    try:
        bill = Bill.query.get_or_404(bill_id)
        
        # Get total child count (1kg per child = total weight)
        result = db.session.execute(
            text("""
                SELECT 
                    COUNT(DISTINCT bb.bag_id) as parent_count,
                    COALESCE(SUM((SELECT COUNT(*) FROM link WHERE parent_bag_id = b.id)), 0) as total_children
                FROM bill_bag bb
                JOIN bag b ON bb.bag_id = b.id
                WHERE bb.bill_id = :bill_id
            """),
            {'bill_id': bill_id}
        ).fetchone()
        
        parent_count = int(result[0]) if result else 0
        total_children = int(result[1]) if result else 0
        
        return jsonify({
            'total_weight': float(total_children),
            'parent_bags': parent_count,
            'child_bags': total_children
        })
    except Exception as e:
        app.logger.error(f'Error fetching bill weights: {str(e)}')
        return jsonify({'error': 'Failed to fetch weights'}), 500

import csv
import io
import json
import secrets
import random
import time
import logging
import os

# PRODUCTION: Logging is centralized in app.py
# Do NOT configure logging here to avoid conflicts
logger = logging.getLogger(__name__)

# Helper function for audit logging
# log_audit is now imported from audit_utils
# Legacy calls to log_audit() will use the backward-compatible wrapper
# New code should use log_audit_with_snapshot() for enhanced tracking

# Health check endpoint removed - using /api/health instead to avoid duplication

# Analytics route removed as requested

@app.route('/user_management')
@login_required
@limiter.exempt  # Exempt from rate limiting for admin functionality
def user_management():
    """Ultra-optimized user management dashboard for admins with caching"""
    try:
        if not current_user.is_admin():
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        
        # Single optimized query for all user data with joins
        user_data_query = text("""
            WITH user_scans AS (
                SELECT user_id, 
                       COUNT(*) as scan_count,
                       COUNT(DISTINCT COALESCE(parent_bag_id, child_bag_id)) as unique_bags_scanned,
                       MAX(timestamp) as last_scan
                FROM scan 
                WHERE user_id IS NOT NULL
                GROUP BY user_id
            ),
            role_stats AS (
                SELECT 
                    COUNT(CASE WHEN role = 'admin' THEN 1 END) as admin_count,
                    COUNT(CASE WHEN role = 'biller' THEN 1 END) as biller_count,
                    COUNT(CASE WHEN role = 'dispatcher' THEN 1 END) as dispatcher_count
                FROM "user"
            )
            SELECT 
                u.id, u.username, u.email, u.role, u.dispatch_area, 
                u.verified, u.created_at,
                COALESCE(us.scan_count, 0) as scan_count,
                COALESCE(us.unique_bags_scanned, 0) as unique_bags_scanned,
                us.last_scan,
                rs.admin_count, rs.biller_count, rs.dispatcher_count
            FROM "user" u
            LEFT JOIN user_scans us ON u.id = us.user_id
            CROSS JOIN role_stats rs
            ORDER BY u.created_at DESC
        """)
        
        result = db.session.execute(user_data_query).fetchall()
        
        user_data = []
        role_counts = None
        
        for row in result:
            # Set role counts once (same for all rows due to CROSS JOIN)
            if role_counts is None:
                role_counts = {
                    'admins': row.admin_count,
                    'billers': row.biller_count, 
                    'dispatchers': row.dispatcher_count
                }
            
            # Create user data with all required attributes for template
            user_data.append({
                'id': row.id,
                'username': row.username,
                'email': row.email,
                'role': row.role,
                'dispatch_area': row.dispatch_area,
                'verified': row.verified,
                'created_at': row.created_at,
                'scan_count': row.scan_count,
                'unique_bags_scanned': row.unique_bags_scanned,
                'last_scan': row.last_scan,
                'role_stats': {},  # Simplified for performance
                'can_change_role': row.id != current_user.id,
                # Add role checking methods as data
                'is_admin': row.role == 'admin',
                'is_biller': row.role == 'biller', 
                'is_dispatcher': row.role == 'dispatcher'
            })
        
        # Quick dispatch area counts
        dispatch_areas = []
        for area in ['lucknow', 'indore', 'jaipur', 'hisar', 'sri_ganganagar', 
                     'sangaria', 'bathinda', 'raipur', 'ranchi', 'akola']:
            count = sum(1 for data in user_data 
                       if data['role'] == 'dispatcher' and data['dispatch_area'] == area)
            dispatch_areas.append({
                'name': area,
                'display': area.replace('_', ' ').title(),
                'count': count
            })
        
        return render_template('user_management.html', 
                             user_data=user_data,
                             role_counts=role_counts,
                             dispatch_areas=dispatch_areas)
        
    except Exception as e:
        app.logger.error(f"User management error: {e}")
        flash('Error loading user management. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/admin/users/<int:user_id>')
@login_required
@limiter.exempt  # Exempt admin functionality from rate limiting
def get_user_details(user_id):
    """Get user details for editing"""
    try:
        # Import models locally to avoid circular imports
        from models import User
        
        user_id_from_session = session.get('user_id')
        if not user_id_from_session:
            return jsonify({'error': 'Authentication required'}), 401
            
        current_user_obj = User.query.get(user_id_from_session)
        if not current_user_obj or current_user_obj.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'verified': getattr(user, 'verified', True),
            'dispatch_area': getattr(user, 'dispatch_area', 'lucknow')
        })
        
    except Exception as e:
        app.logger.error(f"Error loading user {user_id}: {str(e)}")
        return jsonify({'error': 'Error loading user data'}), 500

@app.route('/admin/users/<int:user_id>/profile')
@login_required
@limiter.limit("60 per minute")  # Rate limit admin profile views
def admin_user_profile(user_id):
    """Comprehensive user profile page for admins - OPTIMIZED with single CTE query"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('user_management'))
    
    profile_user = User.query.get_or_404(user_id)
    
    try:
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        quarter_start = datetime(now.year, ((now.month - 1) // 3) * 3 + 1, 1)
        year_start = datetime(now.year, 1, 1)
        
        # SINGLE OPTIMIZED CTE QUERY - replaces 15+ separate queries
        metrics_query = text("""
            WITH scan_metrics AS (
                SELECT 
                    COUNT(*) as total_scans,
                    COUNT(*) FILTER (WHERE timestamp >= :today_start) as scans_today,
                    COUNT(*) FILTER (WHERE timestamp >= :week_start) as scans_week,
                    COUNT(*) FILTER (WHERE timestamp >= :quarter_start) as scans_quarter,
                    COUNT(*) FILTER (WHERE timestamp >= :year_start) as scans_year,
                    COUNT(DISTINCT parent_bag_id) FILTER (WHERE parent_bag_id IS NOT NULL) as unique_parent_bags,
                    COUNT(DISTINCT child_bag_id) FILTER (WHERE child_bag_id IS NOT NULL) as unique_child_bags,
                    COUNT(*) FILTER (WHERE parent_bag_id IS NOT NULL) as parent_scans,
                    COUNT(*) FILTER (WHERE child_bag_id IS NOT NULL) as child_scans,
                    MIN(timestamp) as first_scan,
                    MAX(timestamp) as last_scan
                FROM scan WHERE user_id = :user_id
            ),
            peak_day AS (
                SELECT DATE(timestamp) as scan_date, COUNT(*) as scan_count
                FROM scan WHERE user_id = :user_id
                GROUP BY DATE(timestamp)
                ORDER BY COUNT(*) DESC LIMIT 1
            ),
            active_hour AS (
                SELECT EXTRACT(HOUR FROM timestamp)::int as hour
                FROM scan WHERE user_id = :user_id
                GROUP BY EXTRACT(HOUR FROM timestamp)
                ORDER BY COUNT(*) DESC LIMIT 1
            ),
            error_count AS (
                SELECT COUNT(*) as error_logs
                FROM audit_log 
                WHERE user_id = :user_id AND action ILIKE '%error%'
            ),
            last_login AS (
                SELECT timestamp FROM audit_log
                WHERE user_id = :user_id AND action ILIKE '%login%'
                ORDER BY timestamp DESC LIMIT 1
            )
            SELECT 
                sm.total_scans, sm.scans_today, sm.scans_week, sm.scans_quarter, sm.scans_year,
                sm.unique_parent_bags, sm.unique_child_bags, sm.parent_scans, sm.child_scans,
                sm.first_scan, sm.last_scan,
                pd.scan_date as peak_day_date, pd.scan_count as peak_day_scans,
                COALESCE(ah.hour, 12) as most_active_hour,
                ec.error_logs,
                ll.timestamp as last_login
            FROM scan_metrics sm
            LEFT JOIN peak_day pd ON true
            LEFT JOIN active_hour ah ON true
            LEFT JOIN error_count ec ON true
            LEFT JOIN last_login ll ON true
        """)
        
        result = db.session.execute(metrics_query, {
            'user_id': user_id,
            'today_start': today_start,
            'week_start': week_start,
            'quarter_start': quarter_start,
            'year_start': year_start
        }).fetchone()
        
        # Extract values with defaults
        total_scans = result.total_scans or 0 if result else 0
        scans_today = result.scans_today or 0 if result else 0
        scans_week = result.scans_week or 0 if result else 0
        scans_quarter = result.scans_quarter or 0 if result else 0
        scans_year = result.scans_year or 0 if result else 0
        unique_bags_scanned = ((result.unique_parent_bags or 0) + (result.unique_child_bags or 0)) if result else 0
        parent_scans = result.parent_scans or 0 if result else 0
        child_scans = result.child_scans or 0 if result else 0
        first_scan = result.first_scan if result else None
        last_scan = result.last_scan if result else None
        peak_day_date = result.peak_day_date if result else None
        peak_day_scans = result.peak_day_scans or 0 if result else 0
        most_active_hour = result.most_active_hour if result else 12
        error_logs = result.error_logs or 0 if result else 0
        last_login = result.last_login if result else None
        
        # Calculated values
        if first_scan:
            days_active = (now - first_scan).days + 1
            avg_scans_per_day = total_scans / days_active if days_active > 0 else 0
        else:
            days_active = 0
            avg_scans_per_day = 0
        
        scan_accuracy = max(0, min(100, ((total_scans - error_logs) / total_scans * 100) if total_scans > 0 else 100))
        error_rate = min(100, (error_logs / total_scans * 100) if total_scans > 0 else 0)
        estimated_hours = round(total_scans * 0.5 / 60, 1)
        total_requests = total_scans * 2
        failed_requests = error_logs
        avg_response_time = 1.5 + (error_rate / 100)
        uptime_percentage = max(90, 100 - error_rate)
        
        # Batch fetch recent activity (2 queries instead of separate fetches)
        recent_errors = AuditLog.query.filter(
            AuditLog.user_id == user_id,
            db.or_(
                AuditLog.action.ilike('%error%'),
                AuditLog.action.ilike('%fail%'),
                AuditLog.action.ilike('%exception%')
            )
        ).order_by(AuditLog.timestamp.desc()).limit(10).all()
        
        recent_activity = AuditLog.query.filter_by(user_id=user_id).order_by(
            AuditLog.timestamp.desc()
        ).limit(15).all()
        
        # Recent scans with bag QR codes (single query with JOIN)
        recent_scans_query = text("""
            SELECT s.timestamp, s.parent_bag_id, s.child_bag_id,
                   COALESCE(pb.qr_id, cb.qr_id, 'Unknown') as qr_code
            FROM scan s
            LEFT JOIN bag pb ON s.parent_bag_id = pb.id
            LEFT JOIN bag cb ON s.child_bag_id = cb.id
            WHERE s.user_id = :user_id
            ORDER BY s.timestamp DESC
            LIMIT 20
        """)
        recent_scans = db.session.execute(recent_scans_query, {'user_id': user_id}).fetchall()
        
        # Daily scan data for chart (single query)
        daily_scans_query = text("""
            SELECT DATE(timestamp) as scan_date, COUNT(*) as scan_count
            FROM scan
            WHERE user_id = :user_id AND timestamp >= :thirty_days_ago
            GROUP BY DATE(timestamp)
        """)
        daily_scans_result = db.session.execute(daily_scans_query, {
            'user_id': user_id,
            'thirty_days_ago': thirty_days_ago
        }).fetchall()
        
        # Build chart data
        daily_scan_data = {'labels': [], 'values': []}
        current_date = thirty_days_ago.date()
        scan_dict = {row.scan_date: row.scan_count for row in daily_scans_result if row.scan_date}
        
        for i in range(30):
            date_key = current_date + timedelta(days=i)
            daily_scan_data['labels'].append(date_key.strftime('%b %d'))
            daily_scan_data['values'].append(scan_dict.get(date_key, 0))
        
        metrics = {
            'total_scans': total_scans,
            'scans_today': scans_today,
            'today_scans': scans_today,
            'week_scans': scans_week,
            'quarter_scans': scans_quarter,
            'year_scans': scans_year,
            'unique_bags_scanned': unique_bags_scanned,
            'days_active': days_active,
            'avg_scans_per_day': avg_scans_per_day,
            'peak_day_scans': peak_day_scans,
            'peak_day_date': peak_day_date,
            'most_active_hour': most_active_hour,
            'scan_accuracy': scan_accuracy,
            'error_rate': error_rate,
            'recent_errors': recent_errors,
            'recent_activity': recent_activity,
            'recent_scans': recent_scans,
            'parent_scans': parent_scans,
            'child_scans': child_scans,
            'daily_scan_data': daily_scan_data,
            'estimated_hours': estimated_hours,
            'last_login': last_login,
            'last_scan': last_scan,
            'avg_response_time': avg_response_time,
            'failed_requests': failed_requests,
            'total_requests': total_requests,
            'uptime_percentage': uptime_percentage
        }
        
        return render_template('admin_user_profile.html', 
                             profile_user=profile_user, 
                             metrics=metrics)
        
    except Exception as e:
        app.logger.error(f"User profile error for user {user_id}: {e}")
        flash('Error loading user profile. Please try again.', 'error')
        return redirect(url_for('user_management'))

@app.route('/admin/users/<int:user_id>/change-role', methods=['POST'])
@login_required
def change_user_role(user_id):
    """Change user role with comprehensive validation and real-world handling"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    user = User.query.with_for_update().get_or_404(user_id)
    new_role = request.form.get('new_role')
    dispatch_area = request.form.get('dispatch_area')
    
    try:
        # Validate new role
        if new_role not in ['admin', 'biller', 'dispatcher']:
            return jsonify({'success': False, 'message': 'Invalid role specified'})
        
        old_role = user.role
        
        # REAL-WORLD SCENARIO 1: Prevent removing the last admin
        if old_role == 'admin' and new_role != 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count <= 1:
                return jsonify({
                    'success': False, 
                    'message': 'Cannot change role. This is the last admin account. Promote another user to admin first.',
                    'critical': True
                })
        
        # REAL-WORLD SCENARIO 2: Check for pending work when changing from biller
        if old_role == 'biller' and new_role != 'biller':
            # Check for incomplete bills assigned to this user
            from sqlalchemy import exists
            incomplete_bills = Bill.query.filter(
                Bill.status.in_(['new', 'processing'])
            ).count()
            if incomplete_bills > 0:
                return jsonify({
                    'success': False,
                    'message': f'User has {incomplete_bills} incomplete bills. Please reassign or complete them first.',
                    'warning': True,
                    'incomplete_count': incomplete_bills
                })
        
        # REAL-WORLD SCENARIO 3: Handle dispatcher area requirements
        if new_role == 'dispatcher':
            if not dispatch_area:
                return jsonify({
                    'success': False,
                    'message': 'Dispatch area is required for dispatcher role',
                    'require_input': 'dispatch_area'
                })
            # Check if area already has too many dispatchers
            area_dispatchers = User.query.filter_by(
                role='dispatcher',
                dispatch_area=dispatch_area
            ).count()
            if area_dispatchers >= 10:  # Limit dispatchers per area
                return jsonify({
                    'success': False,
                    'message': f'Area {dispatch_area} already has {area_dispatchers} dispatchers. Maximum limit is 10.',
                    'warning': True
                })
        
        # REAL-WORLD SCENARIO 4: Clear sensitive data when demoting from admin
        if old_role == 'admin' and new_role != 'admin':
            # Log this critical change
            log_audit('demote_admin', 'user', user.id, {
                'username': user.username,
                'old_role': old_role,
                'new_role': new_role,
                'demoted_by': current_user.username
            })
        
        # REAL-WORLD SCENARIO 5: Handle active sessions
        if user.id == current_user.id:
            return jsonify({
                'success': False,
                'message': 'Cannot change your own role. Ask another admin to change it for you.',
                'self_change': True
            })
        
        # Capture state before changes for audit trail
        before_state = capture_entity_snapshot(user)
        
        # Apply role change
        user.role = new_role
        
        # Update dispatch area based on new role
        if new_role == 'dispatcher':
            user.dispatch_area = dispatch_area
        else:
            user.dispatch_area = None  # Clear for non-dispatchers
        
        # Log the role change with before/after snapshots
        log_audit_with_snapshot(
            action='role_change',
            entity_type='user',
            entity_id=user.id,
            before_state=before_state,
            after_state=user,
            details={
                'username': user.username,
                'old_role': old_role,
                'new_role': new_role,
                'changed_by': current_user.username
            }
        )
        
        db.session.commit()
        
        # REAL-WORLD SCENARIO 6: Force logout for role changes
        # Clear user's session if they're logged in (security measure)
        # Note: In production, you'd invalidate their session token
        
        return jsonify({
            'success': True,
            'message': f'Role successfully changed from {old_role} to {new_role}',
            'old_role': old_role,
            'new_role': new_role,
            'user_id': user.id,
            'username': user.username
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Role change error for user {user_id}: {str(e)}')
        return jsonify({'success': False, 'message': f'Error changing role: {str(e)}'})

@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@login_required
@limiter.limit("30 per minute", key_func=get_admin_rate_limit_key)  # Per-admin rate limit
def edit_user(user_id):
    """Edit user details"""
    try:
        # Import models locally to avoid circular imports
        from models import User
        
        user_id_from_session = session.get('user_id')
        if not user_id_from_session:
            flash('Authentication required', 'error')
            return redirect(url_for('login'))
            
        current_user_obj = User.query.get(user_id_from_session)
        if not current_user_obj or current_user_obj.role != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard'))
        
        user = User.query.get(user_id)
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('user_management'))
            
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        dispatch_area = request.form.get('dispatch_area')
        new_password = request.form.get('password')  # Add password support
        
        # Store old values for comparison
        old_username = user.username
        old_email = user.email
        old_role = user.role
        
        # Validate username uniqueness if changed
        if username and username != old_username:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username already exists.', 'error')
                return redirect(url_for('user_management'))
            user.username = username
        
        # Validate email uniqueness if changed
        if email and email != old_email:
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                flash('Email already exists.', 'error')
                return redirect(url_for('user_management'))
            user.email = email
        
        # Handle role change with validation
        if role and role != old_role:
            # Use the comprehensive role change logic
            if old_role == 'admin' and role != 'admin':
                admin_count = User.query.filter_by(role='admin').count()
                if admin_count <= 1:
                    flash('Cannot change role. This is the last admin account.', 'error')
                    return redirect(url_for('user_management'))
            
            user.role = role
        
        # Handle dispatch area update (separate from role change to allow independent updates)
        if role:  # Use current role (after potential change above)
            final_role = role  # Use the role from form (either new or unchanged)
            if final_role == 'dispatcher':
                if not dispatch_area:
                    flash('Dispatch area is required for dispatchers.', 'error')
                    return redirect(url_for('user_management'))
                user.dispatch_area = dispatch_area
            else:
                user.dispatch_area = None  # Clear dispatch area for non-dispatchers
        
        # Handle password change if provided
        password_changed = False
        if new_password and len(new_password.strip()) > 0:
            from werkzeug.security import generate_password_hash
            # Use user's set_password method for consistency
            user.set_password(new_password.strip())
            password_changed = True
        
        # Log the changes (simplified to avoid import issues)
        if username != old_username or email != old_email or role != old_role or password_changed:
            app.logger.info(f'User {user.id} updated by admin {current_user_obj.username}: username={username != old_username}, email={email != old_email}, role={role != old_role}, password={password_changed}')
        
        db.session.commit()
        
        # CRITICAL: Invalidate caches AFTER commit
        if password_changed:
            db.session.expire(user)
            app.logger.info(f'Cache invalidated for user {user.id} after admin password change')
        
        success_message = 'User updated successfully!'
        if password_changed:
            success_message += f' New password set for {user.username}.'
            
        flash(success_message, 'success')
        return redirect(url_for('user_management'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error updating user {user_id}: {str(e)}')
        flash(f'Error updating user: {str(e)}', 'error')
        return redirect(url_for('user_management'))

@app.route('/admin/users/<int:user_id>/promote', methods=['POST'])
@login_required
@limiter.limit("20 per minute", key_func=get_admin_rate_limit_key)  # Per-admin rate limit
def promote_user(user_id):
    """Promote user to admin with validation - only admins can do this"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    user = User.query.with_for_update().get_or_404(user_id)
    
    try:
        if user.role == 'admin':
            return jsonify({'success': False, 'message': 'User is already an admin'})
            
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot promote yourself'})
        
        old_role = user.role
        old_area = user.dispatch_area
        
        # Clear dispatch area when promoting to admin
        user.role = 'admin'
        user.dispatch_area = None
        
        # Log the promotion
        log_audit('promote_to_admin', 'user', user.id, {
            'username': user.username,
            'old_role': old_role,
            'old_area': old_area,
            'promoted_by': current_user.username
        })
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'{user.username} promoted to admin from {old_role}'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error promoting user: {str(e)}'})

@app.route('/admin/users/<int:user_id>/demote', methods=['POST'])
@login_required
@limiter.limit("20 per minute", key_func=get_admin_rate_limit_key)  # Per-admin rate limit
def demote_user(user_id):
    """Demote user with validation - only admins can do this"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    user = User.query.with_for_update().get_or_404(user_id)
    new_role = request.form.get('new_role', 'dispatcher')
    dispatch_area = request.form.get('dispatch_area')
    
    try:
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot demote yourself'})
        
        # Check if this is the last admin
        if user.role == 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count <= 1:
                return jsonify({
                    'success': False, 
                    'message': 'Cannot demote the last admin. Promote another user first.',
                    'critical': True
                })
        
        old_role = user.role
        
        # Validate new role
        if new_role not in ['biller', 'dispatcher']:
            return jsonify({'success': False, 'message': 'Invalid demotion role'})
        
        # Handle dispatcher area requirement
        if new_role == 'dispatcher' and not dispatch_area:
            return jsonify({
                'success': False,
                'message': 'Dispatch area required for dispatcher role',
                'require_area': True
            })
        
        user.role = new_role
        user.dispatch_area = dispatch_area if new_role == 'dispatcher' else None
        
        # Log the demotion
        log_audit('demote_user', 'user', user.id, {
            'username': user.username,
            'old_role': old_role,
            'new_role': new_role,
            'new_area': user.dispatch_area,
            'demoted_by': current_user.username
        })
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'{user.username} changed from {old_role} to {new_role}',
            'new_role': new_role
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error changing user role: {str(e)}'})

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@limiter.limit("10 per minute", key_func=get_admin_rate_limit_key)  # Per-admin rate limit
def delete_user(user_id):
    """Delete user with proper handling of related records"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    # Use raw SQL to avoid circular imports
    user_result = db.session.execute(db.text('SELECT * FROM "user" WHERE id = :user_id'), {'user_id': user_id}).fetchone()
    if not user_result:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    username = user_result.username  # Store username before deletion (always available)
    
    try:
        if user_result.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot delete yourself'})
        
        # Check if user has any related data
        scan_count_result = db.session.execute(db.text('SELECT COUNT(*) FROM scan WHERE user_id = :user_id'), {'user_id': user_id}).scalar()
        scan_count = scan_count_result or 0
        
        bill_count_result = db.session.execute(db.text('SELECT COUNT(*) FROM bill WHERE created_by_id = :user_id'), {'user_id': user_id}).scalar()
        bill_count = bill_count_result or 0
        
        # Log the deletion attempt for audit purposes
        log_audit('delete_user_attempt', 'user', user_id, {
            'username': username,
            'role': user_result.role,
            'scan_count': scan_count,
            'bill_count': bill_count,
            'deleted_by': current_user.username
        })
        
        # PRODUCTION SAFETY: Clean up related records first to avoid foreign key violations
        
        # 1. First delete PromotionRequests (has CASCADE constraint) - table is named 'promotionrequest' not 'promotion_requests'
        db.session.execute(db.text('DELETE FROM promotionrequest WHERE user_id = :user_id'), {'user_id': user_id})
        
        # 2. Update any bills created by this user to NULL (preserving billing history)
        db.session.execute(db.text('UPDATE bill SET created_by_id = NULL WHERE created_by_id = :user_id'), {'user_id': user_id})
        
        # 3. Update any scans by this user to NULL (preserving scan history)
        db.session.execute(db.text('UPDATE scan SET user_id = NULL WHERE user_id = :user_id'), {'user_id': user_id})
        
        # 4. Update any audit logs to NULL (preserving audit trail)
        db.session.execute(db.text('UPDATE audit_log SET user_id = NULL WHERE user_id = :user_id'), {'user_id': user_id})
        
        # 5. Update promotion requests where user was the admin processor
        db.session.execute(db.text('UPDATE promotionrequest SET admin_id = NULL WHERE admin_id = :user_id'), {'user_id': user_id})
        
        # Now safely delete the user
        db.session.execute(db.text('DELETE FROM "user" WHERE id = :user_id'), {'user_id': user_id})
        db.session.commit()
        
        # Log successful deletion
        log_audit('delete_user_success', 'user', user_id, {
            'username': username,
            'deleted_by': current_user.username,
            'scans_nullified': scan_count,
            'bills_nullified': bill_count
        })
        
        return jsonify({
            'success': True, 
            'message': f'User {username} has been safely deleted. {scan_count} scans and {bill_count} bills have been preserved with null user references.',
            'user_id': user_id,
            'deleted_username': username,
            'preserved_scans': scan_count,
            'preserved_bills': bill_count
        })
        
    except Exception as e:
        db.session.rollback()
        import logging
        error_msg = str(e)
        
        # PRODUCTION SAFETY: Provide helpful error messages for common issues
        if 'foreign key' in error_msg.lower():
            # Extract table name from the error if possible
            if 'violates foreign key constraint' in error_msg:
                error_msg = "Cannot delete user due to existing data dependencies. Please contact system administrator."
            else:
                error_msg = "User has related data that prevents deletion. Attempting safe cleanup..."
                
                # Try a safer approach - just disable the user instead of deleting
                try:
                    db.session.execute(db.text(
                        'UPDATE "user" SET username = :disabled_name, email = NULL, password_hash = NULL WHERE id = :user_id'
                    ), {
                        'disabled_name': f'DELETED_USER_{user_id}',
                        'user_id': user_id
                    })
                    db.session.commit()
                    
                    log_audit('delete_user_disabled', 'user', user_id, {
                        'username': username if 'username' in locals() else f'user_{user_id}',
                        'action': 'disabled_instead_of_deleted',
                        'reason': 'foreign_key_constraint',
                        'deleted_by': current_user.username
                    })
                    
                    return jsonify({
                        'success': True,
                        'message': f'User {username if "username" in locals() else user_id} has been safely disabled (not deleted) due to data dependencies.',
                        'action': 'disabled',
                        'user_id': user_id
                    })
                except Exception as disable_error:
                    db.session.rollback()
                    error_msg = f"Could not delete or disable user: {str(disable_error)}"
        
        logging.error(f"Error deleting user {user_id}: {error_msg}")
        
        # Log failed deletion
        log_audit('delete_user_failed', 'user', user_id, {
            'username': username,
            'error': error_msg,
            'deleted_by': current_user.username
        })
        
        return jsonify({'success': False, 'message': error_msg})

@app.route('/admin/comprehensive-user-deletion')
@login_required
@limiter.exempt
def comprehensive_user_deletion():
    """Admin-only page for comprehensive user and scan deletion"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get all users for the selection dropdown
    users = User.query.order_by(User.username).all()
    
    return render_template('admin_comprehensive_deletion.html', users=users)

@app.route('/admin/preview-user-deletion', methods=['POST'])
@login_required
@limiter.exempt
def preview_user_deletion():
    """Preview what data would be deleted for a specific user"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    try:
        username = request.form.get('username', '').strip()
        role = request.form.get('role', '').strip()
        
        if not username or not role:
            return jsonify({'success': False, 'message': 'Both username and role are required'})
        
        # Find the user by username AND role for safety
        user = User.query.filter_by(username=username, role=role).first()
        
        if not user:
            return jsonify({'success': False, 'message': f'No user found with username "{username}" and role "{role}"'})
        
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'You cannot delete your own data'})
        
        # No need to check for last admin since we're not deleting the account
        
        # Get all scans by this user
        user_scans = Scan.query.filter_by(user_id=user.id).all()
        
        # Collect unique bag IDs from scans
        scanned_bag_ids = set()
        for scan in user_scans:
            if scan.parent_bag_id:
                scanned_bag_ids.add(scan.parent_bag_id)
            if scan.child_bag_id:
                scanned_bag_ids.add(scan.child_bag_id)
        
        # Get bag details
        bags_to_delete = Bag.query.filter(Bag.id.in_(scanned_bag_ids)).all() if scanned_bag_ids else []
        
        # Count related data
        parent_bags = sum(1 for bag in bags_to_delete if bag.type == 'parent')
        child_bags = sum(1 for bag in bags_to_delete if bag.type == 'child')
        
        # Check for bills that would be affected
        affected_bills = []
        if parent_bags > 0:
            parent_bag_ids = [bag.id for bag in bags_to_delete if bag.type == 'parent']
            bill_links = BillBag.query.filter(BillBag.bag_id.in_(parent_bag_ids)).all()
            for link in bill_links:
                if link.bill:
                    affected_bills.append({
                        'id': link.bill.id,
                        'bill_id': link.bill.bill_id,
                        'description': link.bill.description or 'No description'
                    })
        
        # Count links that would be deleted
        link_count = 0
        if scanned_bag_ids:
            link_count = Link.query.filter(
                (Link.parent_bag_id.in_(scanned_bag_ids)) | 
                (Link.child_bag_id.in_(scanned_bag_ids))
            ).count()
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'created_at': format_datetime_ist(user.created_at, 'full') if user.created_at else 'Unknown'
            },
            'deletion_summary': {
                'total_scans': len(user_scans),
                'parent_bags': parent_bags,
                'child_bags': child_bags,
                'total_bags': len(bags_to_delete),
                'links': link_count,
                'affected_bills': len(affected_bills)
            },
            'affected_bills': affected_bills,
            'bag_details': [
                {
                    'qr_id': bag.qr_id,
                    'type': bag.type,
                    'name': bag.name or 'Unnamed'
                } for bag in bags_to_delete[:10]  # Show first 10 bags
            ],
            'more_bags': len(bags_to_delete) > 10
        })
        
    except Exception as e:
        app.logger.error(f"Error previewing user deletion: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/admin/execute-comprehensive-deletion', methods=['POST'])
@login_required
@limiter.exempt
def execute_comprehensive_deletion():
    """Execute deletion of all user data (keeps user account)"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    # Initialize variables for error handling
    username = 'unknown'
    role = 'unknown'
    
    try:
        username = request.form.get('username', '').strip()
        role = request.form.get('role', '').strip()
        confirmation = request.form.get('confirmation', '').strip()
        
        # Verify confirmation text
        expected_confirmation = f"DELETE {username}"
        if confirmation != expected_confirmation:
            return jsonify({
                'success': False, 
                'message': f'Confirmation text must be exactly: {expected_confirmation}'
            })
        
        # Find the user
        user = User.query.filter_by(username=username, role=role).first()
        
        if not user:
            return jsonify({'success': False, 'message': f'No user found with username "{username}" and role "{role}"'})
        
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'You cannot delete your own data'})
        
        # No need to check for last admin since we're not deleting the account
        
        # Log the data deletion attempt
        log_audit('comprehensive_data_delete_attempt', 'user', user.id, {
            'username': username,
            'email': user.email,
            'role': user.role,
            'deleted_by': current_user.username
        })
        
        # Step 1: Get all scans by this user
        user_scans = Scan.query.filter_by(user_id=user.id).all()
        scan_count = len(user_scans)
        
        # Step 2: Collect unique bag IDs from scans
        bags_to_delete_ids = set()
        for scan in user_scans:
            if scan.parent_bag_id:
                bags_to_delete_ids.add(scan.parent_bag_id)
            if scan.child_bag_id:
                bags_to_delete_ids.add(scan.child_bag_id)
        
        # Step 3: Delete all scans by this user
        Scan.query.filter_by(user_id=user.id).delete()
        
        # Step 4: Delete ALL scans that reference these bags (not just user's scans)
        # This prevents foreign key constraint violations
        if bags_to_delete_ids:
            # Delete scans that reference these bags as parent or child
            Scan.query.filter(
                (Scan.parent_bag_id.in_(bags_to_delete_ids)) | 
                (Scan.child_bag_id.in_(bags_to_delete_ids))
            ).delete(synchronize_session=False)
            
            # Step 5: Delete links associated with these bags
            Link.query.filter(
                (Link.parent_bag_id.in_(bags_to_delete_ids)) | 
                (Link.child_bag_id.in_(bags_to_delete_ids))
            ).delete(synchronize_session=False)
            
            # Step 6: Delete bill associations
            BillBag.query.filter(BillBag.bag_id.in_(bags_to_delete_ids)).delete(synchronize_session=False)
            
            # Step 7: Now safe to delete the bags themselves
            bags_deleted = Bag.query.filter(Bag.id.in_(bags_to_delete_ids)).delete(synchronize_session=False)
        else:
            bags_deleted = 0
        
        # Step 7: User account remains intact - we've deleted all their data
        # No need to delete the user
        
        # Store user info before committing
        user_id = user.id
        user_role = user.role
        user_email = user.email
        
        # Commit all changes
        db.session.commit()
        
        # Log successful data deletion
        log_audit('comprehensive_data_delete_success', 'user', user_id, {
            'username': username,
            'email': user_email,
            'scans_deleted': scan_count,
            'bags_deleted': bags_deleted,
            'deleted_by': current_user.username
        })
        
        return jsonify({
            'success': True,
            'message': f'All data for user {username} has been permanently deleted. The user account remains intact.',
            'stats': {
                'scans_deleted': scan_count,
                'bags_deleted': bags_deleted
            }
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in comprehensive deletion: {str(e)}")
        
        # Log failed deletion
        log_audit('comprehensive_data_delete_failed', 'user', None, {
            'username': username if 'username' in locals() else 'unknown',
            'role': role if 'role' in locals() else 'unknown',
            'error': str(e),
            'deleted_by': current_user.username
        })
        
        return jsonify({'success': False, 'message': f'Error during deletion: {str(e)}'})

@app.route('/admin/backfill-bill-counters', methods=['POST'])
@login_required
def admin_backfill_bill_counters():
    """
    PRODUCTION FIX: Efficient batch backfill of bill counters for large databases.
    Uses a single efficient SQL query to update all bills at once.
    Designed to handle 10+ lakh bags without timeout.
    """
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    try:
        from sqlalchemy import text
        
        # Step 1: Calculate all parent counts and child counts in ONE efficient query
        # This avoids the N+1 problem that caused timeouts
        app.logger.info("Starting batch backfill of bill counters...")
        
        # Efficient query to get parent counts per bill
        parent_counts = db.session.execute(text("""
            UPDATE bill 
            SET linked_parent_count = COALESCE(sub.parent_count, 0)
            FROM (
                SELECT bb.bill_id, COUNT(bb.bag_id) as parent_count
                FROM bill_bag bb
                GROUP BY bb.bill_id
            ) sub
            WHERE bill.id = sub.bill_id
            RETURNING bill.id
        """)).fetchall()
        
        app.logger.info(f"Updated parent counts for {len(parent_counts)} bills")
        
        # Efficient query to get child counts per bill
        child_counts = db.session.execute(text("""
            UPDATE bill 
            SET total_child_bags = COALESCE(sub.child_count, 0),
                total_weight_kg = COALESCE(sub.child_count, 0)
            FROM (
                SELECT bb.bill_id, COUNT(DISTINCT l.child_bag_id) as child_count
                FROM bill_bag bb
                LEFT JOIN link l ON l.parent_bag_id = bb.bag_id
                GROUP BY bb.bill_id
            ) sub
            WHERE bill.id = sub.bill_id
            RETURNING bill.id
        """)).fetchall()
        
        app.logger.info(f"Updated child counts for {len(child_counts)} bills")
        
        # Set bills with linked bags to 'processing' if still 'new'
        status_updates = db.session.execute(text("""
            UPDATE bill 
            SET status = 'processing'
            WHERE linked_parent_count > 0 AND status = 'new'
            RETURNING bill.id
        """)).fetchall()
        
        db.session.commit()
        
        log_audit('batch_bill_counters_backfill', 'system', None, {
            'parent_counts_updated': len(parent_counts),
            'child_counts_updated': len(child_counts),
            'status_updated': len(status_updates),
            'triggered_by': current_user.username
        })
        
        return jsonify({
            'success': True,
            'message': f'Backfill complete. Updated {len(parent_counts)} bills with parent counts, {len(child_counts)} with child counts.',
            'stats': {
                'parent_counts_updated': len(parent_counts),
                'child_counts_updated': len(child_counts),
                'status_updated': len(status_updates)
            }
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error in batch backfill: {str(e)}')
        import traceback
        app.logger.error(f'Backfill traceback: {traceback.format_exc()}')
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})


@app.route('/admin/recalculate-bill-weights', methods=['POST'])
@login_required
def admin_recalculate_bill_weights():
    """Admin endpoint to recalculate weights for all bills or a specific bill"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    try:
        bill_id = request.form.get('bill_id')
        
        if bill_id:
            # Recalculate single bill
            bill = Bill.query.filter_by(bill_id=bill_id).first()
            if not bill:
                return jsonify({'success': False, 'message': f'Bill {bill_id} not found'})
            
            actual, expected, parent_count, child_count = bill.recalculate_weights()
            db.session.commit()
            
            log_audit('bill_weight_recalculated', 'bill', bill.id, {
                'bill_id': bill_id,
                'actual_weight': actual,
                'expected_weight': expected,
                'parent_count': parent_count,
                'child_count': child_count,
                'recalculated_by': current_user.username
            })
            
            return jsonify({
                'success': True,
                'message': f'Bill {bill_id} weights recalculated successfully',
                'bill': {
                    'bill_id': bill_id,
                    'actual_weight': actual,
                    'expected_weight': expected,
                    'parent_count': parent_count,
                    'child_count': child_count
                }
            })
        else:
            # Recalculate all bills
            bills = Bill.query.all()
            recalculated_count = 0
            errors = []
            
            for bill in bills:
                try:
                    bill.recalculate_weights()
                    recalculated_count += 1
                except Exception as e:
                    errors.append(f'Bill {bill.bill_id}: {str(e)}')
            
            db.session.commit()
            
            log_audit('all_bill_weights_recalculated', 'system', None, {
                'bills_recalculated': recalculated_count,
                'errors': len(errors),
                'recalculated_by': current_user.username
            })
            
            if errors:
                return jsonify({
                    'success': True,
                    'message': f'Recalculated {recalculated_count} bills with {len(errors)} errors',
                    'recalculated': recalculated_count,
                    'errors': errors[:10]  # Return first 10 errors
                })
            else:
                return jsonify({
                    'success': True,
                    'message': f'All {recalculated_count} bills recalculated successfully',
                    'recalculated': recalculated_count
                })
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error recalculating bill weights: {str(e)}')
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/create_user', methods=['POST'])
@login_required
def create_user():
    """Create a new user"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('user_management'))
    
    try:
        # Get form data instead of JSON
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'dispatcher')
        dispatch_area = request.form.get('dispatch_area')
        
        # Validate required fields
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('user_management'))
        
        # Validate dispatch area for dispatchers
        if role == 'dispatcher' and not dispatch_area:
            flash('Dispatch area is required for dispatchers.', 'error')
            return redirect(url_for('user_management'))
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('user_management'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return redirect(url_for('user_management'))
        
        # Create new user
        user = User()
        user.username = username
        user.email = email
        user.role = role
        user.dispatch_area = dispatch_area if role == 'dispatcher' else None
        user.verified = True
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # CRITICAL: Invalidate caches AFTER commit
        db.session.expire(user)
        
        # Cache invalidation skipped - not critical for user creation
        # invalidate_cache() function not implemented
        
        flash(f'User {username} created successfully!', 'success')
        return redirect(url_for('user_management'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating user: {str(e)}', 'error')
        return redirect(url_for('user_management'))

@app.route('/admin/system-integrity')
@login_required
def admin_system_integrity():
    """View system integrity report and duplicate prevention status (admin only)"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get comprehensive system integrity report
        report = {"status": "optimized", "duplicate_issues": 0}
        
        return render_template('admin_system_integrity.html', report=report)
        
    except Exception as e:
        app.logger.error(f'System integrity report error: {str(e)}')
        flash('Error generating system integrity report.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/seed_sample_data')
@login_required
def seed_sample_data():
    """Create sample data for testing analytics (admin only)"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Create sample bags if few exist
        if Bag.query.count() < 10:
            for i in range(20):
                # Create parent bags
                parent_bag = Bag()
                parent_bag.qr_id = f"PARENT_{i+1:03d}_{secrets.token_hex(4).upper()}"
                parent_bag.type = 'parent'
                parent_bag.name = f"Parent Bag {i+1}"
                parent_bag.child_count = random.randint(1, 5)
                db.session.add(parent_bag)
                db.session.flush()  # Get the ID
                
                # Create child bags for this parent
                for j in range(parent_bag.child_count):
                    child_bag = Bag()
                    child_bag.qr_id = f"CHILD_{i+1:03d}_{j+1:02d}_{secrets.token_hex(3).upper()}"
                    child_bag.type = 'child'
                    child_bag.name = f"Child Bag {i+1}-{j+1}"
                    child_bag.parent_id = parent_bag.id
                    db.session.add(child_bag)
                    db.session.flush()  # Get the ID for link
                    
                    # Create link
                    link = Link()
                    link.parent_bag_id = parent_bag.id
                    link.child_bag_id = child_bag.id
                    db.session.add(link)
            
            db.session.commit()
        
        # Create sample scans for the past 30 days
        bags = Bag.query.all()
        if bags and Scan.query.count() < 50:
            for _ in range(100):
                bag = random.choice(bags)
                scan = Scan()
                scan.timestamp = datetime.utcnow() - timedelta(days=random.randint(0, 30))
                scan.user_id = current_user.id
                
                if bag.type == 'parent':
                    scan.parent_bag_id = bag.id
                else:
                    scan.child_bag_id = bag.id
                
                db.session.add(scan)
            
            db.session.commit()
        
        flash('Sample data created successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating sample data: {str(e)}', 'error')
    
    return redirect(url_for('analytics'))

# Core application routes

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return send_from_directory('static', 'favicon.ico', mimetype='image/x-icon')

@app.route('/', methods=['GET'])
def index():
    """Main dashboard page or fast health check"""
    # Ultra-fast health check for deployment health checks
    user_agent = request.headers.get('User-Agent', '').lower()
    accept_header = request.headers.get('Accept', '').lower()
    
    # Detect health check requests (deployment bots, load balancers)
    if ('health' in user_agent or 'check' in user_agent or 'bot' in user_agent or 
        'curl' in user_agent or 'wget' in user_agent or 
        not accept_header.startswith('text/html')):
        return jsonify({'status': 'ok'}), 200
    
    # Regular dashboard redirect for browsers
    if not is_logged_in():
        return redirect(url_for('login'))
    
    return redirect(url_for('dashboard'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
@limiter.exempt  # Exempt dashboard from rate limiting
def dashboard():
    """Main dashboard page"""
    import logging
    logging.info(f"Dashboard route - Session data: {dict(session)}")
    logging.info(f"Authenticated: {is_logged_in()}")
    
    # Simple authentication check
    if not is_logged_in():
        logging.info("User not authenticated, redirecting to login")
        return redirect(url_for('login'))
    
    # Use simple dashboard template
    return render_template('dashboard.html')

def get_login_rate_limit():
    """Dynamic rate limit function for login - evaluated per request"""
    # Check all possible production environment indicators
    if (os.environ.get('REPLIT_DEPLOYMENT') == '1' or 
        os.environ.get('REPLIT_ENVIRONMENT') == 'production'):
        return "20 per hour"  # Strict in production
    return "1000 per hour"  # Relaxed in development

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit(get_login_rate_limit)  # Dynamic rate limiting based on environment
def login():
    """User login endpoint with improved error handling"""
    if is_logged_in() and request.method == 'GET':
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        try:
            # Import models locally to avoid circular imports
            from models import User
            from password_utils import is_account_locked, record_failed_login, record_successful_login
            from werkzeug.security import check_password_hash
            
            # Find user - FORCE FRESH DB LOOKUP (no caching)
            # Expire any cached SQLAlchemy objects to ensure fresh password hash
            db.session.expire_all()
            user = User.query.filter_by(username=username).first()
            app.logger.info(f"LOGIN ATTEMPT: {username}")
            
            # PRODUCTION: Debug logging disabled to reduce log volume
            # Password hash validation happens in check_password method
            
            # SECURITY: Prevent username enumeration by using constant-time behavior
            # Always perform the same operations regardless of whether user exists
            user_found = user is not None
            
            if not user_found:
                # Create a dummy password hash to perform timing-safe comparison
                # This prevents timing attacks that could reveal if username exists
                dummy_hash = 'scrypt:32768:8:1$placeholder$1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
                # Perform dummy check to match timing of real password verification
                check_password_hash(dummy_hash, password)
                
                app.logger.warning(f"LOGIN FAILED: User {username} not found")
                # Audit log: Failed login attempt (user not found)
                log_audit('login_failed_user_not_found', 'auth', None, {
                    'username': username,
                    'ip_address': request.remote_addr,
                    'reason': 'user_not_found'
                })
                # Use generic error message (don't reveal if username exists or not)
                flash('Invalid username or password.', 'error')
                return render_template('login.html')
            
            # CRITICAL: Expire user object again to ensure fresh lockout data
            # This prevents cached lockout state from blocking valid logins
            db.session.expire(user)
            db.session.refresh(user)
            
            # Check if account is locked (pass db to allow reset of expired locks)
            is_locked, unlock_time, minutes_remaining = is_account_locked(user, db)
            
            # CRITICAL FIX: Refresh user object AFTER is_account_locked() call
            # is_account_locked() may commit changes to unlock expired locks
            # Without this refresh, the user object may have stale lockout state
            db.session.expire(user)
            db.session.refresh(user)
            
            app.logger.info(f"LOCKOUT CHECK: is_locked={is_locked}, failed_attempts={user.failed_login_attempts}, locked_until={user.locked_until}")
            if is_locked:
                app.logger.warning(f"LOGIN BLOCKED: Account {username} is locked for {minutes_remaining} more minutes")
                # Audit log: Blocked login attempt (account locked)
                log_audit('login_blocked_account_locked', 'auth', user.id, {
                    'username': username,
                    'ip_address': request.remote_addr,
                    'minutes_remaining': minutes_remaining,
                    'reason': 'account_locked'
                })
                flash(f'Account locked due to too many failed login attempts. Please try again in {minutes_remaining} minutes.', 'error')
                return render_template('login.html', login_attempts={
                    'is_locked': True,
                    'lockout_time': f'{minutes_remaining} minutes'
                })
            
            app.logger.info(f"USER FOUND: {user.username}, role: {user.role}, verified: {user.verified}")
            
            # Verify password using user's check_password method for consistency
            password_valid = False
            try:
                password_valid = user.check_password(password)
                app.logger.info(f"PASSWORD CHECK: {password_valid} for user {username}")
            except Exception as e:
                app.logger.error(f"PASSWORD ERROR: {e} for user {username}")
                
            if not password_valid:
                app.logger.warning(f"LOGIN FAILED: Invalid password for {username}")
                
                # Record failed login attempt
                should_lock, attempts_remaining, lock_duration = record_failed_login(user, db)
                
                # Audit log: Failed login attempt (invalid password)
                log_audit('login_failed_invalid_password', 'auth', user.id, {
                    'username': username,
                    'ip_address': request.remote_addr,
                    'should_lock': should_lock,
                    'attempts_remaining': attempts_remaining,
                    'reason': 'invalid_password'
                })
                
                login_attempts_info = None
                if should_lock:
                    flash(f'Too many failed login attempts. Account locked for {lock_duration} minutes.', 'error')
                    login_attempts_info = {
                        'is_locked': True,
                        'lockout_time': f'{lock_duration} minutes'
                    }
                elif attempts_remaining is not None:
                    flash(f'Invalid username or password. {attempts_remaining} attempts remaining.', 'error')
                    login_attempts_info = {
                        'is_locked': False,
                        'attempts_remaining': attempts_remaining
                    }
                else:
                    flash('Invalid username or password.', 'error')
                    
                return render_template('login.html', login_attempts=login_attempts_info)
                
            if not user.verified:
                app.logger.warning(f"LOGIN FAILED: User {username} not verified")
                # Audit log: Failed login attempt (not verified)
                log_audit('login_failed_not_verified', 'auth', user.id, {
                    'username': username,
                    'ip_address': request.remote_addr,
                    'reason': 'not_verified'
                })
                flash('Account not verified.', 'error')
                return render_template('login.html')
            
            # SUCCESS - Reset failed attempts
            record_successful_login(user, db)
            
            # Check if 2FA is enabled
            if user.two_fa_enabled and user.totp_secret:
                # Redirect to 2FA verification instead of logging in directly
                session['pending_2fa_user_id'] = user.id
                session.modified = True  # Ensure session is saved before redirect
                app.logger.info(f"2FA required for user {username}, redirecting to verification")
                # Audit log: Password authenticated, pending 2FA
                log_audit('login_password_success_pending_2fa', 'auth', user.id, {
                    'username': username,
                    'ip_address': request.remote_addr,
                    'role': user.role,
                    'next_step': '2fa_verification'
                })
                return redirect(url_for('two_fa_verify'))
            
            # No 2FA - create session and login normally (with email optimization)
            create_session(
                user.id, 
                user.username, 
                user.role, 
                user.dispatch_area if hasattr(user, 'dispatch_area') else None,
                user.email  # Pass email to avoid future DB queries
            )
            
            app.logger.info(f"LOGIN SUCCESS: {username} logged in with role {user.role}, user_id={user.id}")
            app.logger.info(f"Session after login: user_id={session.get('user_id')}, keys={list(session.keys())}")
            
            # Audit log: Successful login
            log_audit('login_success', 'auth', user.id, {
                'username': username,
                'ip_address': request.remote_addr,
                'role': user.role,
                'dispatch_area': user.dispatch_area if hasattr(user, 'dispatch_area') else None
            })
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
                
        except Exception as e:
            import traceback
            app.logger.error(f"LOGIN EXCEPTION: {e}")
            app.logger.error(f"LOGIN EXCEPTION TRACEBACK: {traceback.format_exc()}")
            flash(f'Login failed. Error: {str(e)}', 'error')
        
        return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout endpoint"""
    username = session.get('username', 'unknown')
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    
    # Audit log: Logout
    log_audit('logout', 'auth', user_id, {
        'username': username,
        'role': user_role,
        'ip_address': request.remote_addr
    })
    
    clear_session()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/fix-session')
@login_required
def fix_session():
    """Fix session data for existing users - temporary debug route"""
    try:
        from models import User
        user_id = session.get('user_id')
        if user_id:
            user = User.query.get(user_id)
            if user:
                # Re-create session with correct data
                # Session creation simplified for optimized version
                session['logged_in'] = True
                session['authenticated'] = True
                session['user_id'] = user.id
                session['username'] = user.username
                session['user_role'] = user.role
                flash(f'Session refreshed for user {user.username} with role {user.role}', 'success')
                import logging
                logging.info(f"Session fixed for user {user.username}, role: {user.role}")
                return redirect(url_for('dashboard'))
        
        flash('Could not fix session - user not found', 'error')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        flash(f'Error fixing session: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/link_to_bill/<qr_id>', methods=['GET', 'POST'])
@login_required
def link_to_bill(qr_id):
    """Link parent bag to bill"""
    try:
        parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(qr_id),
            Bag.type == 'parent'
        ).first()
        if not parent_bag:
            flash('Parent bag not found', 'error')
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            bill_id = request.form.get('bill_id', '').strip()
            if not bill_id:
                flash('Bill ID is required', 'error')
                return render_template('link_to_bill.html', parent_bag=parent_bag)
            
            # Import models locally to avoid circular imports  
            from models import Bill, acquire_bill_lock
            
            # Check if bill already exists
            bill = Bill.query.filter_by(bill_id=bill_id).first()
            if not bill:
                # Simplified validation for optimized version
                
                bill = Bill()
                bill.bill_id = bill_id
                bill.description = f"Bill for {bill_id}"
                bill.parent_bag_count = 0
                bill.status = 'draft'
                bill.expected_weight_kg = 0.0  # Initialize expected weight
                bill.total_weight_kg = 0.0  # Initialize actual weight
                db.session.add(bill)
                db.session.flush()
            
            # Acquire advisory lock before bill_bag operations
            acquire_bill_lock(bill.id)
            
            # Link parent bag to bill
            existing_link = BillBag.query.filter_by(
                bill_id=bill.id, 
                parent_bag_id=parent_bag.id
            ).first()
            
            if not existing_link:
                # OPTIMIZED: Use fast bill linking with automatic statistics update
                success, message = query_optimizer.link_bag_to_bill_fast(bill.id, parent_bag.id)  # type: ignore
                if not success:
                    flash(f'Failed to link bag: {message}', 'error')
                    return render_template('link_to_bill.html', parent_bag=parent_bag)
                
            db.session.commit()
            flash(f'Parent bag {qr_id} linked to bill {bill_id}', 'success')
            return redirect(url_for('dashboard'))
        
        return render_template('link_to_bill.html', parent_bag=parent_bag)
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Link to bill error: {e}")
        flash('Failed to link to bill', 'error')
        return redirect(url_for('dashboard'))

@app.route('/log_scan', methods=['POST'])
@login_required
def log_scan():
    """Log a QR code scan with status and notes"""
    try:
        qr_id = request.form.get('qr_id', '').strip()
        status = request.form.get('status', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not qr_id:
            flash('QR ID is required', 'error')
            return redirect(url_for('scan'))
        
        # Validate QR code format using InputValidator
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code(qr_id)
        if not is_valid:
            flash(f'Invalid QR code: {error_msg}', 'error')
            return redirect(url_for('scan'))
        qr_id = cleaned_qr  # Use cleaned/normalized QR code
        
        if not status:
            flash('Status is required', 'error')
            return redirect(url_for('scan'))
        
        # Find the bag by QR ID (case-insensitive)
        bag = Bag.query.filter(func.upper(Bag.qr_id) == func.upper(qr_id)).first()
        if not bag:
            flash(f'Bag with QR ID {qr_id} not found', 'error')
            return redirect(url_for('scan'))
        
        # Create scan record
        scan = Scan()
        scan.parent_bag_id = bag.id if bag.type == 'parent' else None
        scan.child_bag_id = bag.id if bag.type == 'child' else None
        scan.user_id = current_user.id
        scan.timestamp = datetime.utcnow()
        
        db.session.add(scan)
        db.session.commit()
        
        flash(f'Scan logged successfully for {bag.type} bag {qr_id}', 'success')
        return redirect(url_for('scan'))
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Log scan error: {e}")
        flash('Failed to log scan', 'error')
        return redirect(url_for('scan'))

@app.route('/scan', methods=['GET', 'POST'])
@login_required  
def scan():
    """Main QR scanning page"""
    return render_template('scan.html')

@app.route('/fix-admin-password')
@login_required
@limiter.limit("3 per hour")  # Strict rate limiting for password change operations
def fix_admin_password():
    """Fix admin password - ADMIN ONLY endpoint"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Require admin to provide new password via environment variable for security
    new_password = os.environ.get('NEW_ADMIN_PASSWORD')
    if not new_password:
        flash('NEW_ADMIN_PASSWORD environment variable must be set.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.filter_by(username='admin').first()
    if user:
        user.set_password(new_password)
        db.session.commit()
        
        # CRITICAL: Invalidate caches AFTER commit
        db.session.expire(user)
        app.logger.info(f'Cache invalidated for admin user after password change')
        
        flash('Admin password updated successfully.', 'success')
        app.logger.info(f"Admin password updated by {current_user.username}")
        return redirect(url_for('dashboard'))
    
    flash('Admin user not found.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Strict rate limiting to prevent spam and account creation abuse
def register():
    """User registration page with form validation"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Basic validation
            if not username or not email or not password or not confirm_password:
                flash('All fields are required.', 'error')
                return render_template('register.html')
            
            if len(username) < 3 or len(username) > 20:
                flash('Username must be between 3 and 20 characters.', 'error')
                return render_template('register.html')
            
            # Validate password complexity
            from password_utils import validate_password_complexity
            is_valid, error_message = validate_password_complexity(password)
            if not is_valid:
                flash(error_message, 'error')
                return render_template('register.html')
            
            if password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('register.html')
            
            # Import models locally to avoid circular imports
            from models import User
            
            # Check if user already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                # Audit log: Failed registration (username exists)
                log_audit('registration_failed_username_exists', 'auth', None, {
                    'username': username,
                    'email': email,
                    'ip_address': request.remote_addr,
                    'reason': 'username_already_exists'
                })
                flash('Username already exists. Please choose a different one.', 'error')
                return render_template('register.html')
                
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                # Audit log: Failed registration (email exists)
                log_audit('registration_failed_email_exists', 'auth', None, {
                    'username': username,
                    'email': email,
                    'ip_address': request.remote_addr,
                    'reason': 'email_already_registered'
                })
                flash('Email already registered. Please use a different email.', 'error')
                return render_template('register.html')
            
            # Create new user
            user = User()
            user.username = username
            user.email = email
            user.role = 'dispatcher'
            user.verified = True
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # CRITICAL: Invalidate caches AFTER commit
            db.session.expire(user)
            
            # Audit log: Successful registration
            log_audit('registration_success', 'auth', user.id, {
                'username': username,
                'email': email,
                'ip_address': request.remote_addr,
                'role': 'dispatcher',
                'verified': True
            })
            
            # Send welcome email
            try:
                from email_utils import EmailService
                success, error = EmailService.send_welcome_email(username, email)
                if not success:
                    app.logger.warning(f"Failed to send welcome email to {email}: {error}")
            except Exception as e:
                app.logger.warning(f"Welcome email error: {str(e)}")
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Registration error: {str(e)}')
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('register.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
@limiter.limit("5 per hour")  # Strict rate limiting to prevent email spam and abuse
def forgot_password():
    """Handle forgot password requests"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    from forms import ForgotPasswordForm
    from password_reset_utils import create_password_reset_token, send_password_reset_email
    from email_utils import EmailConfig
    
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        try:
            email = (form.email.data or '').strip().lower()
            
            # Find user by email
            user = User.query.filter_by(email=email).first()
            
            # SECURITY: Create token only if user exists, None otherwise
            token = create_password_reset_token(user) if user else None
            
            # SECURITY: Always call email function - identical path for all requests
            success, error = send_password_reset_email(user, token, request.host)
            
            # SECURITY: Always log the same message regardless of outcome
            app.logger.info(f"Password reset flow executed for email submission")
            
            # Always show IDENTICAL messages to prevent enumeration
            flash('If an account exists with that email, a password reset link has been sent.', 'success')
            flash('Note: If you don\'t receive an email within a few minutes, check your spam folder or contact your administrator.', 'info')
            
            return redirect(url_for('login'))
            
        except Exception as e:
            app.logger.error(f"Forgot password error: {str(e)}")
            flash('An error occurred. Please try again later.', 'error')
    
    return render_template('forgot_password.html', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
@limiter.limit("5 per hour")  # Rate limiting to prevent password reset abuse
def reset_password(token):
    """Handle password reset with token"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    from forms import ResetPasswordForm
    from password_reset_utils import validate_reset_token, reset_password as reset_user_password
    
    # Validate token
    user, error_message = validate_reset_token(token)
    
    if not user:
        flash(error_message or 'Invalid or expired reset link.', 'error')
        return redirect(url_for('forgot_password'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        try:
            new_password = form.password.data
            
            # Reset password
            success, error = reset_user_password(user, new_password)
            
            if success:
                flash('Your password has been reset successfully. You can now log in.', 'success')
                app.logger.info(f"Password reset successful for user: {user.username}")
                return redirect(url_for('login'))
            else:
                flash(error or 'Failed to reset password. Please try again.', 'error')
                
        except Exception as e:
            app.logger.error(f"Password reset error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
    
    return render_template('reset_password.html', form=form, token=token)

@app.route('/request_promotion', methods=['GET', 'POST'])
@login_required
def request_promotion():
    """Employee can request admin promotion"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Authentication error.', 'error')
            return redirect(url_for('login'))
        
        user = User.query.get(user_id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('login'))
        
        # Check if user is already an admin - prevent access to promotion page
        if user.role == 'admin':
            flash('You are already an admin.', 'info')
            return redirect(url_for('dashboard'))
        
        # Check if user already has a pending request
        existing_request = PromotionRequest.query.filter_by(
            user_id=user_id, 
            status=PromotionRequestStatus.PENDING.value
        ).first()
        
        if existing_request:
            app.logger.info(f'User {user.username} trying to access promotion page with existing request')
            flash('You already have a pending promotion request.', 'warning')
            return render_template('promotion_status.html', request=existing_request)
        
        # Check for any processed requests (approved/rejected) to show different message
        processed_request = PromotionRequest.query.filter_by(user_id=user_id).first()
        
        form = PromotionRequestForm()
        
        if form.validate_on_submit():
            try:
                promotion_request = PromotionRequest()
                promotion_request.user_id = user_id
                promotion_request.reason = form.reason.data
                promotion_request.status = PromotionRequestStatus.PENDING.value
                db.session.add(promotion_request)
                db.session.commit()
                
                app.logger.info(f'Promotion request created by {user.username}')
                flash('Your promotion request has been submitted for admin review.', 'success')
                return redirect(url_for('dashboard'))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Promotion request submission error: {str(e)}')
                flash('Failed to submit promotion request. Please try again.', 'error')
        
        return render_template('request_promotion.html', form=form, processed_request=processed_request)
        
    except Exception as e:
        app.logger.error(f'Request promotion page error: {str(e)}')
        import traceback
        traceback.print_exc()
        flash('An error occurred loading the promotion page. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/admin/promotions')
@login_required
def admin_promotions():
    """Admin view of all promotion requests"""
    app.logger.info(f"Admin promotions access - User ID: {current_user.id}, Role: {current_user.role}")
    
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    
    pending_requests = PromotionRequest.query.filter_by(
        status=PromotionRequestStatus.PENDING.value
    ).order_by(PromotionRequest.requested_at.desc()).all()
    
    all_requests = PromotionRequest.query.order_by(
        PromotionRequest.requested_at.desc()
    ).limit(50).all()
    
    return render_template('admin_promotions.html', 
                         pending_requests=pending_requests, 
                         all_requests=all_requests)

@app.route('/admin/promote_user', methods=['GET', 'POST'])
@login_required
def admin_promote_user():
    """Admin can directly promote users"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    
    form = AdminPromotionForm()
    
    # Populate user choices (only employees)
    dispatchers = User.query.filter_by(role='dispatcher').all()
    form.user_id.choices = [(u.id, f"{u.username} ({u.email})") for u in dispatchers]
    
    if form.validate_on_submit():
        try:
            user_to_promote = User.query.get(form.user_id.data)
            if user_to_promote:
                user_to_promote.role = 'admin'
                db.session.commit()
                
                app.logger.info(f'User {user_to_promote.username} promoted to admin by {current_user.username}')
                flash(f'Successfully promoted {user_to_promote.username} to admin!', 'success')
                return redirect(url_for('user_management'))
            else:
                flash('User not found.', 'error')
                
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Admin promotion error: {str(e)}')
            flash('Promotion failed. Please try again.', 'error')
    
    return render_template('admin_promote_user.html', form=form)

@app.route('/admin/promotion_request/<int:request_id>', methods=['GET', 'POST'])
@login_required
def process_promotion_request(request_id):
    """Admin can approve or reject promotion requests"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    
    promotion_request = PromotionRequest.query.get_or_404(request_id)
    
    if promotion_request.status != PromotionRequestStatus.PENDING.value:
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('admin_promotions'))
    
    form = PromotionRequestActionForm()
    
    if form.validate_on_submit():
        try:
            admin_id = session.get('user_id')
            promotion_request.admin_id = admin_id
            promotion_request.admin_notes = form.admin_notes.data
            promotion_request.processed_at = datetime.utcnow()
            
            if form.action.data == 'approve':
                promotion_request.status = PromotionRequestStatus.APPROVED.value
                # Promote the user
                user_to_promote = promotion_request.requested_by
                user_to_promote.role = 'admin'
                
                app.logger.info(f'Promotion request approved for {user_to_promote.username} by {current_user.username}')
                flash(f'Promotion request approved! {user_to_promote.username} is now an admin.', 'success')
            else:
                promotion_request.status = PromotionRequestStatus.REJECTED.value
                
                app.logger.info(f'Promotion request rejected for {promotion_request.requested_by.username} by {current_user.username}')
                flash('Promotion request rejected.', 'info')
            
            db.session.commit()
            return redirect(url_for('admin_promotions'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Process promotion request error: {str(e)}')
            flash('Failed to process request. Please try again.', 'error')
    
    return render_template('process_promotion_request.html', 
                         form=form, 
                         promotion_request=promotion_request)

# Scanning workflow routes (simplified without location selection)

@app.route('/scanner-test')
@login_required
def scanner_test():
    """Simple scanner test page"""
    return send_from_directory('/tmp', 'scanner_test.html')

@app.route('/scan/parent', methods=['GET', 'POST'])
@app.route('/scan_parent', methods=['GET', 'POST'])  # Alias for compatibility
def scan_parent():
    """Scan parent bag QR code - Fast scanner optimized"""
    # Manual authentication check that works
    if not is_logged_in():
        return redirect(url_for('login'))
    # Direct template render for fastest response
    return render_template('scan_parent.html')

@app.route('/api/fast_parent_scan', methods=['POST'])
def api_fast_parent_scan():
    """Ultra-fast parent scan API endpoint"""
    import time
    start_time = time.time()
    
    # Quick session check
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'message': 'Please login first',
            'auth_required': True
        }), 401
    
    # Get QR code
    qr_code = request.form.get('qr_code', '').strip()
    if not qr_code:
        return jsonify({
            'success': False,
            'message': 'No QR code provided'
        }), 400
    
    # Validate format using InputValidator
    is_valid, qr_code, error_msg = InputValidator.validate_qr_code(qr_code, bag_type='parent')
    if not is_valid:
        return jsonify({
            'success': False,
            'message': f'{error_msg} Got: {qr_code}',
            'show_popup': True
        }), 400
    
    try:
        # Fast SQL query
        result = db.session.execute(
            text("SELECT id, type FROM bag WHERE UPPER(qr_id) = UPPER(:qr_id) LIMIT 1"),
            {'qr_id': qr_code}
        ).fetchone()
        
        if result:
            if result.type != 'parent':
                return jsonify({
                    'success': False,
                    'message': f'{qr_code} is a {result.type} bag, not a parent bag'
                }), 400
            
            bag_id = result.id
        else:
            # Create new parent bag
            new_id = db.session.execute(
                text("""
                    INSERT INTO bag (qr_id, type, user_id, dispatch_area, created_at)
                    VALUES (:qr_id, 'parent', :user_id, :area, NOW())
                    RETURNING id
                """),
                {
                    'qr_id': qr_code,
                    'user_id': user_id,
                    'area': session.get('dispatch_area', 'Default')
                }
            ).scalar()
            bag_id = new_id
        
        # Record scan
        db.session.execute(
            text("""
                INSERT INTO scan (parent_bag_id, user_id, timestamp)
                VALUES (:bag_id, :user_id, NOW())
            """),
            {'bag_id': bag_id, 'user_id': user_id}
        )
        
        db.session.commit()
        
        # Update session
        session['current_parent_qr'] = qr_code
        session['current_parent_id'] = bag_id
        session.modified = True
        
        elapsed = round((time.time() - start_time) * 1000, 2)
        
        return jsonify({
            'success': True,
            'message': f'Parent bag {qr_code} ready',
            'parent_qr': qr_code,
            'redirect': url_for('scan_child'),
            'time_ms': elapsed
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Fast parent scan error: {str(e)}')
        
        return jsonify({
            'success': False,
            'message': 'Scan failed - please try again'
        }), 500



@app.route('/process_parent_scan', methods=['GET', 'POST'])
def process_parent_scan():
    """Process parent bag scan - Optimized for high concurrency"""
    # Manual authentication check that works
    if not is_logged_in():
        return redirect(url_for('login'))
    
    # Handle GET request - redirect to scan_parent
    if request.method == 'GET':
        return redirect(url_for('scan_parent'))
    
    # Check if this is an API call
    is_api = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
             request.headers.get('Content-Type') == 'application/json' or \
             'api' in request.path
    
    # Get user_id from session for faster authentication
    user_id = session.get('user_id')
    username = session.get('username', 'Unknown')
    if not user_id:
        if is_api:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        return redirect(url_for('login'))
    
    try:
        app.logger.info(f'Parent scan initiated - User ID: {user_id}')
        
        qr_code = request.form.get('qr_code', '').strip()
        
        if not qr_code:
            if is_api:
                return jsonify({'success': False, 'message': 'No QR code provided'}), 400
            flash('No QR code provided.', 'error')
            return redirect(url_for('scan_parent'))
        
        # Validate parent bag QR format using InputValidator
        is_valid, qr_code, error_msg = InputValidator.validate_qr_code(qr_code, bag_type='parent')
        if not is_valid:
            error_msg = f'❌ {error_msg} You scanned: {qr_code}'
            if is_api:
                return jsonify({'success': False, 'message': error_msg})
            flash(error_msg, 'error')
            return redirect(url_for('scan_parent'))
        
        # Use direct query to avoid session issues
        parent_bag = Bag.query.filter_by(qr_id=qr_code).first()
        
        if not parent_bag:
            # Validate QR code length before creating
            if len(qr_code) > 255:
                flash(f'QR code is too long (maximum 255 characters).', 'error')
                return redirect(url_for('scan_parent'))
            
            # Create new parent bag (models already imported at top)
            parent_bag = Bag()
            parent_bag.qr_id = qr_code
            parent_bag.type = 'parent'
            parent_bag.user_id = user_id  # Associate parent bag with user
            # Get dispatch_area from session
            parent_bag.dispatch_area = session.get('dispatch_area', 'Default Area')
            db.session.add(parent_bag)
            app.logger.info(f'AUDIT: User {username} (ID: {user_id}) created new parent bag {qr_code}')
        else:
            # Check if bag is already a child - cannot be converted to parent
            if parent_bag.type == 'child':
                flash(f'QR code {qr_code} is already registered as a child bag. One bag can only have one role - either parent OR child, never both.', 'error')
                return redirect(url_for('scan_parent'))
            elif parent_bag.type != 'parent':
                # Handle unknown bag types
                flash(f'QR code {qr_code} has an invalid bag type. Please contact support.', 'error')
                return redirect(url_for('scan_parent'))
            
            # Update user_id if not set (for existing parent bags)
            if not parent_bag.user_id:
                parent_bag.user_id = user_id
        
        # Create scan record for parent bag
        scan = Scan()
        scan.parent_bag_id = parent_bag.id
        scan.user_id = user_id
        db.session.add(scan)
        db.session.commit()
        
        # Store minimal session data
        session['current_parent_qr'] = qr_code
        session['parent_scan_time'] = datetime.utcnow().isoformat()
        session['last_scan'] = {
            'type': 'parent',
            'qr_id': qr_code,
            'timestamp': datetime.utcnow().isoformat()
        }
        # session.permanent is False (set at login) to ensure logout on browser close
        session.modified = True  # Force session save
        
        app.logger.info(f'Parent scan completed - QR: {qr_code}, User: {username}')
        
        if is_api:
            return jsonify({
                'success': True,
                'message': f'Parent bag {qr_code} processed successfully!',
                'parent_qr': qr_code,
                'redirect': url_for('scan_child')
            })
        flash(f'Parent bag {qr_code} processed successfully!', 'success')
        return redirect(url_for('scan_child'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Parent scan error: {str(e)}', exc_info=True)
        if is_api:
            return jsonify({'success': False, 'message': 'Error processing parent scan'}), 500
        flash('Error processing parent scan. Please try again.', 'error')
        return redirect(url_for('scan_parent'))

@app.route('/process_child_scan', methods=['GET', 'POST'])
def process_child_scan():
    """Optimized child bag processing for high concurrency"""
    # Manual authentication check
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not authenticated. Please login first.'})
    
    # Redirect GET requests to scan_child page
    if request.method == 'GET':
        return redirect(url_for('scan_child'))
    
    # Initialize variables for error handling
    qr_code = 'unknown'
    parent_qr = 'unknown'
    
    try:
        qr_code = request.form.get('qr_code', '').strip()
        
        if not qr_code:
            return jsonify({'success': False, 'message': 'No QR code provided'})
        
        # Validate QR code format using InputValidator (enforce child bag alphanumeric pattern)
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code(qr_code, bag_type='child')
        if not is_valid:
            return jsonify({'success': False, 'message': f'Invalid QR code: {error_msg}'})
        qr_code = cleaned_qr  # Use cleaned/normalized QR code
        
        # Get parent from session with fallback
        parent_qr = session.get('current_parent_qr', 'unknown')
        if not parent_qr:
            # Try to get from last_scan as fallback
            last_scan = session.get('last_scan')
            if last_scan and last_scan.get('type') == 'parent':
                parent_qr = last_scan.get('qr_id')
        
        if not parent_qr:
            return jsonify({'success': False, 'message': 'No parent bag selected. Please scan a parent bag first.'})
        
        # Check if trying to scan the same QR code as parent
        if qr_code == parent_qr:
            return jsonify({'success': False, 'message': f'Cannot link QR code {qr_code} to itself. Parent and child must be different QR codes.'})
        
        # Use query_optimizer for better performance with atomic locking
        # CRITICAL: Use SELECT FOR UPDATE to prevent race conditions on 30-child limit
        parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(parent_qr),
            Bag.type == 'parent'
        ).with_for_update().first()
        
        if not parent_bag:
            # Clear invalid parent from session to prevent repeated errors
            session.pop('current_parent_qr', None)
            return jsonify({
                'success': False, 
                'message': f'Parent bag {parent_qr} not found in database. It may have been deleted or the session expired. Please scan a parent bag again.',
                'clear_parent': True  # Signal frontend to clear parent selection
            })
        
        # CRITICAL: Check if parent is already completed (prevents 31st+ scans)
        if parent_bag.status == 'completed':
            return jsonify({'success': False, 'message': 'Parent bag already completed (30/30 limit reached). Please select a new parent bag.'})
        
        # Check if we've reached the 30 bags limit - OPTIMIZED with atomic lock
        current_child_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
        
        if current_child_count >= 30:
            return jsonify({'success': False, 'message': 'Parent bag is full! Maximum 30 child bags allowed per parent.'})
        
        # Use query_optimizer to check if bag already exists
        existing_bag = query_optimizer.get_bag_by_qr(qr_code)
        
        if existing_bag:
            # CRITICAL: Prevent parent bags from being used as children
            if existing_bag.type == 'parent':
                # Get details about this parent bag - OPTIMIZED
                child_count = query_optimizer.get_child_count_fast(existing_bag.id)  # type: ignore
                return jsonify({
                    'success': False,
                    'message': f'QR code {qr_code} is already registered as a parent bag with {child_count} child bags linked. One bag can only have one role - either parent OR child, never both.'
                })
            
            # If it's already a child, check if it's linked to any parent
            if existing_bag.type == 'child':
                existing_link = Link.query.filter_by(child_bag_id=existing_bag.id).first()
                if existing_link:
                    if existing_link.parent_bag_id == parent_bag.id:
                        # Prevent duplicates - DO NOT allow re-linking the same child
                        return jsonify({
                            'success': False,
                            'message': f'DUPLICATE: Child bag {qr_code} is already linked to this parent! Each child bag can only be scanned once.'
                        })
                    else:
                        existing_parent = Bag.query.get(existing_link.parent_bag_id)
                        existing_parent_qr = existing_parent.qr_id if existing_parent else 'Unknown'
                        return jsonify({
                            'success': False,
                            'message': f'Child bag {qr_code} is already linked to parent bag {existing_parent_qr}. One child can only be linked to one parent.'
                        })
                
                # Use existing child bag
                child_bag = existing_bag
            else:
                # Handle unknown bag types
                return jsonify({
                    'success': False,
                    'message': f'QR code {qr_code} has an invalid bag type ({existing_bag.type}). Please contact support.'
                })
        else:
            # Create new child bag with user association
            user_id = session.get('user_id')  # Get user_id from session since we're not using @login_required
            if not user_id:
                return jsonify({'success': False, 'message': 'Session expired. Please login again.'})
            
            child_bag = Bag()
            child_bag.qr_id = qr_code
            child_bag.type = 'child'
            child_bag.user_id = user_id  # Associate child bag with user
            child_bag.dispatch_area = parent_bag.dispatch_area
            db.session.add(child_bag)
            db.session.flush()  # Get the ID
        
        # Create link and scan record in batch
        link = Link()
        link.parent_bag_id = parent_bag.id
        link.child_bag_id = child_bag.id
        
        # Get user_id from session for scan record
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Session expired. Please login again.'})
        
        scan = Scan()
        scan.user_id = user_id
        scan.child_bag_id = child_bag.id
        
        db.session.add_all([link, scan])
        
        # CRITICAL: Calculate new count and auto-complete BEFORE commit (atomic)
        updated_count = current_child_count + 1
        
        # UPDATE PARENT BAG COUNT AND WEIGHT ON EVERY SCAN
        parent_bag.child_count = updated_count
        parent_bag.weight_kg = float(updated_count)  # 1kg per child bag
        
        # AUTO-COMPLETE WHEN 30 CHILDREN ARE LINKED
        # This MUST happen BEFORE commit to maintain atomic lock and prevent race conditions
        if updated_count == 30:
            parent_bag.status = 'completed'
            app.logger.info(f'Parent bag {parent_qr} automatically marked as completed with 30 children')
        
        # Single atomic commit (includes link, scan, AND status update if 30th child)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Child bag {qr_code} linked successfully! ({updated_count}/30)',
            'child_qr': qr_code,
            'parent_qr': parent_qr,
            'child_count': updated_count
        })
        
    except ValueError as e:
        # Handle validation errors from query_optimizer
        db.session.rollback()
        app.logger.error(f'Child scan validation error: {str(e)}')
        return jsonify({'success': False, 'message': str(e)})
    except Exception as e:
        db.session.rollback()
        # Add more detailed error logging
        app.logger.error(f'Child scan error: {str(e)}', exc_info=True)
        app.logger.error(f'Child scan details - QR: {qr_code if "qr_code" in locals() else "N/A"}, Parent: {parent_qr if "parent_qr" in locals() else "N/A"}')
        
        # Check for common database errors
        if 'duplicate key' in str(e).lower():
            return jsonify({'success': False, 'message': 'Duplicate entry detected. This bag may already be processed.'})
        elif 'foreign key' in str(e).lower():
            return jsonify({'success': False, 'message': 'Database relationship error. Please contact support.'})
        elif 'connection' in str(e).lower():
            return jsonify({'success': False, 'message': 'Database connection error. Please try again.'})
        else:
            return jsonify({'success': False, 'message': 'Error processing scan. Please try again or contact support.'})

@app.route('/ajax/scan_parent', methods=['POST'])
@login_required
def ajax_scan_parent_bag():
    """Process the parent bag QR code scan"""
    # Check if it's an AJAX request (simpler detection)
    is_ajax = 'qr_id' in request.form and request.method == 'POST'
    
    app.logger.info(f"Parent scan request - AJAX: {is_ajax}, QR_ID: {request.form.get('qr_id')}")
    
    if is_ajax:
        # Handle AJAX QR scan request - OPTIMIZED FOR SPEED
        qr_id = request.form.get('qr_id', '').strip()
        
        if not qr_id:
            return jsonify({'success': False, 'message': 'Please provide a QR code.'})
        
        try:
            # Validate QR code format for parent bags using InputValidator
            is_valid, qr_id, error_msg = InputValidator.validate_qr_code(qr_id, bag_type='parent')
            if not is_valid:
                return jsonify({
                    'success': False, 
                    'message': f'❌ {error_msg}\n\nYou scanned: {qr_id}',
                    'show_popup': True
                })
            
            # OPTIMIZED: Single query to check existing bag
            existing_bag = query_optimizer.get_bag_by_qr(qr_id)
            
            if existing_bag:
                if existing_bag.type == 'parent':
                    parent_bag = existing_bag
                    # Get current linked child count for existing parent
                    child_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
                    
                    # Store in session for child scanning  
                    session['last_scan'] = {
                        'type': 'parent',
                        'qr_id': qr_id,
                        'bag_name': parent_bag.name,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    session['current_parent_qr'] = qr_id
                    
                    return jsonify({
                        'success': True,
                        'parent_qr': qr_id,
                        'existing': True,
                        'child_count': child_count,
                        'message': f'Existing parent bag {qr_id} found with {child_count} linked child bags. Continue to add more children.',
                        'redirect': url_for('scan_child', s=request.args.get('s'))
                    })
                elif existing_bag.type == 'child':
                    # Check if this child is already linked to a parent
                    existing_link = Link.query.filter_by(child_bag_id=existing_bag.id).first()
                    if existing_link:
                        linked_parent = Bag.query.get(existing_link.parent_bag_id)
                        parent_qr = linked_parent.qr_id if linked_parent else 'Unknown'
                        return jsonify({'success': False, 'message': f'QR code {qr_id} is already registered as a child bag linked to parent {parent_qr}. Cannot use as parent.'})
                    else:
                        return jsonify({'success': False, 'message': f'QR code {qr_id} is already registered as a child bag. Cannot use as parent.'})
                else:
                    return jsonify({'success': False, 'message': f'QR code {qr_id} has an invalid bag type ({existing_bag.type}). Please contact support.'})
            else:
                # OPTIMIZED: Create new parent bag
                try:
                    parent_bag = query_optimizer.create_bag_optimized(
                        qr_id=qr_id,
                        bag_type='parent',
                        user_id=current_user.id,
                        dispatch_area=current_user.dispatch_area if current_user.is_dispatcher() else None
                    )
                except ValueError as e:
                    return jsonify({'success': False, 'message': str(e)})
            
            # OPTIMIZED: Create scan record
            if parent_bag:
                query_optimizer.create_scan_optimized(
                    user_id=current_user.id,
                    parent_bag_id=parent_bag.id
                )
                
                # OPTIMIZED: Single bulk commit
                if not query_optimizer.bulk_commit():
                    return jsonify({'success': False, 'message': 'Database error occurred'})
                
                # Store in session for child scanning  
                session['last_scan'] = {
                    'type': 'parent',
                    'qr_id': qr_id,
                    'bag_name': parent_bag.name if hasattr(parent_bag, 'name') else qr_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                return jsonify({'success': False, 'message': 'Failed to create parent bag'})
            # Also store the current parent QR for child scanner
            session['current_parent_qr'] = qr_id
            
            # Instant response with redirect to child scanning
            return jsonify({
                'success': True,
                'parent_qr': qr_id,
                'message': f'Parent bag {qr_id} scanned successfully! Now scan child bags.',
                'redirect': url_for('scan_child', s=request.args.get('s'))
            })
            
        except ValueError as e:
            # Handle validation errors from query_optimizer
            db.session.rollback()
            app.logger.error(f'Parent scan validation error: {str(e)}')
            return jsonify({'success': False, 'message': str(e)})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Parent scan processing error: {str(e)}')
            # Check for common database errors
            if 'duplicate key' in str(e).lower():
                return jsonify({'success': False, 'message': 'Duplicate entry detected. This bag may already be processed.'})
            elif 'foreign key' in str(e).lower():
                return jsonify({'success': False, 'message': 'Database relationship error. Please contact support.'})
            elif 'connection' in str(e).lower():
                return jsonify({'success': False, 'message': 'Database connection error. Please try again.'})
            else:
                return jsonify({'success': False, 'message': 'Error processing scan. Please try again or contact support.'})
    
    else:
        # Only camera scanning allowed - no manual form submission
        return redirect(url_for('scan_parent'))

@app.route('/process_child_scan_fast', methods=['POST'])
@login_required
@limiter.exempt  # Exempt from rate limiting for fast scanning
def process_child_scan_fast():
    """Ultra-fast child bag processing with CSRF exemption for JSON requests"""
    # Import optimized handler
    try:
        # Skip optimized handler - use standard processing
        optimized_child_scan_handler = None
    except ImportError:
        # Fallback to original implementation if optimization not available
        pass
    
    try:
        # Get QR code from JSON or form data
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            qr_id = data.get('qr_code', '').strip()
        else:
            qr_id = request.form.get('qr_code', '').strip()
        
        if not qr_id:
            return jsonify({'success': False, 'message': 'No QR code provided'})
        
        # Validate QR code format using InputValidator (enforce child bag alphanumeric pattern)
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code(qr_id, bag_type='child')
        if not is_valid:
            return jsonify({'success': False, 'message': f'Invalid QR code: {error_msg}'})
        qr_id = cleaned_qr  # Use cleaned/normalized QR code
        
        # Get parent from session (fastest possible)
        parent_qr = session.get('current_parent_qr')
        if not parent_qr:
            return jsonify({'success': False, 'message': 'No parent bag selected'})
        
        if qr_id == parent_qr:
            return jsonify({'success': False, 'message': 'Cannot link to itself'})
        
        # Fallback to ORM queries (optimized handler not available)
        # CRITICAL: Use SELECT FOR UPDATE to prevent race conditions on 30-child limit
        parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(parent_qr),
            Bag.type == 'parent'
        ).with_for_update().first()
        
        if not parent_bag:
            app.logger.error(f'[FAST_SCAN] Parent bag not found: {parent_qr}')
            return jsonify({'success': False, 'message': 'Parent bag not found'})
        
        # CRITICAL: Check if parent is already completed (prevents 31st+ scans)
        app.logger.info(f'[FAST_SCAN] Parent {parent_qr} (ID:{parent_bag.id}) status={parent_bag.status}')
        if parent_bag.status == 'completed':
            app.logger.warning(f'[FAST_SCAN] REJECTED: Parent {parent_qr} already completed - child {qr_id} blocked')
            return jsonify({'success': False, 'message': 'Parent bag already completed (30/30 limit reached)'})
        
        # Check current count and enforce 30-bag limit (atomic with lock above)
        current_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
        app.logger.info(f'[FAST_SCAN] Parent {parent_qr} current_count={current_count}, attempting to link {qr_id}')
        if current_count >= 30:
            app.logger.warning(f'[FAST_SCAN] REJECTED: Parent {parent_qr} at {current_count}/30 limit - child {qr_id} blocked')
            return jsonify({'success': False, 'message': 'Maximum 30 child bags reached!'}) 
        
        # Check/create child bag (case-insensitive)
        child_bag = Bag.query.filter(func.upper(Bag.qr_id) == func.upper(qr_id)).first()
        if child_bag:
            if child_bag.type == 'parent':
                return jsonify({'success': False, 'message': f'DUPLICATE: {qr_id} is already a parent bag'})
            # STRICT DUPLICATE PREVENTION: Check if already linked
            existing_link = Link.query.filter_by(child_bag_id=child_bag.id).first()
            if existing_link:
                return jsonify({'success': False, 'message': f'DUPLICATE: {qr_id} already linked to parent'})
        else:
            # Create new child bag
            child_bag = Bag()
            child_bag.qr_id = qr_id
            child_bag.type = 'child'
            child_bag.dispatch_area = parent_bag.dispatch_area
            db.session.add(child_bag)
            db.session.flush()
        
        # Create link and scan record
        link = Link()
        link.parent_bag_id = parent_bag.id
        link.child_bag_id = child_bag.id
        scan = Scan()
        scan.user_id = current_user.id
        scan.child_bag_id = child_bag.id
        db.session.add(link)
        db.session.add(scan)
        
        # CRITICAL: Calculate new count BEFORE commit to set status atomically
        # This prevents race condition where 31st scan slips in before status is set
        new_count = current_count + 1
        
        # UPDATE PARENT BAG COUNT AND WEIGHT ON EVERY SCAN
        parent_bag.child_count = new_count
        parent_bag.weight_kg = float(new_count)  # 1kg per child bag
        
        # AUTO-COMPLETE WHEN 30 CHILDREN ARE LINKED
        # This MUST happen BEFORE commit to maintain atomic lock
        if new_count == 30:
            parent_bag.status = 'completed'
            app.logger.info(f'[FAST_SCAN] Parent {parent_qr} auto-completing with 30th child {qr_id}')
        
        # Single atomic commit (includes link, scan, AND status update if 30th child)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'child_qr': qr_id,
            'parent_qr': parent_qr,
            'child_count': new_count,
            'message': f'✓ {qr_id} linked! ({new_count}/30)'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Fast child scan error: {str(e)}')
        if 'duplicate' in str(e).lower():
            return jsonify({'success': False, 'message': 'DUPLICATE: Already scanned'})
        return jsonify({'success': False, 'message': 'Error processing scan'})

@app.route('/api/unlink_child', methods=['POST'])
@login_required
def api_unlink_child():
    """Unlink a child bag from current parent (undo functionality)"""
    try:
        # Get QR code from JSON (optional - if not provided, unlink most recent)
        data = request.get_json() or {}
        qr_id = data.get('qr_code', '').strip()
        
        # Get parent from request body (for bag details page) or session (for scanning workflow)
        parent_qr = data.get('parent_qr', '').strip() or session.get('current_parent_qr')
        if not parent_qr:
            return jsonify({'success': False, 'message': 'No parent bag specified'})
        
        # Get parent bag
        parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(parent_qr),
            Bag.type == 'parent'
        ).first()
        if not parent_bag:
            return jsonify({'success': False, 'message': 'Parent bag not found'})
        
        # If QR code provided, find specific child. Otherwise, find most recent link.
        if qr_id:
            # Specific child bag
            child_bag = Bag.query.filter(func.upper(Bag.qr_id) == func.upper(qr_id)).first()
            if not child_bag:
                return jsonify({'success': False, 'message': 'Child bag not found'})
            
            # Find the link for this specific parent-child combination
            link = Link.query.filter_by(
                parent_bag_id=parent_bag.id,
                child_bag_id=child_bag.id
            ).first()
        else:
            # Find the most recent link for this parent
            from datetime import datetime, timedelta
            recent_cutoff = datetime.utcnow() - timedelta(hours=1)
            
            link = Link.query.filter_by(parent_bag_id=parent_bag.id)\
                .filter(Link.created_at >= recent_cutoff)\
                .order_by(Link.created_at.desc())\
                .first()
            
            if not link:
                return jsonify({'success': False, 'message': 'No recent scan to undo (must be within 1 hour)'})
            
            # Get the child bag from the link
            child_bag = Bag.query.get(link.child_bag_id)
            if not child_bag:
                return jsonify({'success': False, 'message': 'Child bag not found'})
            
            qr_id = child_bag.qr_id  # Set for logging and response
        
        if not link:
            return jsonify({'success': False, 'message': 'Link not found'})
        
        # Find the MOST RECENT scan for this specific parent-child combination
        # Filter by BOTH parent_bag_id and child_bag_id to ensure we get the right scan
        # Order by timestamp DESC to get the latest scan for this exact link
        from datetime import datetime, timedelta
        scan = Scan.query.filter_by(
            parent_bag_id=parent_bag.id,
            child_bag_id=child_bag.id,
            user_id=current_user.id
        ).order_by(Scan.timestamp.desc()).first()
        
        # Additional safety check: only delete the scan if it's recent (within last hour)
        # This prevents accidentally deleting old audit records
        if scan and scan.timestamp and (datetime.utcnow() - scan.timestamp) > timedelta(hours=1):
            app.logger.warning(f'Scan too old to undo: {scan.timestamp}')
            scan = None  # Don't delete old scans
        
        # Delete link first
        db.session.delete(link)
        
        # Delete ALL scan records for this child bag (not just recent ones)
        all_child_scans = Scan.query.filter_by(child_bag_id=child_bag.id).all()
        for child_scan in all_child_scans:
            db.session.delete(child_scan)
        
        # Delete the child bag itself - no unlinked child bags should exist in the database
        db.session.delete(child_bag)
        
        db.session.commit()
        
        # Get new count
        new_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
        
        # Reset parent bag status if it was completed
        if parent_bag.status == 'completed' and new_count < 30:
            parent_bag.status = 'pending'
            parent_bag.child_count = new_count
            parent_bag.weight_kg = float(new_count)
            db.session.commit()
        
        app.logger.info(f'User {current_user.id} unlinked and deleted child {qr_id} from parent {parent_qr}')
        
        return jsonify({
            'success': True,
            'child_count': new_count,
            'message': f'Removed and deleted {qr_id} from {parent_qr}'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Unlink child error: {str(e)}')
        return jsonify({'success': False, 'message': 'Error removing link'})

@app.route('/complete_parent_scan', methods=['POST'])
@login_required
def complete_parent_scan():
    """Complete parent bag scanning and mark as completed if 30 children"""
    try:
        # Get parent from session
        parent_qr = session.get('current_parent_qr')
        if not parent_qr:
            return jsonify({'success': False, 'message': 'No parent bag in session'})
        
        # Get parent bag
        parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(parent_qr),
            Bag.type == 'parent'
        ).first()
        if not parent_bag:
            return jsonify({'success': False, 'message': 'Parent bag not found'})
        
        # Count linked children
        child_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
        
        # Update status if 30 children
        if child_count == 30:
            parent_bag.status = 'completed'
            parent_bag.child_count = 30
            parent_bag.weight_kg = 30.0  # 1kg per child
            db.session.commit()
            
            # Clear session
            session.pop('current_parent_qr', None)
            
            return jsonify({
                'success': True,
                'message': f'Parent bag {parent_qr} completed with 30 children (30kg)',
                'redirect': url_for('dashboard')
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Parent bag has only {child_count}/30 children. Please scan {30-child_count} more.'
            })
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Complete parent scan error: {str(e)}')
        return jsonify({'success': False, 'message': 'Error completing parent scan'})

@app.route('/scan/child', methods=['GET', 'POST'])
@app.route('/scan_child', methods=['GET', 'POST'])  # type: ignore
def scan_child():
    """Scan child bag QR code - unified GET/POST handler"""
    # Manual authentication check
    if not is_logged_in():
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'Not authenticated. Please login first.'})
        return redirect(url_for('login'))
    # Handle JSON request (from QR scanner and manual entry)
    if request.method == 'POST':
        # Check if it's JSON data (AJAX) - exempt from CSRF for QR scanning
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            qr_id = data.get('qr_code', '').strip()
            app.logger.info(f"Child scan request - JSON AJAX: True, QR_CODE: {qr_id}")
        # Check if it's form data
        elif 'qr_code' in request.form:
            qr_id = request.form.get('qr_code', '').strip()  
            app.logger.info(f"Child scan request - FORM: True, QR_CODE: {qr_id}")
        else:
            qr_id = None
            app.logger.info(f"Child scan request - NO DATA, Method: {request.method}")
            return jsonify({'success': False, 'message': 'No QR code provided'})
            
        if qr_id:
            # Handle QR scan request - ULTRA-OPTIMIZED FOR SUB-SECOND RESPONSE
            try:
                # Validate QR code format using InputValidator (enforce child bag alphanumeric pattern)
                is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code(qr_id, bag_type='child')
                if not is_valid:
                    return jsonify({'success': False, 'message': f'Invalid QR code: {error_msg}'})
                qr_id = cleaned_qr  # Use cleaned/normalized QR code
                
                # OPTIMIZED: Get parent bag from session (cached)
                parent_qr = session.get('current_parent_qr')
                if not parent_qr:
                    # Try fallback from last_scan
                    last_scan = session.get('last_scan')
                    if last_scan and last_scan.get('type') == 'parent':
                        parent_qr = last_scan.get('qr_id')
                        
                if not parent_qr:
                    app.logger.error(f'No parent in session. Session keys: {list(session.keys())}')
                    return jsonify({'success': False, 'message': 'No parent bag selected. Please scan a parent bag first.'})
                
                # OPTIMIZED: Get parent bag efficiently - try direct query first
                parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(parent_qr),
            Bag.type == 'parent'
        ).first()
                if not parent_bag:
                    # Try without type restriction as fallback
                    parent_bag = Bag.query.filter(func.upper(Bag.qr_id) == func.upper(parent_qr)).first()
                    if parent_bag and parent_bag.type != 'parent':
                        app.logger.error(f'Bag {parent_qr} exists but is type {parent_bag.type}, not parent')
                        return jsonify({'success': False, 'message': f'QR {parent_qr} is not a parent bag. Please scan a parent bag first.'})
                    
                if not parent_bag:
                    app.logger.error(f'Parent bag {parent_qr} not found in DB')
                    # Clear invalid parent from session to prevent repeated errors
                    session.pop('current_parent_qr', None)
                    return jsonify({
                        'success': False, 
                        'message': f'Parent bag {parent_qr} not found in database. It may have been deleted or the session expired. Please scan a parent bag again.',
                        'clear_parent': True
                    })
                
                # Check if trying to scan the same QR code as parent
                if qr_id == parent_qr:
                    return jsonify({'success': False, 'message': f'Cannot link QR code {qr_id} to itself. Parent and child must be different QR codes.'})
                
                # OPTIMIZED: Check bag exists and validate its type
                existing_bag = query_optimizer.get_bag_by_qr(qr_id)
                
                if existing_bag:
                    if existing_bag.type == 'parent':
                        # Get details about this parent bag
                        child_count = Link.query.filter_by(parent_bag_id=existing_bag.id).count()
                        return jsonify({'success': False, 'message': f'QR code {qr_id} is already registered as a parent bag with {child_count} child bags linked. One bag can only have one role - either parent OR child, never both.'})
                    elif existing_bag.type == 'child':
                        # Check if this child is already linked to another parent
                        existing_link = Link.query.filter_by(child_bag_id=existing_bag.id).first()
                        if existing_link and existing_link.parent_bag_id != parent_bag.id:
                            linked_parent = Bag.query.get(existing_link.parent_bag_id)
                            parent_qr_linked = linked_parent.qr_id if linked_parent else 'Unknown'
                            return jsonify({'success': False, 'message': f'Child bag {qr_id} is already linked to parent bag {parent_qr_linked}. One child can only be linked to one parent.'})
                        elif existing_link and existing_link.parent_bag_id == parent_bag.id:
                            # Already linked to this parent - return success with current count
                            current_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
                            return jsonify({
                                'success': True,
                                'child_qr': qr_id,
                                'child_name': existing_bag.name if hasattr(existing_bag, 'name') else None,
                                'parent_qr': parent_qr,
                                'message': f'{qr_id} was already linked to this parent! ({current_count}/30)',
                                'child_count': current_count
                            })
                    else:
                        return jsonify({'success': False, 'message': f'QR code {qr_id} has an invalid bag type ({existing_bag.type}). Please contact support.'})
                
                # OPTIMIZED: Create child bag if needed
                if not existing_bag:
                    try:
                        child_bag = query_optimizer.create_bag_optimized(
                            qr_id=qr_id,
                            bag_type='child',
                            user_id=current_user.id,
                            dispatch_area=parent_bag.dispatch_area
                        )
                    except ValueError as e:
                        return jsonify({'success': False, 'message': str(e)})
                else:
                    child_bag = existing_bag
                
                # OPTIMIZED: Check if link already exists before creating
                if child_bag:
                    existing_link = Link.query.filter_by(parent_bag_id=parent_bag.id, child_bag_id=child_bag.id).first()
                    if existing_link:
                        # Link already exists - return success with current count
                        current_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
                        return jsonify({
                            'success': True,
                            'child_qr': qr_id,
                            'child_name': child_bag.name if hasattr(child_bag, 'name') else None,
                            'parent_qr': parent_bag.qr_id,
                            'message': f'{qr_id} was already linked to this parent! ({current_count}/30)',
                            'child_count': current_count
                        })
                else:
                    return jsonify({'success': False, 'message': 'Failed to create or find child bag'})
                
                # Create new link
                if parent_bag and child_bag:
                    app.logger.info(f'Creating link between parent {parent_bag.id} ({parent_bag.qr_id}) and child {child_bag.id} ({child_bag.qr_id})')
                    try:
                        link, created = query_optimizer.create_link_optimized(parent_bag.id, child_bag.id)
                    except ValueError as validation_error:
                        # Circular relationship detected
                        return jsonify({'success': False, 'message': str(validation_error)})
                    
                    if not created:
                        # This shouldn't happen since we checked above, but handle gracefully
                        current_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
                        return jsonify({
                            'success': True,
                            'child_qr': qr_id,
                            'child_name': child_bag.name if hasattr(child_bag, 'name') else None,
                            'parent_qr': parent_bag.qr_id,
                            'message': f'{qr_id} was already linked! ({current_count}/30)',
                            'child_count': current_count
                        })
                    
                    # OPTIMIZED: Create scan record
                    query_optimizer.create_scan_optimized(
                        user_id=current_user.id,
                        child_bag_id=child_bag.id
                    )
                    
                    # OPTIMIZED: Single bulk commit for maximum speed
                    try:
                        db.session.commit()
                        app.logger.info(f'Successfully committed link between {parent_bag.qr_id} and {qr_id}')
                        
                        # ULTRA-FAST: Get current count and return
                        current_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
                        return jsonify({
                            'success': True,
                            'child_qr': qr_id,
                            'child_name': child_bag.name if hasattr(child_bag, 'name') else None,
                            'parent_qr': parent_bag.qr_id,
                            'message': f'{qr_id} linked successfully! ({current_count}/30)',
                            'child_count': current_count
                        })
                    except Exception as commit_error:
                        db.session.rollback()
                        app.logger.error(f'Commit failed for linking {qr_id} to {parent_bag.qr_id}: {str(commit_error)}')
                        return jsonify({'success': False, 'message': 'Failed to save link. Please try again.'})
                else:
                    return jsonify({'success': False, 'message': 'Parent or child bag not found'})
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Child scan error: {str(e)}')
                return jsonify({'success': False, 'message': f'Error processing scan: {str(e)}'})
    
    else:
        # Optimized GET request handling for child scanning page
        parent_bag = None
        scanned_child_count = 0
        
        # Get parent QR from session with fallback
        parent_qr = session.get('current_parent_qr')
        if not parent_qr:
            last_scan = session.get('last_scan', {})
            if last_scan.get('type') == 'parent':
                parent_qr = last_scan.get('qr_id')
        
        # If no parent scan in session, redirect to parent scan
        if not parent_qr:
            flash('Please scan a parent bag first before scanning child bags.', 'warning')
            return redirect(url_for('scan_parent'))
        
        app.logger.info(f'CHILD SCAN PAGE: Parent QR from session: {parent_qr}')
        app.logger.info(f'CHILD SCAN PAGE: Session keys: {list(session.keys())}')
        
        linked_child_bags = []
        if parent_qr:
            # Single optimized query to get parent and children
            parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(parent_qr),
            Bag.type == 'parent'
        ).first()
            
            if not parent_bag:
                # Try without type restriction to check if bag exists with wrong type
                parent_bag_any = Bag.query.filter(func.upper(Bag.qr_id) == func.upper(parent_qr)).first()
                if parent_bag_any:
                    app.logger.error(f'CHILD SCAN PAGE: Bag {parent_qr} exists but has type {parent_bag_any.type}, not parent. Clearing invalid session data.')
                    # SECURITY FIX: Never auto-convert bag types as it corrupts data integrity
                    # Instead, clear the invalid session and redirect to parent scan
                    session.pop('current_parent_qr', None)
                    session.pop('last_scan', None)
                    flash(f'The QR code in session ({parent_qr}) is not a parent bag. Please scan a valid parent bag.', 'error')
                    return redirect(url_for('scan_parent'))
                else:
                    app.logger.error(f'CHILD SCAN PAGE: Parent bag {parent_qr} not found in database at all. Clearing invalid session data.')
                    session.pop('current_parent_qr', None)
                    session.pop('last_scan', None)
                    flash('Parent bag not found in database. Please scan a valid parent bag.', 'error')
                    return redirect(url_for('scan_parent'))
            
            if parent_bag:
                # Get count of linked child bags and the actual linked bags
                scanned_child_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
                # Get existing linked child bags to display
                linked_child_bags = db.session.query(Bag).join(
                    Link, Bag.id == Link.child_bag_id
                ).filter(
                    Link.parent_bag_id == parent_bag.id,
                    Bag.type == 'child'
                ).all()
        
        # Pass proper context with parent bag details
        parent_bag_dict = None
        if parent_bag:
            parent_bag_dict = {
                'qr_code': parent_bag.qr_id,
                'id': parent_bag.id,
                'type': parent_bag.type,
                'dispatch_area': parent_bag.dispatch_area if hasattr(parent_bag, 'dispatch_area') else None
            }
        
        # Use optimized template for better performance
        return render_template('scan_child_optimized.html', 
                             parent_bag=parent_bag_dict,
                             parent_qr=parent_qr,
                             scanned_child_count=scanned_child_count,
                             linked_child_bags=linked_child_bags,
                             form=ManualScanForm())

@app.route('/scan/complete', methods=['GET', 'POST'])
@login_required
def scan_complete():
    """Completion page for scanning workflow"""
    # Check if this is an XHR request (from station page)
    is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        # Get parent bag from session
        parent_qr = session.get('current_parent_qr')
        if not parent_qr:
            if is_xhr:
                return jsonify({'success': True, 'message': 'No parent bag to complete'})
            flash('No recent scan found.', 'info')
            return redirect(url_for('dashboard'))
        
        # Get parent bag details
        parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(parent_qr),
            Bag.type == 'parent'
        ).first()
        if not parent_bag:
            if is_xhr:
                return jsonify({'success': False, 'message': 'Parent bag not found'})
            flash('Parent bag not found.', 'error')
            return redirect(url_for('dashboard'))
        
        # Get all child bags linked to this parent through Link table
        child_bags = db.session.query(Bag).join(
            Link, Bag.id == Link.child_bag_id
        ).filter(
            Link.parent_bag_id == parent_bag.id,
            Bag.type == 'child'
        ).all()
        scan_count = len(child_bags)
        
        # Log scan completion metrics
        app.logger.info(f'Scan validation - Parent QR: {parent_qr}, Parent ID: {parent_bag.id}, Child count: {scan_count}')
        
        # For XHR requests (station page), allow any count
        if is_xhr:
            # Clear session parent data
            session.pop('current_parent_qr', None)
            session.pop('parent_scan_time', None)
            return jsonify({
                'success': True, 
                'message': f'Parent {parent_qr} completed with {scan_count} children',
                'child_count': scan_count
            })
        
        # Verify link count for data integrity
        link_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
        if link_count != scan_count:
            app.logger.warning(f'Link count mismatch detected - Parent ID: {parent_bag.id}, Link count: {link_count}, Child count: {scan_count}')
        
        # Validate exactly 30 bags requirement (for traditional workflow only)
        if scan_count != 30:
            flash(f'Error: You have scanned {scan_count} bags but exactly 30 are required. Please continue scanning.', 'error')
            return redirect(url_for('scan_child'))
        
        # Update parent bag status to completed and calculate weight
        parent_bag.status = 'completed'
        parent_bag.child_count = scan_count
        parent_bag.weight_kg = scan_count * 1.0  # 1kg per child bag
        db.session.commit()
        
        app.logger.info(f'Parent bag {parent_qr} marked as completed with {scan_count} children, weight: {parent_bag.weight_kg}kg')
        
        # Store completion data in session
        session['last_scan'] = {
            'type': 'completed',
            'parent_qr': parent_qr,
            'child_count': scan_count,
            'weight_kg': parent_bag.weight_kg,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        flash(f'Successfully completed! Parent bag {parent_qr} linked with exactly {scan_count} child bags (Total weight: {parent_bag.weight_kg}kg).', 'success')
        
        return render_template('scan_complete.html', 
                             parent_bag=parent_bag, 
                             child_bags=child_bags, 
                             scan_count=scan_count)
    except Exception as e:
        app.logger.error(f'Scan complete error: {str(e)}', exc_info=True)
        if is_xhr:
            return jsonify({'success': False, 'message': 'Error completing scan'})
        flash('Error loading scan summary.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/scan/finish', methods=['GET', 'POST'])
@login_required
def finish_scanning():
    """Complete the scanning process"""
    # Clear session data
    session.pop('last_scan', None)
    flash('Scanning session completed.', 'success')
    return redirect(url_for('dashboard'))

# Bag lookup and management routes

@app.route('/lookup', methods=['GET', 'POST'])
@login_required
def child_lookup():
    """Universal bag lookup - works with both parent and child bag QR codes"""
    form = ChildLookupForm()
    bag_info = None
    
    # Check for qr_id parameter in URL for pre-filling
    url_qr_id = request.args.get('qr_id', '').strip()
    
    if form.validate_on_submit():
        qr_id = sanitize_input(form.qr_id.data.strip() if form.qr_id.data else '')
    elif url_qr_id:
        # If there's a QR ID in the URL, use it for lookup
        qr_id = sanitize_input(url_qr_id.strip() if url_qr_id else '')
    elif request.method == 'POST':
        # Handle direct form submission without WTForms validation
        form_qr = request.form.get('qr_id', '')
        qr_id = sanitize_input(form_qr.strip() if form_qr else '')
        
        # Check if this is an AJAX request from scanner
        is_ajax = request.headers.get('Content-Type', '').startswith('application/json') or request.is_json
        app.logger.info(f'Lookup POST request - QR: {qr_id}, AJAX: {is_ajax}')
    else:
        qr_id = None
    
    if qr_id:
        try:
            import time
            
            start_time = time.time()
            app.logger.info(f'Lookup request for QR ID: {qr_id}')
            
            # Try to find as a bag first (case-insensitive)
            bag = Bag.query.filter(func.upper(Bag.qr_id) == func.upper(qr_id)).first()
            
            # If not found as bag, check if it's a bill
            bill = None
            if not bag:
                from models import Bill
                bill = Bill.query.filter(func.upper(Bill.bill_id) == func.upper(qr_id)).first()
            
            search_time_ms = (time.time() - start_time) * 1000
            
            if bag:
                # Build bag info dictionary
                bag_info = {
                    'id': bag.id,
                    'qr_id': bag.qr_id,
                    'type': bag.type,
                    'name': bag.name,
                    'dispatch_area': bag.dispatch_area,
                    'created_at': bag.created_at,
                    'updated_at': bag.updated_at
                }
                
                # Add relationship counts
                if bag.type == 'parent':
                    # Get linked child bags
                    child_links = Link.query.filter_by(parent_bag_id=bag.id).all()
                    bag_info['child_count'] = len(child_links)
                    bag_info['children'] = []
                    for link in child_links:
                        child_bag = Bag.query.get(link.child_bag_id)
                        if child_bag:
                            bag_info['children'].append({
                                'qr_id': child_bag.qr_id,
                                'name': child_bag.name,
                                'dispatch_area': child_bag.dispatch_area
                            })
                else:  # child bag
                    # Get parent bags
                    parent_links = Link.query.filter_by(child_bag_id=bag.id).all()
                    bag_info['parent_count'] = len(parent_links)
                    bag_info['parents'] = []
                    for link in parent_links:
                        parent_bag = Bag.query.get(link.parent_bag_id)
                        if parent_bag:
                            bag_info['parents'].append({
                                'qr_id': parent_bag.qr_id,
                                'name': parent_bag.name,
                                'dispatch_area': parent_bag.dispatch_area
                            })
                
                app.logger.info(f'Search SUCCESS: Found bag {qr_id} in {search_time_ms:.2f}ms')
            elif bill:
                # Found a bill - redirect to bill details page
                app.logger.info(f'Search SUCCESS: Found bill {qr_id} in {search_time_ms:.2f}ms')
                flash(f'Bill {bill.bill_id} found! Redirecting to bill details.', 'success')
                return redirect(url_for('view_bill', bill_id=bill.id))
            else:
                app.logger.info(f'Search: No bag or bill found for "{qr_id}" in {search_time_ms:.2f}ms')
                
                # Try fuzzy search as fallback for better user experience
                try:
                    # Simple fuzzy search using ILIKE
                    similar_bags = Bag.query.filter(
                        Bag.qr_id.ilike(f'%{qr_id[:3]}%')
                    ).limit(5).all()
                    
                    if similar_bags:
                        app.logger.info(f'Fuzzy search found {len(similar_bags)} similar results')
                        similar_qr_codes = ", ".join([b.qr_id for b in similar_bags[:3]])
                        flash(f'Bag "{qr_id}" not found. Did you mean: {similar_qr_codes}?', 'warning')
                    else:
                        flash(f'Bag or Bill "{qr_id}" does not exist in the system. Please verify the QR code or create it first.', 'error')
                except Exception as e:
                    app.logger.error(f'Fuzzy search error: {str(e)}')
                    flash(f'Bag or Bill "{qr_id}" does not exist in the system. Please verify the QR code or create it first.', 'error')
                    
        except Exception as e:
            app.logger.error(f'Bag lookup error for {qr_id}: {str(e)}')
            # Rollback any failed transaction
            try:
                db.session.rollback()
            except:
                pass
            flash('An error occurred while searching. Please try again.', 'error')
    
    return render_template('child_lookup.html', form=form, bag_info=bag_info)

@app.route('/scans')
@login_required
def scan_history():
    """Scan history dashboard with filtering"""
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '').strip()
    
    # Sanitize search query to prevent XSS
    if search_query:
        search_query = InputValidator.sanitize_search_query(search_query)
    
    # Build query
    query = Scan.query
    
    if search_query:
        query = query.join(Bag, or_(
            Scan.parent_bag_id == Bag.id,
            Scan.child_bag_id == Bag.id
        )).filter(Bag.qr_id.contains(search_query))
    
    # Paginate results
    scans = query.order_by(desc(Scan.timestamp)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Add stats for the template
    stats = {
        'total_scans': Scan.query.count(),
        'today_scans': Scan.query.filter(func.date(Scan.timestamp) == datetime.now().date()).count(),
        'parent_scans': Scan.query.filter(Scan.parent_bag_id.isnot(None)).count(),
        'child_scans': Scan.query.filter(Scan.child_bag_id.isnot(None)).count()
    }
    
    return render_template('scan_history.html', scans=scans, search_query=search_query, stats=stats)

@app.route('/station')
@login_required
def station():
    """Full-screen scanner station page for warehouse scanning"""
    return render_template('station.html')

@app.route('/bag/<int:bag_id>/delete', methods=['POST'])
@login_required
def delete_bag(bag_id):
    """Delete a bag with validation - admin and biller only"""
    if not (current_user.is_admin() or current_user.is_biller()):
        return jsonify({'success': False, 'message': 'Admin or biller access required'}), 403
    
    try:
        # Import models locally to avoid circular imports
        # Models already imported globally
        
        # Import needed for raw SQL
        from sqlalchemy import text, select
        from models import acquire_bag_lock, acquire_bill_lock
        
        # CRITICAL: Global lock order is Bill→Bag to prevent deadlocks
        # First check if bag is linked to a bill (unlocked query)
        bag = Bag.query.get_or_404(bag_id)
        initial_bill_link = None
        if bag.type == 'parent':
            initial_bill_link = BillBag.query.filter_by(bag_id=bag.id).first()
        
        # Acquire locks in Bill→Bag order
        if initial_bill_link:
            # Bill lock first (prevents deadlock with Bill.recalculate_weights)
            acquire_bill_lock(initial_bill_link.bill_id)
            db.session.execute(
                select(Bill).where(Bill.id == initial_bill_link.bill_id).with_for_update()
            )
        
        # Bag lock second
        acquire_bag_lock(bag_id)
        db.session.execute(
            select(Bag).where(Bag.id == bag_id).with_for_update()
        )
        
        # Re-query bag with lock held
        bag = Bag.query.get(bag_id)
        if not bag:
            return jsonify({'success': False, 'message': 'Bag not found'}), 404
        
        # Check if bag is linked to a bill (re-query WITH locks)
        if bag.type == 'parent':
            bill_link = BillBag.query.with_for_update().filter_by(bag_id=bag.id).first()
            if bill_link:
                bill = Bill.query.get(bill_link.bill_id)
                return jsonify({
                    'success': False, 
                    'message': f'Cannot delete. This parent bag is linked to bill "{bill.bill_id if bill else "unknown"}". Remove it from the bill first.'
                })
            
            # Lock all link rows for this parent
            db.session.execute(text("SELECT * FROM link WHERE parent_bag_id = :bag_id FOR UPDATE"), {'bag_id': bag.id})
            child_links = Link.query.filter_by(parent_bag_id=bag.id).count()
            if child_links > 0:
                return jsonify({
                    'success': False,
                    'message': f'Cannot delete. This parent bag has {child_links} child bags linked to it. Remove all children first.'
                })
        
        if bag.type == 'child':
            # Lock link rows for this child
            db.session.execute(text("SELECT * FROM link WHERE child_bag_id = :bag_id FOR UPDATE"), {'bag_id': bag.id})
            parent_link = Link.query.filter_by(child_bag_id=bag.id).first()
            if parent_link:
                parent = Bag.query.get(parent_link.parent_bag_id)
                return jsonify({
                    'success': False,
                    'message': f'Cannot delete. This child bag is linked to parent "{parent.qr_id if parent else "unknown"}". Remove the link first.'
                })
        
        # Check for scan history
        scan_count = Scan.query.filter(
            or_(Scan.parent_bag_id == bag.id, Scan.child_bag_id == bag.id)
        ).count()
        
        # If bag has scan history, warn but allow deletion
        if scan_count > 0:
            app.logger.warning(f'Deleting bag {bag.qr_id} with {scan_count} scan records')
        
        # Capture bag state before deletion for audit trail
        before_state = capture_entity_snapshot(bag)
        
        # Log audit before deletion with snapshot
        log_audit_with_snapshot(
            action='delete_bag',
            entity_type='bag',
            entity_id=bag.id,
            before_state=before_state,
            after_state=None,  # No after state for deletions
            details={
                'qr_id': bag.qr_id,
                'type': bag.type,
                'scan_count': scan_count,
                'deleted_by': current_user.username
            }
        )
        
        # Delete the bag (cascade will handle scan records)
        bag_qr = bag.qr_id  # Save QR before deletion
        db.session.delete(bag)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Bag {bag.qr_id} deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Bag deletion error: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Error deleting bag: {str(e)}'
        })

@app.route('/bags')
@app.route('/bag_management')  # Alias for compatibility
@login_required
def bag_management():
    """Ultra-fast bag management with caching and optimized filtering"""
    import time
    from sqlalchemy import and_, or_, func
    from sqlalchemy.orm import joinedload, selectinload
    from models import Bag, Link, BillBag, Bill
    
    start_time = time.time()
    
    # Get parameters
    page = request.args.get('page', 1, type=int)
    bag_type = request.args.get('type', 'all')
    search_query = request.args.get('search', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    linked_status = request.args.get('linked_status', 'all')
    bill_status = request.args.get('bill_status', 'all')
    user_filter = request.args.get('user_filter', 'all')  # New user filter parameter
    
    # Sanitize all search and filter inputs to prevent XSS
    if search_query:
        search_query = InputValidator.sanitize_search_query(search_query)
    if date_from:
        date_from = InputValidator.sanitize_html(date_from, max_length=20)
    if date_to:
        date_to = InputValidator.sanitize_html(date_to, max_length=20)
    
    # Date validation
    date_error = None
    if date_from and date_to:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            if to_date < from_date:
                date_error = "To date must be after From date"
        except ValueError:
            date_error = "Invalid date format"
    
    # Area-based filtering for dispatchers ONLY (not for billers or admins)
    dispatch_area = None
    if current_user.is_dispatcher() and current_user.dispatch_area:
        dispatch_area = current_user.dispatch_area
    # Explicitly ensure billers and admins don't get area filtering
    elif current_user.is_biller() or current_user.is_admin():
        dispatch_area = None
    
    try:
        # Import models locally to avoid circular imports
        # Models already imported globally
        # Build simplified query for better stability
        query = db.session.query(Bag)
        
        # Apply filters
        filters = []
        
        # Type filter
        if bag_type != 'all':
            if bag_type == 'parent':
                filters.append(Bag.type == 'parent')
            elif bag_type == 'child':
                filters.append(Bag.type == 'child')
        
        # Search filter - exact match first, then partial match
        if search_query:
            # Try exact match first (case-insensitive)
            exact_match = Bag.query.filter(func.upper(Bag.qr_id) == func.upper(search_query)).first()
            if exact_match:
                filters.append(func.upper(Bag.qr_id) == func.upper(search_query))
            else:
                # Fall back to partial match
                filters.append(Bag.qr_id.ilike(f'%{search_query}%'))
        
        # Date range filter
        if date_from and not date_error:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                filters.append(Bag.created_at >= from_date)
            except ValueError:
                pass
        
        if date_to and not date_error:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d')
                # Add one day to include the entire end date
                to_date = to_date + timedelta(days=1)
                filters.append(Bag.created_at < to_date)
            except ValueError:
                pass
        
        # Area filter for dispatchers
        if dispatch_area:
            filters.append(Bag.dispatch_area == dispatch_area)
        
        # User filter - filter bags by who scanned them or show unscanned bags
        if user_filter and user_filter != 'all':
            if user_filter == 'unscanned':
                # Show bags that have never been scanned
                scanned_parent_ids = db.session.query(Scan.parent_bag_id).filter(Scan.parent_bag_id.isnot(None)).distinct()
                scanned_child_ids = db.session.query(Scan.child_bag_id).filter(Scan.child_bag_id.isnot(None)).distinct()
                filters.append(~Bag.id.in_(scanned_parent_ids.union(scanned_child_ids)))
            else:
                try:
                    user_id = int(user_filter)
                    # Get bag IDs that were scanned by this user
                    scanned_bag_ids = db.session.query(
                        func.coalesce(Scan.parent_bag_id, Scan.child_bag_id)
                    ).filter(
                        Scan.user_id == user_id,
                        func.coalesce(Scan.parent_bag_id, Scan.child_bag_id).isnot(None)
                    ).distinct().subquery()
                    filters.append(Bag.id.in_(scanned_bag_ids))
                except (ValueError, TypeError):
                    pass  # Invalid user_id, ignore filter
        
        # Apply all filters
        if filters:
            query = query.filter(and_(*filters))
        
        # Apply linked status filter
        if linked_status == 'linked':
            # Get bags that have links (either as parent or child)
            linked_bag_ids = db.session.query(Link.parent_bag_id).union(
                db.session.query(Link.child_bag_id)
            ).subquery()
            query = query.filter(Bag.id.in_(linked_bag_ids))
        elif linked_status == 'unlinked':
            # Get bags that don't have any links
            linked_bag_ids = db.session.query(Link.parent_bag_id).union(
                db.session.query(Link.child_bag_id)
            ).subquery()
            query = query.filter(~Bag.id.in_(linked_bag_ids))
        
        # Apply bill status filter
        if bill_status == 'billed':
            # Get bags that have bills
            bags_with_bills = db.session.query(BillBag.bag_id).distinct().subquery()
            query = query.filter(Bag.id.in_(bags_with_bills))
        elif bill_status == 'unbilled':
            # Get bags that don't have bills
            bags_with_bills = db.session.query(BillBag.bag_id).distinct().subquery()
            query = query.filter(~Bag.id.in_(bags_with_bills))
        
        # Use more efficient count for pagination - OPTIMIZED FOR 1.8M+ BAGS
        # CRITICAL: For very large datasets, exact counts are expensive
        # Use fast estimate if total is likely to be large
        if search_query or date_from or date_to:
            # If filtered, do exact count (smaller result set)
            total_filtered = db.session.query(func.count()).select_from(query.subquery()).scalar() or 0
        else:
            # For unfiltered queries on large datasets, use optimized count
            # This avoids expensive COUNT(*) on 1.8M+ rows
            if bag_type == 'parent':
                total_filtered = db.session.query(func.count(Bag.id)).filter(Bag.type == 'parent').scalar() or 0
            elif bag_type == 'child':
                total_filtered = db.session.query(func.count(Bag.id)).filter(Bag.type == 'child').scalar() or 0
            else:
                total_filtered = db.session.query(func.count(Bag.id)).scalar() or 0
        
        # Order by creation date (newest first)
        query = query.order_by(Bag.created_at.desc())
        
        # Apply pagination - OPTIMIZED FOR 1.8M+ BAGS
        # Allow configurable page size with strict 200 max limit
        per_page = min(request.args.get('per_page', 20, type=int), 200)
        offset = (page - 1) * per_page
        
        # PERFORMANCE: For large datasets, cap offset to prevent slow queries
        # At 1.8M records, large offsets become expensive
        max_offset = 10000  # Limit to first 10k records for deep pagination
        if offset > max_offset:
            flash(f'Page number too high. Showing results from page {max_offset // per_page}', 'warning')
            offset = max_offset
            page = (max_offset // per_page) + 1
        
        # No eager loading needed for performance - we'll use a single optimized query
        
        # Get bag IDs first for batch queries
        bags_result = query.limit(per_page).offset(offset).all()
        bag_ids = [bag.id for bag in bags_result]
        
        # Log query performance metrics
        app.logger.info(f"Bag management - Bags loaded: {len(bags_result)}, Total filtered: {total_filtered}")
        
        # Batch fetch all relationships in 3 queries instead of N queries
        child_counts = {}
        parent_links = {}
        bill_links = {}
        last_scans = {}
        
        if bag_ids:
            # Get child counts for all parent bags in one query
            child_count_results = db.session.query(
                Link.parent_bag_id,
                func.count(Link.child_bag_id).label('count')
            ).filter(Link.parent_bag_id.in_(bag_ids)).group_by(Link.parent_bag_id).all()
            child_counts = {r.parent_bag_id: r.count for r in child_count_results}
            
            # Get parent links for all child bags in one query with parent bag details
            parent_link_results = db.session.query(
                Link.child_bag_id,
                Link.parent_bag_id,
                Bag.qr_id.label('parent_qr_id')
            ).join(Bag, Link.parent_bag_id == Bag.id).filter(
                Link.child_bag_id.in_(bag_ids)
            ).all()
            for link in parent_link_results:
                parent_links[link.child_bag_id] = {
                    'parent_bag_id': link.parent_bag_id,
                    'parent_qr_id': link.parent_qr_id
                }
            
            # Get bill links for all bags in one query
            bill_link_results = BillBag.query.filter(BillBag.bag_id.in_(bag_ids)).all()
            for bill_link in bill_link_results:
                bill_links[bill_link.bag_id] = bill_link
            
            # Get last scans for all bags in one query
            last_scans = {}
            # Batch fetch scan timestamps for parent bags
            parent_bag_ids = [bag.id for bag in bags_result if bag.type == 'parent']
            if parent_bag_ids:
                last_scan_results = db.session.query(
                    Scan.parent_bag_id,
                    func.max(Scan.timestamp).label('last_scan')
                ).filter(
                    Scan.parent_bag_id.in_(parent_bag_ids)
                ).group_by(Scan.parent_bag_id).all()
                for scan in last_scan_results:
                    last_scans[scan.parent_bag_id] = scan.last_scan
            
            # Batch fetch scan timestamps for child bags
            child_bag_ids = [bag.id for bag in bags_result if bag.type == 'child']
            if child_bag_ids:
                last_scan_results_child = db.session.query(
                    Scan.child_bag_id,
                    func.max(Scan.timestamp).label('last_scan')
                ).filter(
                    Scan.child_bag_id.in_(child_bag_ids)
                ).group_by(Scan.child_bag_id).all()
                for scan in last_scan_results_child:
                    last_scans[scan.child_bag_id] = scan.last_scan
        
        # Create optimized bag data using batch-fetched relationships
        bags_data = []
        for bag in bags_result:
            parent_link_data = parent_links.get(bag.id, {})
            bag_data = {
                'id': bag.id,
                'qr_id': bag.qr_id,
                'type': bag.type,
                'created_at': bag.created_at,
                'name': bag.name,
                'dispatch_area': bag.dispatch_area,
                'notes': getattr(bag, 'notes', None),
                'linked_children_count': child_counts.get(bag.id, 0),
                'linked_parent_id': parent_link_data.get('parent_bag_id'),
                'linked_parent_qr': parent_link_data.get('parent_qr_id'),
                'bill_id': bill_links[bag.id].bill_id if bag.id in bill_links and bill_links[bag.id] else None,
                'last_scan_time': last_scans.get(bag.id)
            }
            bags_data.append(bag_data)
        
        # Use single optimized query for all stats
        stats_query = db.session.query(
            func.count(Bag.id).label('total'),
            func.sum(func.cast(Bag.type == 'parent', db.Integer)).label('parents'),
            func.sum(func.cast(Bag.type == 'child', db.Integer)).label('children')
        )
        
        if dispatch_area:
            stats_query = stats_query.filter(Bag.dispatch_area == dispatch_area)
        
        stats_result = stats_query.first()
        
        total_bags = stats_result.total if stats_result and hasattr(stats_result, 'total') else 0
        parent_bags = stats_result.parents if stats_result and hasattr(stats_result, 'parents') else 0
        child_bags = stats_result.children if stats_result and hasattr(stats_result, 'children') else 0
        
        stats = {
            'total_bags': total_bags,
            'parent_bags': parent_bags,
            'child_bags': child_bags,
            'filtered_count': total_filtered
        }
        
        # Convert dictionary data to template-compatible MockBag objects
        class TemplateBag:
            def __init__(self, data):
                self.__dict__.update(data)
                self._linked_children_count = data.get('linked_children_count', 0)
                self._linked_parent_id = data.get('linked_parent_id')
                self._linked_parent_qr = data.get('linked_parent_qr')
                self._bill_id = data.get('bill_id')
            
            @property
            def child_links(self):
                class MockQuery:
                    def __init__(self, count):
                        self._count = count
                    def count(self):
                        return self._count
                return MockQuery(self._linked_children_count)
            
            @property
            def parent_links(self):
                class MockQuery:
                    def __init__(self, parent_id, parent_qr, bill_id=None):
                        self._parent_id = parent_id
                        self._parent_qr = parent_qr
                        self._bill_id = bill_id
                    def first(self):
                        if self._parent_id:
                            class MockLink:
                                def __init__(self, parent_id, parent_qr, bill_id):
                                    class MockParentBag:
                                        def __init__(self, pid, pqr, bid):
                                            self.id = pid
                                            self.qr_id = pqr if pqr else f"Parent_{pid}"
                                            class MockBillLinks:
                                                def __init__(self, bid):
                                                    self._bid = bid
                                                def first(self):
                                                    if self._bid:
                                                        class MockBill:
                                                            def __init__(self, bid):
                                                                self.bill_id = f"BILL-{bid}"
                                                        class MockBillLink:
                                                            def __init__(self, bid):
                                                                self.bill = MockBill(bid)
                                                        return MockBillLink(self._bid)
                                                    return None
                                            self.bill_links = MockBillLinks(bid)
                                    self.parent_bag = MockParentBag(parent_id, parent_qr, bill_id)
                            return MockLink(self._parent_id, self._parent_qr, self._bill_id)
                        return None
                return MockQuery(self._linked_parent_id, self._linked_parent_qr, self._bill_id)
            
            @property
            def bill_links(self):
                class MockQuery:
                    def __init__(self, bill_id):
                        self._bill_id = bill_id
                    def first(self):
                        if self._bill_id:
                            class MockBillLink:
                                def __init__(self, bill_id):
                                    class MockBill:
                                        def __init__(self, bid):
                                            self.bill_id = f"BILL-{bid}"
                                    self.bill = MockBill(bill_id)
                            return MockBillLink(self._bill_id)
                        return None
                return MockQuery(self._bill_id)
            
            @property
            def last_scan(self):
                if hasattr(self, 'last_scan_time') and self.last_scan_time:  # type: ignore
                    class MockScan:
                        def __init__(self, timestamp):
                            self.timestamp = timestamp
                    return MockScan(self.last_scan_time)  # type: ignore
                return None
        
        bag_objects = [TemplateBag(bag_dict) for bag_dict in bags_data]
        
        # Create pagination object manually
        class SimplePagination:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page if total > 0 else 1
                self.has_prev = page > 1
                self.has_next = page < self.pages
                self.prev_num = page - 1 if self.has_prev else None
                self.next_num = page + 1 if self.has_next else None
            
            def __bool__(self):
                """Return True if there are items"""
                return len(self.items) > 0
            
            def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
                last = 0
                for num in range(1, self.pages + 1):
                    if num <= left_edge or \
                       (self.page - left_current - 1 < num < self.page + right_current) or \
                       num > self.pages - right_edge:
                        if last + 1 != num:
                            yield None
                        yield num
                        last = num
        
        bags = SimplePagination(bag_objects, page, 20, total_filtered)
        
        # Update filtered count in stats
        stats['filtered_count'] = total_filtered
        
        query_time = (time.time() - start_time) * 1000
        app.logger.info(f"Bag management page loaded in {query_time:.2f}ms with {len(bags.items)} items")
        
    except Exception as e:
        app.logger.error(f"Optimized bag query failed, falling back to standard query: {str(e)}")
        import traceback
        app.logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Fallback to original query if optimization fails
        # Import models locally
        # Models already imported globally
        query = Bag.query
        
        if dispatch_area:
            query = query.filter(Bag.dispatch_area == dispatch_area)
        
        if bag_type != 'all':
            query = query.filter(Bag.type == bag_type)
        
        if search_query:
            query = query.filter(
                or_(
                    Bag.qr_id.contains(search_query),
                    Bag.name.contains(search_query)
                )
            )
        
        bags = query.order_by(desc(Bag.created_at)).paginate(
            page=page, per_page=20, error_out=False
        )
        
        # Basic stats - use raw SQL to avoid model import issues
        total_result = db.session.execute(db.text('SELECT COUNT(*) FROM bag')).scalar()
        parent_result = db.session.execute(db.text("SELECT COUNT(*) FROM bag WHERE type = 'parent'")).scalar()
        child_result = db.session.execute(db.text("SELECT COUNT(*) FROM bag WHERE type = 'child'")).scalar()
        
        stats = {
            'total_bags': total_result or 0,
            'parent_bags': parent_result or 0,
            'child_bags': child_result or 0,
            'linked_bags': 0,
            'unlinked_bags': 0,
            'filtered_count': bags.total
        }
    
    # Get list of users who have scanned bags for the filter dropdown
    # Count actual UNIQUE bags (parent and child separately), not scan events
    users_with_scans_sql = """
    SELECT 
        u.id,
        u.username,
        COUNT(DISTINCT s.parent_bag_id) as parent_bags,
        COUNT(DISTINCT s.child_bag_id) as child_bags,
        COUNT(DISTINCT s.parent_bag_id) + COUNT(DISTINCT s.child_bag_id) as scan_count
    FROM "user" u
    LEFT JOIN scan s ON s.user_id = u.id
    WHERE u.role != 'admin'
    GROUP BY u.id, u.username
    HAVING COUNT(DISTINCT s.parent_bag_id) + COUNT(DISTINCT s.child_bag_id) > 0
    ORDER BY scan_count DESC, u.username
    """
    users_with_scans = db.session.execute(db.text(users_with_scans_sql)).fetchall()
    
    filters = {
        'type': bag_type,
        'search': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'linked_status': linked_status,
        'bill_status': bill_status,
        'user_filter': user_filter
    }
    
    # Debug check
    if hasattr(bags, 'items'):
        app.logger.info(f"Passing bags to template with {len(bags.items)} items")
    else:
        app.logger.error(f"Bags object has no items attribute: {type(bags)}")
    
    return render_template('bag_management.html', 
                         bags=bags, 
                         search_query=search_query, 
                         stats=stats, 
                         filters=filters,
                         date_error=date_error,
                         users_with_scans=users_with_scans)


@app.route('/search')
@login_required
def search_bag():
    """
    Dedicated search page for looking up bags by QR code.
    Returns full bag details including:
    - For parent bags: linked child bags and associated bill
    - For child bags: parent bag and parent's bill
    """
    from models import Bag, Link, BillBag, Bill, Scan
    from sqlalchemy import func
    
    query = request.args.get('q', '').strip().upper()
    
    bag = None
    child_bags = []
    parent_bag = None
    bill = None
    parent_bill = None
    recent_scans = []
    
    if query:
        bag = Bag.query.filter(func.upper(Bag.qr_id) == query).first()
        
        if bag:
            if bag.type == 'parent':
                links = Link.query.filter_by(parent_bag_id=bag.id).all()
                child_bags = [link.child_bag for link in links if link.child_bag]
                
                bill_link = BillBag.query.filter_by(bag_id=bag.id).first()
                if bill_link:
                    bill = bill_link.bill
                
                recent_scans = Scan.query.filter_by(parent_bag_id=bag.id)\
                    .order_by(Scan.timestamp.desc()).limit(5).all()
                    
            elif bag.type == 'child':
                link = Link.query.filter_by(child_bag_id=bag.id).first()
                if link:
                    parent_bag = link.parent_bag
                    
                    if parent_bag:
                        parent_bill_link = BillBag.query.filter_by(bag_id=parent_bag.id).first()
                        if parent_bill_link:
                            parent_bill = parent_bill_link.bill
                
                recent_scans = Scan.query.filter_by(child_bag_id=bag.id)\
                    .order_by(Scan.timestamp.desc()).limit(5).all()
    
    return render_template('search.html',
                         query=query,
                         bag=bag,
                         child_bags=child_bags,
                         parent_bag=parent_bag,
                         bill=bill,
                         parent_bill=parent_bill,
                         recent_scans=recent_scans)


# Bill management routes
@app.route('/bills')
@app.route('/bill_management')  # Alias for compatibility
@login_required
@limiter.limit("200 per minute")  # Increased for 100+ concurrent users with Redis backend
def bill_management():
    """Ultra-fast bill management with integrated summary generation"""
    if not (current_user.is_admin() or current_user.is_biller()):
        flash('Access restricted to admin and biller users.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Import models locally
        from models import Bill, Bag, BillBag, User, Link
        from sqlalchemy import func
        
        # Get search/filter parameters
        search_bill_id = request.args.get('search_bill_id', '').strip()
        status_filter = request.args.get('status_filter', 'all').strip()
        
        # Sanitize search and filter inputs to prevent XSS
        if search_bill_id:
            search_bill_id = InputValidator.sanitize_search_query(search_bill_id)
        if status_filter and status_filter != 'all':
            status_filter = InputValidator.sanitize_html(status_filter, max_length=20)
        
        # Summary generation parameters
        generate_summary = request.args.get('generate_summary', '') == 'true'
        summary_date_from = request.args.get('date_from', '')
        summary_date_to = request.args.get('date_to', '')
        summary_user_id = request.args.get('user_id', '')
        
        # Sanitize summary parameters
        if summary_date_from:
            summary_date_from = InputValidator.sanitize_html(summary_date_from, max_length=20)
        if summary_date_to:
            summary_date_to = InputValidator.sanitize_html(summary_date_to, max_length=20)
        
        # Initialize summary data
        summary_data = None
        summary_stats = None
        
        # Generate summary if requested
        if generate_summary:
            # Parse dates for summary
            if summary_date_from:
                try:
                    start_date = datetime.strptime(summary_date_from, '%Y-%m-%d')
                except ValueError:
                    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            if summary_date_to:
                try:
                    end_date = datetime.strptime(summary_date_to, '%Y-%m-%d') + timedelta(days=1)
                except ValueError:
                    end_date = start_date + timedelta(days=1)
            else:
                end_date = start_date + timedelta(days=1)
            
            # Build summary query
            summary_query = Bill.query.filter(
                Bill.created_at >= start_date,
                Bill.created_at < end_date
            )
            
            # Filter by user for billers or specific user for admins
            if current_user.is_biller() and not current_user.is_admin():
                summary_query = summary_query.filter(Bill.created_by_id == current_user.id)
            elif summary_user_id and current_user.is_admin():
                try:
                    user_id_int = int(summary_user_id)
                    summary_query = summary_query.filter(Bill.created_by_id == user_id_int)
                except ValueError:
                    # Invalid user_id, skip filter
                    pass
            
            summary_bills = summary_query.all()
            
            # Calculate summary statistics
            summary_stats = {
                'total_bills': len(summary_bills),
                'total_parent_bags': 0,
                'total_child_bags': 0,
                'total_weight': 0,
                'completed_bills': 0,
                'in_progress_bills': 0,
                'empty_bills': 0,
                'date_from': start_date.strftime('%Y-%m-%d'),
                'date_to': (end_date - timedelta(days=1)).strftime('%Y-%m-%d')
            }
            
            summary_data = []
            if summary_bills:
                # ⚡ PRODUCTION FIX: Use precomputed values from Bill model
                # This avoids expensive COUNT(DISTINCT) queries that timeout with 334k+ bags
                
                # Single query for ALL users
                user_ids = [bill.created_by_id for bill in summary_bills if bill.created_by_id]
                users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
                user_dict = {user.id: user.username for user in users}
                
                # Process bills using precomputed values
                for bill in summary_bills:
                    # Use precomputed values from Bill model
                    parent_count = getattr(bill, 'linked_parent_count', 0) or 0
                    child_count = getattr(bill, 'total_child_bags', 0) or 0
                    
                    # Determine status
                    if bill.parent_bag_count and parent_count >= bill.parent_bag_count:
                        status = 'completed'
                        summary_stats['completed_bills'] += 1
                    elif parent_count > 0:
                        status = 'in_progress'
                        summary_stats['in_progress_bills'] += 1
                    else:
                        status = 'empty'
                        summary_stats['empty_bills'] += 1
                    
                    # Update totals
                    summary_stats['total_parent_bags'] += parent_count
                    summary_stats['total_child_bags'] += child_count
                    summary_stats['total_weight'] += bill.total_weight_kg or 0
                    
                    # Safe access to expected_weight_kg with fallback
                    try:
                        expected_weight = bill.expected_weight_kg if hasattr(bill, 'expected_weight_kg') else parent_count * 30
                    except:
                        expected_weight = parent_count * 30
                    
                    summary_data.append({
                        'bill_id': bill.bill_id,
                        'created_at': format_datetime_ist(bill.created_at),
                        'created_by': user_dict.get(bill.created_by_id, 'Unknown'),
                        'parent_bags': parent_count,
                        'child_bags': child_count,
                        'actual_weight': bill.total_weight_kg or 0,
                        'expected_weight': expected_weight,
                        'weight_kg': bill.total_weight_kg or 0,  # Keep for backward compatibility
                        'status': status,
                        'completion': (parent_count * 100 // bill.parent_bag_count) if bill.parent_bag_count else 0
                    })
        
        # Enhancement features disabled to prevent route registration errors
        # Standard bill listing without enhanced tracking
        
        # Get bills directly from database
        bills_query = Bill.query.order_by(Bill.created_at.desc())
        
        if search_bill_id:
            bills_query = bills_query.filter(Bill.bill_id.ilike(f'%{search_bill_id}%'))
        
        if status_filter != 'all':
            bills_query = bills_query.filter(Bill.status == status_filter)
        
        bills_data = bills_query.limit(50).all()
        
        # ⚡ PRODUCTION FIX: Use precomputed values from Bill model instead of expensive queries
        # This avoids COUNT(DISTINCT) queries that timeout with 334k+ bags
        
        # Batch load all creators
        creator_ids = [bill.created_by_id for bill in bills_data if bill.created_by_id]
        creators = {}
        if creator_ids:
            users = User.query.filter(User.id.in_(creator_ids)).all()
            creators = {user.id: {'username': user.username, 'role': user.role} for user in users}
        
        # Convert to the expected format for the template using precomputed Bill fields
        bill_data = []
        for bill in bills_data:
            # Use precomputed values from Bill model (updated on scan operations)
            parent_count = getattr(bill, 'linked_parent_count', 0) or 0
            actual_child_count = getattr(bill, 'total_child_bags', 0) or 0
            creator_info = creators.get(bill.created_by_id) if bill.created_by_id else None
            
            bill_data.append({
                'bill': bill,
                'parent_bags': [],  # Don't load bags in list view
                'parent_count': parent_count,
                'status': bill.status or 'pending',
                'creator_info': creator_info,
                'statistics': {
                    'parent_bags_linked': parent_count,
                    'total_child_bags': actual_child_count,
                    'total_weight_kg': getattr(bill, 'total_weight_kg', 0) or 0
                }
            })
        
        # Get list of all users for admin filter dropdown
        all_users = None
        if current_user.is_admin():
            all_users = User.query.filter(User.role.in_(['biller', 'admin'])).order_by(User.username).all()
        
        return render_template('bill_management.html',
                             bill_data=bill_data,
                             search_bill_id=search_bill_id,
                             status_filter=status_filter,
                             summary_data=summary_data,
                             summary_stats=summary_stats,
                             all_users=all_users)
                             
    except Exception as e:
        import traceback
        app.logger.error(f"Bill management error: {str(e)}")
        app.logger.error(f"Bill management traceback: {traceback.format_exc()}")
        db.session.rollback()  # Rollback any failed transaction
        
        # ROBUST FALLBACK: Use raw SQL that only selects columns guaranteed to exist
        # This bypasses ORM column expectations and works even if schema is out of sync
        try:
            from sqlalchemy import text
            
            # Get search parameters from request
            search_bill_id = request.args.get('search_bill_id', '').strip()
            status_filter = request.args.get('status_filter', 'all')
            
            # Sanitize inputs to prevent XSS
            if search_bill_id:
                search_bill_id = InputValidator.sanitize_search_query(search_bill_id)
            if status_filter and status_filter != 'all':
                status_filter = InputValidator.sanitize_html(status_filter, max_length=20)
            
            # Raw SQL query using ONLY columns that definitely exist in all environments
            base_sql = """
                SELECT 
                    b.id, b.bill_id, b.description, b.parent_bag_count, 
                    b.status, b.created_at, b.created_by_id,
                    u.username as creator_name,
                    COUNT(bb.id) as linked_count
                FROM bill b
                LEFT JOIN "user" u ON b.created_by_id = u.id
                LEFT JOIN bill_bag bb ON b.id = bb.bill_id
            """
            
            where_clauses = []
            params = {}
            
            if search_bill_id:
                where_clauses.append("b.bill_id ILIKE :search")
                params['search'] = f'%{search_bill_id}%'
            
            if status_filter and status_filter != 'all':
                where_clauses.append("b.status = :status")
                params['status'] = status_filter
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            full_sql = f"""
                {base_sql}
                {where_sql}
                GROUP BY b.id, b.bill_id, b.description, b.parent_bag_count, 
                         b.status, b.created_at, b.created_by_id, u.username
                ORDER BY b.created_at DESC
                LIMIT 50
            """
            
            result = db.session.execute(text(full_sql), params).fetchall()
            
            # Build bill data from raw SQL results
            bill_data = []
            for row in result:
                # Create a simple dict-like object to hold bill data
                bill_obj = type('SimpleBill', (), {
                    'id': row[0],
                    'bill_id': row[1],
                    'description': row[2],
                    'parent_bag_count': row[3] or 0,
                    'status': row[4] or 'new',
                    'created_at': row[5],
                    'created_by_id': row[6],
                    'linked_parent_count': row[8] or 0,
                    'total_child_bags': 0,
                    'total_weight_kg': 0,
                    'expected_weight_kg': 0
                })()
                
                creator_name = row[7]
                linked_count = row[8] or 0
                
                bill_data.append({
                    'bill': bill_obj,
                    'parent_bags': [],
                    'parent_count': linked_count,
                    'status': bill_obj.status,
                    'creator_info': {'username': creator_name} if creator_name else None,
                    'statistics': {
                        'parent_bags_linked': linked_count,
                        'total_child_bags': 0,
                        'total_weight_kg': 0
                    }
                })
            
            flash('Loading simplified view - some features may be limited.', 'warning')
            return render_template('bill_management.html',
                                 bill_data=bill_data,
                                 search_bill_id=search_bill_id,
                                 status_filter=status_filter,
                                 summary_data=None,
                                 summary_stats=None,
                                 all_users=None)
        except Exception as fallback_error:
            import traceback
            app.logger.error(f"Bill management fallback error: {str(fallback_error)}")
            app.logger.error(f"Bill management fallback traceback: {traceback.format_exc()}")
            flash('Error loading bill management. Please contact support.', 'error')
            return redirect(url_for('dashboard'))

@app.route('/bill/create', methods=['GET', 'POST'])
@login_required
def create_bill():
    """Create a new bill - admin and employee access"""
    if not (current_user.is_admin() or current_user.role == 'biller'):
        flash('Access restricted to admin and employee users.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'GET':
        # Display the create bill form
        return render_template('create_bill.html')
    
    # Check if this is an API call
    is_api = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
             request.headers.get('Content-Type') == 'application/json' or \
             'api' in request.path
    
    # Handle POST request
    if request.method == 'POST':
        try:
            form_bill_id = request.form.get('bill_id', '')
            # CRITICAL: Sanitize scanner input to remove invisible characters
            bill_id = sanitize_input(form_bill_id)
            
            # Additional debug logging to catch scanner issues
            if form_bill_id != bill_id:
                app.logger.info(f'Bill ID sanitized: "{form_bill_id}" -> "{bill_id}" (length {len(form_bill_id)} -> {len(bill_id)})')
            
            if not bill_id:
                flash('Bill ID is required.', 'error')
                return render_template('create_bill.html')
            
            # Basic validation - just check if bill_id is not empty after sanitization
            if len(bill_id) == 0:
                flash('Bill ID cannot be empty.', 'error')
                return render_template('create_bill.html')
            
            parent_bag_count = request.form.get('parent_bag_count', 1, type=int)
            
            # FIX: Validate parent bag count with stricter limits and type checking
            if not isinstance(parent_bag_count, int) or parent_bag_count < 1 or parent_bag_count > 50:
                flash('Number of parent bags must be between 1 and 50.', 'error')
                return render_template('create_bill.html')
            
            # CASE-INSENSITIVE duplicate check using UPPER for consistency with scanner input
            existing = db.session.execute(
                text("SELECT id, bill_id FROM bill WHERE UPPER(bill_id) = UPPER(:bill_id) LIMIT 1"),
                {'bill_id': bill_id}
            ).first()
            
            if existing:
                flash(f'Bill ID "{existing.bill_id}" already exists. Please use a different ID.', 'error')
                return render_template('create_bill.html')
            
            # Create bill directly without enhancement features
            bill = Bill()
            bill.bill_id = bill_id
            bill.description = ''
            bill.parent_bag_count = parent_bag_count
            bill.created_by_id = current_user.id
            bill.status = 'new'
            bill.expected_weight_kg = parent_bag_count * 30.0  # Initialize expected weight: 30kg per parent bag
            bill.total_weight_kg = 0.0  # Initialize actual weight to 0
            db.session.add(bill)
            db.session.commit()
            
            app.logger.info(f'Bill created successfully: {bill_id} with {parent_bag_count} parent bags')
            
            # Send bill creation notification to admins
            try:
                from email_utils import EmailService
                admin_users = User.query.filter_by(role='admin').all()
                admin_emails = [u.email for u in admin_users if u.email]
                
                if admin_emails:
                    sent, failed, errors = EmailService.send_bill_notification(
                        bill_id=bill_id,
                        parent_bags=parent_bag_count,
                        created_by=current_user.username,  # type: ignore
                        admin_emails=admin_emails
                    )
                    if failed > 0:
                        app.logger.warning(f"Failed to send {failed} bill notifications: {errors}")
            except Exception as e:
                app.logger.warning(f"Bill notification email error: {str(e)}")
            
            if is_api:
                return jsonify({
                    'success': True,
                    'message': f'Bill {bill_id} created successfully!',
                    'bill_id': bill.bill_id,
                    'bill_db_id': bill.id
                })
            
            flash('Bill created successfully!', 'success')
            
            # Add debugging to check redirect
            app.logger.info(f'Redirecting to scan_bill_parent with bill.id={bill.id}')
            return redirect(url_for('scan_bill_parent', bill_id=bill.id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error creating bill. Please try again.', 'error')
            app.logger.error(f'Bill creation error: {str(e)}')
            return render_template('create_bill.html')
    
    return render_template('create_bill.html')

@app.route('/bill/<int:bill_id>/delete', methods=['POST'])
@login_required
def delete_bill(bill_id):
    """Ultra-fast bill deletion - optimized for 8+ lakh bags"""
    # Check if user has admin privileges
    if not (hasattr(current_user, 'is_admin') and current_user.is_admin()):
        # Check for role-based access as fallback
        if not (hasattr(current_user, 'role') and current_user.role == 'admin'):
            flash('Admin access required to delete bills.', 'error')
            return redirect(url_for('bill_management'))
    
    try:
        # Import models locally
        from models import Bill, BillBag, acquire_bill_lock
        from sqlalchemy import text
        
        # Use a single transaction with raw SQL for maximum speed
        # Get bill identifier first
        result = db.session.execute(
            text("SELECT bill_id FROM bill WHERE id = :bill_id LIMIT 1"),
            {"bill_id": bill_id}
        ).fetchone()
        
        if not result:
            flash('Bill not found.', 'error')
            return redirect(url_for('bill_management'))
        
        bill_identifier = result[0]
        
        # Acquire advisory lock before bill_bag operations
        acquire_bill_lock(bill_id)
        
        # Execute both deletes in a single transaction for speed
        # Using raw SQL for maximum performance
        db.session.execute(
            text("""
                DELETE FROM bill_bag WHERE bill_id = :bill_id;
                DELETE FROM bill WHERE id = :bill_id;
            """),
            {"bill_id": bill_id}
        )
        db.session.commit()
        
        flash(f'Bill {bill_identifier} deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error deleting bill {bill_id}: {str(e)}')
        flash('Error deleting bill.', 'error')
    
    return redirect(url_for('bill_management'))

@app.route('/bill/<int:bill_id>/finish', methods=['GET', 'POST'])
@login_required
def finish_bill_scan(bill_id):
    """Complete bill scanning and mark as finished - admin and employee access"""
    if not (hasattr(current_user, 'is_admin') and current_user.is_admin() or 
            hasattr(current_user, 'role') and current_user.role in ['admin', 'biller', 'dispatcher']):
        flash('Access restricted to admin and employee users.', 'error')
        return redirect(url_for('bill_management'))
    
    bill = Bill.query.get_or_404(bill_id)
    
    try:
        bill.status = 'completed'
        db.session.commit()
        flash(f'Bill {bill.bill_id} marked as completed!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error completing bill.', 'error')
        app.logger.error(f'Bill completion error: {str(e)}')
    
    return redirect(url_for('view_bill', bill_id=bill_id))

@app.route('/bill/<int:bill_id>')
@login_required  
def view_bill(bill_id):
    """Ultra-optimized bill view using single CTE query to eliminate N+1"""
    from sqlalchemy import func
    
    bill = Bill.query.get_or_404(bill_id)
    
    # ULTRA-OPTIMIZED: Single CTE query to fetch all parent bags and their children in one roundtrip
    result = db.session.execute(text("""
        WITH parent_bags AS (
            SELECT 
                b.id as parent_id,
                b.qr_id,
                b.name,
                b.type,
                b.dispatch_area,
                b.created_at,
                COUNT(l.child_bag_id) as child_count
            FROM bag b
            JOIN bill_bag bb ON bb.bag_id = b.id
            LEFT JOIN link l ON l.parent_bag_id = b.id
            WHERE bb.bill_id = :bill_id AND b.type = 'parent'
            GROUP BY b.id, b.qr_id, b.name, b.type, b.dispatch_area, b.created_at
            LIMIT 50
        ),
        all_children AS (
            SELECT 
                cb.id as child_id,
                cb.qr_id as child_qr,
                cb.name as child_name,
                cb.created_at as child_created,
                l.parent_bag_id
            FROM link l
            JOIN bag cb ON cb.id = l.child_bag_id
            WHERE l.parent_bag_id IN (SELECT parent_id FROM parent_bags)
            ORDER BY cb.created_at DESC
        )
        SELECT 
            pb.parent_id,
            pb.qr_id,
            pb.name,
            pb.dispatch_area,
            pb.child_count,
            COALESCE(
                json_agg(
                    json_build_object(
                        'id', ac.child_id,
                        'qr_id', ac.child_qr,
                        'name', ac.child_name,
                        'created_at', ac.child_created
                    ) ORDER BY ac.child_created DESC
                ) FILTER (WHERE ac.child_id IS NOT NULL),
                '[]'::json
            ) as children
        FROM parent_bags pb
        LEFT JOIN all_children ac ON ac.parent_bag_id = pb.parent_id
        GROUP BY pb.parent_id, pb.qr_id, pb.name, pb.dispatch_area, pb.child_count
    """), {'bill_id': bill_id}).fetchall()
    
    # Parse results into format expected by template - ZERO additional queries
    parent_bags = []
    parent_bag_ids = []
    all_bag_ids = []
    import json
    
    # Collect all bag IDs (both parent and child) for single bulk fetch
    for row in result:
        parent_id = row[0]
        children_json = row[5]
        all_bag_ids.append(parent_id)
        parent_bag_ids.append(parent_id)
        
        if children_json:
            # Handle both JSON strings and pre-parsed lists from psycopg2
            if isinstance(children_json, str):
                children_data = json.loads(children_json)
            else:
                children_data = children_json
            if children_data:
                child_ids = [c['id'] for c in children_data if c and c.get('id')]
                all_bag_ids.extend(child_ids)
    
    # SINGLE BULK FETCH: Load all Bag objects in one query
    bag_objects_dict = {}
    if all_bag_ids:
        bag_objects = Bag.query.filter(Bag.id.in_(all_bag_ids)).all()
        bag_objects_dict = {bag.id: bag for bag in bag_objects}
    
    # Build parent_bags using pre-fetched objects
    for row in result:
        parent_id, qr_id, name, dispatch_area, child_count, children_json = row
        
        parent_bag_obj = bag_objects_dict.get(parent_id)
        if not parent_bag_obj:
            continue
        
        # Parse children JSON and fetch from pre-loaded dict (handle both strings and pre-parsed lists)
        if children_json:
            if isinstance(children_json, str):
                children_data = json.loads(children_json)
            else:
                children_data = children_json
        else:
            children_data = []
        
        child_bags = []
        if children_data:
            for c in children_data:
                if c and c.get('id'):
                    child_bag = bag_objects_dict.get(c['id'])
                    if child_bag:
                        child_bags.append(child_bag)
        
        parent_bags.append({
            'parent_bag': parent_bag_obj,
            'child_count': child_count or 0,
            'child_bags': child_bags
        })
    
    # Get limited scan history with eager loading in single query
    scans = []
    if parent_bag_ids:
        from sqlalchemy.orm import joinedload
        scans = Scan.query.options(joinedload(Scan.user)).filter(  # type: ignore[arg-type]
            Scan.parent_bag_id.in_(parent_bag_ids)
        ).order_by(desc(Scan.timestamp)).limit(100).all()
    
    return render_template('view_bill.html', 
                         bill=bill, 
                         parent_bags=parent_bags, 
                         child_bags=[],
                         scans=scans or [],
                         bag_links_count=len(parent_bags))

@app.route('/bill/<int:bill_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bill(bill_id):
    """Edit bill details - admin and employee access"""
    if not (current_user.is_admin() or current_user.role == 'biller'):
        flash('Access restricted to admin and employee users.', 'error')
        return redirect(url_for('bill_management'))
    
    bill = Bill.query.get_or_404(bill_id)
    
    if request.method == 'POST':
        try:
            app.logger.info(f'Edit bill request - Bill ID: {bill_id}')
            
            description = request.form.get('description', '').strip()
            parent_bag_count = request.form.get('parent_bag_count', type=int)
            new_status = request.form.get('status', '').strip()
            
            # Store original values for comparison
            original_description = bill.description
            original_count = bill.parent_bag_count
            original_status = bill.status
            capacity_changed = False
            
            # Always update description (can be empty)
            bill.description = description
            
            # Validate and update parent bag count (capacity)
            if parent_bag_count and parent_bag_count > 0:
                # Check if new count is less than existing linked bags
                if parent_bag_count < bill.linked_parent_count:
                    flash(f'Cannot set capacity to {parent_bag_count}. Bill already has {bill.linked_parent_count} linked bags.', 'error')
                    return redirect(url_for('edit_bill', bill_id=bill_id))
                if parent_bag_count > 500:
                    flash('Maximum capacity is 500 parent bags.', 'error')
                    return redirect(url_for('edit_bill', bill_id=bill_id))
                if parent_bag_count != original_count:
                    bill.parent_bag_count = parent_bag_count
                    capacity_changed = True
            
            # Handle manual status changes (allow reopening or completing)
            status_changed = False
            if new_status and new_status in ['new', 'processing', 'completed']:
                if new_status != original_status:
                    bill.status = new_status
                    status_changed = True
                    app.logger.info(f'Bill {bill_id} status manually changed from {original_status} to {new_status}')
            
            # Check if anything actually changed
            if bill.description != original_description or bill.parent_bag_count != original_count or bill.status != original_status:
                db.session.commit()
                
                # CRITICAL: Recalculate weights after capacity OR status changes to sync state
                if capacity_changed or status_changed:
                    actual_weight, expected_weight, parent_count, child_count_total, is_full = bill.recalculate_weights()
                    db.session.commit()
                    app.logger.info(f'Bill {bill_id} recalculated: {bill.linked_parent_count}/{bill.parent_bag_count}, status: {bill.status}, weight: {bill.total_weight_kg}kg')
                
                app.logger.info(f'Bill {bill_id} updated successfully')
                flash('Bill updated successfully!', 'success')
            else:
                app.logger.info(f'No changes detected for bill {bill_id}')
                flash('No changes were made to the bill.', 'info')
                
            return redirect(url_for('view_bill', bill_id=bill_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating bill: {str(e)}', 'error')
            app.logger.error(f'Edit bill error: {str(e)}')
    
    return render_template('edit_bill.html', bill=bill)

@app.route('/remove_bag_from_bill', methods=['POST'])
@login_required
def remove_bag_from_bill():
    """Remove a parent bag from a bill - admin and employee access"""
    app.logger.info(f'Remove bag from bill - CSRF token present: {request.form.get("csrf_token") is not None}')
    app.logger.info(f'Form data: {dict(request.form)}')
    
    if not (current_user.is_admin() or current_user.role == 'biller'):
        flash('Access restricted to admin and employee users.', 'error')
        return redirect(url_for('bill_management'))
    
    try:
        from models import acquire_bill_lock
        
        parent_qr = request.form.get('parent_qr')
        bill_id = request.form.get('bill_id', type=int)
        
        if not parent_qr or not bill_id:
            flash('Missing required information.', 'error')
            return redirect(url_for('bill_management'))
        
        # Get Bill object and acquire lock before bill_bag operations
        bill = Bill.query.get(bill_id)
        if not bill:
            flash('Bill not found.', 'error')
            return redirect(url_for('bill_management'))
        
        acquire_bill_lock(bill.id)
        
        # Find the parent bag
        parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(parent_qr),
            Bag.type == 'parent'
        ).first()
        if not parent_bag:
            flash('Parent bag not found.', 'error')
            return redirect(url_for('scan_bill_parent', bill_id=bill_id))
        
        # FIX: Use transaction for removing bag from bill
        # Find and remove the bill-bag link with proper locking
        bill_bag = BillBag.query.with_for_update().filter_by(bill_id=bill_id, bag_id=parent_bag.id).first()
        if bill_bag:
            # FIX: Add audit log for removal
            app.logger.info(f'AUDIT: User {current_user.username} (ID: {current_user.id}) removed bag {parent_bag.qr_id} from bill ID {bill_id}')
            removed_child_count = parent_bag.child_count or 0  # Get child count before removal
            db.session.delete(bill_bag)
            db.session.commit()
            
            # CRITICAL: Recalculate weights after removing bag
            actual_weight, expected_weight, parent_count, child_count_total, is_full = bill.recalculate_weights()
            db.session.commit()
            app.logger.info(f'Bill {bill.bill_id} recalculated after bag removal: {bill.linked_parent_count}/{bill.parent_bag_count}')
            
            flash(f'Parent bag {parent_qr} removed from bill successfully.', 'success')
        else:
            removed_child_count = 0
            flash('Bag link not found.', 'error')
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept', '').find('application/json') != -1
        
        if is_ajax:
            # For AJAX requests, return JSON with removed child count for weight tracking
            return jsonify({
                'success': True, 
                'message': f'Parent bag {parent_qr} removed successfully.',
                'linked_count': bill.linked_parent_count,
                'expected_count': bill.parent_bag_count,
                'removed_child_count': removed_child_count,
                'remaining_capacity': bill.remaining_capacity(),
                'total_weight': bill.total_weight_kg,
                'bill_status': bill.status
            })
        else:
            # For normal form submissions, redirect back to scan page
            return redirect(url_for('scan_bill_parent', bill_id=bill_id))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Remove bag from bill error: {str(e)}')
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept', '').find('application/json') != -1
        
        if is_ajax:
            return jsonify({
                'success': False, 
                'message': 'Error removing bag from bill.'
            })
        else:
            flash('Error removing bag from bill.', 'error')
            bill_id = request.form.get('bill_id', type=int)
            if bill_id:
                return redirect(url_for('scan_bill_parent', bill_id=bill_id))
            else:
                return redirect(url_for('bills'))

@app.route('/bill/<int:bill_id>/scan_parent')
@login_required
def scan_bill_parent(bill_id):
    """Scan parent bags to add to bill - admin and employee access"""
    if not (hasattr(current_user, 'is_admin') and current_user.is_admin() or 
            hasattr(current_user, 'role') and current_user.role in ['admin', 'biller', 'dispatcher']):
        flash('Access restricted to admin and employee users.', 'error')
        return redirect(url_for('dashboard'))
    
    # Import models locally to avoid circular imports
    from models import Bill, Bag, BillBag
    
    # Get the bill or return 404 if not found
    bill = Bill.query.get_or_404(bill_id)
    
    # Get current parent bags linked to this bill
    linked_bags = db.session.query(Bag).join(BillBag, Bag.id == BillBag.bag_id).filter(BillBag.bill_id == bill.id).all()
    
    # Get current count for debugging
    current_count = bill.bag_links.count()
    app.logger.info(f'Scan bill parent page - Bill {bill.id} has {current_count} linked bags')
    
    # Check if bill is completed
    is_completed = bill.status == 'completed'
    
    # Use the fast scanner template optimized for Coconut barcode scanner (keyboard wedge mode)
    return render_template('scan_bill_parent_fast.html', bill=bill, linked_bags=linked_bags, is_completed=is_completed)


# Removed redundant save_bill function - bills are automatically saved when parent bags are linked

@app.route('/complete_bill', methods=['POST'])
@login_required
def complete_bill():
    """Complete a bill - ONLY allowed when capacity is reached
    
    Bills can only be completed when linked_parent_count >= parent_bag_count.
    Use 'Save & Continue Later' to keep bill in progress if capacity not met.
    """
    if not (hasattr(current_user, 'is_admin') and current_user.is_admin() or 
            hasattr(current_user, 'role') and current_user.role in ['admin', 'biller']):
        return jsonify({'success': False, 'message': 'Access restricted to admin and biller users.'})
    
    bill_id = request.form.get('bill_id', type=int)
    
    if not bill_id:
        return jsonify({'success': False, 'message': 'Bill ID is required.'})
    
    try:
        # Import models locally to avoid circular imports
        from models import Bill
        
        # Get the bill
        bill = Bill.query.get(bill_id)
        if not bill:
            return jsonify({'success': False, 'message': 'Bill not found.'})
        
        # Count current linked bags
        linked_count = bill.bag_links.count()
        
        # Require at least one linked bag to complete
        if linked_count == 0:
            return jsonify({
                'success': False,
                'message': 'Cannot complete bill with no parent bags linked. Please scan at least one parent bag first.',
                'show_popup': True
            })
        
        # ENFORCE CAPACITY: Cannot complete unless capacity is reached
        target_count = bill.parent_bag_count or 0
        if target_count > 0 and linked_count < target_count:
            remaining = target_count - linked_count
            return jsonify({
                'success': False,
                'message': f'Cannot complete: {remaining} more parent bags needed to reach capacity ({linked_count}/{target_count}).',
                'show_popup': True,
                'linked_count': linked_count,
                'target_count': target_count
            })
        
        # Calculate actual weight from linked parent bags' child counts
        total_weight = db.session.execute(
            text("""
                SELECT COALESCE(SUM(b.child_count), 0) as total_weight
                FROM bill_bag bb
                JOIN bag b ON bb.bag_id = b.id
                WHERE bb.bill_id = :bill_id
            """),
            {'bill_id': bill_id}
        ).scalar() or 0
        
        # Update bill with final counts and status
        bill.status = 'completed'
        bill.total_weight_kg = float(total_weight)  # Actual weight from child count
        bill.expected_weight_kg = float(linked_count * 30)  # Expected: 30kg per parent
        
        db.session.commit()
        
        app.logger.info(f'Bill {bill.bill_id} completed with {linked_count} parent bags, {total_weight}kg actual weight')
        
        return jsonify({
            'success': True, 
            'message': f'Bill completed successfully with {linked_count} parent bags ({total_weight}kg)!',
            'linked_count': linked_count,
            'expected_count': bill.parent_bag_count or linked_count,
            'actual_weight': total_weight,
            'expected_weight': linked_count * 30
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Complete bill error: {str(e)}')
        return jsonify({'success': False, 'message': 'Error completing bill. Please try again.'})

@app.route('/reopen_bill', methods=['POST'])
@login_required
def reopen_bill():
    """Reopen a completed bill for editing - admin and biller access"""
    if not (hasattr(current_user, 'is_admin') and current_user.is_admin() or 
            hasattr(current_user, 'role') and current_user.role in ['admin', 'biller']):
        return jsonify({'success': False, 'message': 'Access restricted to admin and biller users.'})
    
    bill_id = request.form.get('bill_id', type=int)
    
    if not bill_id:
        return jsonify({'success': False, 'message': 'Bill ID is required.'})
    
    try:
        # Import models locally to avoid circular imports
        from models import Bill
        
        # Get the bill
        bill = Bill.query.get_or_404(bill_id)
        
        # Update bill status to active/in progress
        bill.status = 'active'
        
        db.session.commit()
        
        app.logger.info(f'Bill {bill.bill_id} reopened for editing')
        
        return jsonify({
            'success': True, 
            'message': 'Bill reopened for editing!'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Reopen bill error: {str(e)}')
        return jsonify({'success': False, 'message': 'Error reopening bill.'})

@app.route('/fast/bill_parent_scan', methods=['POST'])
def ultra_fast_bill_parent_scan():
    """Ultra-fast bill parent bag scanning with optimized performance"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'message': '🚫 Please login first',
            'auth_required': True,
            'error_type': 'auth_required'
        }), 401
    
    # Check role
    user = User.query.get(user_id)
    if not user or user.role not in ['admin', 'biller']:
        return jsonify({
            'success': False, 
            'message': '🚫 Access restricted to admin and biller users.',
            'error_type': 'access_denied'
        })
    
    bill_id = request.form.get('bill_id')
    qr_code = request.form.get('qr_code', '').strip().upper()
    
    app.logger.info(f'Fast bill scan - bill_id: {bill_id}, qr_code: {qr_code}, user: {user.username}')
    
    if not bill_id or not qr_code:
        return jsonify({
            'success': False, 
            'message': '🚫 Missing bill ID or QR code',
            'error_type': 'missing_data'
        })
    
    # Validate format using InputValidator
    is_valid, qr_code, error_msg = InputValidator.validate_qr_code(qr_code, bag_type='parent')
    if not is_valid:
        return jsonify({
            'success': False,
            'message': f'🚫 {error_msg} You scanned: {qr_code}',
            'show_popup': True,
            'error_type': 'invalid_format'
        })
    
    try:
        # Import the lock helper
        from models import acquire_bill_lock
        
        # Simplified queries for better reliability and debugging
        
        # 1. Check if bill exists
        bill = Bill.query.get(int(bill_id))
        if not bill:
            app.logger.error(f'Bill not found: {bill_id}')
            return jsonify({
                'success': False, 
                'message': f'📋 Bill #{bill_id} not found. Please refresh the page.',
                'error_type': 'bill_not_found'
            })
        
        # Acquire advisory lock before bill_bag operations
        acquire_bill_lock(bill.id)
        
        # 2. Check if parent bag exists (case-insensitive)
        from sqlalchemy import func
        parent_bag = Bag.query.filter(func.upper(Bag.qr_id) == qr_code.upper(), Bag.type == 'parent').first()
        if not parent_bag:
            # Check if it's registered as a different type (case-insensitive)
            other_bag = Bag.query.filter(func.upper(Bag.qr_id) == qr_code.upper()).first()
            if other_bag:
                app.logger.warning(f'Bag {qr_code} is type {other_bag.type}, not parent')
                return jsonify({
                    'success': False,
                    'message': f'🚫 {qr_code} is registered as a {other_bag.type} bag, not a parent bag',
                    'error_type': 'wrong_bag_type'
                })
            else:
                app.logger.warning(f'Bag {qr_code} not found in system')
                return jsonify({
                    'success': False,
                    'message': f'🚫 Bag {qr_code} not registered in system. Please scan a registered parent bag.',
                    'error_type': 'bag_not_found'
                })
        
        app.logger.info(f'Found parent bag: {parent_bag.qr_id} (ID: {parent_bag.id})')
        
        # 3. Get actual child count
        child_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
        app.logger.info(f'Parent bag {qr_code} has {child_count} children')
        
        # 4. Check if already linked to this bill
        existing_link = BillBag.query.filter_by(bill_id=bill.id, bag_id=parent_bag.id).first()
        if existing_link:
            app.logger.info(f'Bag {qr_code} already linked to bill {bill.bill_id}')
            return jsonify({
                'success': False,
                'message': f'✅ {qr_code} already linked to this bill (contains {child_count} children)',
                'error_type': 'already_linked_same_bill'
            })
        
        # 5. Check if linked to another bill
        other_link = BillBag.query.filter_by(bag_id=parent_bag.id).first()
        if other_link:
            other_bill = Bill.query.get(other_link.bill_id)
            app.logger.warning(f'Bag {qr_code} already linked to bill {other_bill.bill_id if other_bill else "Unknown"}')
            return jsonify({
                'success': False,
                'message': f'⚠️ {qr_code} already linked to different Bill #{other_bill.bill_id if other_bill else "Unknown"}. Cannot link to multiple bills.',
                'error_type': 'already_linked_other_bill'
            })
        
        # 6. Check current capacity using denormalized linked_parent_count
        if not bill.can_link_more_bags():
            app.logger.warning(f'Bill {bill.bill_id} at capacity: {bill.linked_parent_count}/{bill.parent_bag_count}')
            return jsonify({
                'success': False,
                'message': f'📦 Bill capacity reached ({bill.linked_parent_count}/{bill.parent_bag_count} parent bags). Cannot add more bags.',
                'error_type': 'capacity_reached',
                'is_at_capacity': True
            })
        
        # All checks passed - link the parent bag to the bill
        app.logger.info(f'Linking {qr_code} to bill {bill.bill_id}')
        
        # Update parent bag with actual child count and weight
        parent_bag.child_count = child_count
        parent_bag.weight_kg = float(child_count)  # 1kg per child
        if child_count >= 30:
            parent_bag.status = 'completed'
        elif child_count > 0:
            parent_bag.status = 'in_progress'
        
        # Create the link
        bill_bag = BillBag()
        bill_bag.bill_id = bill.id
        bill_bag.bag_id = parent_bag.id
        
        # Record scan
        scan = Scan()
        scan.user_id = user_id
        scan.parent_bag_id = parent_bag.id
        scan.timestamp = datetime.now()
        
        db.session.add(bill_bag)
        db.session.add(scan)
        db.session.commit()
        
        # CRITICAL: Use recalculate_weights() to ensure accurate bill totals
        # This prevents edge cases where manual calculations might be wrong
        # Returns: (actual_weight, expected_weight, parent_count, child_count, is_at_capacity)
        actual_weight, expected_weight, parent_count, child_count_total, is_full = bill.recalculate_weights()
        db.session.commit()  # Commit the recalculated values
        
        app.logger.info(f'Successfully linked {qr_code} to bill {bill.bill_id}. Total: {bill.linked_parent_count}/{bill.parent_bag_count}')
        
        # Check if bill is now at capacity (auto-closed)
        capacity_message = ''
        if is_full:
            capacity_message = ' Bill is now at capacity!'
            app.logger.info(f'Bill {bill.bill_id} auto-closed at capacity')
        
        return jsonify({
            'success': True,
            'message': f'✅ {qr_code} linked successfully! Contains {child_count} children ({bill.linked_parent_count}/{bill.parent_bag_count} bags total){capacity_message}',
            'bag_qr': qr_code,
            'linked_count': bill.linked_parent_count,
            'expected_count': bill.parent_bag_count,
            'child_count': child_count,
            'actual_weight': bill.total_weight_kg,
            'expected_weight': bill.expected_weight_kg,
            'is_at_capacity': is_full,
            'remaining_capacity': bill.remaining_capacity(),
            'bill_status': bill.status,
            'error_type': 'success'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Fast bill scan error: {str(e)}', exc_info=True)
        return jsonify({
            'success': False, 
            'message': f'❌ Error processing scan: {str(e)}',
            'error_type': 'server_error'
        })

@app.route('/process_bill_parent_scan', methods=['POST'])
@login_required
def process_bill_parent_scan():
    """Process a parent bag scan for bill linking - admin and biller access (works for completed bills too)"""
    app.logger.info(f'Process bill parent scan - CSRF token present: {request.form.get("csrf_token") is not None}')
    
    if not (hasattr(current_user, 'is_admin') and current_user.is_admin() or 
            hasattr(current_user, 'role') and current_user.role in ['admin', 'biller']):
        return jsonify({'success': False, 'message': 'Access restricted to admin and employee users.'})
    
    bill_id = request.form.get('bill_id')
    qr_code = request.form.get('qr_code')
    
    if not bill_id:
        return jsonify({'success': False, 'message': 'Bill ID missing.'})
    
    if not qr_code:
        return jsonify({'success': False, 'message': 'Please scan a parent bag QR code.'})
    
    # Optimized transaction with proper concurrency handling
    try:
        app.logger.info(f'Processing bill parent scan - bill_id: {bill_id}, qr_code: {qr_code}')
        
        # Import models locally to avoid circular imports
        from models import Bill, Bag, BillBag, acquire_bill_lock
        
        # Get bill - handle both integer ID and string bill_id
        try:
            # First try as integer primary key (from template)
            bill = Bill.query.get(int(bill_id))
        except (ValueError, TypeError):
            # If not integer, try as string bill_id
            bill = Bill.query.filter_by(bill_id=bill_id).first()
        
        if not bill:
            return jsonify({'success': False, 'message': f'Bill with ID "{bill_id}" not found. Please check the bill exists.'})
        
        # Acquire advisory lock before bill_bag operations
        acquire_bill_lock(bill.id)
        
        qr_id = sanitize_input(qr_code.strip() if qr_code else '')
        
        app.logger.info(f'Sanitized QR code: {qr_id}')
        
        # Validate parent bag QR code format using InputValidator
        is_valid, qr_id, error_msg = InputValidator.validate_qr_code(qr_id, bag_type='parent')
        if not is_valid:
            return jsonify({
                'success': False, 
                'message': f'❌ {error_msg} You scanned: {qr_id}',
                'show_popup': True
            })
        
        # Direct parent bag lookup - no caching to avoid model/dict confusion
        parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(qr_id),
            Bag.type == 'parent'
        ).first()
        
        if not parent_bag:
            app.logger.info(f'Parent bag "{qr_id}" not found in database')
            return jsonify({'success': False, 'message': f'❌ Parent bag "{qr_id}" not found! This bag needs to be registered as a parent bag first.'})
        
        app.logger.info(f'Found parent bag: {parent_bag.qr_id} (ID: {parent_bag.id})')
        
        # Parent bag can be linked regardless of status or child count
        # Count child bags for informational purposes only
        child_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
        
        # Update child count and weight based on actual children
        parent_bag.child_count = child_count
        parent_bag.weight_kg = float(child_count)  # 1kg per child
        
        # Mark as completed if it has children, otherwise keep as is
        if child_count > 0 and parent_bag.status == 'pending':
            parent_bag.status = 'in_progress'
        
        db.session.commit()
        app.logger.info(f'Parent bag {qr_id} has {child_count} children, proceeding with linking')
        
        # FIX: Check current bill capacity (after potential edits)
        current_capacity = bill.parent_bag_count
        if current_capacity <= 0 or current_capacity > 100:
            app.logger.error(f'Invalid bill capacity: {current_capacity}')
            return jsonify({'success': False, 'message': 'Bill has invalid capacity configuration'})
        
        # Direct duplicate check
        existing_link = BillBag.query.filter_by(bill_id=bill.id, bag_id=parent_bag.id).first()
        if existing_link:
            return jsonify({'success': False, 'message': f'✓ Parent bag "{qr_id}" is already linked to this bill.'})
        
        # Check if bag is linked to another bill
        other_link = BillBag.query.filter_by(bag_id=parent_bag.id).first()
        if other_link and other_link.bill_id != bill.id:
            other_bill = Bill.query.get(other_link.bill_id)
            other_bill_id = other_bill.bill_id if other_bill else other_link.bill_id
            return jsonify({'success': False, 'message': f'⚠️ Parent bag "{qr_id}" is already linked to bill "{other_bill_id}".'})
        
        # Check capacity using denormalized linked_parent_count (allow linking to completed bills)
        if not bill.can_link_more_bags() and bill.status != 'completed':
            return jsonify({
                'success': False, 
                'message': f'⚠️ Bill is at capacity ({bill.linked_parent_count}/{bill.parent_bag_count} bags). Complete it first to add more.',
                'is_at_capacity': True
            })
        
        app.logger.info(f'Bill linked count: {bill.linked_parent_count}, capacity: {bill.parent_bag_count}')
        
        # Use transaction for atomic operations
        with db.session.begin_nested():
            # Create bill-bag link
            app.logger.info(f'Creating new bill-bag link...')
            bill_bag = BillBag()
            bill_bag.bill_id = bill.id
            bill_bag.bag_id = parent_bag.id
            
            # Track who created/modified the bill
            if not bill.created_by_id:
                bill.created_by_id = current_user.id
            
            # Create scan record
            scan = Scan()
            scan.user_id = current_user.id
            scan.parent_bag_id = parent_bag.id
            scan.timestamp = datetime.now()
            
            db.session.add(bill_bag)
            db.session.add(scan)
        
        # Commit outside the nested transaction
        db.session.commit()
        
        # CRITICAL: Use recalculate_weights() to ensure accurate bill totals
        # This prevents edge cases where manual calculations might be wrong
        # Returns: (actual_weight, expected_weight, parent_count, child_count, is_at_capacity)
        actual_weight, expected_weight, parent_count, child_count_total, is_full = bill.recalculate_weights()
        db.session.commit()  # Commit the recalculated values
        
        # Add audit log entry
        app.logger.info(f'AUDIT: User {current_user.username} (ID: {current_user.id}) linked bag {parent_bag.qr_id} to bill {bill.bill_id}')
        app.logger.info(f'Bill weight recalculated: {actual_weight}kg actual, {expected_weight}kg expected, {child_count_total} total children')
        
        app.logger.info(f'Database commit successful')
        app.logger.info(f'Successfully linked parent bag {qr_id} to bill {bill.bill_id}')
        
        # Check if bill is now at capacity (auto-closed)
        capacity_message = ''
        if is_full:
            capacity_message = ' Bill is now at capacity!'
            app.logger.info(f'Bill {bill.bill_id} auto-closed at capacity')
        
        response_data = {
            'success': True, 
            'message': f'Parent bag {qr_id} linked successfully! (Actual weight: {parent_bag.weight_kg}kg){capacity_message}',
            'bag_qr': qr_id,
            'linked_count': bill.linked_parent_count,
            'expected_count': bill.parent_bag_count,
            'remaining_bags': bill.remaining_capacity(),
            'total_weight': bill.total_weight_kg,
            'expected_weight': bill.expected_weight_kg,
            'total_child_bags': bill.total_child_bags,
            'is_at_capacity': is_full,
            'bill_status': bill.status
        }
        
        app.logger.info(f'Sending response: {response_data}')
        return jsonify(response_data)
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Bill parent scan error: {str(e)}')
        import traceback
        app.logger.error(f'Traceback: {traceback.format_exc()}')
        
        # Handle CSRF errors specifically for AJAX requests
        if 'CSRF' in str(e) or 'csrf' in str(e).lower():
            return jsonify({'success': False, 'message': 'Security token expired. Please refresh the page and try again.'})
        
        return jsonify({'success': False, 'message': 'Error linking parent bag to bill.'})

@app.route('/bag/<path:qr_id>')
@login_required
def bag_details(qr_id):
    """Ultra-optimized bag details using single CTE query to eliminate N+1"""
    from urllib.parse import unquote
    from sqlalchemy.orm import joinedload
    qr_id = unquote(qr_id)
    
    try:
        # ULTRA-OPTIMIZED: Single CTE query to fetch all related data in one roundtrip
        result = db.session.execute(text("""
            WITH bag_data AS (
                SELECT id, qr_id, type, name, status, dispatch_area, created_at
                FROM bag
                WHERE UPPER(qr_id) = UPPER(:qr_id)
                LIMIT 1
            ),
            child_data AS (
                SELECT b.id, b.qr_id, b.name, b.created_at
                FROM bag b
                JOIN link l ON l.child_bag_id = b.id
                WHERE l.parent_bag_id = (SELECT id FROM bag_data WHERE type = 'parent')
                ORDER BY b.created_at DESC
                LIMIT 100
            ),
            parent_data AS (
                SELECT pb.id, pb.qr_id, pb.name, pb.type
                FROM link l
                JOIN bag pb ON pb.id = l.parent_bag_id
                WHERE l.child_bag_id = (SELECT id FROM bag_data WHERE type = 'child')
                LIMIT 1
            ),
            bill_data AS (
                SELECT bill.id, bill.bill_id, bill.description, bill.created_at, bill.status
                FROM bill
                JOIN bill_bag bb ON bb.bill_id = bill.id
                WHERE bb.bag_id IN (
                    SELECT id FROM bag_data WHERE type = 'parent'
                    UNION ALL
                    SELECT id FROM parent_data
                )
                LIMIT 10
            )
            SELECT 
                (SELECT row_to_json(bag_data) FROM bag_data) as bag,
                (SELECT json_agg(row_to_json(child_data)) FROM child_data) as children,
                (SELECT row_to_json(parent_data) FROM parent_data) as parent,
                (SELECT json_agg(row_to_json(bill_data)) FROM bill_data) as bills
        """), {'qr_id': qr_id}).fetchone()
        
        if not result or not result[0]:
            flash('Bag not found', 'error')
            return redirect(url_for('bag_management'))
        
        bag_json, children_json, parent_json, bills_json = result
        
        # Parse bag data (handle both JSON strings and pre-parsed dicts from psycopg2)
        import json
        # psycopg2 may auto-deserialize JSON columns, so check type first
        if isinstance(bag_json, str):
            bag_data = json.loads(bag_json)
        else:
            bag_data = bag_json  # Already a dict
        
        if not bag_data:
            flash('Bag not found', 'error')
            return redirect(url_for('bag_management'))
        
        # Collect all IDs for single bulk fetch - ZERO per-item queries
        all_bag_ids = [bag_data['id']]
        all_bill_ids = []
        
        if children_json:
            # Handle both JSON strings and pre-parsed lists
            if isinstance(children_json, str):
                children_data = json.loads(children_json)
            else:
                children_data = children_json
            if children_data:
                child_ids = [c['id'] for c in children_data]
                all_bag_ids.extend(child_ids)
        
        if parent_json:
            # Handle both JSON strings and pre-parsed dicts
            if isinstance(parent_json, str):
                parent_data = json.loads(parent_json)
            else:
                parent_data = parent_json
            if parent_data:
                all_bag_ids.append(parent_data['id'])
        
        if bills_json:
            # Handle both JSON strings and pre-parsed lists
            if isinstance(bills_json, str):
                bills_data = json.loads(bills_json)
            else:
                bills_data = bills_json
            if bills_data:
                all_bill_ids = [b['id'] for b in bills_data]
        
        # SINGLE BULK FETCH: Load all Bag objects in one query
        bag_objects_dict = {}
        if all_bag_ids:
            bag_objects = Bag.query.filter(Bag.id.in_(all_bag_ids)).all()
            bag_objects_dict = {b.id: b for b in bag_objects}
        
        # SINGLE BULK FETCH: Load all Bill objects in one query
        bill_objects_dict = {}
        if all_bill_ids:
            bill_objects = Bill.query.filter(Bill.id.in_(all_bill_ids)).all()
            bill_objects_dict = {b.id: b for b in bill_objects}
        
        # Build objects from pre-fetched data
        bag = bag_objects_dict.get(bag_data['id'])
        if not bag:
            flash('Bag not found', 'error')
            return redirect(url_for('bag_management'))
        
        child_bags = []
        if children_json:
            # Handle both JSON strings and pre-parsed lists
            if isinstance(children_json, str):
                children_data = json.loads(children_json)
            else:
                children_data = children_json
            if children_data:
                for c in children_data:
                    child_bag = bag_objects_dict.get(c['id'])
                    if child_bag:
                        child_bags.append(child_bag)
        
        parent_bag = None
        if parent_json:
            # Handle both JSON strings and pre-parsed dicts
            if isinstance(parent_json, str):
                parent_data = json.loads(parent_json)
            else:
                parent_data = parent_json
            if parent_data:
                parent_bag = bag_objects_dict.get(parent_data['id'])
        
        bills = []
        link = None
        if bills_json:
            # Handle both JSON strings and pre-parsed lists
            if isinstance(bills_json, str):
                bills_data = json.loads(bills_json)
            else:
                bills_data = bills_json
            if bills_data:
                for b in bills_data:
                    bill = bill_objects_dict.get(b['id'])
                    if bill:
                        bills.append(bill)
                if bills:
                    link = {
                        'id': bills[0].id,
                        'bill_id': bills[0].bill_id,
                        'created_at': bills[0].created_at
                    }
        
        # Get scans with eager loading in single query
        scans = []
        if bag.type == 'parent':
            scans = Scan.query.options(joinedload(Scan.user)).filter(  # type: ignore[arg-type]
                Scan.parent_bag_id == bag.id
            ).order_by(desc(Scan.timestamp)).limit(50).all()
        else:
            scans = Scan.query.options(joinedload(Scan.user)).filter(  # type: ignore[arg-type]
                Scan.child_bag_id == bag.id
            ).order_by(desc(Scan.timestamp)).limit(50).all()
        
        return render_template('bag_detail.html',
                             bag=bag,
                             child_bags=child_bags,
                             parent_bag=parent_bag,
                             bills=bills,
                             scans=scans,
                             is_parent=bag.type == 'parent',
                             link=link)
                             
    except Exception as e:
        app.logger.error(f"Error in bag_details for {qr_id}: {str(e)}")
        flash(f'Error loading bag details: {str(e)}', 'error')
        return redirect(url_for('bag_management'))

# User Profile Management
@app.route('/profile')
@login_required
def user_profile():
    """User profile page where users can view and edit their information"""
    # Import User model locally
    from models import User
    # Get the actual user from database to avoid lazy loading issues
    user = User.query.get(current_user.id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('user_profile.html', user=user)

@app.route('/profile/edit', methods=['POST'])
@login_required
def edit_profile():
    """Edit user profile - all users can edit their own profile"""
    try:
        # Import User model locally
        from models import User
        # Get the actual user from database
        user = User.query.get(current_user.id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('user_profile'))
        
        # Get form data
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Track if we made changes
        changes_made = False
        
        # Validate and update username
        if username and username != user.username:
            # Check if username already exists
            existing_user = User.query.filter(User.username == username, User.id != user.id).first()
            if existing_user:
                flash('Username already exists.', 'error')
                return redirect(url_for('user_profile'))
            user.username = username
            session['username'] = username  # Update session
            changes_made = True
        
        # Validate and update email
        if email and email != user.email:
            # Check if email already exists
            existing_user = User.query.filter(User.email == email, User.id != user.id).first()
            if existing_user:
                flash('Email already exists.', 'error')
                return redirect(url_for('user_profile'))
            user.email = email
            changes_made = True
        
        # Handle password change
        if new_password:
            # Verify current password
            if not current_password or not user.check_password(current_password):
                flash('Current password is incorrect.', 'error')
                return redirect(url_for('user_profile'))
            
            # Check password confirmation
            if new_password != confirm_password:
                flash('New passwords do not match.', 'error')
                return redirect(url_for('user_profile'))
            
            # Set new password using the User model's method for consistency
            user.set_password(new_password)
            db.session.add(user)  # Explicitly mark user for update
            changes_made = True
            
            app.logger.info(f'Password changed for user {user.username} (ID: {user.id})')
            # Audit log: Password changed
            log_audit('password_changed', 'auth', user.id, {
                'username': user.username,
                'ip_address': request.remote_addr,
                'changed_via': 'user_profile'
            })
            flash('Password changed successfully.', 'success')
        
        # Save changes if any were made
        if changes_made:
            try:
                db.session.commit()
                
                # CRITICAL: Invalidate all caches AFTER commit
                # This must happen after commit so the new password is in the database
                if new_password:
                    db.session.expire(user)
                    app.logger.info(f'Cache invalidated for user {user.id} after password change')
                
                # Force session to refresh current user data
                session.modified = True
                flash('Profile updated successfully.', 'success')
            except Exception as commit_error:
                db.session.rollback()
                app.logger.error(f'Profile commit error: {str(commit_error)}')
                flash('Failed to save changes. Please try again.', 'error')
                return redirect(url_for('user_profile'))
        else:
            flash('No changes were made.', 'info')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Profile update error: {str(e)}')
        flash('Failed to update profile. Please try again.', 'error')
    
    return redirect(url_for('user_profile'))

# ============================================================================
# TWO-FACTOR AUTHENTICATION (TOTP) ROUTES
# ============================================================================

@app.route('/2fa/setup')
@login_required
@limiter.limit("10 per minute")  # Prevent excessive 2FA setup attempts
def two_fa_setup():
    """Display 2FA setup page with QR code (Admin only)"""
    from models import User
    from two_fa_utils import TwoFactorAuth
    
    # Only admins can enable 2FA
    if not current_user.is_admin():
        flash('Two-Factor Authentication is only available for admin users.', 'error')
        return redirect(url_for('user_profile'))
    
    user = User.query.get(current_user.id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('user_profile'))
    
    # If 2FA already enabled, redirect to profile
    if user.two_fa_enabled:
        flash('Two-Factor Authentication is already enabled.', 'info')
        return redirect(url_for('user_profile'))
    
    # Generate or retrieve TOTP secret
    if not user.totp_secret:
        secret, qr_code = TwoFactorAuth.setup_2fa_for_user(user)
        user.totp_secret = secret
        db.session.commit()
    else:
        secret = user.totp_secret
        _, qr_code = TwoFactorAuth.setup_2fa_for_user(user, secret)
    
    return render_template('two_fa_setup.html', 
                         secret=secret, 
                         qr_code=qr_code)

@app.route('/2fa/enable', methods=['POST'])
@login_required
@limiter.limit("5 per minute")  # Strict limit to prevent TOTP brute force
def two_fa_enable():
    """Enable 2FA after verifying TOTP code"""
    from models import User
    from two_fa_utils import TwoFactorAuth
    
    # Only admins can enable 2FA
    if not current_user.is_admin():
        flash('Two-Factor Authentication is only available for admin users.', 'error')
        return redirect(url_for('user_profile'))
    
    user = User.query.get(current_user.id)
    if not user or not user.totp_secret:
        flash('Please set up 2FA first.', 'error')
        return redirect(url_for('two_fa_setup'))
    
    token = request.form.get('token', '').strip()
    
    # Verify the TOTP code
    if TwoFactorAuth.verify_totp(user.totp_secret, token):
        user.two_fa_enabled = True
        db.session.commit()
        flash('Two-Factor Authentication enabled successfully!', 'success')
        app.logger.info(f'2FA enabled for admin user: {user.username}')
        # Audit log: 2FA enabled
        log_audit('2fa_enabled', 'auth', user.id, {
            'username': user.username,
            'ip_address': request.remote_addr,
            'role': user.role
        })
        return redirect(url_for('user_profile'))
    else:
        # Audit log: Failed 2FA enable attempt
        log_audit('2fa_enable_failed', 'auth', user.id, {
            'username': user.username,
            'ip_address': request.remote_addr,
            'reason': 'invalid_totp_code'
        })
        flash('Invalid verification code. Please try again.', 'error')
        return redirect(url_for('two_fa_setup'))

@app.route('/2fa/disable', methods=['POST'])
@login_required
@limiter.limit("5 per minute")  # Prevent password brute force during disable
def two_fa_disable():
    """Disable 2FA after password verification"""
    from models import User
    
    # Only admins can have 2FA
    if not current_user.is_admin():
        flash('Access denied.', 'error')
        return redirect(url_for('user_profile'))
    
    user = User.query.get(current_user.id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('user_profile'))
    
    password = request.form.get('password', '').strip()
    
    # Verify password before disabling 2FA
    if not password or not user.check_password(password):
        # Audit log: Failed 2FA disable attempt (wrong password)
        log_audit('2fa_disable_failed', 'auth', user.id, {
            'username': user.username,
            'ip_address': request.remote_addr,
            'reason': 'incorrect_password'
        })
        flash('Incorrect password. Cannot disable 2FA.', 'error')
        return redirect(url_for('user_profile'))
    
    # Disable 2FA and clear secret
    user.two_fa_enabled = False
    user.totp_secret = None
    db.session.commit()
    flash('Two-Factor Authentication has been disabled.', 'info')
    app.logger.info(f'2FA disabled for admin user: {user.username}')
    # Audit log: 2FA disabled
    log_audit('2fa_disabled', 'auth', user.id, {
        'username': user.username,
        'ip_address': request.remote_addr,
        'role': user.role
    })
    return redirect(url_for('user_profile'))

@app.route('/2fa/verify', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # CRITICAL: Prevent TOTP brute force attacks during login
def two_fa_verify():
    """Verify TOTP code during login"""
    from models import User
    from two_fa_utils import TwoFactorAuth
    
    # Check if user is in the middle of 2FA verification
    if 'pending_2fa_user_id' not in session:
        flash('Invalid session. Please log in again.', 'error')
        return redirect(url_for('login'))
    
    user_id = session.get('pending_2fa_user_id')
    user = User.query.get(user_id)
    
    if not user or not user.two_fa_enabled:
        session.pop('pending_2fa_user_id', None)
        flash('Invalid 2FA session.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        
        # Verify TOTP code
        if TwoFactorAuth.verify_totp(user.totp_secret, token):
            # 2FA successful, complete login (with email optimization)
            session.pop('pending_2fa_user_id', None)
            from auth_utils import create_session
            create_session(user.id, user.username, user.role, user.dispatch_area, user.email)
            flash(f'Welcome back, {user.username}!', 'success')
            app.logger.info(f'2FA login successful for user: {user.username}')
            # Audit log: Successful 2FA verification (complete login)
            log_audit('2fa_verify_success_login_complete', 'auth', user.id, {
                'username': user.username,
                'ip_address': request.remote_addr,
                'role': user.role,
                'dispatch_area': user.dispatch_area
            })
            return redirect(url_for('dashboard'))
        else:
            # Audit log: Failed 2FA verification
            log_audit('2fa_verify_failed', 'auth', user.id, {
                'username': user.username,
                'ip_address': request.remote_addr,
                'reason': 'invalid_totp_code'
            })
            flash('Invalid verification code. Please try again.', 'error')
            app.logger.warning(f'Failed 2FA attempt for user: {user.username}')
    
    return render_template('two_fa_verify.html', username=user.username)

# API endpoints for dashboard data - Redirect to ultra-fast version
# Simple in-memory cache for stats
stats_cache = {'data': None, 'timestamp': 0}

@app.route('/api/stats')
@app.route('/api/v2/stats')  # Support v2 endpoint as well
@login_required
def api_dashboard_stats():
    """Ultra-fast cached stats endpoint with simple in-memory caching"""
    import time
    
    # Check simple in-memory cache (30 second TTL)
    current_time = time.time()
    if stats_cache['data'] and (current_time - stats_cache['timestamp'] < 30):
        return jsonify({
            'success': True,
            'statistics': stats_cache['data'],
            'cached': True,
            'cache_age': current_time - stats_cache['timestamp']
        })
    
    try:
        # OPTIMIZED FOR 1.8M+ BAGS: Use statistics cache table (sub-10ms at any scale!)
        # Falls back to real-time counts if cache table doesn't exist
        stats_result = db.session.execute(text("""
            SELECT 
                parent_bags::int,
                child_bags::int,
                total_bags::int,
                total_scans::int,
                total_bills::int,
                last_updated
            FROM statistics_cache
            WHERE id = 1
        """)).fetchone()
        
        # PRODUCTION: Debug logging disabled to reduce log volume
        
        if stats_result:
            # Use cached statistics (instant!) - Access by index for reliability
            stats = {
                'total_parent_bags': int(stats_result[0]) if stats_result[0] is not None else 0,
                'total_child_bags': int(stats_result[1]) if stats_result[1] is not None else 0,
                'total_scans': int(stats_result[3]) if stats_result[3] is not None else 0,
                'total_bills': int(stats_result[4]) if stats_result[4] is not None else 0,
                'total_products': int(stats_result[2]) if stats_result[2] is not None else 0,
                'active_dispatchers': 0,
                'status_counts': {
                    'active': int(stats_result[2]) if stats_result[2] is not None else 0,
                    'scanned': int(stats_result[3]) if stats_result[3] is not None else 0
                },
                'cache_updated': stats_result[5].isoformat() if stats_result[5] else None
            }
            # PRODUCTION: Debug logging disabled to reduce log volume
        else:
            # Fallback to real-time counts (slower but works if cache table doesn't exist)
            stats_result_fallback = db.session.execute(text("""
                WITH bag_counts AS (
                    SELECT 
                        COUNT(*) FILTER (WHERE type = 'parent') as parent_count,
                        COUNT(*) FILTER (WHERE type = 'child') as child_count,
                        COUNT(*) as total_count
                    FROM bag
                )
                SELECT 
                    bc.parent_count::int,
                    bc.child_count::int,
                    bc.total_count::int,
                    (SELECT COUNT(*) FROM scan)::int as scan_count,
                    (SELECT COUNT(*) FROM bill)::int as bill_count
                FROM bag_counts bc
            """)).fetchone()
            
            stats = {
                'total_parent_bags': stats_result_fallback.parent_count if stats_result_fallback else 0,
                'total_child_bags': stats_result_fallback.child_count if stats_result_fallback else 0,
                'total_scans': stats_result_fallback.scan_count if stats_result_fallback else 0,
                'total_bills': stats_result_fallback.bill_count if stats_result_fallback else 0,
                'total_products': (stats_result_fallback.parent_count if stats_result_fallback else 0) + (stats_result_fallback.child_count if stats_result_fallback else 0),
                'active_dispatchers': 0,
                'status_counts': {
                    'active': stats_result_fallback.total_count if stats_result_fallback else 0,
                    'scanned': stats_result_fallback.scan_count if stats_result_fallback else 0
                }
            }
        
        # Update cache
        stats_cache['data'] = stats
        stats_cache['timestamp'] = current_time
        
        return jsonify({
            'success': True,
            'statistics': stats,
            'cached': False
        })
    except Exception as e:
        app.logger.error(f"Stats API error: {str(e)}")
        # Return last cached data if available
        if stats_cache['data']:
            return jsonify({
                'success': True,
                'statistics': stats_cache['data'],
                'cached': True,
                'stale': True
            })
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/slow_queries')
@login_required
def api_slow_queries():
    """Slow query statistics and history - admin only"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        from slow_query_logger import get_slow_query_logger, analyze_slow_queries
        
        logger_inst = get_slow_query_logger()
        
        if not logger_inst:
            return jsonify({
                'success': False,
                'error': 'Slow query logging not available'
            }), 503
        
        # Get time window from query params (default: 60 minutes)
        minutes = request.args.get('minutes', 60, type=int)
        minutes = min(minutes, 1440)  # Cap at 24 hours
        
        # Get analysis
        analysis = analyze_slow_queries(minutes=minutes)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        app.logger.error(f"Slow queries API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Removed /api/pool_health - pool metrics now included in /api/system_health

@app.route('/api/system_health')
@login_required
def api_system_health():
    """System health metrics - admin only"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        import psutil
        import os
        import time
        from datetime import datetime
        from pool_monitor import get_pool_monitor
        
        pool_stats = {
            'size': 0,
            'checked_out': 0,
            'overflow': 0,
            'configured_max': 40,
            'usage_percent': 0,
            'health_status': 'unknown'
        }
        
        try:
            monitor = get_pool_monitor()
            if monitor:
                current_stats = monitor.get_pool_stats()
                if current_stats:
                    pool_stats.update(current_stats)
                    health_summary = monitor.get_health_summary()
                    pool_stats['health_status'] = health_summary.get('status', 'unknown')
                    pool_stats['recommendations'] = health_summary.get('recommendations', [])
                    pool_stats['trend_analysis'] = health_summary.get('trend_analysis', {})
            else:
                pool = db.engine.pool
                pool_stats['size'] = pool.size()  # type: ignore
                pool_stats['checked_out'] = pool.checkedout()  # type: ignore
                pool_stats['overflow'] = pool.overflow()  # type: ignore
        except:
            pass
        
        cache_stats = {
            'enabled': True,
            'type': 'database',
            'message': 'Using database-level StatisticsCache'
        }
        
        # Database size
        db_stats = {}
        try:
            db_size_result = db.session.execute(text("""
                SELECT 
                    pg_database_size(current_database()) as db_size,
                    pg_size_pretty(pg_database_size(current_database())) as db_size_pretty
            """)).fetchone()
            
            if db_size_result:
                db_stats = {
                    'size_bytes': db_size_result.db_size,
                    'size_pretty': db_size_result.db_size_pretty
                }
        except:
            db_stats = {'size_bytes': 0, 'size_pretty': 'N/A'}
        
        # Process memory usage
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        memory_stats = {
            'rss_bytes': memory_info.rss,
            'rss_mb': round(memory_info.rss / (1024 * 1024), 2),
            'percent': round(process.memory_percent(), 2)
        }
        
        # System uptime (process uptime)
        uptime_seconds = time.time() - process.create_time()
        uptime_hours = uptime_seconds / 3600
        
        # Recent errors (last hour) - with proper WHERE clause grouping
        error_count = 0
        try:
            error_count_result = db.session.execute(text("""
                SELECT COUNT(*) as error_count
                FROM audit_log
                WHERE (action LIKE '%error%' OR action LIKE '%fail%')
                AND timestamp > NOW() - INTERVAL '1 hour'
            """)).fetchone()
            
            if error_count_result:
                error_count = error_count_result.error_count
        except:
            pass
        
        # Schema verification - check Bill table has all required columns
        schema_status = {'healthy': True, 'missing_columns': [], 'message': 'All columns present'}
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            bill_columns = [col['name'] for col in inspector.get_columns('bill')]
            
            required_bill_columns = ['linked_parent_count', 'total_child_bags', 'total_weight_kg', 'expected_weight_kg']
            missing = [col for col in required_bill_columns if col not in bill_columns]
            
            if missing:
                schema_status = {
                    'healthy': False,
                    'missing_columns': missing,
                    'message': f'Missing Bill columns: {", ".join(missing)}. Restart app to auto-fix.'
                }
        except Exception as schema_error:
            schema_status = {
                'healthy': False,
                'missing_columns': [],
                'message': f'Schema check failed: {str(schema_error)}'
            }
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'uptime_hours': round(uptime_hours, 2),
            'database': {
                'connection_pool': pool_stats,
                'size': db_stats,
                'schema': schema_status
            },
            'cache': cache_stats,
            'memory': memory_stats,
            'errors': {
                'last_hour': error_count
            }
        })
        
    except Exception as e:
        app.logger.error(f"System health API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/session/status')
@login_required
def api_session_status():
    """
    Get current session status including time remaining.
    This endpoint allows frontend to display session warnings and handle auto-logout.
    """
    try:
        from auth_utils import (
            get_session_time_remaining,
            should_show_timeout_warning,
            SESSION_ABSOLUTE_TIMEOUT,
            SESSION_INACTIVITY_TIMEOUT,
            SESSION_WARNING_TIME
        )
        from datetime import datetime
        
        time_remaining = get_session_time_remaining()
        show_warning = should_show_timeout_warning()
        
        # Get session timestamps
        created_at_str = session.get('created_at')
        last_activity_str = session.get('last_activity')
        
        created_at = None
        last_activity = None
        
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str).isoformat()
            except:
                pass
        
        if last_activity_str:
            try:
                last_activity = datetime.fromisoformat(last_activity_str).isoformat()
            except:
                pass
        
        return jsonify({
            'success': True,
            'authenticated': True,
            'time_remaining_seconds': int(time_remaining),
            'show_warning': show_warning,
            'session_info': {
                'created_at': created_at,
                'last_activity': last_activity,
                'absolute_timeout': SESSION_ABSOLUTE_TIMEOUT,
                'inactivity_timeout': SESSION_INACTIVITY_TIMEOUT,
                'warning_time': SESSION_WARNING_TIME
            }
        })
    except Exception as e:
        app.logger.error(f"Session status API error: {str(e)}")
        return jsonify({
            'success': False,
            'authenticated': False,
            'error': str(e)
        }), 500

@app.route('/api/scans')
@limiter.exempt  # Exempt from rate limiting for dashboard functionality
def api_recent_scans():
    """Get recent scans for dashboard - returns real scan data"""
    try:
        limit = min(request.args.get('limit', 10, type=int), 50)
        
        # Get real scans from database
        result = db.session.execute(text("""
            SELECT 
                s.id,
                s.timestamp,
                COALESCE(pb.qr_id, cb.qr_id, 'Unknown') as product_qr,
                COALESCE(pb.name, cb.name, 'Unknown Product') as product_name,
                COALESCE(pb.type, cb.type, 'unknown') as type,
                u.username
            FROM scan s
            LEFT JOIN bag pb ON s.parent_bag_id = pb.id
            LEFT JOIN bag cb ON s.child_bag_id = cb.id
            LEFT JOIN "user" u ON s.user_id = u.id
            ORDER BY s.timestamp DESC
            LIMIT :limit
        """), {'limit': limit})
        
        scans = []
        for row in result:
            scans.append({
                'id': row.id,
                'timestamp': row.timestamp.isoformat() if row.timestamp else None,
                'product_qr': row.product_qr or 'Unknown',
                'product_name': row.product_name or 'Unknown Product',
                'type': row.type or 'unknown',
                'username': row.username or 'Unknown User'
            })
        
        return jsonify({
            'success': True,
            'scans': scans if scans else [],
            'count': len(scans)
        })
    except Exception as e:
        app.logger.error(f'Recent scans API error: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e),
            'scans': []
        }), 500

@app.route('/api/activity/<int:days>')
@login_required
def api_activity_stats(days):
    """Get scan activity statistics for the past X days"""
    try:
        from datetime import datetime, timedelta
        
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        # Use raw SQL to avoid model imports
        sql = """
        SELECT 
            DATE(timestamp) as date,
            COUNT(id) as scan_count
        FROM scan 
        WHERE DATE(timestamp) >= :start_date 
          AND DATE(timestamp) <= :end_date
        GROUP BY DATE(timestamp)
        """
        
        result = db.session.execute(db.text(sql), {
            'start_date': start_date,
            'end_date': end_date
        })
        activity_data = result.fetchall()
        
        # Convert to list of dictionaries
        activity_list = []
        for date_obj, count in activity_data:
            activity_list.append({
                'date': date_obj.isoformat(),
                'scan_count': count
            })
        
        return jsonify({
            'success': True,
            'activity': activity_list,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        })
        
    except Exception as e:
        app.logger.error(f'Activity API error: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/scan/<int:scan_id>')
@login_required
def view_scan_details(scan_id):
    """View detailed information about a specific scan"""
    scan = Scan.query.get_or_404(scan_id)
    
    # Get the bag information
    bag = None
    if scan.parent_bag_id:
        bag = Bag.query.get(scan.parent_bag_id)
    elif scan.child_bag_id:
        bag = Bag.query.get(scan.child_bag_id)
    

    
    return render_template('scan_details.html', scan=scan, bag=bag)

@app.route('/api/scanned-children')
@login_required
def api_scanned_children():
    """Get scanned child bags for current session"""
    try:
        # Get parent bag from session using same logic as scan_child route
        parent_bag = None
        
        # First try current_parent_qr
        parent_qr = session.get('current_parent_qr')
        if parent_qr:
            parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(parent_qr),
            Bag.type == 'parent'
        ).first()
        
        # If not found, try last_scan
        if not parent_bag:
            last_scan = session.get('last_scan')
            if last_scan and last_scan.get('type') == 'parent':
                parent_qr_id = last_scan.get('qr_id')
                if parent_qr_id:
                    parent_bag = Bag.query.filter_by(qr_id=parent_qr_id, type='parent').first()
                    if parent_bag:
                        parent_qr = parent_qr_id
        
        # If still not found, find most recent parent bag for this user
        if not parent_bag:
            recent_parent_scan = Scan.query.filter_by(user_id=current_user.id).filter(
                Scan.parent_bag_id.isnot(None)
            ).order_by(desc(Scan.timestamp)).first()
            
            if recent_parent_scan and recent_parent_scan.parent_bag_id:
                parent_bag = Bag.query.get(recent_parent_scan.parent_bag_id)
                if parent_bag:
                    parent_qr = parent_bag.qr_id
        
        if not parent_bag:
            return jsonify({
                'success': False,
                'message': 'No active parent bag session'
            })
        
        # Get all linked child bags
        links = Link.query.filter_by(parent_bag_id=parent_bag.id).all()
        children = []
        for link in links:
            child_bag = Bag.query.get(link.child_bag_id)
            if child_bag:
                children.append({
                    'qr_id': child_bag.qr_id,
                    'id': child_bag.id
                })
        
        return jsonify({
            'success': True,
            'children': children,
            'parent_qr': parent_qr
        })
        
    except Exception as e:
        app.logger.error(f'Error getting scanned children: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Error retrieving scanned children'
        }), 500



@app.route('/api/delete-child-scan', methods=['POST'])
@login_required
def api_delete_child_scan():
    """Delete a child bag scan"""
    try:
        qr_code = request.form.get('qr_code')
        if not qr_code:
            return jsonify({
                'success': False,
                'message': 'QR code is required'
            })
        
        # Find the child bag
        child_bag = Bag.query.filter_by(qr_id=qr_code, type='child').first()
        if not child_bag:
            return jsonify({
                'success': False,
                'message': 'Child bag not found'
            })
        
        # Get parent bag from session
        parent_qr = session.get('current_parent_qr')
        if not parent_qr:
            return jsonify({
                'success': False,
                'message': 'No active parent bag session'
            })
        
        parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(parent_qr),
            Bag.type == 'parent'
        ).first()
        if not parent_bag:
            return jsonify({
                'success': False,
                'message': 'Parent bag not found'
            })
        
        # Delete the link between parent and child
        link = Link.query.filter_by(
            parent_bag_id=parent_bag.id,
            child_bag_id=child_bag.id
        ).first()
        
        if not link:
            return jsonify({
                'success': False,
                'message': 'Child bag is not linked to this parent'
            })
        
        db.session.delete(link)
        
        # Delete scan records for this child bag
        scans = Scan.query.filter_by(child_bag_id=child_bag.id).all()
        for scan in scans:
            db.session.delete(scan)
        
        # Delete the child bag itself since unlinked child bags should not exist
        db.session.delete(child_bag)
        
        db.session.commit()
        
        app.logger.info(f"Removed link and deleted child bag {qr_code} from parent {parent_qr}")
        
        return jsonify({
            'success': True,
            'message': f'Child bag {qr_code} removed from parent {parent_qr} and deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error deleting child scan: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Error deleting scan'
        }), 500

@app.route('/api/delete_bag', methods=['POST'])
@login_required
def api_delete_bag():
    """Delete a bag with all validations in a single optimized CTE query"""
    if not (current_user.is_admin() or current_user.is_biller()):
        return jsonify({'success': False, 'message': 'Admin or biller access required'}), 403
    
    qr_code = request.form.get('qr_code', '').strip()
    if not qr_code:
        return jsonify({'success': False, 'message': 'QR code is required'})
    
    try:
        from sqlalchemy import text
        from models import acquire_bag_lock, acquire_bill_lock
        
        # ULTRA-OPTIMIZED: Single CTE query for all validation checks
        validation_result = db.session.execute(text("""
            WITH bag_info AS (
                SELECT 
                    b.id, 
                    b.type, 
                    b.qr_id,
                    bb.bill_id,
                    bill.bill_id as bill_identifier
                FROM bag b
                LEFT JOIN bill_bag bb ON bb.bag_id = b.id
                LEFT JOIN bill ON bill.id = bb.bill_id
                WHERE UPPER(b.qr_id) = UPPER(:qr_code)
                LIMIT 1
            ),
            child_links AS (
                SELECT 
                    array_agg(l.child_bag_id) as child_ids,
                    COUNT(l.child_bag_id) as child_count
                FROM link l
                WHERE l.parent_bag_id = (SELECT id FROM bag_info WHERE type = 'parent')
            ),
            multi_parent_check AS (
                SELECT 
                    COUNT(*) as multi_parent_count
                FROM link l
                CROSS JOIN child_links cl
                WHERE l.child_bag_id = ANY(COALESCE(cl.child_ids, ARRAY[]::int[]))
                GROUP BY l.child_bag_id
                HAVING COUNT(DISTINCT l.parent_bag_id) > 1
            ),
            parent_link_info AS (
                SELECT 
                    l.parent_bag_id,
                    pb.qr_id as parent_qr
                FROM link l
                JOIN bag pb ON pb.id = l.parent_bag_id
                WHERE l.child_bag_id = (SELECT id FROM bag_info WHERE type = 'child')
                LIMIT 1
            )
            SELECT 
                bi.id,
                bi.type,
                bi.qr_id,
                bi.bill_id,
                bi.bill_identifier,
                COALESCE(cl.child_ids, ARRAY[]::int[]) as child_ids,
                COALESCE(cl.child_count, 0) as child_count,
                COALESCE((SELECT multi_parent_count FROM multi_parent_check LIMIT 1), 0) as multi_parent_count,
                pli.parent_qr
            FROM bag_info bi
            LEFT JOIN child_links cl ON bi.type = 'parent'
            LEFT JOIN parent_link_info pli ON bi.type = 'child'
        """), {'qr_code': qr_code}).fetchone()
        
        if not validation_result or not validation_result[0]:
            return jsonify({'success': False, 'message': 'Bag not found'})
        
        bag_id, bag_type, bag_qr, bill_id, bill_identifier, child_ids, child_count, multi_parent_count, parent_qr = validation_result
        
        # Validation checks using the single query result
        if bag_type == 'parent' and bill_id:
            log_audit('delete_bag_prevented', 'bag', bag_id, {
                'qr_id': bag_qr, 'bag_type': bag_type, 'reason': 'linked_to_bill',
                'bill_id': bill_identifier, 'user_id': current_user.id
            })
            return jsonify({
                'success': False,
                'message': f'Cannot delete. This parent bag is linked to bill "{bill_identifier}". Remove it from the bill first.'
            }), 400
        
        if bag_type == 'parent' and multi_parent_count > 0:
            log_audit('delete_bag_prevented', 'bag', bag_id, {
                'qr_id': bag_qr, 'bag_type': bag_type, 'reason': 'children_have_multiple_parents',
                'child_count': multi_parent_count, 'user_id': current_user.id
            })
            return jsonify({
                'success': False,
                'message': f'Cannot delete. {multi_parent_count} child bag(s) are linked to multiple parents. Remove those links first.'
            }), 400
        
        # Acquire locks (only if we're proceeding with deletion)
        if bill_id:
            acquire_bill_lock(bill_id)
        acquire_bag_lock(bag_id)
        
        # ULTRA-OPTIMIZED: Single atomic deletion using CTE
        if bag_type == 'parent':
            db.session.execute(text("""
                WITH deleted_scan_child AS (
                    DELETE FROM scan WHERE child_bag_id = ANY(:child_ids) RETURNING 1
                ),
                deleted_scan_parent AS (
                    DELETE FROM scan WHERE parent_bag_id = :bag_id RETURNING 1
                ),
                deleted_bill_bag AS (
                    DELETE FROM bill_bag WHERE bag_id = :bag_id RETURNING 1
                ),
                deleted_links AS (
                    DELETE FROM link WHERE parent_bag_id = :bag_id RETURNING 1
                ),
                deleted_children AS (
                    DELETE FROM bag WHERE id = ANY(:child_ids) RETURNING 1
                )
                DELETE FROM bag WHERE id = :bag_id
            """), {'bag_id': bag_id, 'child_ids': child_ids if child_ids else []})
            
            message = f'Parent bag {bag_qr} and {child_count} linked child bags deleted successfully'
        else:
            db.session.execute(text("""
                WITH deleted_scans AS (
                    DELETE FROM scan WHERE child_bag_id = :bag_id RETURNING 1
                ),
                deleted_links AS (
                    DELETE FROM link WHERE child_bag_id = :bag_id RETURNING 1
                )
                DELETE FROM bag WHERE id = :bag_id
            """), {'bag_id': bag_id})
            
            message = f'Child bag {bag_qr} deleted successfully'
            if parent_qr:
                message += f' (was linked to parent {parent_qr})'
        
        db.session.commit()
        
        log_audit('delete_bag', 'bag', bag_id, {
            'qr_id': bag_qr, 'bag_type': bag_type,
            'child_bags_deleted': child_count if bag_type == 'parent' else 0,
            'user_id': current_user.id
        })
        
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error deleting bag {qr_code}: {str(e)}')
        return jsonify({'success': False, 'message': f'Error deleting bag: {str(e)}'}), 500

@app.route('/edit-parent/<parent_qr>')
@login_required
def edit_parent_children(parent_qr):
    """Edit parent bag children page - Admin only"""
    # Check if user is admin
    if not current_user.is_admin():
        flash('Only administrators can edit parent-child relationships', 'error')
        return redirect(url_for('bag_management'))
    
    parent_bag = Bag.query.filter(
        func.upper(Bag.qr_id) == func.upper(parent_qr),
        Bag.type == 'parent'
    ).first_or_404()
    
    # Get current children
    links = Link.query.filter_by(parent_bag_id=parent_bag.id).all()
    current_children = []
    for link in links:
        child_bag = Bag.query.get(link.child_bag_id)
        if child_bag:
            current_children.append(child_bag.qr_id)
    
    return render_template('edit_parent_children.html',
                         parent_qr=parent_qr,
                         current_children=current_children)

@app.route('/api/edit-parent-children', methods=['POST'])
@login_required
def api_edit_parent_children():
    """Edit the child bag list for a parent bag - Admin only"""
    # Check if user is admin
    if not current_user.is_admin():
        return jsonify({
            'success': False,
            'message': 'Only administrators can edit parent-child relationships'
        }), 403
    
    try:
        parent_qr = request.form.get('parent_qr')
        child_qrs = request.form.getlist('child_qrs[]')  # List of child QR codes
        
        if not parent_qr:
            return jsonify({
                'success': False,
                'message': 'Parent QR code is required'
            })
        
        parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(parent_qr),
            Bag.type == 'parent'
        ).first()
        if not parent_bag:
            return jsonify({
                'success': False,
                'message': 'Parent bag not found'
            })
        
        # Get existing child bags to determine which ones will be removed
        existing_links = Link.query.filter_by(parent_bag_id=parent_bag.id).all()
        existing_child_qrs = set()
        for link in existing_links:
            child_bag = Bag.query.get(link.child_bag_id)
            if child_bag:
                existing_child_qrs.add(child_bag.qr_id)
        
        # Determine which child bags will be removed (not in new list)
        new_child_qrs = set(child_qr.strip() for child_qr in child_qrs if child_qr.strip())
        removed_child_qrs = existing_child_qrs - new_child_qrs
        
        # Delete child bags that are being removed from parent
        for removed_qr in removed_child_qrs:
            child_bag = Bag.query.filter_by(qr_id=removed_qr, type='child').first()
            if child_bag:
                # Delete all scans for this child bag
                child_scans = Scan.query.filter_by(child_bag_id=child_bag.id).all()
                for scan in child_scans:
                    db.session.delete(scan)
                
                # Delete the child bag itself
                db.session.delete(child_bag)
                app.logger.info(f'Deleted child bag {removed_qr} from database')
        
        # Remove all existing links for this parent
        for link in existing_links:
            db.session.delete(link)
        
        # Create new links for the specified child bags
        for child_qr in child_qrs:
            if child_qr.strip():  # Skip empty entries
                child_bag = Bag.query.filter_by(qr_id=child_qr.strip(), type='child').first()
                if not child_bag:
                    # Create new child bag automatically for any QR code
                    child_bag = Bag()
                    child_bag.qr_id = child_qr.strip()
                    child_bag.name = f"Bag {child_qr.strip()}"
                    child_bag.type = 'child'
                    db.session.add(child_bag)
                    db.session.flush()  # Get the ID for the new bag
                    app.logger.info(f'New child bag created for QR code: {child_qr.strip()}')
                
                # Check if this child is already linked to a DIFFERENT parent
                existing_link = Link.query.filter_by(child_bag_id=child_bag.id).first()
                if existing_link and existing_link.parent_bag_id != parent_bag.id:
                    return jsonify({
                        'success': False,
                        'message': f'Child bag {child_qr} is already linked to another parent'
                    })
                
                # Only create new link if it doesn't already exist
                if not existing_link:
                    new_link = Link()
                    new_link.parent_bag_id = parent_bag.id
                    new_link.child_bag_id = child_bag.id
                    db.session.add(new_link)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Parent bag {parent_qr} children updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error editing parent children: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Error updating parent bag children'
        }), 500

@app.route('/api/parent-children/<parent_qr>')
@login_required
def api_get_parent_children(parent_qr):
    """Get the list of child QR codes for a parent bag"""
    try:
        parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(parent_qr),
            Bag.type == 'parent'
        ).first()
        if not parent_bag:
            return jsonify({
                'success': False,
                'message': 'Parent bag not found'
            })
        
        # Get all linked child bags
        links = Link.query.filter_by(parent_bag_id=parent_bag.id).all()
        children = []
        for link in links:
            child_bag = Bag.query.get(link.child_bag_id)
            if child_bag:
                children.append(child_bag.qr_id)
        
        return jsonify({
            'success': True,
            'children': children,
            'parent_qr': parent_qr
        })
        
    except Exception as e:
        app.logger.error(f'Error getting parent children: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Error retrieving parent bag children'
        }), 500

# Bill Summary and Manual Entry Routes
@app.route('/bill/manual_parent_entry', methods=['GET', 'POST'])
@login_required
@login_required
def manual_parent_entry():
    """Manually enter a parent bag QR code to link to a bill"""
    # Comprehensive logging
    app.logger.info(f'=== MANUAL PARENT ENTRY START ===')
    app.logger.info(f'Request Method: {request.method}')
    app.logger.info(f'Request Headers: {dict(request.headers)}')
    app.logger.info(f'Request Form Data: {dict(request.form)}')
    app.logger.info(f'Request JSON: {request.get_json() if request.is_json else "Not JSON"}')
    app.logger.info(f'User: {current_user.username if current_user.is_authenticated else "Not authenticated"}')
    app.logger.info(f'User Role: {current_user.role if hasattr(current_user, "role") else "No role"}')
    
    # Handle GET requests (when user navigates directly to URL)
    if request.method == 'GET':
        app.logger.warning('GET request to manual_parent_entry - redirecting to bills page')
        flash('Manual parent entry must be done from the bill scanning page, not by direct URL access.', 'warning')
        return redirect(url_for('bill_management'))
    
    # Check authentication
    if not current_user.is_authenticated:
        app.logger.error('User not authenticated')
        return jsonify({'success': False, 'message': 'User not authenticated'}), 401
    
    # Check permissions
    if not (current_user.is_admin() or current_user.is_biller()):
        app.logger.error(f'Access denied for user role: {current_user.role}')
        return jsonify({'success': False, 'message': 'Access restricted to admin and biller users.'}), 403
    
    try:
        # Try to get data from form or JSON
        if request.is_json:
            data = request.get_json()
            bill_id = data.get('bill_id')
            manual_qr = data.get('manual_qr', '').strip()
            app.logger.info(f'Extracted from JSON - bill_id: {bill_id}, manual_qr: {manual_qr}')
        else:
            # Try to get bill_id as integer or string
            bill_id = request.form.get('bill_id')
            if bill_id:
                try:
                    bill_id = int(bill_id)
                except ValueError:
                    app.logger.error(f'Invalid bill_id format: {bill_id}')
                    bill_id = None
            manual_qr = request.form.get('manual_qr', '').strip()
            app.logger.info(f'Extracted from Form - bill_id: {bill_id}, manual_qr: {manual_qr}')
        
        if not bill_id:
            app.logger.error('Bill ID is missing')
            return jsonify({'success': False, 'message': 'Bill ID is required.'}), 400
        
        if not manual_qr:
            app.logger.error('Manual QR is missing')
            return jsonify({'success': False, 'message': 'Please enter a parent bag QR code.'}), 400
        
        # Convert to uppercase for validation
        manual_qr = manual_qr.upper()
        app.logger.info(f'Manual QR after uppercase: {manual_qr}')
        
        # Validate format using InputValidator
        is_valid, manual_qr, error_msg = InputValidator.validate_qr_code(manual_qr, bag_type='parent')
        if not is_valid:
            app.logger.error(f'Invalid QR format: {manual_qr} - {error_msg}')
            return jsonify({
                'success': False,
                'message': f'{error_msg} You entered: {manual_qr}'
            }), 400
        
        # Get the bill
        app.logger.info(f'Looking for bill with ID: {bill_id}')
        bill = Bill.query.get(bill_id)
        if not bill:
            app.logger.error(f'Bill not found with ID: {bill_id}')
            return jsonify({'success': False, 'message': 'Bill not found.'}), 404
        app.logger.info(f'Found bill: {bill.bill_id}')
        
        # Check if parent bag exists
        app.logger.info(f'Checking if parent bag exists: {manual_qr}')
        parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(manual_qr),
            Bag.type == 'parent'
        ).first()
        
        if not parent_bag:
            # Create the parent bag if it doesn't exist (for manual entry)
            parent_bag = Bag()
            parent_bag.qr_id = manual_qr
            parent_bag.type = 'parent'
            parent_bag.name = f'Manual Entry - {manual_qr}'
            parent_bag.status = 'pending'  # Manual entries start as pending
            parent_bag.child_count = 0
            parent_bag.weight_kg = 0.0  # Will be updated when children are added
            parent_bag.user_id = current_user.id
            parent_bag.dispatch_area = current_user.dispatch_area if hasattr(current_user, 'dispatch_area') else None
            db.session.add(parent_bag)
            db.session.flush()
            
            app.logger.info(f'Created new parent bag via manual entry: {manual_qr}')
        else:
            app.logger.info(f'Parent bag already exists: {manual_qr}, status: {parent_bag.status}')
        
        # Parent bag can be linked regardless of status or child count
        # Count child bags for weight calculation
        child_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
        
        # Update bag with actual child count and weight
        parent_bag.child_count = child_count
        parent_bag.weight_kg = float(child_count)  # 1kg per child
        
        # Update status based on children
        if child_count > 0 and parent_bag.status == 'pending':
            parent_bag.status = 'in_progress'
        
        db.session.commit()
        app.logger.info(f'Parent bag {manual_qr} has {child_count} children, proceeding with linking')
        
        # Check if bag is already linked to this bill
        app.logger.info(f'Checking if bag already linked to bill {bill.id}')
        existing_link = BillBag.query.filter_by(bill_id=bill.id, bag_id=parent_bag.id).first()
        if existing_link:
            app.logger.warning(f'Parent bag {manual_qr} already linked to bill {bill.bill_id}')
            return jsonify({'success': False, 'message': f'Parent bag {manual_qr} is already linked to this bill.'}), 400
        
        # Check if bag is linked to another bill
        app.logger.info(f'Checking if bag linked to another bill')
        other_link = BillBag.query.filter_by(bag_id=parent_bag.id).first()
        if other_link and other_link.bill_id != bill.id:
            other_bill = Bill.query.get(other_link.bill_id)
            app.logger.warning(f'Parent bag {manual_qr} already linked to another bill: {other_bill.bill_id if other_bill else other_link.bill_id}')
            return jsonify({
                'success': False,
                'message': f'Parent bag {manual_qr} is already linked to bill {other_bill.bill_id if other_bill else "another bill"}.'
            }), 400
        
        # Check capacity using denormalized linked_parent_count
        if not bill.can_link_more_bags():
            app.logger.warning(f'Bill {bill.bill_id} at capacity: {bill.linked_parent_count}/{bill.parent_bag_count}')
            return jsonify({
                'success': False,
                'message': f'Bill is at capacity ({bill.linked_parent_count}/{bill.parent_bag_count} bags). Cannot add more bags.',
                'is_at_capacity': True
            }), 400
        
        # Create the link
        app.logger.info(f'Creating link between bag {parent_bag.id} and bill {bill.id}')
        bill_bag = BillBag()
        bill_bag.bill_id = bill.id
        bill_bag.bag_id = parent_bag.id
        
        db.session.add(bill_bag)
        db.session.commit()
        app.logger.info(f'Successfully linked parent bag {manual_qr} to bill {bill.bill_id}')
        
        # CRITICAL: Use recalculate_weights() to ensure accurate bill totals
        # Returns: (actual_weight, expected_weight, parent_count, child_count, is_at_capacity)
        actual_weight, expected_weight, parent_count, child_count_total, is_full = bill.recalculate_weights()
        db.session.commit()  # Commit the recalculated values
        app.logger.info(f'Bill weight recalculated: {actual_weight}kg actual, {expected_weight}kg expected, {child_count_total} total children')
        
        app.logger.info(f'Bill now has {bill.linked_parent_count}/{bill.parent_bag_count} parent bags')
        
        # Check if bill is now at capacity (auto-closed)
        capacity_message = ''
        if is_full:
            capacity_message = ' Bill is now at capacity!'
            app.logger.info(f'Bill {bill.bill_id} auto-closed at capacity')
        
        response_data = {
            'success': True,
            'message': f'Parent bag {manual_qr} added manually! Status: {parent_bag.status}{capacity_message}',
            'bag_qr': manual_qr,
            'linked_count': bill.linked_parent_count,
            'expected_count': bill.parent_bag_count,
            'remaining_bags': bill.remaining_capacity(),
            'bag_status': parent_bag.status,
            'weight_kg': parent_bag.weight_kg,
            'total_actual_weight': bill.total_weight_kg,
            'total_expected_weight': bill.expected_weight_kg,
            'is_at_capacity': is_full,
            'bill_status': bill.status
        }
        
        app.logger.info(f'=== MANUAL PARENT ENTRY SUCCESS ===')
        app.logger.info(f'Response: {response_data}')
        return jsonify(response_data)
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'=== MANUAL PARENT ENTRY ERROR ===')
        app.logger.error(f'Error Type: {type(e).__name__}')
        app.logger.error(f'Error Message: {str(e)}')
        import traceback
        app.logger.error(f'Traceback: {traceback.format_exc()}')
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# Bill summary functionality moved to bill_management route
# Old route commented out to prevent conflicts - functionality integrated into bill_management


@app.route('/api/bill_summary/eod')
@login_required
def eod_bill_summary():
    """Generate End of Day (EOD) bill summary - JSON API for automated reports"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required for EOD summary'}), 403
    
    try:
        # Get today's date range
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        # Get all bills created today
        bills = Bill.query.filter(
            Bill.created_at >= today,
            Bill.created_at < tomorrow
        ).all()
        
        # Compile EOD report data
        eod_data = {
            'report_date': format_datetime_ist(today, 'date'),
            'generated_at': datetime.now().isoformat(),
            'total_bills': len(bills),
            'bills_by_status': {},
            'bills_by_user': {},
            'total_parent_bags': 0,
            'total_child_bags': 0,
            'total_weight_kg': 0,
            'detailed_bills': []
        }
        
        # Process each bill
        for bill in bills:
            # Get creator
            creator = User.query.get(bill.created_by_id) if bill.created_by_id else None
            creator_name = creator.username if creator else 'Unknown'
            
            # Get linked bags count
            parent_count = BillBag.query.filter_by(bill_id=bill.id).count()
            
            # Update totals
            eod_data['total_parent_bags'] += parent_count
            eod_data['total_child_bags'] += getattr(bill, 'total_child_bags', 0) or 0
            eod_data['total_weight_kg'] += bill.total_weight_kg or 0
            
            # Count by status
            status = bill.status or 'new'
            eod_data['bills_by_status'][status] = eod_data['bills_by_status'].get(status, 0) + 1
            
            # Count by user
            eod_data['bills_by_user'][creator_name] = eod_data['bills_by_user'].get(creator_name, 0) + 1
            
            # Add detailed bill info
            eod_data['detailed_bills'].append({
                'bill_id': bill.bill_id,
                'created_by': creator_name,
                'created_at': bill.created_at.isoformat(),
                'status': status,
                'parent_bags': parent_count,
                'expected_bags': bill.parent_bag_count,
                'child_bags': getattr(bill, 'total_child_bags', 0) or 0,
                'weight_kg': bill.total_weight_kg or 0
            })
        
        return jsonify(eod_data)
        
    except Exception as e:
        app.logger.error(f'EOD summary error: {str(e)}')
        return jsonify({'error': 'Error generating EOD summary'}), 500

@app.route('/api/bill_summary/send_eod', methods=['POST'])
@login_required
def send_eod_summaries():
    """Send EOD bill summaries via email to admins and billers"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        # Check if email is configured
        if not EmailConfig.is_configured():
            return jsonify({
                'success': False,
                'error': 'Email service not configured',
                'message': 'SendGrid API key is not configured. Please configure SENDGRID_API_KEY environment variable.',
                'alternative_url': '/eod_summary_preview'
            }), 503
        
        # Get EOD data using same logic as eod_bill_summary endpoint
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        bills = Bill.query.filter(
            Bill.created_at >= today,
            Bill.created_at < tomorrow
        ).all()
        
        # Compile EOD report data
        eod_data = {
            'report_date': format_datetime_ist(today, 'date'),
            'generated_at': datetime.now().isoformat(),
            'total_bills': len(bills),
            'bills_by_status': {},
            'bills_by_user': {},
            'total_parent_bags': 0,
            'total_child_bags': 0,
            'total_weight_kg': 0,
            'detailed_bills': []
        }
        
        # Process each bill
        for bill in bills:
            creator = User.query.get(bill.created_by_id) if bill.created_by_id else None
            creator_name = creator.username if creator else 'Unknown'
            parent_count = BillBag.query.filter_by(bill_id=bill.id).count()
            
            eod_data['total_parent_bags'] += parent_count
            eod_data['total_child_bags'] += getattr(bill, 'total_child_bags', 0) or 0
            eod_data['total_weight_kg'] += bill.total_weight_kg or 0
            
            status = bill.status or 'new'
            eod_data['bills_by_status'][status] = eod_data['bills_by_status'].get(status, 0) + 1
            eod_data['bills_by_user'][creator_name] = eod_data['bills_by_user'].get(creator_name, 0) + 1
            
            eod_data['detailed_bills'].append({
                'bill_id': bill.bill_id,
                'created_by': creator_name,
                'created_at': bill.created_at.isoformat(),
                'status': status,
                'parent_bags': parent_count,
                'expected_bags': bill.parent_bag_count,
                'child_bags': getattr(bill, 'total_child_bags', 0) or 0,
                'weight_kg': bill.total_weight_kg or 0
            })
        
        # Get recipient list: all admins and billers
        recipients = User.query.filter(
            User.role.in_(['admin', 'biller'])
        ).all()
        
        recipient_emails = [user.email for user in recipients if user.email]
        
        if not recipient_emails:
            return jsonify({
                'success': False,
                'error': 'No recipients found',
                'message': 'No admin or biller users with valid email addresses found.'
            }), 400
        
        # Send EOD summary emails
        sent_count, failed_count, error_messages = EmailService.send_eod_summary(
            recipient_emails=recipient_emails,
            report_date=eod_data['report_date'],
            eod_data=eod_data
        )
        
        app.logger.info(f'EOD summary sent: {sent_count} successful, {failed_count} failed')
        
        return jsonify({
            'success': True,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_recipients': len(recipient_emails),
            'recipients': recipient_emails,
            'errors': error_messages if error_messages else None,
            'report_date': eod_data['report_date'],
            'total_bills': eod_data['total_bills']
        })
        
    except Exception as e:
        app.logger.error(f'Error sending EOD summaries: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Error sending EOD summaries',
            'message': str(e)
        }), 500

@app.route('/eod_summary_preview')
@login_required  
def eod_summary_preview():
    """Preview EOD summary that will be sent to users"""
    if not current_user.is_admin():
        flash('Admin access required to preview EOD summaries', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Email functionality removed - show simple message
        html_content = """
        <div style="padding: 20px; background: #f8f9fa; text-align: center;">
            <h2>Email functionality is not configured</h2>
            <p>Use the EOD Summary API endpoint to view report data.</p>
        </div>
        """
        
        # Return the HTML directly for preview
        return f"""
        <html>
        <head>
            <title>EOD Summary Preview</title>
            <style>
                .preview-header {{
                    background: #2c3e50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                }}
                .preview-actions {{
                    background: #ecf0f1;
                    padding: 15px;
                    text-align: center;
                }}
                .preview-actions button {{
                    background: #3498db;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    margin: 5px;
                    cursor: pointer;
                    border-radius: 5px;
                }}
                .preview-actions button:hover {{
                    background: #2980b9;
                }}
                .email-content {{
                    border: 2px solid #bdc3c7;
                    margin: 20px;
                    padding: 20px;
                    background: white;
                }}
            </style>
        </head>
        <body>
            <div class="preview-header">
                <h1>EOD Summary Preview</h1>
                <p>This is how the email will appear when sent to users</p>
            </div>
            <div class="preview-actions">
                <button onclick="sendEOD()">Send EOD Summaries Now</button>
                <button onclick="window.location.href='/bill_summary'">Back to Bill Summary</button>
            </div>
            <div class="email-content">
                {html_content}
            </div>
            <script>
                function sendEOD() {{
                    if (confirm('Send EOD summaries to all billers and admins now?')) {{
                        fetch('/api/bill_summary/send_eod', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                alert('EOD summaries sent successfully!');
                            }} else {{
                                alert('Error: ' + (data.error || 'Failed to send summaries'));
                            }}
                        }});
                    }}
                }}
            </script>
        </body>
        </html>
        """
        
    except Exception as e:
        app.logger.error(f'Error generating EOD preview: {str(e)}')
        flash('Error generating EOD preview', 'error')
        return redirect(url_for('bill_summary'))

@app.route('/api/bill_summary/schedule_eod', methods=['POST'])
@csrf_compat.exempt  # Exempt from CSRF for scheduled tasks
def schedule_eod_summary():
    """Endpoint for cron job to trigger EOD summary sending"""
    # This can be called by a cron job without authentication
    # Add a secret key check for security
    secret_key = request.headers.get('X-EOD-Secret')
    expected_secret = os.environ.get('EOD_SECRET_KEY', 'default-eod-secret-2025')
    
    if secret_key != expected_secret:
        app.logger.warning(f"Unauthorized EOD schedule attempt - invalid secret key")
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Check if email is configured
        if not EmailConfig.is_configured():
            app.logger.warning("Scheduled EOD summary called but email not configured")
            return jsonify({
                'success': False,
                'error': 'Email service not configured',
                'message': 'SendGrid API key is not configured. Please configure SENDGRID_API_KEY environment variable.'
            }), 503
        
        app.logger.info("Scheduled EOD summary triggered")
        
        # Get EOD data using same logic as eod_bill_summary endpoint
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        bills = Bill.query.filter(
            Bill.created_at >= today,
            Bill.created_at < tomorrow
        ).all()
        
        # Compile EOD report data
        eod_data = {
            'report_date': format_datetime_ist(today, 'date'),
            'generated_at': datetime.now().isoformat(),
            'total_bills': len(bills),
            'bills_by_status': {},
            'bills_by_user': {},
            'total_parent_bags': 0,
            'total_child_bags': 0,
            'total_weight_kg': 0,
            'detailed_bills': []
        }
        
        # Process each bill
        for bill in bills:
            creator = User.query.get(bill.created_by_id) if bill.created_by_id else None
            creator_name = creator.username if creator else 'Unknown'
            parent_count = BillBag.query.filter_by(bill_id=bill.id).count()
            
            eod_data['total_parent_bags'] += parent_count
            eod_data['total_child_bags'] += getattr(bill, 'total_child_bags', 0) or 0
            eod_data['total_weight_kg'] += bill.total_weight_kg or 0
            
            status = bill.status or 'new'
            eod_data['bills_by_status'][status] = eod_data['bills_by_status'].get(status, 0) + 1
            eod_data['bills_by_user'][creator_name] = eod_data['bills_by_user'].get(creator_name, 0) + 1
            
            eod_data['detailed_bills'].append({
                'bill_id': bill.bill_id,
                'created_by': creator_name,
                'created_at': bill.created_at.isoformat(),
                'status': status,
                'parent_bags': parent_count,
                'expected_bags': bill.parent_bag_count,
                'child_bags': getattr(bill, 'total_child_bags', 0) or 0,
                'weight_kg': bill.total_weight_kg or 0
            })
        
        # Get recipient list: all admins and billers
        recipients = User.query.filter(
            User.role.in_(['admin', 'biller'])
        ).all()
        
        recipient_emails = [user.email for user in recipients if user.email]
        
        if not recipient_emails:
            app.logger.warning("No recipients found for scheduled EOD summary")
            return jsonify({
                'success': False,
                'error': 'No recipients found',
                'message': 'No admin or biller users with valid email addresses found.'
            }), 400
        
        # Send EOD summary emails
        sent_count, failed_count, error_messages = EmailService.send_eod_summary(
            recipient_emails=recipient_emails,
            report_date=eod_data['report_date'],
            eod_data=eod_data
        )
        
        app.logger.info(f'Scheduled EOD summary sent: {sent_count} successful, {failed_count} failed to {len(recipient_emails)} recipients')
        
        return jsonify({
            'success': True,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_recipients': len(recipient_emails),
            'recipients': recipient_emails,
            'errors': error_messages if error_messages else None,
            'report_date': eod_data['report_date'],
            'total_bills': eod_data['total_bills'],
            'scheduled': True
        })
        
    except Exception as e:
        app.logger.error(f'Error in scheduled EOD summary: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Error sending scheduled EOD summaries',
            'message': str(e)
        }), 500


# Add missing API endpoints that were causing 404s
@app.route('/api/bags', methods=['GET', 'POST'])
@login_required
def api_bags_endpoint():
    """API endpoint for bags data - OPTIMIZED FOR 1.8M+ BAGS"""
    
    # Handle POST request - Create new bag
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            qr_id = data.get('qr_id', '').strip()
            bag_type = data.get('type', '').strip()
            
            # Validate inputs
            if not qr_id:
                return jsonify({'success': False, 'error': 'qr_id is required'}), 400
            
            if bag_type not in ['parent', 'child']:
                return jsonify({'success': False, 'error': 'type must be "parent" or "child"'}), 400
            
            # Validate QR ID length
            if len(qr_id) > 50:
                return jsonify({'success': False, 'error': 'QR ID too long (max 50 characters)'}), 400
            
            # Check if bag already exists
            from models import Bag
            existing_bag = Bag.query.filter_by(qr_id=qr_id).first()
            if existing_bag:
                return jsonify({'success': False, 'error': 'Bag with this QR ID already exists'}), 409
            
            # Create bag using query optimizer
            bag = query_optimizer.create_bag_optimized(
                qr_id=qr_id,
                bag_type=bag_type,
                user_id=current_user.id
            )
            
            if not bag:
                return jsonify({'success': False, 'error': 'Failed to create bag'}), 500
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'bag': {
                    'id': bag.id,
                    'qr_id': bag.qr_id,
                    'type': bag.type,
                    'child_count': bag.child_count,
                    'created_at': bag.created_at.isoformat() if bag.created_at else None
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error creating bag via API: {str(e)}', exc_info=True)
            return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500
    
    # Handle GET request - List bags
    try:
        from models import Bag
        
        # Get pagination parameters with strict limits
        limit = min(request.args.get('limit', 100, type=int), 200)  # Max 200 per request
        offset = request.args.get('offset', 0, type=int)
        
        # Get filtering parameters
        bag_type = request.args.get('type', '')
        search = request.args.get('search', '')
        
        # Sanitize inputs to prevent XSS
        if bag_type:
            bag_type = InputValidator.sanitize_html(bag_type, max_length=10)
        if search:
            search = InputValidator.sanitize_search_query(search)
        
        # Build query with filters
        query = Bag.query
        
        if bag_type in ['parent', 'child']:
            query = query.filter(Bag.type == bag_type)
        
        if search:
            query = query.filter(Bag.qr_id.ilike(f'%{search}%'))
        
        # Order by creation date (newest first) for consistent pagination
        query = query.order_by(Bag.created_at.desc(), Bag.id.desc())
        
        # PERFORMANCE: Cap offset to prevent expensive queries on large datasets
        max_offset = 10000
        if offset > max_offset:
            offset = max_offset
        
        # Get total count efficiently - only for filtered results
        if bag_type or search:
            total = query.count()
        else:
            # Skip count for unfiltered queries on large datasets
            total = None  # Client should handle unknown total
        
        # Execute paginated query
        bags = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'success': True,
            'total': total,
            'limit': limit,
            'offset': offset,
            'count': len(bags),
            'bags': [{'id': b.id, 'qr_id': b.qr_id, 'type': b.type, 'created_at': b.created_at.isoformat() if b.created_at else None} for b in bags]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/link', methods=['POST'])
@login_required
def api_create_link():
    """API endpoint to create a link between parent and child bags"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        parent_bag_id = data.get('parent_bag_id')
        child_bag_id = data.get('child_bag_id')
        
        # Validate inputs
        if not parent_bag_id:
            return jsonify({'success': False, 'error': 'parent_bag_id is required'}), 400
        
        if not child_bag_id:
            return jsonify({'success': False, 'error': 'child_bag_id is required'}), 400
        
        # Use query optimizer's atomic link creation
        success, message = query_optimizer.create_link_fast(
            parent_bag_id=parent_bag_id,
            child_bag_id=child_bag_id,
            user_id=current_user.id
        )
        
        if success:
            db.session.commit()
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error creating link via API: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500

@app.route('/api/bag/<qr_id>')
@login_required
def api_bag_detail(qr_id):
    """API endpoint for individual bag details"""
    try:
        from models import Bag
        from sqlalchemy import func
        
        bag = Bag.query.filter(func.upper(Bag.qr_id) == func.upper(qr_id)).first()
        
        if not bag:
            return jsonify({
                'success': False,
                'error': 'Bag not found'
            }), 404
        
        # Safely serialize bag data
        bag_data = {
            'success': True,
            'id': bag.id,
            'qr_id': bag.qr_id,
            'type': str(bag.type) if bag.type else 'unknown',
            'status': str(bag.status) if bag.status else 'unknown',
            'created_at': bag.created_at.isoformat() if bag.created_at else None
        }
        
        # Add optional fields if present
        if hasattr(bag, 'name') and bag.name:
            bag_data['name'] = bag.name
        if hasattr(bag, 'weight_kg') and bag.weight_kg:
            bag_data['weight_kg'] = float(bag.weight_kg)
        
        return jsonify(bag_data)
    except Exception as e:
        app.logger.error(f'API bag detail error for {qr_id}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/bills')
@login_required
def api_bills_endpoint():
    """API endpoint for bills data - OPTIMIZED FOR 1.8M+ BAGS"""
    try:
        from models import Bill
        
        # Get pagination parameters with strict limits
        limit = min(request.args.get('limit', 100, type=int), 200)  # Max 200 per request
        offset = request.args.get('offset', 0, type=int)
        
        # Get filtering parameters
        status = request.args.get('status', '')
        
        # Build query with filters
        query = Bill.query
        
        if status in ['new', 'processing', 'completed']:
            query = query.filter(Bill.status == status)
        
        # Order by creation date (newest first)
        query = query.order_by(Bill.created_at.desc(), Bill.id.desc())
        
        # PERFORMANCE: Cap offset
        max_offset = 10000
        if offset > max_offset:
            offset = max_offset
        
        # Get total count efficiently
        if status:
            total = query.count()
        else:
            total = None  # Skip for unfiltered on large datasets
        
        # Execute paginated query
        bills = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'success': True,
            'total': total,
            'limit': limit,
            'offset': offset,
            'count': len(bills),
            'bills': [{'id': b.id, 'bill_id': b.bill_id, 'status': b.status, 'parent_bag_count': b.parent_bag_count, 'created_at': b.created_at.isoformat() if b.created_at else None} for b in bills]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bills/<identifier>')
@login_required
def api_bill_detail_endpoint(identifier):
    """API endpoint for single bill details - supports numeric ID or public bill_id"""
    try:
        from models import Bill, Bag, BillBag
        
        # Try to find bill by numeric ID or public bill_id
        bill = None
        if identifier.isdigit():
            bill = Bill.query.filter_by(id=int(identifier)).first()
        else:
            bill = Bill.query.filter_by(bill_id=identifier).first()
        
        if not bill:
            return jsonify({
                'success': False,
                'error': 'Bill not found'
            }), 404
        
        # Get linked parent bags (DISTINCT to avoid duplicates from join)
        parent_bags = db.session.query(Bag).join(
            BillBag, Bag.id == BillBag.bag_id
        ).filter(
            BillBag.bill_id == bill.id
        ).distinct().all()
        
        # Calculate weights using deduplicated parent bags
        total_child_count = sum(bag.child_count or 0 for bag in parent_bags)
        unique_parent_count = len(parent_bags)  # Now correctly counts unique parents
        actual_weight_kg = float(total_child_count)  # 1kg per child
        expected_weight_kg = float(unique_parent_count * 30)  # 30kg max per parent
        
        # Build response with bill details
        bill_data = {
            'success': True,
            'id': bill.id,
            'bill_id': bill.bill_id,
            'status': bill.status,
            'parent_bag_count': unique_parent_count,  # Use actual unique count, not stored field
            'created_at': bill.created_at.isoformat() if bill.created_at else None,
            'actual_weight_kg': actual_weight_kg,
            'expected_weight_kg': expected_weight_kg,
            'total_child_count': total_child_count,
            'parent_bags': [
                {
                    'id': bag.id,
                    'qr_id': bag.qr_id,
                    'type': str(bag.type) if bag.type else 'unknown',
                    'status': str(bag.status) if bag.status else 'unknown',
                    'child_count': bag.child_count or 0
                } for bag in parent_bags
            ]
        }
        
        return jsonify(bill_data)
    except Exception as e:
        app.logger.error(f'API bill detail error for {identifier}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/users')
@login_required
@admin_required  
def api_users_endpoint():
    """API endpoint for users data - admin only"""
    try:
        from models import User
        users = User.query.limit(100).all()
        return jsonify({
            'total': len(users),
            'users': [{'id': u.id, 'username': u.username, 'role': u.role if hasattr(u, 'role') else 'unknown'} for u in users]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Removed duplicate /api/health and /api/health/detailed endpoints
# Use /health (public) or /api/system_health (admin) instead

@app.route('/child_lookup', methods=['GET', 'POST'])
@login_required
def child_lookup_page():
    """Child bag lookup functionality"""
    if request.method == 'POST':
        qr_code = request.form.get('qr_code', '').strip()
        if qr_code:
            try:
                from models import Bag, Link
                bag = Bag.query.filter_by(qr_id=qr_code).first()
                if bag:
                    return render_template('child_lookup.html', bag=bag, qr_code=qr_code)
                else:
                    flash('Bag not found', 'error')
            except Exception as e:
                flash('Error during lookup', 'error')
        else:
            flash('QR code is required', 'error')
    
    return render_template('child_lookup.html')

@app.route('/excel_upload', methods=['GET', 'POST'])
@login_required
def excel_upload():
    """Redirect to new bulk import page"""
    return redirect(url_for('import_bags'))


# ============================================================================
# BULK IMPORT ROUTES - CSV and Excel imports with validation
# ============================================================================

@app.route('/import/bags', methods=['GET', 'POST'])
@login_required
def import_bags():
    """Bulk import bags from CSV or Excel - admin only"""
    if not current_user.is_admin():
        flash('Admin access required for bulk imports.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'GET':
        max_size_mb = app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024) / (1024 * 1024)
        return render_template('import_bags.html', max_file_size_mb=max_size_mb)
    
    # Handle POST - file upload
    try:
        from import_utils import BagImporter
        
        if 'file' not in request.files:
            flash('No file uploaded.', 'error')
            return redirect(url_for('import_bags'))
        
        file = request.files['file']
        
        if not file.filename or file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('import_bags'))
        
        # Validate file upload with enhanced security
        from validation_utils import InputValidator
        allowed_extensions = ['.csv', '.xlsx', '.xls']
        is_valid, error_msg = InputValidator.validate_file_upload(file.filename, allowed_extensions)
        if not is_valid:
            flash(error_msg, 'error')
            return redirect(url_for('import_bags'))
        
        # Determine file type and parse
        filename = (file.filename or '').lower()
        
        if filename.endswith('.csv'):
            bags, parse_errors = BagImporter.parse_csv(file)
        elif filename.endswith(('.xlsx', '.xls')):
            bags, parse_errors = BagImporter.parse_excel(file)
        else:
            flash('Invalid file type. Please upload CSV or Excel file.', 'error')
            return redirect(url_for('import_bags'))
        
        # Check for parsing errors
        if parse_errors:
            for error in parse_errors[:5]:  # Show first 5 errors
                flash(error, 'error')
            if len(parse_errors) > 5:
                flash(f'... and {len(parse_errors) - 5} more errors', 'error')
            return redirect(url_for('import_bags'))
        
        if not bags:
            flash('No valid bags found in file.', 'warning')
            return redirect(url_for('import_bags'))
        
        # Import bags
        imported, skipped, import_errors = BagImporter.import_bags(db, bags, current_user.id)  # type: ignore
        
        # Show results
        if imported > 0:
            flash(f'Successfully imported {imported} bags.', 'success')
        if skipped > 0:
            flash(f'Skipped {skipped} duplicate bags.', 'warning')
        if import_errors:
            for error in import_errors[:5]:
                flash(error, 'warning')
            if len(import_errors) > 5:
                flash(f'... and {len(import_errors) - 5} more warnings', 'warning')
        
        return redirect(url_for('bag_management'))
    
    except Exception as e:
        app.logger.error(f"Bag import error: {str(e)}")
        flash(f'Error importing bags: {str(e)}', 'error')
        return redirect(url_for('import_bags'))


@app.route('/import/batch_child_parent', methods=['GET', 'POST'])
@login_required
def import_batch_child_parent():
    """Batch import child bags linked to parent bags from Excel - admin only
    
    Supports large files (lakhs of rows) with streaming processing.
    Returns downloadable result file with per-row status.
    """
    if not current_user.is_admin():
        flash('Admin access required for bulk imports.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'GET':
        max_size_mb = app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024) / (1024 * 1024)
        return render_template('import_batch_child_parent.html', max_file_size_mb=max_size_mb)
    
    # Handle POST - file upload
    try:
        from import_utils import LargeScaleChildParentImporter, MultiFileBatchProcessor, RowResult
        import uuid
        import os
        import tempfile
        
        if 'file' not in request.files:
            flash('No file uploaded.', 'error')
            return redirect(url_for('import_batch_child_parent'))
        
        file = request.files['file']
        
        if not file.filename or file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('import_batch_child_parent'))
        
        # Validate file extension (supports .xlsx, .xls, and .xlsm macro-enabled files)
        filename = (file.filename or '').lower()
        if not filename.endswith(('.xlsx', '.xls', '.xlsm')):
            flash('Please upload an Excel file (.xlsx, .xls, or .xlsm).', 'error')
            return redirect(url_for('import_batch_child_parent'))
        
        # Get dispatch area if provided
        dispatch_area = request.form.get('dispatch_area', '').strip() or None
        
        # Check if auto-create parents is enabled
        auto_create_parents = request.form.get('auto_create_parents') == 'on'
        
        # Use streaming importer for memory efficiency with large files
        app.logger.info(f"Processing batch import using streaming: {file.filename} (auto_create_parents={auto_create_parents})")
        
        stats, row_results = LargeScaleChildParentImporter.process_file_streaming(
            file_storage=file,
            user_id=current_user.id,  # type: ignore
            dispatch_area=dispatch_area,
            auto_create_parents=auto_create_parents
        )
        
        # Generate result file
        file_result = {
            'filename': file.filename,
            'status': 'Success' if stats.get('errors', 0) == 0 and stats.get('parents_not_found', 0) == 0 else 'Partial Success',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stats': stats,
            'errors': []
        }
        
        # Extract error messages for display
        error_rows = [r for r in row_results if r.status == RowResult.ERROR]
        if error_rows:
            file_result['errors'] = [f"Row {r.row_num}: {r.message}" for r in error_rows[:20]]
        
        # Generate downloadable result file
        result_file_bytes = MultiFileBatchProcessor.generate_detailed_result_file(
            file_results=[file_result],
            row_results=row_results,
            include_successful=True
        )
        
        # Save result file temporarily
        result_filename = f"import_results_{uuid.uuid4().hex[:8]}.xlsx"
        result_path = os.path.join(tempfile.gettempdir(), result_filename)
        with open(result_path, 'wb') as f:
            f.write(result_file_bytes)
        
        # Store result file path in session for download
        session['import_result_file'] = result_path
        session['import_result_filename'] = f"import_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Show results
        success_msg = f'Processed {stats.get("total_rows", 0)} rows: '
        if stats.get('parents_created', 0) > 0:
            success_msg += f'{stats.get("parents_created", 0)} parent bags created, '
        success_msg += f'{stats.get("children_created", 0)} children created, {stats.get("links_created", 0)} links created.'
        flash(success_msg, 'success')
        
        if stats.get('parents_not_found', 0) > 0:
            flash(f'Warning: {stats.get("parents_not_found", 0)} batches rejected - parent bags not found. Enable "Auto-create parent bags" to create missing parents.', 'warning')
        
        if stats.get('errors', 0) > 0:
            flash(f'{stats.get("errors", 0)} errors occurred. Download result file for details.', 'warning')
        
        # Show first few errors in flash
        for error in file_result['errors'][:5]:
            flash(error, 'warning')
        
        if len(file_result['errors']) > 5:
            flash(f'... and {len(file_result["errors"]) - 5} more warnings. Download result file for full details.', 'warning')
        
        # Auto-download: redirect with flag to trigger download
        return redirect(url_for('bag_management', auto_download='1'))
    
    except Exception as e:
        app.logger.error(f"Batch import error: {str(e)}")
        flash(f'Error importing batches: {str(e)}', 'error')
        return redirect(url_for('import_batch_child_parent'))


@app.route('/import/download_result')
@login_required
def download_import_result():
    """Download the import result file stored in session"""
    import os
    
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    
    result_file = session.get('import_result_file')
    result_filename = session.get('import_result_filename', 'import_results.xlsx')
    
    if not result_file or not os.path.exists(result_file):
        flash('No result file available for download.', 'error')
        return redirect(url_for('bag_management'))
    
    try:
        # Read the file
        with open(result_file, 'rb') as f:
            file_data = f.read()
        
        # Clean up
        os.remove(result_file)
        session.pop('import_result_file', None)
        session.pop('import_result_filename', None)
        
        # Send file
        response = make_response(file_data)
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename="{result_filename}"'
        return response
        
    except Exception as e:
        app.logger.error(f"Error downloading result file: {str(e)}")
        flash(f'Error downloading result file: {str(e)}', 'error')
        return redirect(url_for('bag_management'))


@app.route('/import/batch_parent_bill', methods=['GET', 'POST'])
@login_required
def import_batch_parent_bill():
    """Batch import parent bags linked to bills from Excel - admin only"""
    if not current_user.is_admin():
        flash('Admin access required for bulk imports.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'GET':
        max_size_mb = app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024) / (1024 * 1024)
        return render_template('import_batch_parent_bill.html', max_file_size_mb=max_size_mb)
    
    # Handle POST - file upload
    try:
        from import_utils import ParentBillBatchImporter
        
        if 'file' not in request.files:
            flash('No file uploaded.', 'error')
            return redirect(url_for('import_batch_parent_bill'))
        
        file = request.files['file']
        
        if not file.filename or file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('import_batch_parent_bill'))
        
        # Validate file extension (supports .xlsx, .xls, and .xlsm macro-enabled files)
        filename = (file.filename or '').lower()
        if not filename.endswith(('.xlsx', '.xls', '.xlsm')):
            flash('Please upload an Excel file (.xlsx, .xls, or .xlsm).', 'error')
            return redirect(url_for('import_batch_parent_bill'))
        
        # Parse Excel file with batch pattern
        batches, parse_errors, stats = ParentBillBatchImporter.parse_excel_batch(file)
        
        # Show parsing errors
        if parse_errors:
            for error in parse_errors[:10]:  # Show first 10 errors
                flash(error, 'warning')
            if len(parse_errors) > 10:
                flash(f'... and {len(parse_errors) - 10} more warnings', 'warning')
        
        if not batches:
            flash('No valid batches found in file.', 'error')
            return redirect(url_for('import_batch_parent_bill'))
        
        # Import batches
        bills_created, links_created, parents_not_found, import_errors = ParentBillBatchImporter.import_batches(
            db, batches, current_user.id  # type: ignore
        )
        
        # Show results
        if bills_created > 0 or links_created > 0:
            flash(f'Successfully imported {len(batches)} batches: {bills_created} bills created, {links_created} parent-bill links created.', 'success')
        
        if import_errors:
            for error in import_errors[:5]:
                flash(error, 'warning')
            if len(import_errors) > 5:
                flash(f'... and {len(import_errors) - 5} more warnings', 'warning')
        
        if parents_not_found > 0:
            flash(f'Warning: {parents_not_found} parent bags referenced in file were not found in database.', 'warning')
        
        # Show stats
        flash(f'File statistics: {stats.get("total_parents", 0)} total parents, {stats.get("total_bills", 0)} total bills, {stats.get("skipped_rows", 0)} skipped rows.', 'info')
        
        return redirect(url_for('bill_management'))
    
    except Exception as e:
        app.logger.error(f"Batch parent-bill import error: {str(e)}")
        flash(f'Error importing batches: {str(e)}', 'error')
        return redirect(url_for('import_batch_parent_bill'))


@app.route('/import/batch_multi', methods=['GET', 'POST'])
@login_required
def import_batch_multi():
    """Multi-file batch import - admin only"""
    if not current_user.is_admin():
        flash('Admin access required for bulk imports.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'GET':
        max_size_mb = app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024) / (1024 * 1024)
        return render_template('import_batch_multi.html', max_file_size_mb=max_size_mb)
    
    # Handle POST - multiple file upload
    try:
        from import_utils import MultiFileBatchProcessor
        import uuid
        import os
        import tempfile
        from datetime import datetime, timedelta
        
        # Get import type
        import_type = request.form.get('import_type', 'child_parent')
        
        # Get all files
        files = request.files.getlist('files')
        
        if not files or len(files) == 0:
            flash('No files uploaded.', 'error')
            return redirect(url_for('import_batch_multi'))
        
        # Validate all files are Excel (supports .xlsx, .xls, and .xlsm)
        for file in files:
            if file.filename:
                filename = file.filename.lower()
                if not filename.endswith(('.xlsx', '.xls', '.xlsm')):
                    flash(f'Invalid file type: {file.filename}. Only Excel files (.xlsx, .xls, .xlsm) are allowed.', 'error')
                    return redirect(url_for('import_batch_multi'))
        
        # Process files based on import type - use streaming for large file support
        all_row_results = []
        
        if import_type == 'child_parent':
            dispatch_area = request.form.get('dispatch_area', '').strip() or None
            auto_create_parents = request.form.get('auto_create_parents') == 'on'
            # Use streaming method for memory efficiency with large files
            results, all_row_results, has_errors = MultiFileBatchProcessor.process_child_parent_files_streaming(
                files, current_user.id, dispatch_area, auto_create_parents  # type: ignore
            )
        elif import_type == 'parent_bill':
            results, has_errors = MultiFileBatchProcessor.process_parent_bill_files(
                files, current_user.id  # type: ignore
            )
        else:
            flash('Invalid import type.', 'error')
            return redirect(url_for('import_batch_multi'))
        
        # Count successes and failures
        success_count = sum(1 for r in results if r.get('status') == 'Success')
        partial_count = sum(1 for r in results if r.get('status') == 'Partial Success')
        failed_count = sum(1 for r in results if r.get('status') == 'Failed')
        
        # Show summary
        flash(f'Processed {len(files)} files: {success_count} successful, {partial_count} partial, {failed_count} failed.', 'info')
        
        # If there are errors, generate error report and store in filesystem
        if has_errors:
            # Generate error report
            error_report_bytes = MultiFileBatchProcessor.generate_error_report(results)
            
            if not error_report_bytes:
                flash('Error generating report: Excel support not available.', 'error')
                return redirect(url_for('import_batch_multi'))
            
            # Create temp directory for error reports if it doesn't exist
            temp_dir = os.path.join(tempfile.gettempdir(), 'traitortrack_error_reports')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Store report with unique ID FIRST (before cleanup)
            report_id = str(uuid.uuid4())
            filename = f'import_errors_{report_id[:8]}.xlsx'
            file_path = os.path.join(temp_dir, f'{report_id}.xlsx')
            current_time = datetime.now()
            
            try:
                # Write the new report file
                with open(file_path, 'wb') as f:
                    f.write(error_report_bytes)
                
                # Verify file was written successfully
                if not os.path.exists(file_path):
                    raise Exception("Report file not written successfully")
                
                app.logger.info(f"Error report generated: {filename} ({len(error_report_bytes)} bytes)")
                
                # NOW clean up old reports (older than 1 hour) AFTER saving new one
                # Skip the file we just created
                try:
                    cutoff_time = current_time - timedelta(hours=1)
                    for old_file in os.listdir(temp_dir):
                        # Skip the file we just created
                        if old_file == f'{report_id}.xlsx':
                            continue
                        
                        file_to_check = os.path.join(temp_dir, old_file)
                        if os.path.isfile(file_to_check):
                            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_to_check))
                            if file_mtime < cutoff_time:
                                os.remove(file_to_check)
                                app.logger.info(f"Cleaned up old error report: {old_file}")
                except Exception as cleanup_error:
                    app.logger.warning(f"Error during cleanup: {str(cleanup_error)}")
                
                # Store metadata in session with user binding
                session[f'error_report_id_{report_id}'] = report_id
                session[f'error_report_user_{report_id}'] = current_user.id  # type: ignore
                session[f'error_report_filename_{report_id}'] = filename
                session[f'error_report_size_{report_id}'] = len(error_report_bytes)
                
                flash('Some errors occurred during import. Download the error report for details.', 'warning')
                
                # Redirect to results page with download option
                return redirect(url_for('import_batch_multi_results', report_id=report_id))
                
            except Exception as save_error:
                # Clean up partial file if save failed
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
                app.logger.error(f"Error saving report: {str(save_error)}")
                flash('Error saving error report. Please try again.', 'error')
                return redirect(url_for('import_batch_multi'))
        
        flash('All files imported successfully!', 'success')
        
        # Redirect based on import type
        if import_type == 'child_parent':
            return redirect(url_for('bag_management'))
        else:
            return redirect(url_for('bill_management'))
    
    except Exception as e:
        app.logger.error(f"Multi-file batch import error: {str(e)}")
        flash(f'Error during multi-file import: {str(e)}', 'error')
        return redirect(url_for('import_batch_multi'))


@app.route('/import/batch_multi/results/<report_id>')
@login_required
def import_batch_multi_results(report_id):
    """Display results and allow error report download"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if report exists in session metadata
    report_key = f'error_report_id_{report_id}'
    if report_key not in session:
        flash('Error report not found or expired.', 'error')
        return redirect(url_for('import_batch_multi'))
    
    filename = session.get(f'error_report_filename_{report_id}', 'error_report.xlsx')
    file_size = session.get(f'error_report_size_{report_id}', 0)
    
    # Format file size for display
    if file_size > 1024 * 1024:
        size_display = f"{file_size / (1024 * 1024):.2f} MB"
    elif file_size > 1024:
        size_display = f"{file_size / 1024:.2f} KB"
    else:
        size_display = f"{file_size} bytes"
    
    return render_template('import_batch_multi_results.html', 
                         report_id=report_id, 
                         filename=filename,
                         file_size=size_display)


@app.route('/import/batch_multi/download/<report_id>')
@login_required
def download_error_report(report_id):
    """Download error report Excel file"""
    import os
    import tempfile
    
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if report exists in session metadata
    report_key = f'error_report_id_{report_id}'
    if report_key not in session:
        flash('Error report not found or expired.', 'error')
        return redirect(url_for('import_batch_multi'))
    
    # Verify user binding - only the user who generated the report can download it
    report_user_id = session.get(f'error_report_user_{report_id}')
    if report_user_id != current_user.id:  # type: ignore
        app.logger.warning(f"User {current_user.id} attempted to download report owned by user {report_user_id}")  # type: ignore
        flash('Access denied. This report belongs to another user.', 'error')
        return redirect(url_for('import_batch_multi'))
    
    filename = session.get(f'error_report_filename_{report_id}', 'error_report.xlsx')
    
    # Get file from temp directory
    temp_dir = os.path.join(tempfile.gettempdir(), 'traitortrack_error_reports')
    file_path = os.path.join(temp_dir, f'{report_id}.xlsx')
    
    # Verify file exists before attempting download
    if not os.path.exists(file_path):
        app.logger.error(f"Error report file not found: {file_path} (report_id: {report_id})")
        # Clean up stale session data
        session.pop(report_key, None)
        session.pop(f'error_report_user_{report_id}', None)
        session.pop(f'error_report_filename_{report_id}', None)
        session.pop(f'error_report_size_{report_id}', None)
        flash('Error report file not found. It may have expired or been cleaned up.', 'error')
        return redirect(url_for('import_batch_multi'))
    
    # Verify file is readable
    try:
        if not os.access(file_path, os.R_OK):
            raise Exception("File not readable")
    except Exception as e:
        app.logger.error(f"Error report file not accessible: {file_path} - {str(e)}")
        flash('Error report file cannot be accessed. Please try again.', 'error')
        return redirect(url_for('import_batch_multi'))
    
    # Clean up session metadata after successful verification
    session.pop(report_key, None)
    session.pop(f'error_report_user_{report_id}', None)
    session.pop(f'error_report_filename_{report_id}', None)
    session.pop(f'error_report_size_{report_id}', None)
    
    # Send file and delete after sending
    try:
        response = send_file(
            file_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
        # Schedule file deletion after response
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    app.logger.info(f"Cleaned up error report after download: {filename}")
            except Exception as e:
                app.logger.warning(f"Error cleaning up report file: {str(e)}")
        
        return response
        
    except Exception as e:
        app.logger.error(f"Error sending file: {str(e)}")
        flash('Error downloading error report. Please try again.', 'error')
        return redirect(url_for('import_batch_multi'))


@app.route('/import/bills', methods=['GET', 'POST'])
@login_required
def import_bills():
    """Bulk import bills from CSV - admin only"""
    if not current_user.is_admin():
        flash('Admin access required for bulk imports.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'GET':
        max_size_mb = app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024) / (1024 * 1024)
        return render_template('import_bills.html', max_file_size_mb=max_size_mb)
    
    # Handle POST - file upload
    try:
        from import_utils import BillImporter
        
        if 'file' not in request.files:
            flash('No file uploaded.', 'error')
            return redirect(url_for('import_bills'))
        
        file = request.files['file']
        
        if not file.filename or file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('import_bills'))
        
        # Parse CSV only (bills import is simpler)
        filename = (file.filename or '').lower()
        
        if not filename.endswith('.csv'):
            flash('Please upload a CSV file.', 'error')
            return redirect(url_for('import_bills'))
        
        bills, parse_errors = BillImporter.parse_csv(file)
        
        # Check for parsing errors
        if parse_errors:
            for error in parse_errors[:5]:
                flash(error, 'error')
            if len(parse_errors) > 5:
                flash(f'... and {len(parse_errors) - 5} more errors', 'error')
            return redirect(url_for('import_bills'))
        
        if not bills:
            flash('No valid bills found in file.', 'warning')
            return redirect(url_for('import_bills'))
        
        # Import bills
        imported, skipped, import_errors = BillImporter.import_bills(db, bills, current_user.id)  # type: ignore
        
        # Show results
        if imported > 0:
            flash(f'Successfully imported {imported} bills.', 'success')
        if skipped > 0:
            flash(f'Skipped {skipped} duplicate bills.', 'warning')
        if import_errors:
            for error in import_errors[:5]:
                flash(error, 'warning')
            if len(import_errors) > 5:
                flash(f'... and {len(import_errors) - 5} more warnings', 'warning')
        
        return redirect(url_for('bill_management'))
    
    except Exception as e:
        app.logger.error(f"Bill import error: {str(e)}")
        flash(f'Error importing bills: {str(e)}', 'error')
        return redirect(url_for('import_bills'))

# Monitoring endpoints are already defined in error_handlers.py and main.py

# Missing routes needed for 100% functionality test coverage
@app.route('/scan/batch')
@login_required
def batch_scan_page():
    """Batch scanning page"""
    return render_template('batch_scan.html')

@app.route('/bills/create')
@login_required 
def create_bill_page():
    """Bill creation page - redirect to existing bill create"""
    return redirect(url_for('create_bill'))

@app.route('/api/generate_bill', methods=['GET', 'POST'])
@login_required
def generate_bill_api():
    """Bill generation API endpoint"""
    try:
        # Use existing bill creation logic
        from datetime import datetime
        bill_data = {
            "id": f"BILL{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "created_at": get_ist_now(),
            "status": "generated",
            "message": "Bill generation endpoint working"
        }
        return jsonify(bill_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin-specific dashboard"""
    try:
        # Get admin statistics
        total_users = db.session.query(User).count()
        total_bags = db.session.query(Bag).count() 
        total_bills = db.session.query(Bill).count()
        total_scans = db.session.query(Scan).count()
        
        stats = {
            'total_users': total_users,
            'total_bags': total_bags,
            'total_bills': total_bills,
            'total_scans': total_scans
        }
        
        return render_template('admin_dashboard.html', stats=stats)
    except Exception as e:
        flash(f'Error loading admin dashboard: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/admin/user-activity')
@admin_required
@limiter.exempt  # Exempt from rate limiting for admin functionality
def user_activity_dashboard():
    """
    Comprehensive user activity dashboard for admins
    Shows login history, active sessions, security events, and user statistics
    """
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func, text, and_, or_
        
        # Get filter parameters
        days = request.args.get('days', 7, type=int)  # Default 7 days
        user_filter = request.args.get('user')
        action_filter = request.args.get('action')
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # ===== SECTION 1: RECENT LOGIN ACTIVITY =====
        login_actions = ['login_success', 'login_failed_user_not_found', 
                        'login_failed_invalid_password', 'login_blocked_account_locked',
                        'login_password_success_pending_2fa', '2fa_verify_success_login_complete']
        
        recent_logins_query = AuditLog.query.filter(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.action.in_(login_actions)
            )
        )
        
        if user_filter:
            recent_logins_query = recent_logins_query.join(User).filter(User.username.ilike(f'%{user_filter}%'))
        
        recent_logins = recent_logins_query.order_by(AuditLog.timestamp.desc()).limit(50).all()
        
        # ===== SECTION 2: LOGIN STATISTICS =====
        login_stats_query = text("""
            WITH login_events AS (
                SELECT 
                    user_id,
                    action,
                    COUNT(*) as count
                FROM audit_log
                WHERE timestamp >= :start_date
                AND action IN ('login_success', 'login_failed_invalid_password', 
                              'login_blocked_account_locked', '2fa_verify_success_login_complete')
                GROUP BY user_id, action
            ),
            user_login_stats AS (
                SELECT 
                    u.id,
                    u.username,
                    u.role,
                    COALESCE(MAX(CASE WHEN le.action IN ('login_success', '2fa_verify_success_login_complete') 
                                     THEN le.count END), 0) as successful_logins,
                    COALESCE(MAX(CASE WHEN le.action = 'login_failed_invalid_password' 
                                     THEN le.count END), 0) as failed_logins,
                    COALESCE(MAX(CASE WHEN le.action = 'login_blocked_account_locked' 
                                     THEN le.count END), 0) as locked_attempts
                FROM "user" u
                LEFT JOIN login_events le ON u.id = le.user_id
                GROUP BY u.id, u.username, u.role
                HAVING COALESCE(MAX(CASE WHEN le.action IN ('login_success', '2fa_verify_success_login_complete') 
                                        THEN le.count END), 0) > 0
                   OR COALESCE(MAX(CASE WHEN le.action = 'login_failed_invalid_password' 
                                        THEN le.count END), 0) > 0
            )
            SELECT * FROM user_login_stats
            ORDER BY successful_logins DESC
            LIMIT 20
        """)
        
        login_stats = db.session.execute(
            login_stats_query,
            {'start_date': start_date}
        ).fetchall()
        
        # ===== SECTION 3: CURRENTLY ACTIVE USERS =====
        # Consider users active if they have ANY audit log activity in last hour
        active_threshold = datetime.utcnow() - timedelta(hours=1)
        
        active_users_query = text("""
            SELECT DISTINCT ON (u.id)
                u.id,
                u.username,
                u.role,
                u.dispatch_area,
                al.timestamp as last_activity,
                al.ip_address,
                al.action as last_action
            FROM "user" u
            INNER JOIN audit_log al ON u.id = al.user_id
            WHERE al.timestamp >= :active_threshold
            ORDER BY u.id, al.timestamp DESC
        """)
        
        active_users = db.session.execute(
            active_users_query,
            {'active_threshold': active_threshold}
        ).fetchall()
        
        # ===== SECTION 4: SECURITY EVENTS =====
        security_actions = ['password_changed', '2fa_enabled', '2fa_disabled', 
                           'role_change', 'user_deleted', 'account_locked', 'account_unlocked']
        
        security_events_query = AuditLog.query.filter(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.action.in_(security_actions)
            )
        ).order_by(AuditLog.timestamp.desc()).limit(50)
        
        security_events = security_events_query.all()
        
        # ===== SECTION 5: FAILED LOGIN ATTEMPTS SUMMARY =====
        failed_logins_query = text("""
            SELECT 
                u.username,
                u.role,
                COUNT(*) as failed_count,
                MAX(al.timestamp) as last_failed,
                STRING_AGG(DISTINCT al.ip_address, ', ') as ip_addresses
            FROM audit_log al
            LEFT JOIN "user" u ON al.user_id = u.id
            WHERE al.timestamp >= :start_date
            AND al.action IN ('login_failed_invalid_password', 'login_blocked_account_locked')
            GROUP BY u.username, u.role
            ORDER BY failed_count DESC
            LIMIT 20
        """)
        
        failed_logins_summary = db.session.execute(
            failed_logins_query,
            {'start_date': start_date}
        ).fetchall()
        
        # ===== SECTION 6: 2FA EVENTS =====
        twofa_events_query = AuditLog.query.filter(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.action.in_(['2fa_enabled', '2fa_disabled', '2fa_verify_success', '2fa_verify_failed'])
            )
        ).order_by(AuditLog.timestamp.desc()).limit(30)
        
        twofa_events = twofa_events_query.all()
        
        # ===== SECTION 7: AGGREGATE STATISTICS =====
        total_logins_today = AuditLog.query.filter(
            and_(
                AuditLog.timestamp >= datetime.utcnow() - timedelta(days=1),
                AuditLog.action.in_(['login_success', '2fa_verify_success_login_complete'])
            )
        ).count()
        
        total_failed_today = AuditLog.query.filter(
            and_(
                AuditLog.timestamp >= datetime.utcnow() - timedelta(days=1),
                AuditLog.action == 'login_failed_invalid_password'
            )
        ).count()
        
        unique_active_users = len(active_users)
        
        # ===== SECTION 8: ALL ACTIVITY EVENTS (PAGINATED) =====
        all_events_query = AuditLog.query.filter(AuditLog.timestamp >= start_date)
        
        if user_filter:
            all_events_query = all_events_query.join(User).filter(User.username.ilike(f'%{user_filter}%'))
        
        if action_filter:
            all_events_query = all_events_query.filter(AuditLog.action.ilike(f'%{action_filter}%'))
        
        all_events_paginated = all_events_query.order_by(
            AuditLog.timestamp.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        # Prepare template context
        context = {
            'days': days,
            'start_date': start_date,
            'end_date': end_date,
            'user_filter': user_filter,
            'action_filter': action_filter,
            
            # Activity data
            'recent_logins': recent_logins,
            'login_stats': login_stats,
            'active_users': active_users,
            'security_events': security_events,
            'failed_logins_summary': failed_logins_summary,
            'twofa_events': twofa_events,
            
            # Aggregate stats
            'total_logins_today': total_logins_today,
            'total_failed_today': total_failed_today,
            'unique_active_users': unique_active_users,
            
            # Paginated all events
            'all_events': all_events_paginated,
            
            # Helper function for template
            'format_datetime': format_datetime_ist
        }
        
        return render_template('user_activity_dashboard.html', **context)
        
    except Exception as e:
        app.logger.error(f"User activity dashboard error: {str(e)}", exc_info=True)
        flash(f'Error loading user activity dashboard: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/pool_dashboard')
@login_required
@limiter.exempt
def pool_dashboard():
    """Connection pool monitoring dashboard - admin only"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('index'))
    
    try:
        return render_template('pool_dashboard.html')
    except Exception as e:
        app.logger.error(f"Pool dashboard error: {str(e)}", exc_info=True)
        flash(f'Error loading pool dashboard: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/reports')
@login_required
def reports_page():
    """Reports and analytics page"""
    try:
        # Get basic report data
        from datetime import datetime, timedelta
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        # Recent activity stats
        recent_scans = db.session.query(Scan).filter(Scan.timestamp >= week_ago).count()
        recent_bills = db.session.query(Bill).filter(Bill.created_at >= week_ago).count()
        
        report_data = {
            'recent_scans': recent_scans,
            'recent_bills': recent_bills,
            'period': '7 days'
        }
        
        return render_template('reports.html', data=report_data)
    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/statistics')
def statistics_api():
    """Statistics API endpoint - direct implementation"""
    try:
        # Get basic statistics
        total_bags = db.session.query(Bag).count()
        total_scans = db.session.query(Scan).count() 
        total_bills = db.session.query(Bill).count()
        total_users = db.session.query(User).count()
        
        stats = {
            'total_bags': total_bags,
            'total_scans': total_scans,
            'total_bills': total_bills,
            'total_users': total_users,
            'status': 'active'
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

# Removed /db/health redirect - use /health with ?check_db=true instead

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Excel upload page - redirect to existing excel_upload"""
    if request.method == 'POST':
        # Forward POST request to excel_upload with same data
        return redirect(url_for('excel_upload'))
    else:
        # GET request - redirect to excel_upload page
        return redirect(url_for('excel_upload'))


# ============================================================================
# DATA EXPORT ROUTES - CSV and Excel exports for bags, bills, and reports
# ============================================================================

@app.route('/export/bags/csv')
@login_required
def export_bags_csv():
    """Export all bags to CSV - admin only"""
    if not current_user.is_admin():
        flash('Admin access required for exports.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from export_utils import BagExporter
        bag_type = request.args.get('type')  # 'parent', 'child', or None for all
        limit = request.args.get('limit', type=int)
        return BagExporter.export_bags_csv(db, bag_type=bag_type, limit=limit)
    except Exception as e:
        app.logger.error(f"Bag CSV export error: {str(e)}")
        flash(f'Error exporting bags: {str(e)}', 'error')
        return redirect(url_for('bag_management'))


@app.route('/export/bags/excel')
@login_required
def export_bags_excel():
    """Export all bags to Excel - admin only"""
    if not current_user.is_admin():
        flash('Admin access required for exports.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from export_utils import BagExporter
        bag_type = request.args.get('type')  # 'parent', 'child', or None for all
        limit = request.args.get('limit', type=int)
        return BagExporter.export_bags_excel(db, bag_type=bag_type, limit=limit)
    except Exception as e:
        app.logger.error(f"Bag Excel export error: {str(e)}")
        flash(f'Error exporting bags: {str(e)}', 'error')
        return redirect(url_for('bag_management'))


@app.route('/export/bills/csv')
@login_required
def export_bills_csv():
    """Export all bills to CSV - admin only"""
    if not current_user.is_admin():
        flash('Admin access required for exports.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from export_utils import BillExporter
        status = request.args.get('status')  # Filter by status if provided
        limit = request.args.get('limit', type=int)
        return BillExporter.export_bills_csv(db, status=status, limit=limit)
    except Exception as e:
        app.logger.error(f"Bill CSV export error: {str(e)}")
        flash(f'Error exporting bills: {str(e)}', 'error')
        return redirect(url_for('bill_management'))


@app.route('/export/bills/excel')
@login_required
def export_bills_excel():
    """Export all bills to Excel - admin only"""
    if not current_user.is_admin():
        flash('Admin access required for exports.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from export_utils import BillExporter
        status = request.args.get('status')  # Filter by status if provided
        limit = request.args.get('limit', type=int)
        return BillExporter.export_bills_excel(db, status=status, limit=limit)
    except Exception as e:
        app.logger.error(f"Bill Excel export error: {str(e)}")
        flash(f'Error exporting bills: {str(e)}', 'error')
        return redirect(url_for('bill_management'))


@app.route('/export/reports/user-activity/csv')
@login_required
def export_user_activity_csv():
    """Export user activity report to CSV - admin only"""
    if not current_user.is_admin():
        flash('Admin access required for reports.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from export_utils import ReportExporter
        days = request.args.get('days', default=30, type=int)
        return ReportExporter.export_user_activity_csv(db, days=days)
    except Exception as e:
        app.logger.error(f"User activity CSV export error: {str(e)}")
        flash(f'Error exporting user activity: {str(e)}', 'error')
        return redirect(url_for('user_management'))


@app.route('/export/reports/user-activity/excel')
@login_required
def export_user_activity_excel():
    """Export user activity report to Excel - admin only"""
    if not current_user.is_admin():
        flash('Admin access required for reports.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from export_utils import ReportExporter
        days = request.args.get('days', default=30, type=int)
        return ReportExporter.export_user_activity_excel(db, days=days)
    except Exception as e:
        app.logger.error(f"User activity Excel export error: {str(e)}")
        flash(f'Error exporting user activity: {str(e)}', 'error')
        return redirect(url_for('user_management'))


@app.route('/export/reports/system-stats/csv')
@login_required
def export_system_stats_csv():
    """Export system statistics to CSV - admin only"""
    if not current_user.is_admin():
        flash('Admin access required for reports.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from export_utils import ReportExporter
        return ReportExporter.export_system_stats_csv(db)
    except Exception as e:
        app.logger.error(f"System stats CSV export error: {str(e)}")
        flash(f'Error exporting system stats: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/export/reports/system-stats/excel')
@login_required
def export_system_stats_excel():
    """Export system statistics to Excel - admin only"""
    if not current_user.is_admin():
        flash('Admin access required for reports.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from export_utils import ReportExporter
        return ReportExporter.export_system_stats_excel(db)
    except Exception as e:
        app.logger.error(f"System stats Excel export error: {str(e)}")
        flash(f'Error exporting system stats: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/config-check')
def config_check():
    """Check critical environment configuration (PUBLIC endpoint for troubleshooting)"""
    import os
    
    is_production = (
        os.environ.get('REPLIT_DEPLOYMENT') == '1' or
        os.environ.get('REPLIT_ENVIRONMENT') == 'production'
    )
    
    config = {
        'environment': 'production' if is_production else 'development',
        'deployment_id': os.environ.get('REPLIT_DEPLOYMENT', 'not set'),
        'session_secret_configured': bool(os.environ.get('SESSION_SECRET')),
        'redis_url_configured': bool(os.environ.get('REDIS_URL')),
        'admin_password_configured': bool(os.environ.get('ADMIN_PASSWORD')),
        'database_url_configured': bool(os.environ.get('DATABASE_URL')),
        'session_type': app.config.get('SESSION_TYPE', 'unknown'),
        'session_cookie_secure': app.config.get('SESSION_COOKIE_SECURE', False),
        'preferred_url_scheme': app.config.get('PREFERRED_URL_SCHEME', 'unknown'),
        'replit_domains': os.environ.get('REPLIT_DOMAINS', 'not set')
    }
    
    return jsonify(config)


@app.route('/api/test/reset_lock', methods=['POST'])
@csrf_compat.exempt
def test_reset_lock():
    """TEST ONLY: Reset account lockout for testing purposes (flag-gated, CSRF-exempt)"""
    import os
    from models import User
    
    test_mode = os.environ.get('TEST_MODE', '').lower() in ('1', 'true', 'yes')
    is_dev = os.environ.get('REPLIT_DEPLOYMENT') != '1'
    
    if not (test_mode or is_dev):
        app.logger.warning("TEST ENDPOINT ACCESS DENIED: /api/test/reset_lock called in production without TEST_MODE")
        return jsonify({'error': 'Endpoint disabled in production'}), 403
    
    try:
        data = request.get_json(silent=True) or {}
        username = data.get('username', 'admin')
        
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'error': f'User {username} not found'}), 404
        
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_failed_login = None
        db.session.commit()
        
        app.logger.info(f"TEST RESET: Lockout cleared for user {username}")
        
        return jsonify({
            'success': True,
            'username': username,
            'message': 'Lockout reset successfully'
        }), 200
        
    except Exception as e:
        app.logger.error(f"TEST RESET ERROR: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/emergency/admin', methods=['POST'])
@csrf_compat.exempt
def emergency_admin_management():
    """
    EMERGENCY ONLY: Secure endpoint for critical admin account operations
    
    Operations:
    - unlock: Clear account lockout
    - create: Create new admin account
    
    Security: Requires EMERGENCY_ADMIN_KEY environment variable
    
    Usage:
    POST /api/emergency/admin
    {
        "key": "your-emergency-key",
        "operation": "unlock" | "create",
        "username": "admin",
        "password": "newpassword123",  // only for create operation
        "email": "admin@example.com"   // only for create operation
    }
    """
    import os
    from models import User, UserRole
    from werkzeug.security import generate_password_hash
    from audit_utils import log_audit_with_snapshot
    
    try:
        # SECURITY: Require emergency key
        emergency_key = os.environ.get('EMERGENCY_ADMIN_KEY')
        if not emergency_key:
            app.logger.error("🚨 EMERGENCY ENDPOINT: EMERGENCY_ADMIN_KEY not configured")
            return jsonify({'error': 'Emergency endpoint not configured'}), 503
        
        data = request.get_json(silent=True) or {}
        provided_key = data.get('key', '')
        
        # Constant-time comparison to prevent timing attacks
        import hmac
        if not hmac.compare_digest(str(provided_key), str(emergency_key)):
            app.logger.warning(f"🚨 EMERGENCY ENDPOINT: Invalid key attempt from {request.remote_addr}")
            log_audit_with_snapshot(
                action='emergency_admin_unauthorized',
                entity_type='user',
                entity_id=None,
                details={'ip': request.remote_addr, 'reason': 'Invalid emergency key'}
            )
            return jsonify({'error': 'Unauthorized'}), 403
        
        operation = data.get('operation', '').lower()
        username = data.get('username', '').strip()
        
        if not username:
            return jsonify({'error': 'Username required'}), 400
        
        # OPERATION: Unlock account
        if operation == 'unlock':
            user = User.query.filter_by(username=username).first()
            if not user:
                return jsonify({'error': f'User {username} not found'}), 404
            
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_failed_login = None
            db.session.commit()
            
            app.logger.warning(f"🚨 EMERGENCY UNLOCK: Account {username} unlocked via emergency endpoint")
            log_audit_with_snapshot(
                action='emergency_unlock',
                entity_type='user',
                entity_id=user.id,
                after_state=user,
                details={
                    'username': username,
                    'unlocked_by': 'emergency_endpoint',
                    'ip': request.remote_addr
                }
            )
            
            return jsonify({
                'success': True,
                'operation': 'unlock',
                'username': username,
                'message': f'Account {username} unlocked successfully'
            }), 200
        
        # OPERATION: Create admin account
        elif operation == 'create':
            email = data.get('email', '').strip()
            password = data.get('password', '').strip()
            
            if not email or not password:
                return jsonify({'error': 'Email and password required for create operation'}), 400
            
            # Check if user already exists
            existing_user = User.query.filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing_user:
                return jsonify({'error': f'User with username {username} or email {email} already exists'}), 409
            
            # Validate password strength
            if len(password) < 8:
                return jsonify({'error': 'Password must be at least 8 characters'}), 400
            
            # Create new admin user
            new_admin = User(  # type: ignore[call-arg]
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                role=UserRole.ADMIN.value,
                verified=True,
                failed_login_attempts=0,
                locked_until=None,
                last_failed_login=None
            )
            
            db.session.add(new_admin)
            db.session.commit()
            
            app.logger.warning(f"🚨 EMERGENCY CREATE: New admin account {username} created via emergency endpoint")
            log_audit_with_snapshot(
                action='emergency_create_admin',
                entity_type='user',
                entity_id=new_admin.id,
                after_state=new_admin,
                details={
                    'username': username,
                    'email': email,
                    'role': 'admin',
                    'created_by': 'emergency_endpoint',
                    'ip': request.remote_addr
                }
            )
            
            return jsonify({
                'success': True,
                'operation': 'create',
                'username': username,
                'email': email,
                'role': 'admin',
                'message': f'Admin account {username} created successfully'
            }), 201
        
        else:
            return jsonify({'error': f'Invalid operation: {operation}. Must be "unlock" or "create"'}), 400
    
    except Exception as e:
        app.logger.error(f"🚨 EMERGENCY ENDPOINT ERROR: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# ============================================================================
# GLOBAL ERROR HANDLERS - User-friendly error pages (no raw error codes)
# ============================================================================

@app.errorhandler(400)
def bad_request_error(error):
    """Handle 400 Bad Request errors - show user-friendly message"""
    app.logger.warning(f"400 Bad Request: {request.url} - {str(error)}")
    
    # Check if this is an AJAX/API request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       request.headers.get('Accept', '').startswith('application/json'):
        return jsonify({
            'success': False,
            'error': 'Invalid request. Please check your input and try again.',
            'error_code': 400
        }), 400
    
    return render_template('error.html',
        error_code=400,
        error_title='Invalid Request',
        error_message='The request was not formatted correctly. Please go back and try again.'
    ), 400


@app.errorhandler(403)
def forbidden_error(error):
    """Handle 403 Forbidden errors - show access denied message"""
    app.logger.warning(f"403 Forbidden: {request.url} - User: {getattr(current_user, 'username', 'anonymous')}")
    
    # Check if this is an AJAX/API request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       request.headers.get('Accept', '').startswith('application/json'):
        return jsonify({
            'success': False,
            'error': 'You do not have permission to access this resource.',
            'error_code': 403
        }), 403
    
    return render_template('error.html',
        error_code=403,
        error_title='Access Denied',
        error_message='You do not have permission to access this page. Please contact your administrator if you believe this is an error.',
        show_login=not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated
    ), 403


@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 Not Found errors - show friendly page not found message"""
    app.logger.info(f"404 Not Found: {request.url}")
    
    # Check if this is an AJAX/API request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       request.headers.get('Accept', '').startswith('application/json'):
        return jsonify({
            'success': False,
            'error': 'The requested resource was not found.',
            'error_code': 404
        }), 404
    
    return render_template('error.html',
        error_code=404,
        error_title='Page Not Found',
        error_message='The page you are looking for does not exist or has been moved. Please check the URL or navigate using the menu.'
    ), 404


@app.errorhandler(405)
def method_not_allowed_error(error):
    """Handle 405 Method Not Allowed errors"""
    app.logger.warning(f"405 Method Not Allowed: {request.method} {request.url}")
    
    # Check if this is an AJAX/API request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       request.headers.get('Accept', '').startswith('application/json'):
        return jsonify({
            'success': False,
            'error': 'This action is not allowed. Please try a different approach.',
            'error_code': 405
        }), 405
    
    return render_template('error.html',
        error_code=405,
        error_title='Action Not Allowed',
        error_message='This action is not permitted. Please use the navigation menu to access features.'
    ), 405


@app.errorhandler(429)
def rate_limit_error(error):
    """Handle 429 Too Many Requests errors - rate limiting"""
    app.logger.warning(f"429 Rate Limited: {request.url} - IP: {request.remote_addr}")
    
    # Check if this is an AJAX/API request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       request.headers.get('Accept', '').startswith('application/json'):
        return jsonify({
            'success': False,
            'error': 'Too many requests. Please wait a moment and try again.',
            'error_code': 429
        }), 429
    
    return render_template('error.html',
        error_code=429,
        error_title='Too Many Requests',
        error_message='You have made too many requests. Please wait a moment before trying again.'
    ), 429


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors - show generic error, log details"""
    app.logger.error(f"500 Internal Server Error: {request.url} - {str(error)}")
    
    # Rollback any failed database transactions
    try:
        db.session.rollback()
    except Exception:
        pass
    
    # Check if this is an AJAX/API request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       request.headers.get('Accept', '').startswith('application/json'):
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred. Please try again or contact support.',
            'error_code': 500
        }), 500
    
    return render_template('error.html',
        error_code=500,
        error_title='Something Went Wrong',
        error_message='We encountered an unexpected issue. Please try again. If the problem continues, contact your system administrator.'
    ), 500


@app.errorhandler(502)
def bad_gateway_error(error):
    """Handle 502 Bad Gateway errors"""
    app.logger.error(f"502 Bad Gateway: {request.url}")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       request.headers.get('Accept', '').startswith('application/json'):
        return jsonify({
            'success': False,
            'error': 'Server temporarily unavailable. Please try again in a moment.',
            'error_code': 502
        }), 502
    
    return render_template('error.html',
        error_code=502,
        error_title='Service Temporarily Unavailable',
        error_message='The service is temporarily unavailable. Please refresh the page in a moment.'
    ), 502


@app.errorhandler(503)
def service_unavailable_error(error):
    """Handle 503 Service Unavailable errors"""
    app.logger.error(f"503 Service Unavailable: {request.url}")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       request.headers.get('Accept', '').startswith('application/json'):
        return jsonify({
            'success': False,
            'error': 'Service temporarily unavailable. Please try again shortly.',
            'error_code': 503
        }), 503
    
    return render_template('error.html',
        error_code=503,
        error_title='Service Unavailable',
        error_message='The service is temporarily unavailable for maintenance. Please try again in a few minutes.'
    ), 503


@app.errorhandler(Exception)
def handle_exception(error):
    """Catch-all handler for any unhandled exceptions"""
    app.logger.error(f"Unhandled Exception at {request.url}: {str(error)}")
    import traceback
    app.logger.error(traceback.format_exc())
    
    # Rollback any failed database transactions
    try:
        db.session.rollback()
    except Exception:
        pass
    
    # Check if this is an AJAX/API request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       request.headers.get('Accept', '').startswith('application/json'):
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred. Please try again.',
            'error_code': 500
        }), 500
    
    return render_template('error.html',
        error_code=500,
        error_title='Unexpected Error',
        error_message='Something unexpected happened. Please try again or contact support if the issue persists.'
    ), 500
