import logging
import re
import io
import base64
import qrcode
from flask import render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import generate_csrf
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

from app_clean import app, db, limiter
from models import User, UserRole, Bag, BagType, Link, Scan, Bill, BillBag
from forms import LoginForm, RegistrationForm, LocationSelectionForm, ScanParentForm, ScanChildForm, ChildLookupForm, PromoteToAdminForm, BillCreationForm
from account_security import is_account_locked, record_failed_attempt, reset_failed_attempts, track_login_activity
from validation_utils import validate_parent_qr_id, validate_child_qr_id, validate_bill_id, sanitize_input

# Analytics and User Management functionality
@app.route('/analytics')
@login_required
def analytics():
    """Analytics dashboard for system insights"""
    if not current_user.is_admin():
        flash('Admin access required for analytics.', 'danger')
        return redirect(url_for('index'))
    
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    
    # Basic statistics
    total_scans = Scan.query.count()
    total_bags = Bag.query.count()
    active_users = User.query.filter(User.verified == True).count()
    
    # User activity statistics
    user_stats = []
    today = datetime.now().date()
    
    users = User.query.all()
    max_user_scans = 0
    
    for user in users:
        total_user_scans = Scan.query.filter_by(user_id=user.id).count()
        today_scans = Scan.query.filter(
            Scan.user_id == user.id,
            func.date(Scan.timestamp) == today
        ).count()
        
        last_scan = Scan.query.filter_by(user_id=user.id).order_by(Scan.timestamp.desc()).first()
        last_active = last_scan.timestamp if last_scan else None
        
        user_stats.append({
            'username': user.username,
            'is_admin': user.is_admin(),
            'total_scans': total_user_scans,
            'today_scans': today_scans,
            'last_active': last_active
        })
        
        if total_user_scans > max_user_scans:
            max_user_scans = total_user_scans
    
    # Scans over time (last 7 days)
    scans_over_time = {'labels': [], 'data': []}
    for i in range(6, -1, -1):
        date = datetime.now().date() - timedelta(days=i)
        scan_count = Scan.query.filter(func.date(Scan.timestamp) == date).count()
        scans_over_time['labels'].append(date.strftime('%m/%d'))
        scans_over_time['data'].append(scan_count)
    
    # Location data
    location_data = {'labels': [], 'data': []}
    locations = Location.query.all()
    for location in locations:
        scan_count = Scan.query.filter_by(location_id=location.id).count()
        location_data['labels'].append(location.name)
        location_data['data'].append(scan_count)
    
    # Ensure we have some default data if no locations exist
    if not location_data['labels']:
        location_data['labels'] = ['No Data']
        location_data['data'] = [0]
    
    # Performance metrics
    daily_scans = Scan.query.filter(func.date(Scan.timestamp) == today).count()
    daily_performance = min((daily_scans / max(total_scans / 30, 1)) * 100, 100) if total_scans > 0 else 0
    
    linked_bags = db.session.query(Link.parent_bag_id).distinct().count() + db.session.query(Link.child_bag_id).distinct().count()
    bag_utilization = (linked_bags / max(total_bags, 1)) * 100 if total_bags > 0 else 0
    
    active_locations = db.session.query(Scan.location_id).distinct().count()
    location_coverage = (active_locations / max(total_locations, 1)) * 100 if total_locations > 0 else 0
    
    # Recent activity with proper relationships
    recent_activity = Scan.query.order_by(Scan.timestamp.desc()).limit(20).all()
    
    analytics_data = {
        'total_scans': total_scans,
        'total_bags': total_bags,
        'active_users': active_users,
        'total_locations': total_locations,
        'user_stats': user_stats,
        'max_user_scans': max_user_scans,
        'scans_over_time': scans_over_time,
        'location_data': location_data,
        'daily_performance': round(daily_performance, 1),
        'bag_utilization': round(bag_utilization, 1),
        'location_coverage': round(location_coverage, 1),
        'recent_activity': recent_activity
    }
    
    return render_template('analytics.html', analytics=analytics_data)

@app.route('/admin/users')
@login_required
def user_management():
    """User management dashboard for admins"""
    if not current_user.is_admin():
        flash('Admin access required for user management.', 'danger')
        return redirect(url_for('index'))
    
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    # Get all users with additional data
    users = User.query.all()
    today = datetime.now().date()
    week_ago = datetime.now() - timedelta(days=7)
    
    # Add scan counts and last activity to users
    for user in users:
        user.scan_count = Scan.query.filter_by(user_id=user.id).count()
        last_scan = Scan.query.filter_by(user_id=user.id).order_by(Scan.timestamp.desc()).first()
        user.last_activity = last_scan.timestamp if last_scan else None
    
    # User statistics
    user_stats = {
        'total_users': len(users),
        'active_users': Scan.query.filter(func.date(Scan.timestamp) == today).distinct(Scan.user_id).count(),
        'admin_users': User.query.filter_by(role=UserRole.ADMIN.value).count(),
        'new_users_this_week': User.query.filter(User.created_at >= week_ago).count()
    }
    
    return render_template('user_management.html', users=users, user_stats=user_stats)

@app.route('/admin/users/create', methods=['POST'])
@login_required
def create_user():
    """Create a new user"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    try:
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'employee')
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('user_management'))
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('user_management'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('user_management'))
        
        # Create new user
        new_user = User()
        new_user.username = username
        new_user.email = email
        new_user.set_password(password)
        new_user.role = role
        new_user.verified = True  # Admin-created users are automatically verified
        
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'User {username} created successfully.', 'success')
        return redirect(url_for('user_management'))
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating user: {str(e)}")
        flash('Error creating user. Please try again.', 'danger')
        return redirect(url_for('user_management'))

@app.route('/admin/users/<int:user_id>')
@login_required
def get_user(user_id):
    """Get user data for editing"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
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
    
    try:
        user = User.query.get_or_404(user_id)
        
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'employee')
        
        # Validation
        if not username or not email:
            flash('Username and email are required.', 'danger')
            return redirect(url_for('user_management'))
        
        # Check for duplicate username/email (excluding current user)
        existing_user = User.query.filter(User.username == username, User.id != user_id).first()
        if existing_user:
            flash('Username already exists.', 'danger')
            return redirect(url_for('user_management'))
        
        existing_email = User.query.filter(User.email == email, User.id != user_id).first()
        if existing_email:
            flash('Email already exists.', 'danger')
            return redirect(url_for('user_management'))
        
        # Update user
        user.username = username
        user.email = email
        user.role = role
        
        if password:
            user.set_password(password)
        
        db.session.commit()
        flash(f'User {username} updated successfully.', 'success')
        return redirect(url_for('user_management'))
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating user: {str(e)}")
        flash('Error updating user. Please try again.', 'danger')
        return redirect(url_for('user_management'))

