"""
Routes for traitor track application - Location functionality completely removed
"""
from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_file, abort, make_response

def validate_qr_code(qr_id):
    """Validate that a QR code is not a URL and meets basic requirements"""
    if not qr_id or len(qr_id.strip()) == 0:
        return False, "QR code cannot be empty"
    
    qr_id = qr_id.strip()
    
    # Check if it looks like a URL
    if qr_id.startswith(('http://', 'https://', 'ftp://', 'www.')) or '://' in qr_id:
        return False, "URLs are not valid QR codes for bag identifiers"
    
    # Check length (reasonable limits)
    if len(qr_id) > 100:
        return False, "QR code is too long (max 100 characters)"
    
    # Check for problematic characters
    invalid_chars = ['<', '>', '"', "'", '&', '%']
    if any(char in qr_id for char in invalid_chars):
        return False, "QR code contains invalid characters"
    
    return True, "Valid QR code"
# Session-based authentication - no longer using Flask-Login
from werkzeug.security import check_password_hash, generate_password_hash

# Import authentication functions from simple_auth
from simple_auth import is_authenticated as simple_is_authenticated, require_auth as simple_require_auth

# Compatibility layer for existing code
def is_authenticated():
    # Use both session formats for compatibility
    return (
        session.get('logged_in', False) or 
        session.get('authenticated', False)
    ) and session.get('user_id') is not None

def require_auth(f):
    return simple_require_auth(f)

def is_admin():
    """Check if current user is admin"""
    return session.get('user_role') == 'admin'

def is_biller():
    """Check if current user is a biller"""
    return session.get('user_role') == 'biller'

def is_dispatcher():
    """Check if current user is a dispatcher"""
    return session.get('user_role') == 'dispatcher'

def can_edit_bills():
    """Check if current user can edit bills"""
    role = session.get('user_role')
    return role in ['admin', 'biller']

def can_manage_users():
    """Check if current user can manage other users"""
    return session.get('user_role') == 'admin'

def get_user_dispatch_area():
    """Get current user's dispatch area"""
    return session.get('dispatch_area')

def get_current_user_id():
    """Get current user ID from session"""
    return session.get('user_id')

# Use the simple auth decorator
login_required = require_auth

class CurrentUser:
    """Current user object for simple authentication"""
    @property
    def id(self):
        return session.get('user_id')
    
    @property
    def username(self):
        return session.get('username')
    
    @property
    def email(self):
        from simple_auth import get_current_user_data
        user_data = get_current_user_data()
        return user_data.get('email') if user_data else None
    
    @property
    def role(self):
        return session.get('user_role')
    
    @property
    def dispatch_area(self):
        return session.get('dispatch_area')
    
    @property
    def is_authenticated(self):
        # Check both session formats for compatibility
        return (
            session.get('logged_in', False) or 
            session.get('authenticated', False)
        ) and session.get('user_id') is not None
    
    def is_admin(self):
        """Check if user is admin"""
        return session.get('user_role') == 'admin'
    
    def is_biller(self):
        """Check if user is a biller"""
        return session.get('user_role') == 'biller'
    
    def is_dispatcher(self):
        """Check if user is a dispatcher"""
        return session.get('user_role') == 'dispatcher'
    
    def can_edit_bills(self):
        """Check if user can edit bills"""
        role = session.get('user_role')
        return role in ['admin', 'biller']
    
    def can_manage_users(self):
        """Check if user can manage other users"""
        return session.get('user_role') == 'admin'
    
    def can_access_area(self, area):
        """Check if user can access a specific dispatch area"""
        role = session.get('user_role')
        if role in ['admin', 'biller']:
            return True
        if role == 'dispatcher':
            return session.get('dispatch_area') == area
        return False

# Create current_user object for routes using session data
class RouteCurrentUser:
    """Current user object for route handlers using session data"""
    @property
    def id(self):
        return session.get('user_id')
    
    @property
    def username(self):
        return session.get('username')
    
    @property
    def role(self):
        return session.get('user_role')
    
    @property
    def dispatch_area(self):
        return session.get('dispatch_area')
    
    @property
    def is_authenticated(self):
        return (
            session.get('logged_in', False) or 
            session.get('authenticated', False)
        ) and session.get('user_id') is not None
    
    def is_admin(self):
        """Check if user is admin"""
        role = session.get('user_role')
        # Debug logging
        import logging
        logging.info(f"Admin check - User role from session: '{role}', type: {type(role)}")
        return role == 'admin'
    
    def is_biller(self):
        """Check if user is a biller"""
        return session.get('user_role') == 'biller'
    
    def is_dispatcher(self):
        """Check if user is a dispatcher"""
        return session.get('user_role') == 'dispatcher'
    
    def can_edit_bills(self):
        """Check if user can edit bills"""
        role = session.get('user_role')
        return role in ['admin', 'biller']
    
    def can_manage_users(self):
        """Check if user can manage other users"""
        return session.get('user_role') == 'admin'

current_user = RouteCurrentUser()

from sqlalchemy import desc, func, and_, or_
from datetime import datetime, timedelta

from app_clean import app, db, limiter


from models import User, UserRole, Bag, BagType, Link, Scan, Bill, BillBag, PromotionRequest, PromotionRequestStatus
from forms import LoginForm, RegistrationForm, ScanParentForm, ScanChildForm, ChildLookupForm, PromotionRequestForm, AdminPromotionForm, PromotionRequestActionForm, BillCreationForm
from account_security import is_account_locked, record_failed_attempt, reset_failed_attempts, track_login_activity
from validation_utils import validate_parent_qr_id, validate_child_qr_id, validate_bill_id, sanitize_input
from duplicate_prevention import (
    validate_new_bag_qr_code, 
    validate_new_bill_id, 
    check_qr_code_uniqueness,
    log_duplicate_attempt,
    get_system_integrity_report
)

import csv
import io
import json
import secrets
import random
import time
import logging

# Analytics route removed as requested

@app.route('/user_management')
@login_required
def user_management():
    """User management dashboard for admins"""
    try:
        # Debug logging for admin check
        import logging
        logging.info(f"User management route - User ID: {current_user.id}, Role: {current_user.role}, Is Admin: {current_user.is_admin()}")
        
        if not current_user.is_admin():
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        
        users = User.query.order_by(User.created_at.desc()).all()
        
        # Get statistics for each user
        user_data = []
        for user in users:
            try:
                scan_count = Scan.query.filter(Scan.user_id == user.id).count()
                last_scan = Scan.query.filter(Scan.user_id == user.id).order_by(desc(Scan.timestamp)).first()
                
                user_data.append({
                    'user': user,
                    'scan_count': scan_count,
                    'last_scan': last_scan.timestamp if last_scan else None
                })
            except Exception as e:
                app.logger.error(f"Error processing user {user.id}: {e}")
                user_data.append({
                    'user': user,
                    'scan_count': 0,
                    'last_scan': None
                })
        
        return render_template('user_management.html', user_data=user_data)
        
    except Exception as e:
        app.logger.error(f"User management error: {e}")
        flash('Error loading user management. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/admin/users/<int:user_id>')
@login_required
def get_user_details(user_id):
    """Get user details for editing"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role
    })

@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@login_required
def edit_user(user_id):
    """Edit user details"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    user = User.query.get_or_404(user_id)
    
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        dispatch_area = request.form.get('dispatch_area')
        
        if username:
            user.username = username
        if email:
            user.email = email
        if role and role in [UserRole.ADMIN.value, UserRole.BILLER.value, UserRole.DISPATCHER.value]:
            user.role = role
            # Update dispatch area based on role
            if role == UserRole.DISPATCHER.value:
                if not dispatch_area:
                    flash('Dispatch area is required for dispatchers.', 'error')
                    return redirect(url_for('user_management'))
                user.dispatch_area = dispatch_area
            else:
                user.dispatch_area = None  # Clear dispatch area for non-dispatchers
            
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('user_management'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user: {str(e)}', 'error')
        return redirect(url_for('user_management'))

@app.route('/admin/users/<int:user_id>/promote', methods=['POST'])
@login_required
def promote_user(user_id):
    """Promote user to admin - only admins can do this"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    user = User.query.get_or_404(user_id)
    
    try:
        if user.role == UserRole.ADMIN.value:
            return jsonify({'success': False, 'message': 'User is already an admin'})
            
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot promote yourself'})
            
        user.role = UserRole.ADMIN.value
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'{user.username} promoted to admin'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error promoting user: {str(e)}'})

@app.route('/admin/users/<int:user_id>/demote', methods=['POST'])
@login_required
def demote_user(user_id):
    """Demote admin to employee - only admins can do this, cannot demote yourself"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    user = User.query.get_or_404(user_id)
    
    try:
        if user.role == UserRole.DISPATCHER.value:
            return jsonify({'success': False, 'message': 'User is already an employee'})
            
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot demote yourself'})
            
        user.role = UserRole.DISPATCHER.value
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'{user.username} demoted to employee'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error demoting user: {str(e)}'})

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete user"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    user = User.query.get_or_404(user_id)
    
    try:
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot delete yourself'})
            
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'User {user.username} deleted'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting user: {str(e)}'})

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
        role = request.form.get('role', UserRole.DISPATCHER.value)
        dispatch_area = request.form.get('dispatch_area')
        
        # Validate required fields
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('user_management'))
        
        # Validate dispatch area for dispatchers
        if role == UserRole.DISPATCHER.value and not dispatch_area:
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
        user.dispatch_area = dispatch_area if role == UserRole.DISPATCHER.value else None
        user.verified = True
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
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
        return redirect(url_for('index'))
    
    try:
        # Get comprehensive system integrity report
        report = get_system_integrity_report()
        
        return render_template('admin_system_integrity.html', report=report)
        
    except Exception as e:
        app.logger.error(f'System integrity report error: {str(e)}')
        flash('Error generating system integrity report.', 'error')
        return redirect(url_for('index'))