@app.route('/admin/users/<int:user_id>/promote', methods=['POST'])
@login_required
def promote_user(user_id):
    """Promote user to admin"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    try:
        user = User.query.get_or_404(user_id)
        user.role = UserRole.ADMIN.value
        db.session.commit()
        return jsonify({'success': True, 'message': f'User {user.username} promoted to admin'})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error promoting user: {str(e)}")
        return jsonify({'success': False, 'message': 'Error promoting user'}), 500

@app.route('/admin/users/<int:user_id>/demote', methods=['POST'])
@login_required
def demote_user(user_id):
    """Demote admin to employee"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    try:
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot demote yourself'}), 400
        
        user.role = UserRole.EMPLOYEE.value
        db.session.commit()
        return jsonify({'success': True, 'message': f'User {user.username} demoted to employee'})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error demoting user: {str(e)}")
        return jsonify({'success': False, 'message': 'Error demoting user'}), 500

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete user account"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    try:
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot delete yourself'}), 400
        
        username = user.username
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True, 'message': f'User {username} deleted successfully'})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting user: {str(e)}")
        return jsonify({'success': False, 'message': 'Error deleting user'}), 500

@app.route('/admin/seed_data')
@login_required
def seed_sample_data():
    """Create sample data for testing analytics (admin only)"""
    if not current_user.is_admin():
        flash('Admin access required.', 'danger')
        return redirect(url_for('index'))
    
    try:
        from datetime import datetime, timedelta
        import random
        
        # Create locations if none exist
        if Location.query.count() == 0:
            locations_data = [
                {'name': 'Warehouse A', 'address': '123 Storage St'},
                {'name': 'Warehouse B', 'address': '456 Logistics Ave'},
                {'name': 'Distribution Center', 'address': '789 Supply Chain Blvd'},
                {'name': 'Retail Store', 'address': '321 Commerce St'}
            ]
            
            for loc_data in locations_data:
                location = Location()
                location.name = loc_data['name']
                db.session.add(location)
            
            db.session.commit()
        
        # Create sample bags if few exist
        if Bag.query.count() < 10:
            for i in range(1, 11):
                if not Bag.query.filter_by(qr_id=f"PAR{i:03d}").first():
                    bag = Bag()
                    bag.qr_id = f"PAR{i:03d}"
                    bag.type = BagType.PARENT.value
                    bag.name = f"Parent Bag {i}"
                    db.session.add(bag)
            
            for i in range(1, 21):
                if not Bag.query.filter_by(qr_id=f"CHI{i:03d}").first():
                    bag = Bag()
                    bag.qr_id = f"CHI{i:03d}"
                    bag.type = BagType.CHILD.value
                    bag.name = f"Child Bag {i}"
                    db.session.add(bag)
            
            db.session.commit()
        
        # Create sample scans for analytics
        if Scan.query.count() < 20:
            locations = Location.query.all()
            bags = Bag.query.all()
            
            if locations and bags:
                for days_ago in range(7):
                    scan_date = datetime.now() - timedelta(days=days_ago)
                    scans_for_day = random.randint(3, 8)
                    
                    for _ in range(scans_for_day):
                        scan = Scan()
                        scan.timestamp = scan_date.replace(
                            hour=random.randint(8, 18),
                            minute=random.randint(0, 59)
                        )
                        scan.location_id = random.choice(locations).id
                        scan.user_id = current_user.id
                        
                        bag = random.choice(bags)
                        if bag.type == BagType.PARENT.value:
                            scan.parent_bag_id = bag.id
                        else:
                            scan.child_bag_id = bag.id
                        
                        db.session.add(scan)
                
                db.session.commit()
        
        flash('Sample data created successfully for analytics testing.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating sample data: {str(e)}")
        flash('Error creating sample data.', 'danger')
    
    return redirect(url_for('analytics'))

@app.route('/export/analytics_csv')
@login_required
def export_analytics_csv():
    """Export analytics data as CSV"""
    if not current_user.is_admin():
        flash('Admin access required for exports.', 'danger')
        return redirect(url_for('index'))
    
    try:
        from io import StringIO
        import csv
        from datetime import datetime
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write analytics summary
        writer.writerow(['TraceTrack Analytics Export'])
        writer.writerow(['Generated on:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        # System statistics
        writer.writerow(['System Statistics'])
        writer.writerow(['Total Scans', Scan.query.count()])
        writer.writerow(['Total Bags', Bag.query.count()])
        writer.writerow(['Active Users', User.query.filter(User.verified == True).count()])
        writer.writerow(['Total Locations', Location.query.count()])
        writer.writerow([])
        
        # User activity
        writer.writerow(['User Activity'])
        writer.writerow(['Username', 'Email', 'Role', 'Total Scans', 'Created Date'])
        
        users = User.query.all()
        for user in users:
            scan_count = Scan.query.filter_by(user_id=user.id).count()
            writer.writerow([
                user.username,
                user.email,
                user.role,
                scan_count,
                user.created_at.strftime('%Y-%m-%d')
            ])
        
        output.seek(0)
        response = app.response_class(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=analytics_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
        )
        return response
        
    except Exception as e:
        logging.error(f"Error exporting analytics: {str(e)}")
        flash('Error exporting analytics data.', 'danger')
        return redirect(url_for('analytics'))

# Export functionality
@app.route('/export/<format>')
@login_required
def export_data(format):
    """Export data in various formats"""
    if not current_user.is_admin:
        flash('Admin access required for exports.', 'danger')
        return redirect(url_for('index'))
    
    try:
        if format == 'csv':
            # Export all bags data
            from io import StringIO
            import csv
            
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['Type', 'QR ID', 'Name', 'Created At', 'Status'])
            
            bags = Bag.query.all()
            for bag in bags:
                bag_type = 'Parent' if bag.type == BagType.PARENT.value else 'Child'
                writer.writerow([
                    bag_type,
                    bag.qr_id,
                    bag.name or f'{bag_type} Bag',
                    bag.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'Active'
                ])
            
            output.seek(0)
            response = app.response_class(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=tracetrack_export.csv'}
            )
            return response
            
        elif format == 'analytics':
            # Generate analytics report
            stats = {
                'total_parent_bags': Bag.query.filter_by(type=BagType.PARENT.value).count(),
                'total_child_bags': Bag.query.filter_by(type=BagType.CHILD.value).count(),
                'total_bills': Bill.query.count(),
                'total_scans': Scan.query.count(),
                'recent_scans': Scan.query.order_by(Scan.timestamp.desc()).limit(10).all()
            }
            return render_template('analytics_report.html', stats=stats)
            
    except Exception as e:
        flash(f'Export failed: {str(e)}', 'danger')
        return redirect(url_for('index'))

# User management routes
@app.route('/users')
@login_required
def manage_users():
    """User management for administrators"""
    if not current_user.is_admin:
        flash('Admin access required.', 'danger')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('user_management_fixed.html', users=users)

@app.route('/api/users/<int:user_id>/role', methods=['POST'])
@login_required
def update_user_role(user_id):
    """Update user role"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'})
    
    data = request.get_json()
    new_role = data.get('role')
    
    if new_role not in ['admin', 'employee']:
        return jsonify({'success': False, 'message': 'Invalid role'})
    
    user = User.query.get_or_404(user_id)
    user.is_admin = (new_role == 'admin')
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': f'User role updated to {new_role}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# Webhook notifications
@app.route('/api/webhook/scan', methods=['POST'])
def webhook_scan_notification():
    """Webhook endpoint for scan notifications"""
    data = request.get_json()
    
    # Log critical movements
    if data.get('bag_type') == 'parent' and data.get('location_change'):
        # This would integrate with external notification services
        # For now, we'll log the event
        app.logger.info(f"Critical movement detected: {data}")
    
    return jsonify({'status': 'received'})

# Main routes
@app.route('/')
def index():
    """Main dashboard page"""
    stats = {
        'parent_bags': Bag.query.filter_by(type=BagType.PARENT.value).count(),
        'child_bags': Bag.query.filter_by(type=BagType.CHILD.value).count(),
        'bills': Bill.query.count(),
        'total_scans': Scan.query.count()
    }
    
    recent_scans = []
    if current_user.is_authenticated:
        # Optimized query with eager loading to reduce N+1 queries
        from sqlalchemy.orm import joinedload
        recent_scans = (Scan.query
                       .join(Location, Scan.location_id == Location.id, isouter=True)
                       .join(Bag, Scan.parent_bag_id == Bag.id, isouter=True)
                       .join(User, Scan.user_id == User.id, isouter=True)
                       .order_by(Scan.timestamp.desc())
                       .limit(10)
                       .all())
    
    return render_template('index.html', 
                           user=current_user,
                           is_admin=current_user.is_admin() if current_user.is_authenticated else False,
                           stats=stats,
                           recent_scans=recent_scans)

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"])
@limiter.limit("5/minute, 100/day", error_message="Too many login attempts, please try again later.")
def login():
    """User login page with rate limiting and account lockout to prevent brute force attacks"""
    from forms import LoginForm
    import traceback
    
    # If user is already logged in, redirect to homepage
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    
    try:
        # Handle login attempts
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data
            remember = form.remember.data
            
            logging.debug(f"Login attempt for username: {username}")
            
            try:
                # Check if the account is locked
                is_locked, remaining_time = is_account_locked(username)
                if is_locked:
                    flash(f'Account temporarily locked. Try again in {remaining_time} seconds.', 'danger')
                    return render_template('login.html', form=form, login_attempts={'is_locked': True, 'lockout_time': remaining_time})
            except Exception as e:
                logging.error(f"Error checking account lock: {str(e)}")
                logging.error(traceback.format_exc())
            
            try:
                # Find the user
                user = User.query.filter_by(username=username).first()
                
                # Handle non-existent user
                if not user:
                    flash('Invalid username or password.', 'danger')
                    return render_template('login.html', form=form)
            except Exception as e:
                logging.error(f"Error finding user: {str(e)}")
                logging.error(traceback.format_exc())
            
            try:
                # Verify password
                if not user.check_password(password):
                    # Record failed login attempt
                    is_locked, attempts, lockout_time = record_failed_attempt(username)
                    
                    if is_locked:
                        flash(f'Account locked due to too many failed attempts. Try again in {lockout_time}.', 'danger')
                        login_attempts = {'is_locked': True, 'lockout_time': lockout_time}
                    else:
                        flash(f'Invalid username or password. {attempts} attempts remaining before lockout.', 'danger')
                        login_attempts = {'attempts_remaining': attempts}
                    
                    return render_template('login.html', form=form, login_attempts=login_attempts)
            except Exception as e:
                logging.error(f"Error verifying password: {str(e)}")
                logging.error(traceback.format_exc())
            
            try:
                # Check verification status
                if not user.verified:
                    flash('Your account is not verified. Please check your email for verification instructions.', 'warning')
                    return render_template('login.html', form=form)
            except Exception as e:
                logging.error(f"Error checking verification: {str(e)}")
                logging.error(traceback.format_exc())
            
            try:
                # Login successful
                
                # Reset failed attempts on successful login
                reset_failed_attempts(username)
                
                # Clear session before login to prevent session fixation
                session.clear()
                
                # Login user with Flask-Login
                login_user(user, remember=remember)
                
                # Set session as permanent to respect the configured lifetime
                session.permanent = True
                
                # Track login activity
                track_login_activity(user.id, success=True)
                
                # Redirect to appropriate page
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('index'))
            except Exception as e:
                logging.error(f"Error during login process: {str(e)}")
                logging.error(traceback.format_exc())
                flash('An error occurred during login. Please try again.', 'danger')
    except Exception as e:
        logging.error(f"Uncaught exception in login route: {str(e)}")
        logging.error(traceback.format_exc())
        flash('An unexpected error occurred. Please try again later.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    # Clear any scanning session data
    session.pop('current_location_id', None)
    session.pop('current_parent_bag_id', None)
    session.pop('child_bags_scanned', None)
    
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page with form validation"""
    from forms import RegistrationForm
    
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            verified=True  # Auto-verify for testing
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/promote_admin', methods=['GET', 'POST'])
@login_required
def promote_admin():
    """Allow users to promote themselves to admin with secret code"""
    from forms import PromoteToAdminForm
    
    if current_user.is_admin():
        flash('You are already an admin.', 'info')
        return redirect(url_for('index'))
    
    form = PromoteToAdminForm()
    
    if form.validate_on_submit():
        secret_code = form.secret_code.data
        
        if secret_code == 'tracetracksecret':
            current_user.role = UserRole.ADMIN.value
            db.session.commit()
            flash('You have been promoted to admin!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid secret code.', 'danger')
    
    return render_template('promote_admin.html', form=form)

# Workflow A: Parent-Child Scanning
@app.route('/select_location', methods=['GET', 'POST'])
@login_required
def select_location():
    """Select location for scanning operations"""
    from forms import LocationSelectionForm
    import traceback
    
    try:
        # Get all locations
        locations = Location.query.all()
        
        # Create form and set choices
        form = LocationSelectionForm()
        form.location.choices = [(loc.id, loc.name) for loc in locations]
        
        if form.validate_on_submit():
            location_id = form.location.data
            session['current_location_id'] = location_id
            flash('Location selected successfully.', 'success')
            return redirect(url_for('scan_parent'))
            
        # If POST request but form validation failed
        elif request.method == 'POST':
            # Check for direct form submission
            location_id = request.form.get('location_id')
            if location_id:
                try:
                    location_id = int(location_id)
                    # Verify location exists
                    location = Location.query.get(location_id)
                    if location:
                        session['current_location_id'] = location_id
                        flash('Location selected successfully.', 'success')
                        return redirect(url_for('scan_parent'))
                except Exception as e:
                    logging.error(f"Error processing location selection: {str(e)}")
                    logging.error(traceback.format_exc())
            
            flash('Please select a valid location.', 'warning')
        
        # Clear any existing scanning session
        session.pop('current_parent_bag_id', None)
        session.pop('child_bags_scanned', None)
        
        return render_template('select_location.html', locations=locations, form=form)
    except Exception as e:
        logging.error(f"Error in select_location: {str(e)}")
        logging.error(traceback.format_exc())
        flash('An error occurred while loading locations. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/scan_parent')
@login_required
def scan_parent():
    """Scan parent bag QR code - Direct scan without location selection"""
    # Clear any existing scanning session
    session.pop('current_parent_bag_id', None)
    session.pop('child_bags_scanned', None)
    
    # Set default location if none exists
    if 'current_location_id' not in session:
        default_location = Location.query.first()
        if default_location:
            session['current_location_id'] = default_location.id
        else:
            # Create a default location if none exists
            default_location = Location(name='Default Location', description='Mobile scanning location')
            db.session.add(default_location)
            db.session.commit()
            session['current_location_id'] = default_location.id
    
    return render_template('scan_parent.html')

@app.route('/process_parent_scan', methods=['POST'])
@login_required
def process_parent_scan():
    """Process the parent bag QR code scan"""
    if 'current_location_id' not in session:
        return jsonify({'success': False, 'message': 'No location selected'})
    
    qr_code = request.form.get('qr_code')
    if not qr_code:
        return jsonify({'success': False, 'message': 'No QR code provided'})
    
    # Clean up the QR code
    qr_code = qr_code.strip()
    
    # Validate the QR code using the improved validator that handles any format
    is_valid, message, child_count = validate_parent_qr_id(qr_code)
    if not is_valid:
        return jsonify({'success': False, 'message': message})
    
    # Look up or create the parent bag
    parent_bag = Bag.query.filter_by(qr_id=qr_code, type=BagType.PARENT.value).first()
    
    if not parent_bag:
        # Create new parent bag
        parent_bag = Bag(qr_id=qr_code, type=BagType.PARENT.value)
        db.session.add(parent_bag)
        db.session.commit()
    
    # Record the scan
    location = Location.query.get(session['current_location_id'])
    scan = Scan(parent_bag_id=parent_bag.id, location_id=location.id, user_id=current_user.id)
    db.session.add(scan)
    db.session.commit()
    
    # Store parent bag ID in session
    session['current_parent_bag_id'] = parent_bag.id
    session['child_bags_scanned'] = []
    
    # Use the improved validate_parent_qr_id function to get child count
    is_valid, message, expected_child_count = validate_parent_qr_id(qr_code)
    # Update parent bag with the extracted child count
    parent_bag.child_count = expected_child_count
    db.session.commit()
    
    return jsonify({
        'success': True,
        'parent_id': parent_bag.id,
        'parent_qr': parent_bag.qr_id,
        'expected_child_count': expected_child_count,
        'message': f'Parent bag {qr_code} scanned successfully. Please scan {expected_child_count} child bags.'
    })

@app.route('/scan_child')
@login_required
def scan_child():
    """Scan child bag QR code"""
    # Ensure parent bag is scanned
    if 'current_parent_bag_id' not in session:
        flash('Please scan a parent bag first.', 'warning')
        return redirect(url_for('scan_parent'))
    
    parent_bag = Bag.query.get(session['current_parent_bag_id'])
    
    # Initialize child bags scanned list if not already in session
    if 'child_bags_scanned' not in session:
        session['child_bags_scanned'] = []
    
    # Calculate expected child count from parent QR
    try:
        expected_child_count = int(parent_bag.qr_id.split('-')[1])
    except:
        expected_child_count = 5  # Default
    
    # Get scanned child bag IDs
    scanned_child_ids = session.get('child_bags_scanned', [])
    
    return render_template('scan_child.html', 
                           parent_bag=parent_bag,
                           expected_child_count=expected_child_count,
                           scanned_child_count=len(scanned_child_ids))

@app.route('/process_child_scan', methods=['POST'])
@login_required
def process_child_scan():
    """Process the child bag QR code scan"""
    if 'current_parent_bag_id' not in session:
        return jsonify({'success': False, 'message': 'No parent bag selected'})
    
    qr_code = request.form.get('qr_code', '').strip()
    if not qr_code:
        return jsonify({'success': False, 'message': 'No QR code provided'})
    
    # Validate the QR code using the improved validator that handles any format
    is_valid, message = validate_child_qr_id(qr_code)
    if not is_valid:
        return jsonify({'success': False, 'message': message})
    
    # Check if this child bag is already scanned in this session
    child_bags_scanned = session.get('child_bags_scanned', [])
    if qr_code in child_bags_scanned:
        return jsonify({'success': False, 'message': f'Child bag {qr_code} already scanned'})
    
    # Look up or create the child bag - accepting any QR code format
    child_bag = Bag.query.filter_by(qr_id=qr_code).first()
    
    if not child_bag:
        # Create new child bag with any QR format
        child_bag = Bag(qr_id=qr_code, type=BagType.CHILD.value)
        db.session.add(child_bag)
        db.session.commit()
    elif child_bag.type != BagType.CHILD.value:
        # If the bag exists but isn't marked as a child bag, update it
        child_bag.type = BagType.CHILD.value
        db.session.commit()
    
    # Record the scan
    location_id = session['current_location_id']
    parent_bag_id = session['current_parent_bag_id']
    
    scan = Scan(child_bag_id=child_bag.id, location_id=location_id, user_id=current_user.id)
    db.session.add(scan)
    
    # Link parent to child
    link = Link.query.filter_by(parent_bag_id=parent_bag_id, child_bag_id=child_bag.id).first()
    if not link:
        link = Link(parent_bag_id=parent_bag_id, child_bag_id=child_bag.id)
        db.session.add(link)
    
    db.session.commit()
    
    # Update session data
    child_bags_scanned.append(qr_code)
    session['child_bags_scanned'] = child_bags_scanned
    
    # Get parent information
    parent_bag = Bag.query.get(parent_bag_id)
    
    # Calculate expected child count from parent QR
    try:
        expected_child_count = int(parent_bag.qr_id.split('-')[1])
    except:
        expected_child_count = 5  # Default
    
    # Check if all expected child bags are scanned
    all_scanned = len(child_bags_scanned) >= expected_child_count
    
    return jsonify({
        'success': True,
        'child_id': child_bag.id,
        'child_qr': child_bag.qr_id,
        'scanned_count': len(child_bags_scanned),
        'expected_count': expected_child_count,
        'all_scanned': all_scanned,
        'message': f'Child bag {qr_code} linked to parent successfully.'
    })

@app.route('/scan_complete')
@login_required
def scan_complete():
    """Completion page for scanning workflow"""
    # Clear scanning session data
    parent_bag_id = session.pop('current_parent_bag_id', None)
    child_bags = session.pop('child_bags_scanned', [])
    
    if not parent_bag_id:
        flash('No scanning session found.', 'warning')
        return redirect(url_for('index'))
    
    # Get parent and child bag info for display
    parent_bag = Bag.query.get(parent_bag_id)
    child_bags_info = []
    
    for child_id in child_bags:
        # Get the child bag by its ID (numeric) not by its QR code (string)
        try:
            # Ensure we're querying with a numeric ID
            if isinstance(child_id, str) and not child_id.isdigit():
                # If it's a QR code, find the bag by QR code instead
                child_bag = Bag.query.filter_by(qr_id=child_id).first()
            else:
                child_bag = Bag.query.get(child_id)
                
            if child_bag:
                child_bags_info.append(child_bag)
        except Exception as e:
            app.logger.error(f"Error retrieving child bag {child_id}: {str(e)}")
            
    return render_template('scan_complete.html', 
                          parent_bag=parent_bag,
                          child_bags=child_bags_info,
                          scan_count=len(child_bags_info))

@app.route('/finish_scanning')
@login_required
def finish_scanning():
    """Complete the scanning process"""
    if 'current_parent_bag_id' not in session:
        flash('No parent bag was scanned', 'warning')
        return redirect(url_for('index'))
    
    parent_bag_id = session['current_parent_bag_id']
    parent_bag = Bag.query.get(parent_bag_id)
    
    if not parent_bag:
        flash('Parent bag not found', 'danger')
        return redirect(url_for('index'))
    
    child_bags_scanned = session.get('child_bags_scanned', [])
    
    # Clear scanning session
    session.pop('current_parent_bag_id', None)
    session.pop('child_bags_scanned', None)
    
    flash(f'Scanning completed. Parent bag {parent_bag.qr_id} linked to {len(child_bags_scanned)} child bags.', 'success')
    return redirect(url_for('index'))

# Workflow B: Bill Management
@app.route('/bill_management')
@login_required
def bill_management():
    """Bill management dashboard with search functionality"""
    # Get search parameters
    search_bill_id = request.args.get('search_bill_id', '').strip()
    status_filter = request.args.get('status_filter', 'all')
    
    # Start with base query
    query = Bill.query
    
    # Apply search filters
    if search_bill_id:
        # Search by bill ID (partial match)
        query = query.filter(Bill.bill_id.ilike(f'%{search_bill_id}%'))
    
    if status_filter != 'all':
        query = query.filter(Bill.status == status_filter)
    
    # Execute query
    bills = query.order_by(Bill.created_at.desc()).all()
    
    return render_template('bill_management.html', bills=bills)

@app.route('/create_bill', methods=['GET', 'POST'])
@login_required
def create_bill():
    """Create a new bill"""
    # Create a form instance with CSRF token
    form = BillCreationForm()
    
    if request.method == 'POST':
        bill_id = request.form.get('bill_id', '').strip()
        parent_bag_count = request.form.get('parent_bag_count', '5')
        
        if not bill_id:
            flash('Bill ID is required', 'danger')
            return render_template('create_bill.html', form=form)
        
        try:
            parent_bag_count = int(parent_bag_count)
            if parent_bag_count < 1 or parent_bag_count > 50:
                flash('Parent bag count must be between 1 and 50', 'danger')
                return render_template('create_bill.html', form=form)
        except ValueError:
            flash('Invalid parent bag count', 'danger')
            return render_template('create_bill.html', form=form)
        
        # Check if bill_id already exists
        existing_bill = Bill.query.filter_by(bill_id=bill_id).first()
        if existing_bill:
            flash(f'Bill ID {bill_id} already exists', 'danger')
            return render_template('create_bill.html', form=form)
        
        try:
            # Create new bill using direct property assignment
            new_bill = Bill()
            new_bill.bill_id = bill_id
            new_bill.parent_bag_count = parent_bag_count
            db.session.add(new_bill)
            db.session.commit()
            
            # Store bill in session for scanning parent bags
            session['current_bill_id'] = new_bill.id
            
            flash(f'Bill {bill_id} created successfully. Please scan {parent_bag_count} parent bags to add to this bill.', 'success')
            return redirect(url_for('scan_bill_parent'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating bill: {str(e)}")
            flash(f'Error creating bill: {str(e)}', 'danger')
            return render_template('create_bill.html', form=form)
    
    return render_template('create_bill.html', form=form)
    
@app.route('/delete_bill/<int:bill_id>')
@login_required
def delete_bill(bill_id):
    """Delete a bill and all its bag links"""
    try:
        bill = Bill.query.get(bill_id)
        if not bill:
            flash('Bill not found', 'danger')
            return redirect(url_for('bill_management'))
            
        # Get the bill ID for the flash message
        bill_id_text = bill.bill_id
        
        # Delete all BillBag links for this bill
        BillBag.query.filter_by(bill_id=bill_id).delete()
        
        # Delete the bill itself
        db.session.delete(bill)
        db.session.commit()
        
        flash(f'Bill {bill_id_text} deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting bill: {str(e)}")
        flash(f'Error deleting bill: {str(e)}', 'danger')
        
    return redirect(url_for('bill_management'))

@app.route('/finish_bill_scan/<int:bill_id>')
@login_required
def finish_bill_scan(bill_id):
    """Complete the bill scanning process"""
    try:
        bill = Bill.query.get(bill_id)
        if not bill:
            flash('Bill not found', 'danger')
            return redirect(url_for('bill_management'))
        
        # Update bill status to completed
        bill.status = 'completed'
        db.session.commit()
        
        # Clear session data
        session.pop('current_bill_id', None)
        
        # Count linked bags
        linked_count = BillBag.query.filter_by(bill_id=bill_id).count()
        
        flash(f'Bill {bill.bill_id} completed successfully with {linked_count} parent bags linked.', 'success')
        return redirect(url_for('bill_management'))
        
    except Exception as e:
        app.logger.error(f"Error finishing bill scan: {str(e)}")
        flash(f'Error completing bill: {str(e)}', 'danger')
        return redirect(url_for('bill_management'))

@app.route('/scan_bill_parent')
@app.route('/scan_bill_parent/<int:bill_id>')
@login_required
def scan_bill_parent(bill_id=None):
    """Scan parent bags to add to bill"""
    try:
        # Use bill_id from URL if provided, otherwise from session
        if bill_id:
            bill = Bill.query.get(bill_id)
            # Update session with current bill
            session['current_bill_id'] = bill_id
        elif 'current_bill_id' in session:
            bill = Bill.query.get(session['current_bill_id'])
        else:
            flash('Please create or select a bill first', 'warning')
            return redirect(url_for('bill_management'))
        
        if not bill:
            flash('Selected bill not found. Please create a new bill.', 'danger')
            # Clear the invalid bill ID from session
            session.pop('current_bill_id', None)
            return redirect(url_for('create_bill'))
            
        # Get parent bags already linked to this bill
        linked_parent_bags = db.session.query(Bag).join(
            BillBag, Bag.id == BillBag.bag_id
        ).filter(BillBag.bill_id == bill.id).all()
        
        return render_template('scan_bill_parent.html', 
                            bill=bill,
                            linked_parent_bags=linked_parent_bags)
                            
    except Exception as e:
        app.logger.error(f"Error in scan_bill_parent: {str(e)}")
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('bill_management'))

@app.route('/process_bill_parent_scan', methods=['POST'])
@login_required
def process_bill_parent_scan():
    """Process a parent bag scan for bill linking"""
    if 'current_bill_id' not in session:
        return jsonify({'success': False, 'message': 'No bill selected'})
    
    qr_code = request.form.get('qr_code')
    if not qr_code:
        return jsonify({'success': False, 'message': 'No QR code provided'})
    
    # Clean up the QR code
    qr_code = qr_code.strip()
    
    # Validate the QR code using the improved validator that handles any format
    is_valid, message, child_count = validate_parent_qr_id(qr_code)
    if not is_valid:
        return jsonify({'success': False, 'message': message})
    
    # Look up or create the parent bag
    parent_bag = Bag.query.filter_by(qr_id=qr_code, type=BagType.PARENT.value).first()
    
    if not parent_bag:
        # Create new parent bag
        parent_bag = Bag(qr_id=qr_code, type=BagType.PARENT.value)
        db.session.add(parent_bag)
        db.session.commit()
    
    # Link parent bag to bill
    bill_id = session['current_bill_id']
    bill = Bill.query.get(bill_id)
    
    # Check if already linked
    existing_link = BillBag.query.filter_by(bill_id=bill_id, bag_id=parent_bag.id).first()
    if existing_link:
        return jsonify({
            'success': False,
            'message': f'Parent bag {qr_code} already linked to bill {bill.bill_id}'
        })
    
    # Check if bill has reached maximum parent bag count
    current_count = BillBag.query.filter_by(bill_id=bill_id).count()
    if current_count >= bill.parent_bag_count:
        return jsonify({
            'success': False,
            'message': f'Bill already has maximum {bill.parent_bag_count} parent bags linked'
        })
    
    # Create new link
    bill_bag = BillBag(bill_id=bill_id, bag_id=parent_bag.id)
    db.session.add(bill_bag)
    db.session.commit()
    
    # Get updated count of linked bags
    linked_count = BillBag.query.filter_by(bill_id=bill_id).count()
    
    return jsonify({
        'success': True,
        'parent_id': parent_bag.id,
        'parent_qr': parent_bag.qr_id,
        'bill_id': bill.bill_id,
        'parent_count': linked_count,
        'linked_count': linked_count,
        'expected_count': bill.parent_bag_count,
        'message': f'Parent bag {qr_code} linked to bill {bill.bill_id} successfully'
    })

@app.route('/remove_bag_from_bill', methods=['POST'])
@login_required
def remove_bag_from_bill():
    """Remove a parent bag from a bill"""
    parent_qr = request.form.get('parent_qr')
    bill_id = request.form.get('bill_id')
    
    if not parent_qr or not bill_id:
        flash('Missing parent QR code or bill ID', 'error')
        return redirect(url_for('scan_bill_parent', bill_id=bill_id))
    
    # Get bill and parent bag
    bill = Bill.query.get(bill_id)
    parent_bag = Bag.query.filter_by(qr_id=parent_qr).first()
    
    if not bill or not parent_bag:
        flash('Bill or parent bag not found', 'error')
        return redirect(url_for('scan_bill_parent', bill_id=bill_id))
    
    # Find and remove the link
    bill_bag = BillBag.query.filter_by(bill_id=bill.id, bag_id=parent_bag.id).first()
    
    if bill_bag:
        db.session.delete(bill_bag)
        db.session.commit()
        flash(f'Parent bag {parent_qr} removed from bill {bill.bill_id}', 'success')
    else:
        flash(f'Parent bag {parent_qr} not linked to bill {bill.bill_id}', 'error')
    
    return redirect(url_for('scan_bill_parent', bill_id=bill_id))

@app.route('/view_bill/<int:bill_id>')
@login_required
def view_bill(bill_id):
    """View bill details with parent bags and child bags"""
    bill = Bill.query.get_or_404(bill_id)
    
    # Get all parent bags linked to this bill with their child bags
    parent_bags = []
    bag_links_count = len(list(bill.bag_links))
    
    for bill_bag in bill.bag_links:
        parent_bag = bill_bag.bag
        child_bags = [link.child_bag for link in parent_bag.child_links]
        child_count = len(child_bags)
        parent_bags.append({
            'parent_bag': parent_bag,
            'child_bags': child_bags,
            'child_count': child_count
        })
    
    return render_template('view_bill.html', bill=bill, parent_bags=parent_bags, bag_links_count=bag_links_count)

@app.route('/finish_bill')
@login_required
def finish_bill():
    """Complete the bill creation process"""
    if 'current_bill_id' not in session:
        flash('No bill was selected', 'warning')
        return redirect(url_for('bill_management'))
    
    bill_id = session['current_bill_id']
    bill = Bill.query.get(bill_id)
    
    if not bill:
        flash('Bill not found', 'danger')
        return redirect(url_for('bill_management'))
    
    # Get count of linked parent bags
    linked_count = BillBag.query.filter_by(bill_id=bill_id).count()
    
    # Clear bill session
    session.pop('current_bill_id', None)
    
    flash(f'Bill {bill.bill_id} finalized with {linked_count} parent bags linked.', 'success')
    return redirect(url_for('bill_management'))

# Workflow C: Child Bag Lookup
@app.route('/child_lookup', methods=['GET', 'POST'])
@login_required
def child_lookup():
    """Universal bag lookup - works with both parent and child bag QR codes"""
    if request.method == 'POST':
        qr_code = request.form.get('qr_code', '').strip()
        
        if not qr_code:
            flash('Please enter a bag QR code', 'warning')
            return render_template('child_lookup.html')
        
        # Accept any QR code format - no validation required
        qr_code = qr_code.strip()
        
        # Look up any bag with this QR code
        bag = Bag.query.filter_by(qr_id=qr_code).first()
        
        if not bag:
            flash(f'Bag {qr_code} not found', 'danger')
            return render_template('child_lookup.html')
        
        # Handle based on bag type
        if bag.type == BagType.CHILD.value:
            # Child bag - find parent and bill
            link = Link.query.filter_by(child_bag_id=bag.id).first()
            
            if not link:
                flash(f'Child bag {qr_code} is not linked to any parent bag', 'warning')
                return render_template('child_lookup.html', searched_bag=bag, bag_type='child')
            
            parent_bag = Bag.query.get(link.parent_bag_id)
            child_scans = Scan.query.filter_by(child_bag_id=bag.id).order_by(Scan.timestamp.desc()).all()
            
            # Find bill linked to parent bag
            bill_bag = BillBag.query.filter_by(bag_id=parent_bag.id).first()
            bill = Bill.query.get(bill_bag.bill_id) if bill_bag else None
            
            # Get all children of this parent for context
            all_children_links = Link.query.filter_by(parent_bag_id=parent_bag.id).all()
            all_children = [link.child_bag for link in all_children_links]
            
            return render_template('bag_lookup_result.html',
                                  searched_bag=bag,
                                  bag_type='child',
                                  parent_bag=parent_bag,
                                  child_bags=all_children,
                                  bill=bill,
                                  scans=child_scans)
        
        else:
            # Parent bag - find children and bill
            children_links = Link.query.filter_by(parent_bag_id=bag.id).all()
            child_bags = [link.child_bag for link in children_links]
            
            # Find bill linked to this parent bag
            bill_bag = BillBag.query.filter_by(bag_id=bag.id).first()
            bill = Bill.query.get(bill_bag.bill_id) if bill_bag else None
            
            # Get scan history for parent bag
            parent_scans = Scan.query.filter_by(parent_bag_id=bag.id).order_by(Scan.timestamp.desc()).all()
            
            return render_template('bag_lookup_result.html',
                                  searched_bag=bag,
                                  bag_type='parent',
                                  parent_bag=bag,
                                  child_bags=child_bags,
                                  bill=bill,
                                  scans=parent_scans)
    
    # Store navigation context for backtracing
    session['previous_page'] = request.referrer or url_for('index')
    return render_template('child_lookup.html')

# Enhanced Bag Management with Filtering
@app.route('/bags')
@login_required
def bag_management():
    """Optimized bag management with efficient filtering"""
    
    # Get filter parameters
    bag_type = request.args.get('type', 'all')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    linked_status = request.args.get('linked_status', 'all')
    search_query = request.args.get('search', '')
    location_filter = request.args.get('location', 'all')
    bill_status = request.args.get('bill_status', 'all')
    
    # Build optimized query
    query = Bag.query
    
    # Apply basic filters directly in SQL
    if bag_type == 'parent':
        query = query.filter(Bag.type == BagType.PARENT.value)
    elif bag_type == 'child':
        query = query.filter(Bag.type == BagType.CHILD.value)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Bag.created_at >= from_date)
        except ValueError:
            flash('Invalid from date format', 'warning')
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Bag.created_at < to_date)
        except ValueError:
            flash('Invalid to date format', 'warning')
    
    if search_query:
        query = query.filter(Bag.qr_id.ilike(f'%{search_query}%'))
    
    # Apply advanced filters using subqueries for better performance
    if linked_status != 'all':
        if linked_status == 'unlinked':
            # Bags with no links
            linked_parent_ids = db.session.query(Link.parent_bag_id).distinct()
            linked_child_ids = db.session.query(Link.child_bag_id).distinct()
            query = query.filter(and_(
                Bag.id.notin_(linked_parent_ids),
                Bag.id.notin_(linked_child_ids)
            ))
        elif linked_status == 'linked':
            # Bags with links
            linked_parent_ids = db.session.query(Link.parent_bag_id).distinct()
            linked_child_ids = db.session.query(Link.child_bag_id).distinct()
            query = query.filter(or_(
                Bag.id.in_(linked_parent_ids),
                Bag.id.in_(linked_child_ids)
            ))
        elif linked_status == 'orphaned':
            # Parent bags with children but no bill
            orphaned_parents = db.session.query(Link.parent_bag_id).distinct().subquery()
            billed_parents = db.session.query(BillBag.bag_id).distinct().subquery()
            query = query.filter(and_(
                Bag.type == BagType.PARENT.value,
                Bag.id.in_(db.session.query(orphaned_parents.c.parent_bag_id)),
                Bag.id.notin_(db.session.query(billed_parents.c.bag_id))
            ))
    
    if bill_status != 'all':
        billed_bag_ids = db.session.query(BillBag.bag_id).distinct()
        if bill_status == 'billed':
            query = query.filter(Bag.id.in_(billed_bag_ids))
        elif bill_status == 'unbilled':
            query = query.filter(Bag.id.notin_(billed_bag_ids))
    
    if location_filter != 'all':
        # Get bags scanned at specific location
        location_bag_ids = db.session.query(Scan.parent_bag_id).join(Location).filter(
            Location.name == location_filter, Scan.parent_bag_id.isnot(None)
        ).union(
            db.session.query(Scan.child_bag_id).join(Location).filter(
                Location.name == location_filter, Scan.child_bag_id.isnot(None)
            )
        )
        query = query.filter(Bag.id.in_(location_bag_ids))
    
    # Execute query with pagination for better performance
    bags = query.order_by(Bag.created_at.desc()).limit(1000).all()
    
    # Calculate statistics efficiently using count queries instead of loading all data
    total_bags = query.count()
    parent_bags = query.filter(Bag.type == BagType.PARENT.value).count()
    child_bags = query.filter(Bag.type == BagType.CHILD.value).count()
    
    # Calculate linked stats efficiently
    bag_ids = [b.id for b in bags]
    if bag_ids:
        linked_parent_count = db.session.query(Link.parent_bag_id).filter(Link.parent_bag_id.in_(bag_ids)).distinct().count()
    else:
        linked_parent_count = 0
    linked_child_count = db.session.query(Link.child_bag_id).filter(Link.child_bag_id.in_(bag_ids)).distinct().count()
    linked_bags = linked_parent_count + linked_child_count
    unlinked_bags = total_bags - linked_bags
    
    # Count orphaned bags (parent bags with children but no bill)
    parent_bag_ids = [b.id for b in bags if b.type == BagType.PARENT.value]
    if parent_bag_ids:
        parents_with_children = db.session.query(Link.parent_bag_id).filter(Link.parent_bag_id.in_(parent_bag_ids)).distinct().subquery()
        parents_with_bills = db.session.query(BillBag.bag_id).filter(BillBag.bag_id.in_(parent_bag_ids)).distinct().subquery()
        orphaned_count = db.session.query(parents_with_children.c.parent_bag_id).filter(
            parents_with_children.c.parent_bag_id.notin_(db.session.query(parents_with_bills.c.bag_id))
        ).count()
        orphaned_bags = orphaned_count
    else:
        orphaned_bags = 0
    
    stats = {
        'total_bags': total_bags,
        'parent_bags': parent_bags,
        'child_bags': child_bags,
        'linked_bags': linked_bags,
        'unlinked_bags': unlinked_bags,
        'orphaned_bags': orphaned_bags
    }
    
    # Get locations efficiently
    locations = [loc[0] for loc in db.session.query(Location.name).distinct().all()]
    
    return render_template('bag_management.html', 
                         bags=bags,
                         stats=stats,
                         locations=locations,
                         filters={
                             'type': bag_type,
                             'date_from': date_from,
                             'date_to': date_to,
                             'linked_status': linked_status,
                             'search': search_query,
                             'location': location_filter,
                             'bill_status': bill_status
                         })

@app.route('/bag_detail/<qr_id>')
@login_required
def bag_detail(qr_id):
    """Display detailed information about a specific bag"""
    bag = Bag.query.filter_by(qr_id=qr_id).first_or_404()
    
    # Get scan history
    scans = Scan.query.filter(
        or_(Scan.parent_bag_id == bag.id, Scan.child_bag_id == bag.id)
    ).order_by(Scan.timestamp.desc()).all()
    
    # Get linked bags
    linked_bags = []
    if bag.type == BagType.PARENT.value:
        # Get child bags
        links = Link.query.filter_by(parent_bag_id=bag.id).all()
        linked_bags = [link.child_bag for link in links]
    else:
        # Get parent bag
        link = Link.query.filter_by(child_bag_id=bag.id).first()
        if link:
            linked_bags = [link.parent_bag]
    
    # Get bill information
    bill_link = BillBag.query.filter_by(bag_id=bag.id).first()
    bill = bill_link.bill if bill_link else None
    
    # Store navigation context for backtracing
    session['previous_page'] = request.referrer or url_for('bag_management')
    
    return render_template('bag_detail.html',
                         bag=bag,
                         scans=scans,
                         linked_bags=linked_bags,
                         child_bags=linked_bags if bag.type == BagType.PARENT.value else [],
                         bill=bill,
                         is_parent=(bag.type == BagType.PARENT.value))