@app.route('/seed_sample_data')
@login_required
def seed_sample_data():
    """Create sample data for testing analytics (admin only)"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Create sample bags if few exist
        if Bag.query.count() < 10:
            for i in range(20):
                # Create parent bags
                parent_bag = Bag()
                parent_bag.qr_id = f"PARENT_{i+1:03d}_{secrets.token_hex(4).upper()}"
                parent_bag.type = BagType.PARENT.value
                parent_bag.name = f"Parent Bag {i+1}"
                parent_bag.child_count = random.randint(1, 5)
                db.session.add(parent_bag)
                db.session.flush()  # Get the ID
                
                # Create child bags for this parent
                for j in range(parent_bag.child_count):
                    child_bag = Bag()
                    child_bag.qr_id = f"CHILD_{i+1:03d}_{j+1:02d}_{secrets.token_hex(3).upper()}"
                    child_bag.type = BagType.CHILD.value
                    child_bag.name = f"Child Bag {i+1}-{j+1}"
                    child_bag.parent_id = parent_bag.id
                    db.session.add(child_bag)
                    
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
                
                if bag.type == BagType.PARENT.value:
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

@app.route('/', methods=['GET', 'POST'])
def index():
    """Main dashboard page"""
    import logging
    logging.info(f"Index route - Session data: {dict(session)}")
    logging.info(f"Authenticated: {is_authenticated()}")
    
    # Simple authentication check
    if not is_authenticated():
        logging.info("User not authenticated, showing landing page")
        return render_template('landing.html')
    
    # Dashboard data for logged-in users
    today = datetime.now().date()
    
    # User's scan activity today
    user_scans_today = Scan.query.filter(
        Scan.user_id == session.get('user_id'),
        func.date(Scan.timestamp) == today
    ).count()
    
    # Recent scans by current user
    recent_scans = Scan.query.filter(Scan.user_id == session.get('user_id'))\
                             .order_by(desc(Scan.timestamp))\
                             .limit(5).all()
    
    # System-wide statistics (for context)
    total_scans_today = Scan.query.filter(func.date(Scan.timestamp) == today).count()
    total_bags = Bag.query.count()
    
    return render_template('dashboard.html',
                         user_scans_today=user_scans_today,
                         recent_scans=recent_scans,
                         total_scans_today=total_scans_today,
                         total_bags=total_bags)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login endpoint"""
    if is_authenticated() and request.method == 'GET':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # Validate CSRF token first
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.form.get('csrf_token'))
            except Exception as csrf_error:
                app.logger.warning(f'CSRF validation failed for login: {csrf_error}')
                flash('Security token expired. Please refresh the page and try again.', 'error')
                return render_template('login.html')
        except ImportError:
            # Handle case where CSRF is not available
            pass
            
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        # Check if account is locked
        locked, remaining_time = is_account_locked(username)
        if locked:
            flash(f'Account locked. Try again in {remaining_time} seconds.', 'error')
            return render_template('login.html')
        
        try:
            user = User.query.filter_by(username=username).first()
            app.logger.info(f"Login attempt for username: {username}")
            app.logger.info(f"User found: {user is not None}")
            if user:
                app.logger.info(f"User role: {user.role}, verified: {user.verified}")
                password_valid = check_password_hash(user.password_hash, password)
                app.logger.info(f"Password valid: {password_valid}")
                
            if user and user.verified and check_password_hash(user.password_hash, password):
                # Reset failed attempts on successful login
                reset_failed_attempts(username)
                
                # Create authenticated session
                session.clear()
                session.permanent = True
                session['logged_in'] = True
                session['authenticated'] = True
                session['user_id'] = user.id
                session['username'] = user.username
                session['user_role'] = user.role
                session['dispatch_area'] = user.dispatch_area  # Store dispatch area for area-based access control
                session['auth_time'] = time.time()
                
                # Track successful login
                track_login_activity(user.id, success=True)
                
                flash('Login successful!', 'success')
                return redirect(url_for('index'))
            else:
                # Record failed attempt
                record_failed_attempt(username)
                flash('Invalid username or password.', 'error')
                
        except Exception as e:
            logging.error(f"Login error: {e}")
            flash('Login failed. Please try again.', 'error')
        
        return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout endpoint"""
    username = session.get('username', 'unknown')
    session.clear()
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
                from simple_auth import create_auth_session
                create_auth_session(user)
                flash(f'Session refreshed for user {user.username} with role {user.role}', 'success')
                import logging
                logging.info(f"Session fixed for user {user.username}, role: {user.role}")
                return redirect(url_for('index'))
        
        flash('Could not fix session - user not found', 'error')
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Error fixing session: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/auth-test')
def auth_test():
    """Authentication test page to debug session issues"""
    from flask import session
    
    # Get session data for debugging
    session_data = dict(session)
    
    return render_template('auth_test.html', session_data=session_data)



@app.route('/link_to_bill/<qr_id>', methods=['GET', 'POST'])
@login_required
def link_to_bill(qr_id):
    """Link parent bag to bill"""
    try:
        parent_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.PARENT.value).first()
        if not parent_bag:
            flash('Parent bag not found', 'error')
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            bill_id = request.form.get('bill_id', '').strip()
            if not bill_id:
                flash('Bill ID is required', 'error')
                return render_template('link_to_bill.html', parent_bag=parent_bag)
            
            # Check if bill already exists
            bill = Bill.query.filter_by(bill_id=bill_id).first()
            if not bill:
                # Validate bill ID uniqueness before creating
                is_valid, error_message = validate_new_bill_id(bill_id)
                if not is_valid:
                    log_duplicate_attempt(bill_id, 'bill', 'bag', current_user.id)
                    flash(error_message or 'Invalid bill ID', 'error')
                    return render_template('link_to_bill.html', parent_bag=parent_bag)
                
                bill = Bill()
                bill.bill_id = bill_id
                bill.description = f"Bill for {bill_id}"
                bill.parent_bag_count = 0
                bill.status = 'draft'
                db.session.add(bill)
                db.session.flush()
            
            # Link parent bag to bill
            existing_link = BillBag.query.filter_by(
                bill_id=bill.id, 
                parent_bag_id=parent_bag.id
            ).first()
            
            if not existing_link:
                bill_bag = BillBag()
                bill_bag.bill_id = bill.id
                bill_bag.bag_id = parent_bag.id
                db.session.add(bill_bag)
                
                # Update bill count
                bill.parent_bag_count = BillBag.query.filter_by(bill_id=bill.id).count() + 1
                
            db.session.commit()
            flash(f'Parent bag {qr_id} linked to bill {bill_id}', 'success')
            return redirect(url_for('index'))
        
        return render_template('link_to_bill.html', parent_bag=parent_bag)
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Link to bill error: {e}")
        flash('Failed to link to bill', 'error')
        return redirect(url_for('index'))

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
        
        if not status:
            flash('Status is required', 'error')
            return redirect(url_for('scan'))
        
        # Find the bag by QR ID
        bag = Bag.query.filter_by(qr_id=qr_id).first()
        if not bag:
            flash(f'Bag with QR ID {qr_id} not found', 'error')
            return redirect(url_for('scan'))
        
        # Create scan record
        scan = Scan()
        scan.parent_bag_id = bag.id if bag.type == BagType.PARENT.value else None
        scan.child_bag_id = bag.id if bag.type == BagType.CHILD.value else None
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

@app.route('/fix-admin-password')
def fix_admin_password():
    """Fix admin password - temporary endpoint"""
    from werkzeug.security import generate_password_hash
    user = User.query.filter_by(username='admin').first()
    if user:
        user.password_hash = generate_password_hash('admin')
        db.session.commit()
        return "Admin password fixed. Username: admin, Password: admin"
    return "Admin user not found"

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("50 per minute")  # Further increased for development testing
def register():
    """User registration page with form validation"""
    if is_authenticated():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # Validate CSRF token first
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.form.get('csrf_token'))
            except Exception as csrf_error:
                app.logger.warning(f'CSRF validation failed for registration: {csrf_error}')
                flash('Security token expired. Please refresh the page and try again.', 'error')
                return render_template('register.html')
            
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
            
            if len(password) < 8:
                flash('Password must be at least 8 characters long.', 'error')
                return render_template('register.html')
            
            if password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('register.html')
            
            # Check if user already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username already exists. Please choose a different one.', 'error')
                return render_template('register.html')
                
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                flash('Email already registered. Please use a different email.', 'error')
                return render_template('register.html')
            
            # Create new user
            user = User()
            user.username = username
            user.email = email
            user.role = UserRole.DISPATCHER.value
            user.verified = True
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Registration error: {str(e)}')
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('register.html')

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
            return redirect(url_for('index'))
        
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
                return redirect(url_for('index'))
                
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
        return redirect(url_for('index'))

@app.route('/admin/promotions')
@login_required
def admin_promotions():
    """Admin view of all promotion requests"""
    # Debug logging for admin check
    import logging
    logging.info(f"Admin promotions route - User ID: {current_user.id}, Role: {current_user.role}, Is Admin: {current_user.is_admin()}")
    
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('index'))
    
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
        return redirect(url_for('index'))
    
    form = AdminPromotionForm()
    
    # Populate user choices (only employees)
    dispatchers = User.query.filter_by(role=UserRole.DISPATCHER.value).all()
    form.user_id.choices = [(u.id, f"{u.username} ({u.email})") for u in dispatchers]
    
    if form.validate_on_submit():
        try:
            user_to_promote = User.query.get(form.user_id.data)
            if user_to_promote:
                user_to_promote.role = UserRole.ADMIN.value
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
        return redirect(url_for('index'))
    
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
                user_to_promote.role = UserRole.ADMIN.value
                
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

@app.route('/scan/parent')
@login_required
def scan_parent():
    """Scan parent bag QR code - Direct scan without location selection"""
    form = ScanParentForm()
    return render_template('scan_parent.html', form=form)

@app.route('/scan/parent', methods=['POST'])
@login_required
def scan_parent_bag():
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
            # FAST: Single query to check existing bag
            existing_bag = Bag.query.filter_by(qr_id=qr_id).first()
            
            if existing_bag:
                if existing_bag.type == BagType.PARENT.value:
                    # Use existing parent bag
                    parent_bag = existing_bag
                else:
                    # QR code exists as child bag - prevent cross-type usage
                    return jsonify({'success': False, 'message': f'QR code {qr_id} is already registered as a child bag.'})
            else:
                # Create new parent bag instantly
                parent_bag = Bag(
                    qr_id=qr_id,
                    name=f"Bag {qr_id}",
                    type=BagType.PARENT.value,
                    dispatch_area=current_user.dispatch_area if current_user.is_dispatcher() else None
                )
                db.session.add(parent_bag)
                db.session.flush() # Get ID without full commit
            
            # FAST: Create scan record
            scan = Scan(
                parent_bag_id=parent_bag.id,
                user_id=current_user.id,
                timestamp=datetime.utcnow()
            )
            db.session.add(scan)
            
            # Single commit for both operations
            db.session.commit()
            
            # Store in session for child scanning  
            session['last_scan'] = {
                'type': 'parent',
                'qr_id': qr_id,
                'bag_name': parent_bag.name,
                'timestamp': scan.timestamp.isoformat()
            }
            # Also store the current parent QR for child scanner
            session['current_parent_qr'] = qr_id
            
            # Instant response
            return jsonify({
                'success': True,
                'parent_qr': qr_id,
                'message': f'Parent bag {qr_id} scanned successfully!'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Processing failed: {str(e)}'})
    
    else:
        # Handle regular form submission
        form = ScanParentForm()
        
        if form.validate_on_submit():
            try:
                qr_id = sanitize_input(getattr(form, 'qr_id', form).data).strip()
                
                # Accept any QR code format - no validation restrictions
                if not qr_id:
                    flash('Please enter a QR code.', 'error')
                    return render_template('scan_parent.html', form=form)
                
                # Comprehensive duplicate check for QR code uniqueness
                is_valid, error_message = validate_new_bag_qr_code(qr_id, BagType.PARENT.value)
                existing_bag = Bag.query.filter_by(qr_id=qr_id).first()
                
                if existing_bag:
                    if existing_bag.type == BagType.PARENT.value:
                        parent_bag = existing_bag
                    else:
                        log_duplicate_attempt(qr_id, 'parent', 'child', current_user.id)
                        flash(f'QR code {qr_id} is already registered as a child bag. Cannot use as parent bag.', 'error')
                        return render_template('scan_parent.html', form=form)
                else:
                    if not is_valid:
                        log_duplicate_attempt(qr_id, 'parent', 'bill', current_user.id)
                        flash(error_message or 'Invalid QR code', 'error')
                        return render_template('scan_parent.html', form=form)
                    
                    # Create new parent bag
                    parent_bag = Bag()
                    parent_bag.qr_id = qr_id
                    parent_bag.name = f"Bag {qr_id}"
                    parent_bag.type = BagType.PARENT.value
                    parent_bag.dispatch_area = current_user.dispatch_area if current_user.is_dispatcher() else None
                    db.session.add(parent_bag)
                    db.session.commit()
                    flash(f'New parent bag created for QR code: {qr_id}', 'info')
                
                # Record the scan
                scan = Scan()
                scan.parent_bag_id = parent_bag.id
                scan.user_id = current_user.id
                scan.timestamp = datetime.utcnow()
                
                db.session.add(scan)
                db.session.commit()
                
                # Store in session for the completion page
                session['last_scan'] = {
                    'type': 'parent',
                    'qr_id': qr_id,
                    'bag_name': parent_bag.name,
                    'timestamp': scan.timestamp.isoformat()
                }
                # Also store the current parent QR for child scanner
                session['current_parent_qr'] = qr_id
                
                flash('Parent bag scanned successfully!', 'success')
                return redirect(url_for('scan_complete', s=request.args.get('s')))
                
            except Exception as e:
                db.session.rollback()
                flash('Error processing scan. Please try again.', 'error')
                app.logger.error(f'Parent scan error: {str(e)}')
        
        return render_template('scan_parent.html', form=form)

@app.route('/scan/child', methods=['GET', 'POST'])
@login_required
def scan_child():
    """Scan child bag QR code - unified GET/POST handler"""
    # Check if it's an AJAX request (simpler detection)
    is_ajax = 'qr_code' in request.form and request.method == 'POST'
    
    app.logger.info(f"Child scan request - AJAX: {is_ajax}, QR_CODE: {request.form.get('qr_code')}")
    
    if request.method == 'POST' and is_ajax:
        # Handle AJAX QR scan request - ULTRA-OPTIMIZED FOR SUB-SECOND RESPONSE
        qr_id = request.form.get('qr_code', '').strip()
        
        if not qr_id:
            return jsonify({'success': False, 'message': 'QR code required'})
        
        try:
            # ULTRA-FAST: Get parent bag from session (cached)
            parent_qr = session.get('current_parent_qr')
            if not parent_qr:
                return jsonify({'success': False, 'message': 'No parent bag selected'})
            
            # LIGHTNING-FAST: Get parent bag from cached session
            parent_bag = Bag.query.filter_by(qr_id=parent_qr, type=BagType.PARENT.value).first()
            if not parent_bag:
                return jsonify({'success': False, 'message': 'Parent bag not found'})
            
            # LIGHTNING-FAST: Check child bag exists (minimal query)
            existing_child = Bag.query.filter_by(qr_id=qr_id).first()
            
            if existing_child and existing_child.type != BagType.CHILD.value:
                return jsonify({'success': False, 'message': f'{qr_id} exists as parent bag'})
            
            # LIGHTNING-FAST: Skip duplicate check - create child bag instantly
            if not existing_child:
                child_bag = Bag(
                    qr_id=qr_id,
                    name=f"Child {qr_id}",
                    type=BagType.CHILD.value,
                    dispatch_area=parent_bag.dispatch_area
                )
                db.session.add(child_bag)
                db.session.flush()  # Get ID without full commit
            else:
                child_bag = existing_child
            
            # LIGHTNING-FAST: Create link without duplicate check (faster)
            link = Link(
                parent_bag_id=parent_bag.id,
                child_bag_id=child_bag.id
            )
            db.session.add(link)
            
            # LIGHTNING-FAST: Create scan record
            scan = Scan(
                child_bag_id=child_bag.id,
                user_id=current_user.id,
                timestamp=datetime.utcnow()
            )
            db.session.add(scan)
            
            # LIGHTNING-FAST: Single commit for all operations
            try:
                db.session.commit()
            except Exception as e:
                # Handle duplicate link error gracefully
                db.session.rollback()
                if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
                    return jsonify({'success': False, 'message': f'{qr_id} already linked'})
                raise e
            
            # ULTRA-FAST: Skip count query for maximum speed
            # We can get count from client-side instead of server query
            
            # Instant JSON response (removed count query for speed)
            return jsonify({
                'success': True,
                'child_qr': qr_id,
                'parent_qr': parent_bag.qr_id,
                'message': f'{qr_id} linked!'
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Child scan error: {str(e)}')
            return jsonify({'success': False, 'message': f'Error processing scan: {str(e)}'})
    
    else:
        # Handle regular form submission
        form = ScanChildForm()
        
        if form.validate_on_submit():
            try:
                qr_id = sanitize_input(getattr(form, 'qr_id', form).data).strip()
                
                if not qr_id:
                    flash('Please enter a QR code.', 'error')
                    return render_template('scan_child.html', form=form)
                
                # Same logic as AJAX but with redirect
                # ... (similar processing logic)
                flash('Child bag scanned successfully!', 'success')
                return redirect(url_for('scan_complete', s=request.args.get('s')))
                
            except Exception as e:
                db.session.rollback()
                flash('Error processing scan. Please try again.', 'error')
                app.logger.error(f'Child scan error: {str(e)}')
        
        # Get parent bag from session for display
        parent_bag = None
        scanned_child_count = 0
        
        # Get parent QR from session
        parent_qr = session.get('current_parent_qr')
        if not parent_qr:
            # Try from last_scan as backup
            last_scan = session.get('last_scan')
            if last_scan and last_scan.get('type') == 'parent':
                parent_qr = last_scan.get('qr_id')
        
        if parent_qr:
            parent_bag = Bag.query.filter_by(qr_id=parent_qr, type=BagType.PARENT.value).first()
            if parent_bag:
                # Get count of linked child bags
                scanned_child_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
        
        return render_template('scan_child.html', 
                             form=form, 
                             parent_bag=parent_bag, 
                             scanned_child_count=scanned_child_count)

@app.route('/scan/complete')
@login_required
def scan_complete():
    """Completion page for scanning workflow"""
    last_scan = session.get('last_scan')
    if not last_scan:
        flash('No recent scan found.', 'info')
        return redirect(url_for('index'))
    
    return render_template('scan_complete.html', scan_data=last_scan)

@app.route('/scan/finish')
@login_required
def finish_scanning():
    """Complete the scanning process"""
    # Clear session data
    session.pop('last_scan', None)
    flash('Scanning session completed.', 'success')
    return redirect(url_for('index'))

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
        qr_id = sanitize_input(form.qr_id.data).strip()
    elif url_qr_id:
        # If there's a QR ID in the URL, use it for lookup
        qr_id = sanitize_input(url_qr_id).strip()
    elif request.method == 'POST':
        # Handle direct form submission without WTForms validation
        qr_id = sanitize_input(request.form.get('qr_id', '')).strip()
    else:
        qr_id = None
    
    if qr_id:
        app.logger.info(f'Lookup request for QR ID: {qr_id}')
        
        # Try exact match first (most efficient)
        bag = Bag.query.filter_by(qr_id=qr_id).first()
        if not bag:
            # Try case-insensitive lookup using SQLAlchemy's func.lower
            bag = Bag.query.filter(func.lower(Bag.qr_id) == qr_id.lower()).first()
        if not bag:
            # Try with original form data (for backward compatibility)
            original_qr = request.form.get('qr_id', '') if request.method == 'POST' else url_qr_id
            if original_qr and original_qr != qr_id:
                bag = Bag.query.filter_by(qr_id=original_qr).first()
        
        app.logger.info(f'Bag found: {bag.qr_id if bag else "None"}')
        app.logger.info(f'Total bags in database: {Bag.query.count()}')
        
        if bag:
            # Get related information based on bag type
            if bag.type == BagType.PARENT.value:
                # Get child bags using explicit join conditions
                child_bags = db.session.query(Bag).join(
                    Link, Link.child_bag_id == Bag.id
                ).filter(Link.parent_bag_id == bag.id).all()
                
                # Get bills this parent bag is linked to
                bills = db.session.query(Bill).join(
                    BillBag, BillBag.bill_id == Bill.id
                ).filter(BillBag.bag_id == bag.id).all()
                
                bag_info = {
                    'bag': bag,
                    'type': 'parent',
                    'child_bags': child_bags,
                    'bills': bills,
                    'parent_bag': None
                }
            else:  # Child bag
                # Get parent bag
                link = Link.query.filter_by(child_bag_id=bag.id).first()
                parent_bag = link.parent_bag if link else None
                
                # Get all child bags in the same parent (siblings)
                child_bags = []
                if parent_bag:
                    child_bags = db.session.query(Bag).join(
                        Link, Link.child_bag_id == Bag.id
                    ).filter(Link.parent_bag_id == parent_bag.id).all()
                
                # Get bills through parent bag
                bills = []
                if parent_bag:
                    bills = db.session.query(Bill).join(
                        BillBag, BillBag.bill_id == Bill.id
                    ).filter(BillBag.bag_id == parent_bag.id).all()
                
                bag_info = {
                    'bag': bag,
                    'type': 'child',
                    'child_bags': child_bags,
                    'bills': bills,
                    'parent_bag': parent_bag
                }
            
            # Get scan history
            if bag.type == BagType.PARENT.value:
                scans = Scan.query.filter_by(parent_bag_id=bag.id).order_by(desc(Scan.timestamp)).limit(10).all()
            else:
                scans = Scan.query.filter_by(child_bag_id=bag.id).order_by(desc(Scan.timestamp)).limit(10).all()
            
            bag_info['scans'] = scans
        else:
            # More descriptive error message based on the searched QR code
            original_qr = request.form.get('qr_id', qr_id)
            flash(f'Bag "{original_qr}" does not exist in the system. Please verify the QR code or create the bag first.', 'error')
    
    return render_template('child_lookup.html', form=form, bag_info=bag_info)

@app.route('/scans')
@login_required
def scan_history():
    """Scan history dashboard with filtering"""
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '').strip()
    
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



@app.route('/bags')
@login_required
def bag_management():
    """Complete bag management with all filtering options"""
    page = request.args.get('page', 1, type=int)
    bag_type = request.args.get('type', 'all')
    search_query = request.args.get('search', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    linked_status = request.args.get('linked_status', 'all')
    bill_status = request.args.get('bill_status', 'all')
    
    # Build query
    query = Bag.query
    
    # Area-based filtering for dispatchers
    if current_user.is_dispatcher() and current_user.dispatch_area:
        query = query.filter(Bag.dispatch_area == current_user.dispatch_area)
    
    # Type filter
    if bag_type != 'all':
        query = query.filter(Bag.type == bag_type)
    
    # Search filter
    if search_query:
        query = query.filter(
            or_(
                Bag.qr_id.contains(search_query),
                Bag.name.contains(search_query)
            )
        )
    
    # Date filters with validation
    date_error = None
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(func.date(Bag.created_at) >= from_date)
        except ValueError:
            date_error = "Invalid from date format"
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(func.date(Bag.created_at) <= to_date)
        except ValueError:
            date_error = "Invalid to date format"
    
    # Validate date range
    if date_from and date_to and not date_error:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            if to_date < from_date:
                date_error = "To date must be after From date"
        except ValueError:
            pass
    
    # Linked status filter
    if linked_status == 'linked':
        # Only bags that have links (parent bags with children or child bags with parents)
        query = query.filter(
            or_(
                and_(Bag.type == BagType.PARENT.value, 
                     Bag.id.in_(db.session.query(Link.parent_bag_id).distinct())),
                and_(Bag.type == BagType.CHILD.value, 
                     Bag.id.in_(db.session.query(Link.child_bag_id).distinct()))
            )
        )
    elif linked_status == 'unlinked':
        # Parent bags without children or child bags without parents
        query = query.filter(
            or_(
                and_(Bag.type == BagType.PARENT.value, 
                     ~Bag.id.in_(db.session.query(Link.parent_bag_id).distinct())),
                and_(Bag.type == BagType.CHILD.value, 
                     ~Bag.id.in_(db.session.query(Link.child_bag_id).distinct()))
            )
        )

    
    # Bill status filter - only applies to parent bags since only they can be in bills
    if bill_status == 'billed':
        # Only parent bags that are in bills
        query = query.filter(
            and_(
                Bag.type == BagType.PARENT.value,
                Bag.id.in_(db.session.query(BillBag.bag_id).distinct())
            )
        )
    elif bill_status == 'unbilled':
        # Only parent bags not in any bills
        query = query.filter(
            and_(
                Bag.type == BagType.PARENT.value,
                ~Bag.id.in_(db.session.query(BillBag.bag_id).distinct())
            )
        )
    
    # Get total count of filtered results before pagination
    filtered_count = query.count()
    
    # Paginate results
    bags = query.order_by(desc(Bag.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Calculate comprehensive stats
    total_bags = Bag.query.count()
    parent_bags = Bag.query.filter(Bag.type == BagType.PARENT.value).count()
    child_bags = Bag.query.filter(Bag.type == BagType.CHILD.value).count()
    
    # Linked/unlinked stats
    linked_parent_bags = db.session.query(func.count(func.distinct(Link.parent_bag_id))).scalar()
    linked_child_bags = db.session.query(func.count(func.distinct(Link.child_bag_id))).scalar()
    unlinked_bags = total_bags - linked_parent_bags - linked_child_bags
    
    stats = {
        'total_bags': total_bags,
        'parent_bags': parent_bags,
        'child_bags': child_bags,
        'linked_bags': linked_parent_bags + linked_child_bags,
        'unlinked_bags': unlinked_bags,
        'filtered_count': filtered_count
    }
    
    filters = {
        'type': bag_type,
        'date_from': date_from,
        'date_to': date_to,
        'linked_status': linked_status,
        'bill_status': bill_status
    }
    
    return render_template('bag_management.html', 
                         bags=bags, 
                         search_query=search_query, 
                         stats=stats, 
                         filters=filters,
                         date_error=date_error)

# Bill management routes
@app.route('/bills')
@login_required
def bill_management():
    """Bill management dashboard with search functionality - admin and biller access"""
    if not current_user.can_edit_bills():
        flash('Access restricted to admin and biller users.', 'error')
        return redirect(url_for('index'))
    
    # Get search parameters
    search_bill_id = request.args.get('search_bill_id', '').strip()
    status_filter = request.args.get('status_filter', 'all').strip()
    
    # Build query
    query = Bill.query
    
    # Apply bill ID search if provided
    if search_bill_id:
        query = query.filter(Bill.bill_id.contains(search_bill_id))
    
    # Get all bills first, then filter by status after calculating bag counts
    bills = query.order_by(desc(Bill.created_at)).all()
    
    # Get parent bags count for each bill and apply status filter
    bill_data = []
    for bill in bills:
        parent_bags = db.session.query(Bag).join(BillBag, Bag.id == BillBag.bag_id).filter(BillBag.bill_id == bill.id).all()
        parent_count = len(parent_bags)
        
        # Determine status based on bag count
        if parent_count == bill.parent_bag_count:
            bill_status = 'completed'
        elif parent_count > 0:
            bill_status = 'in_progress'
        else:
            bill_status = 'empty'
        
        # Apply status filter
        if status_filter == 'all' or status_filter == bill_status:
            bill_data.append({
                'bill': bill,
                'parent_bags': parent_bags,
                'parent_count': parent_count,
                'status': bill_status
            })
    
    return render_template('bill_management.html', 
                         bill_data=bill_data, 
                         search_bill_id=search_bill_id,
                         status_filter=status_filter)

@app.route('/bill/create', methods=['GET', 'POST'])
@login_required
def create_bill():
    """Create a new bill - admin and employee access"""
    if not (current_user.is_admin() or current_user.role == 'employee'):
        flash('Access restricted to admin and employee users.', 'error')
        return redirect(url_for('index'))
    if request.method == 'GET':
        # Display the create bill form
        return render_template('create_bill.html')
    
    # Handle POST request
    if request.method == 'POST':
        try:
            bill_id = sanitize_input(request.form.get('bill_id', '')).strip()
            parent_bag_count = request.form.get('parent_bag_count', 1, type=int)
            
            if not bill_id:
                flash('Bill ID is required.', 'error')
                return render_template('create_bill.html')
            
            # Basic validation - just check if bill_id is not empty
            if len(bill_id.strip()) == 0:
                flash('Bill ID cannot be empty.', 'error')
                return render_template('create_bill.html')
            
            # Comprehensive duplicate check for bill ID uniqueness
            is_valid, error_message = validate_new_bill_id(bill_id)
            if not is_valid:
                log_duplicate_attempt(bill_id, 'bill', 'bag', current_user.id)
                flash(error_message or 'Invalid bill ID', 'error')
                return render_template('create_bill.html')
            
            # Validate parent bag count
            if parent_bag_count < 1 or parent_bag_count > 50:
                flash('Number of parent bags must be between 1 and 50.', 'error')
                return render_template('create_bill.html')
            
            # Create new bill
            bill = Bill()
            bill.bill_id = bill_id
            bill.description = ''
            bill.parent_bag_count = parent_bag_count
            bill.status = 'new'
            
            db.session.add(bill)
            db.session.commit()
            
            app.logger.info(f'Bill created successfully: {bill_id} with {parent_bag_count} parent bags')
            flash('Bill created successfully!', 'success')
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
    """Delete a bill and all its bag links - admin only"""
    if not is_admin():
        flash('Admin access required to delete bills.', 'error')
        return redirect(url_for('bill_management'))
    try:
        bill = Bill.query.get_or_404(bill_id)
        
        # Delete all bag links first
        BillBag.query.filter_by(bill_id=bill.id).delete()
        
        # Delete the bill
        db.session.delete(bill)
        db.session.commit()
        
        flash('Bill deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error deleting bill.', 'error')
        app.logger.error(f'Bill deletion error: {str(e)}')
    
    return redirect(url_for('bill_management'))

@app.route('/bill/<int:bill_id>/finish', methods=['GET', 'POST'])
@login_required
def finish_bill_scan(bill_id):
    """Complete bill scanning and mark as finished - admin and employee access"""
    if not (is_admin() or session.get('user_role') == 'employee'):
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
    """View bill details with parent bags and child bags"""
    bill = Bill.query.get_or_404(bill_id)
    
    # Get all parent bags linked to this bill
    parent_bags_raw = db.session.query(Bag).join(BillBag, Bag.id == BillBag.bag_id).filter(BillBag.bill_id == bill.id).all()
    
    # Format parent bags data for template
    parent_bags = []
    for parent_bag in parent_bags_raw:
        # Get child bags for this parent
        child_bags = db.session.query(Bag).join(Link, Bag.id == Link.child_bag_id).filter(Link.parent_bag_id == parent_bag.id).all()
        
        parent_bags.append({
            'parent_bag': parent_bag,
            'child_count': len(child_bags),
            'child_bags': child_bags
        })
    
    # Get all child bags for scan history
    all_child_bags = []
    for parent_bag in parent_bags_raw:
        children = db.session.query(Bag).join(Link, Bag.id == Link.child_bag_id).filter(Link.parent_bag_id == parent_bag.id).all()
        all_child_bags.extend(children)
    
    # Get scan history for all bags in this bill
    scans = Scan.query.filter(
        or_(
            Scan.parent_bag_id.in_([bag.id for bag in parent_bags_raw]),
            Scan.child_bag_id.in_([bag.id for bag in all_child_bags])
        )
    ).order_by(desc(Scan.timestamp)).all()
    
    # Count of parent bags linked to this bill
    bag_links_count = len(parent_bags_raw)
    
    return render_template('view_bill.html', 
                         bill=bill, 
                         parent_bags=parent_bags, 
                         child_bags=all_child_bags,
                         scans=scans,
                         bag_links_count=bag_links_count)

@app.route('/bill/<int:bill_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bill(bill_id):
    """Edit bill details - admin and employee access"""
    if not (current_user.is_admin() or current_user.role == 'employee'):
        flash('Access restricted to admin and employee users.', 'error')
        return redirect(url_for('bill_management'))
    
    bill = Bill.query.get_or_404(bill_id)
    
    if request.method == 'POST':
        try:
            # Debug logging
            app.logger.info(f'Edit bill POST request for bill_id: {bill_id}')
            app.logger.info(f'Form data: {dict(request.form)}')
            
            description = request.form.get('description', '').strip()
            parent_bag_count = request.form.get('parent_bag_count', type=int)
            
            app.logger.info(f'Parsed - description: "{description}", parent_bag_count: {parent_bag_count}')
            
            # Store original values for comparison
            original_description = bill.description
            original_count = bill.parent_bag_count
            
            # Always update description (can be empty)
            bill.description = description
            
            # Update parent bag count if valid
            if parent_bag_count and parent_bag_count > 0:
                bill.parent_bag_count = parent_bag_count
            
            # Check if anything actually changed
            if bill.description != original_description or bill.parent_bag_count != original_count:
                db.session.commit()
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
    if not (current_user.is_admin() or current_user.role == 'employee'):
        flash('Access restricted to admin and employee users.', 'error')
        return redirect(url_for('bill_management'))
    
    try:
        parent_qr = request.form.get('parent_qr')
        bill_id = request.form.get('bill_id', type=int)
        
        if not parent_qr or not bill_id:
            flash('Missing required information.', 'error')
            return redirect(url_for('bill_management'))
        
        # Find the parent bag
        parent_bag = Bag.query.filter_by(qr_id=parent_qr, type=BagType.PARENT.value).first()
        if not parent_bag:
            flash('Parent bag not found.', 'error')
            return redirect(url_for('scan_bill_parent', bill_id=bill_id))
        
        # Find and remove the bill-bag link
        bill_bag = BillBag.query.filter_by(bill_id=bill_id, bag_id=parent_bag.id).first()
        if bill_bag:
            db.session.delete(bill_bag)
            db.session.commit()
            flash(f'Parent bag {parent_qr} removed from bill successfully.', 'success')
        else:
            flash('Bag link not found.', 'error')
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept', '').find('application/json') != -1
        
        if is_ajax:
            # For AJAX requests, return JSON
            current_bag_count = BillBag.query.filter_by(bill_id=bill_id).count()
            bill = Bill.query.get(bill_id)
            return jsonify({
                'success': True, 
                'message': f'Parent bag {parent_qr} removed successfully.',
                'linked_count': current_bag_count,
                'expected_count': bill.parent_bag_count or 10 if bill else 10
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
        return redirect(url_for('index'))
    
    # Get the bill or return 404 if not found
    bill = Bill.query.get_or_404(bill_id)
    
    form = ScanParentForm()
    
    # Get current parent bags linked to this bill
    linked_bags = db.session.query(Bag).join(BillBag, Bag.id == BillBag.bag_id).filter(BillBag.bill_id == bill.id).all()
    
    # Get current count for debugging
    current_count = bill.bag_links.count()
    app.logger.info(f'Scan bill parent page - Bill {bill.id} has {current_count} linked bags')
    
    return render_template('scan_bill_parent.html', form=form, bill=bill, linked_bags=linked_bags)

@app.route('/process_bill_parent_scan', methods=['POST'])
@login_required
def process_bill_parent_scan():
    """Process a parent bag scan for bill linking - admin and employee access"""
    if not (hasattr(current_user, 'is_admin') and current_user.is_admin() or 
            hasattr(current_user, 'role') and current_user.role in ['admin', 'biller', 'dispatcher']):
        return jsonify({'success': False, 'message': 'Access restricted to admin and employee users.'})
    
    bill_id = request.form.get('bill_id')
    qr_code = request.form.get('qr_code')
    
    if not bill_id:
        return jsonify({'success': False, 'message': 'Bill ID missing.'})
    
    if not qr_code:
        return jsonify({'success': False, 'message': 'QR code missing.'})
    
    try:
        app.logger.info(f'Processing bill parent scan - bill_id: {bill_id}, qr_code: {qr_code}')
        
        bill = Bill.query.get_or_404(bill_id)
        qr_id = sanitize_input(qr_code).strip()  # Don't force uppercase to preserve original format
        
        app.logger.info(f'Sanitized QR code: {qr_id}')
        
        # First validate that it's not a URL
        is_qr_valid, qr_error = validate_qr_code(qr_id)
        if not is_qr_valid:
            app.logger.warning(f'Invalid QR code: {qr_id} - {qr_error}')
            return jsonify({'success': False, 'message': qr_error})
        
        is_valid, error_message, child_count = validate_parent_qr_id(qr_id)
        if not is_valid:
            app.logger.warning(f'Invalid parent QR format: {qr_id} - {error_message}')
            return jsonify({'success': False, 'message': f'Invalid parent bag QR code format: {error_message}'})
        
        # Check if this QR code exists and validate it can be used as parent bag
        existing_bag = Bag.query.filter_by(qr_id=qr_id).first()
        
        if existing_bag:
            if existing_bag.type == BagType.CHILD.value:
                log_duplicate_attempt(qr_id, 'parent', 'child', current_user.id)
                return jsonify({'success': False, 'message': f'QR code {qr_id} is already registered as a child bag. Cannot use as parent bag for bills.'})
            elif existing_bag.type == BagType.PARENT.value:
                parent_bag = existing_bag
            else:
                return jsonify({'success': False, 'message': f'Invalid bag type for QR code {qr_id}.'})
        else:
            # Check if QR code conflicts with bill IDs
            is_unique, conflict_type, conflict_details = check_qr_code_uniqueness(qr_id)
            if not is_unique and conflict_type == 'bill':
                log_duplicate_attempt(qr_id, 'parent', 'bill', current_user.id)
                return jsonify({'success': False, 'message': f'QR code {qr_id} is already used as a bill ID. Cannot use as parent bag.'})
            
            # Try exact match for existing parent bag first
            parent_bag = Bag.query.filter(
                Bag.qr_id == qr_id,
                Bag.type == BagType.PARENT.value
            ).first()
            
            # If no exact match, try case-insensitive search
            if not parent_bag:
                parent_bag = Bag.query.filter(
                    func.lower(Bag.qr_id) == qr_id.lower(),
                    Bag.type == BagType.PARENT.value
                ).first()
        
        if not parent_bag:
            app.logger.warning(f'Parent bag not found: {qr_id}')
            # Check if bag exists with different type (exact match first, then case-insensitive)
            any_bag = Bag.query.filter(Bag.qr_id == qr_id).first()
            if not any_bag:
                any_bag = Bag.query.filter(func.lower(Bag.qr_id) == qr_id.lower()).first()
            if any_bag:
                app.logger.info(f'Found bag with type: {any_bag.type} and QR: {any_bag.qr_id}')
                return jsonify({'success': False, 'message': f'QR code {any_bag.qr_id} exists but is registered as a {any_bag.type} bag, not a parent bag.'})
            
            # List available parent bags for reference
            available_parents = Bag.query.filter(Bag.type == BagType.PARENT.value).limit(5).all()
            available_qrs = [bag.qr_id for bag in available_parents]
            
            if available_qrs:
                return jsonify({'success': False, 'message': f'Parent bag with QR code "{qr_id}" not found. Available parent bags: {", ".join(available_qrs)}'})
            else:
                return jsonify({'success': False, 'message': f'Parent bag with QR code "{qr_id}" not found. No parent bags exist in the system yet.'})
        
        app.logger.info(f'Found parent bag: {parent_bag.qr_id}')
        
        # Check if already linked to this bill
        existing_link = BillBag.query.filter_by(bill_id=bill.id, bag_id=parent_bag.id).first()
        if existing_link:
            app.logger.warning(f'Bag already linked to bill: {qr_id}')
            return jsonify({'success': False, 'message': 'This parent bag is already linked to this bill.'})
        
        # Check if parent bag is already linked to any other bill
        existing_bill_link = BillBag.query.filter_by(bag_id=parent_bag.id).first()
        if existing_bill_link:
            linked_bill = Bill.query.get(existing_bill_link.bill_id)
            if linked_bill:
                app.logger.warning(f'Parent bag {qr_id} already linked to bill {linked_bill.bill_id}')
                return jsonify({
                    'success': False, 
                    'message': f'This parent bag is already linked to bill {linked_bill.bill_id}. Each parent bag can only be attached to one bill.'
                })
            else:
                app.logger.warning(f'Parent bag {qr_id} has invalid bill link, cleaning up')
                # Clean up invalid link
                db.session.delete(existing_bill_link)
                db.session.commit()
        
        # Check if bill already has the maximum number of bags
        current_bag_count = BillBag.query.filter_by(bill_id=bill.id).count()
        app.logger.info(f'Current bag count: {current_bag_count}, max: {bill.parent_bag_count}')
        
        if current_bag_count >= bill.parent_bag_count:
            return jsonify({'success': False, 'message': f'Bill already has the maximum number of parent bags ({bill.parent_bag_count}). Cannot add more bags.'})
        
        # Create bill-bag link
        bill_bag = BillBag()
        bill_bag.bill_id = bill.id
        bill_bag.bag_id = parent_bag.id
        
        db.session.add(bill_bag)
        db.session.commit()
        
        app.logger.info(f'Successfully linked parent bag {qr_id} to bill {bill.bill_id}')
        
        # Get updated count after adding the bag
        updated_bag_count = BillBag.query.filter_by(bill_id=bill.id).count()
        
        app.logger.info(f'Response data - linked_count: {updated_bag_count}, expected_count: {bill.parent_bag_count}')
        
        response_data = {
            'success': True, 
            'message': f'Parent bag {qr_id} linked to bill successfully!',
            'parent_qr': qr_id,
            'linked_count': updated_bag_count,
            'expected_count': bill.parent_bag_count or 10,  # Ensure expected_count is always set
            'remaining_bags': (bill.parent_bag_count or 10) - updated_bag_count
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
    """Display detailed information about a specific bag"""
    # URL decode the qr_id to handle special characters
    from urllib.parse import unquote
    qr_id = unquote(qr_id)
    
    # Log the QR ID for debugging
    app.logger.info(f'Looking up bag with QR ID: {qr_id}')
    
    bag = Bag.query.filter_by(qr_id=qr_id).first_or_404()
    
    # Get related information
    if bag.type == BagType.PARENT.value:
        # Get child bags through links
        links = Link.query.filter_by(parent_bag_id=bag.id).all()
        child_bags = [Bag.query.get(link.child_bag_id) for link in links if link.child_bag_id]
        child_bags = [child for child in child_bags if child]  # Filter out None values
        parent_bag = None
        bills = db.session.query(Bill).join(BillBag).filter(BillBag.bag_id == bag.id).all()
        scans = Scan.query.filter_by(parent_bag_id=bag.id).order_by(desc(Scan.timestamp)).all()
    else:
        child_bags = []
        link = Link.query.filter_by(child_bag_id=bag.id).first()
        parent_bag = Bag.query.get(link.parent_bag_id) if link and link.parent_bag_id else None
        bills = []
        if parent_bag:
            bills = db.session.query(Bill).join(BillBag).filter(BillBag.bag_id == parent_bag.id).all()
        scans = Scan.query.filter_by(child_bag_id=bag.id).order_by(desc(Scan.timestamp)).all()
    
    return render_template('bag_detail.html',
                         bag=bag,
                         child_bags=child_bags,
                         parent_bag=parent_bag,
                         bills=bills,
                         scans=scans,
                         is_parent=bag.type == BagType.PARENT.value,
                         link=bills[0] if bills else None)

# API endpoints for dashboard data
@app.route('/api/stats')
def api_dashboard_stats():
    """Get dashboard statistics"""
    try:
        total_parent_bags = Bag.query.filter_by(type=BagType.PARENT.value).count()
        total_child_bags = Bag.query.filter_by(type=BagType.CHILD.value).count()
        total_scans = Scan.query.count()
        total_bills = Bill.query.count() if 'Bill' in globals() else 0
        
        # Update dashboard elements - show 0 if count is zero
        stats = {
            'total_parent_bags': total_parent_bags,
            'total_child_bags': total_child_bags,
            'total_scans': total_scans,
            'total_bills': total_bills,
            'total_products': total_parent_bags + total_child_bags,
            'status_counts': {
                'active': total_parent_bags + total_child_bags,
                'scanned': total_scans
            }
        }
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/scans')
def api_recent_scans():
    """Get recent scans for dashboard"""
    try:
        limit = request.args.get('limit', 20, type=int)
        scans = Scan.query.order_by(desc(Scan.timestamp)).limit(limit).all()
        
        scan_data = []
        for scan in scans:
            bag = None
            if scan.parent_bag_id:
                bag = Bag.query.get(scan.parent_bag_id)
            elif scan.child_bag_id:
                bag = Bag.query.get(scan.child_bag_id)
            
            scan_data.append({
                'id': scan.id,
                'timestamp': scan.timestamp.isoformat() if scan.timestamp else None,
                'product_qr': bag.qr_id if bag else 'Unknown',
                'product_name': bag.name if bag else 'Unknown Product',
                'type': 'parent' if scan.parent_bag_id else 'child',
                'username': scan.scanned_by.username if scan.scanned_by else 'Unknown'
            })
        
        return jsonify({
            'success': True,
            'scans': scan_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/activity/<int:days>')
@login_required
def api_activity_stats(days):
    """Get scan activity statistics for the past X days"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        # Query scan counts by date
        activity_data = db.session.query(
            func.date(Scan.timestamp).label('date'),
            func.count(Scan.id).label('scan_count')
        ).filter(
            func.date(Scan.timestamp) >= start_date,
            func.date(Scan.timestamp) <= end_date
        ).group_by(
            func.date(Scan.timestamp)
        ).all()
        
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
            parent_bag = Bag.query.filter_by(qr_id=parent_qr, type='parent').first()
        
        # If not found, try last_scan
        if not parent_bag:
            last_scan = session.get('last_scan')
            if last_scan and last_scan.get('type') == 'parent':
                parent_qr_id = last_scan.get('qr_id')
                if parent_qr_id:
                    parent_bag = Bag.query.filter_by(qr_id=parent_qr_id, type=BagType.PARENT.value).first()
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
        
        parent_bag = Bag.query.filter_by(qr_id=parent_qr, type='parent').first()
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

@app.route('/api/delete-bag', methods=['POST'])
@login_required
def api_delete_bag():
    """Delete a bag and handle parent/child relationships"""
    try:
        qr_code = request.form.get('qr_code')
        if not qr_code:
            return jsonify({
                'success': False,
                'message': 'QR code is required'
            })
        
        bag = Bag.query.filter_by(qr_id=qr_code).first()
        if not bag:
            return jsonify({
                'success': False,
                'message': 'Bag not found'
            })
        
        if bag.type == 'parent':
            # Delete parent bag and all its linked child bags
            links = Link.query.filter_by(parent_bag_id=bag.id).all()
            child_count = len(links)
            
            # Delete all child bags and their links
            for link in links:
                child_bag = Bag.query.get(link.child_bag_id)
                if child_bag:
                    # Delete child bag scans
                    child_scans = Scan.query.filter_by(child_bag_id=child_bag.id).all()
                    for scan in child_scans:
                        db.session.delete(scan)
                    # Delete child bag
                    db.session.delete(child_bag)
                # Delete link
                db.session.delete(link)
            
            # Delete parent bag scans
            parent_scans = Scan.query.filter_by(parent_bag_id=bag.id).all()
            for scan in parent_scans:
                db.session.delete(scan)
            
            # Delete bill links if any
            bill_links = BillBag.query.filter_by(bag_id=bag.id).all()
            for bill_link in bill_links:
                db.session.delete(bill_link)
            
            # Delete parent bag
            db.session.delete(bag)
            db.session.commit()
            
            message = f'Parent bag {qr_code} and {child_count} linked child bags deleted successfully'
            
        else:
            # Delete child bag only
            # Remove link to parent
            link = Link.query.filter_by(child_bag_id=bag.id).first()
            if link:
                db.session.delete(link)
            
            # Delete child bag scans
            child_scans = Scan.query.filter_by(child_bag_id=bag.id).all()
            for scan in child_scans:
                db.session.delete(scan)
            
            # Delete child bag
            db.session.delete(bag)
            db.session.commit()
            
            message = f'Child bag {qr_code} deleted successfully'
        
        app.logger.info(f"Deleted bag {qr_code} ({bag.type})")
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error deleting bag: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Error deleting bag'
        }), 500

@app.route('/edit-parent/<parent_qr>')
@login_required
def edit_parent_children(parent_qr):
    """Edit parent bag children page"""
    parent_bag = Bag.query.filter_by(qr_id=parent_qr, type='parent').first_or_404()
    
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
    """Edit the child bag list for a parent bag"""
    try:
        parent_qr = request.form.get('parent_qr')
        child_qrs = request.form.getlist('child_qrs[]')  # List of child QR codes
        
        if not parent_qr:
            return jsonify({
                'success': False,
                'message': 'Parent QR code is required'
            })
        
        parent_bag = Bag.query.filter_by(qr_id=parent_qr, type='parent').first()
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
                    child_bag.type = BagType.CHILD.value
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
        parent_bag = Bag.query.filter_by(qr_id=parent_qr, type='parent').first()
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
