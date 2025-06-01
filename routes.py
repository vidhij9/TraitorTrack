"""
Routes for TraceTrack application - Location functionality completely removed
"""
from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_file, abort, make_response
# Session-based authentication - no longer using Flask-Login
from werkzeug.security import check_password_hash, generate_password_hash

def is_admin():
    """Check if current user is admin"""
    return session.get('user_role') == 'admin'

def get_current_user_id():
    """Get current user ID from session"""
    return session.get('user_id')

def is_authenticated():
    """Check if user is logged in"""
    return session.get('logged_in', False)

def login_required(f):
    """Decorator to require login for routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

class CurrentUser:
    """Mock current_user object for compatibility"""
    @property
    def id(self):
        return session.get('user_id')
    
    @property
    def is_authenticated(self):
        return session.get('logged_in', False)
    
    def is_admin(self):
        return session.get('user_role') == 'admin'

current_user = CurrentUser()
from sqlalchemy import desc, func, and_, or_
from datetime import datetime, timedelta

from app_clean import app, db, limiter
from models import User, UserRole, Bag, BagType, Link, Scan, Bill, BillBag
from forms import LoginForm, RegistrationForm, ScanParentForm, ScanChildForm, ChildLookupForm, PromoteToAdminForm, BillCreationForm
from account_security import is_account_locked, record_failed_attempt, reset_failed_attempts, track_login_activity
from validation_utils import validate_parent_qr_id, validate_child_qr_id, validate_bill_id, sanitize_input

import csv
import io
import json
import secrets
import random

@app.route('/analytics')
@login_required
def analytics():
    """Analytics dashboard for system insights"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('index'))
    
    # Basic statistics
    total_scans = Scan.query.count()
    total_bags = Bag.query.count()
    active_users = User.query.filter(User.verified == True).count()
    
    # User activity statistics
    user_stats = []
    today = datetime.now().date()
    
    users = User.query.all()
    for user in users:
        user_scans_today = Scan.query.filter(
            Scan.user_id == user.id,
            func.date(Scan.timestamp) == today
        ).count()
        
        user_scans_total = Scan.query.filter(Scan.user_id == user.id).count()
        
        user_stats.append({
            'username': user.username,
            'scans_today': user_scans_today,
            'total_scans': user_scans_total,
            'role': user.role
        })
    
    # Recent activity
    recent_scans = Scan.query.order_by(desc(Scan.timestamp)).limit(10).all()
    
    # Bag statistics
    parent_bags_count = Bag.query.filter(Bag.type == BagType.PARENT.value).count()
    child_bags_count = Bag.query.filter(Bag.type == BagType.CHILD.value).count()
    
    # Time-based scan data for charts
    scan_data_7days = []
    for i in range(7):
        date = today - timedelta(days=i)
        scans_count = Scan.query.filter(func.date(Scan.timestamp) == date).count()
        scan_data_7days.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': scans_count
        })
    scan_data_7days.reverse()
    
    # User scan distribution
    user_scan_distribution = db.session.query(
        User.username,
        func.count(Scan.id).label('scan_count')
    ).join(Scan).group_by(User.id, User.username).order_by(desc('scan_count')).limit(10).all()
    
    # Calculate max user scans for progress bars
    max_user_scans = max([len(user_stats)] + [stat['total_scans'] for stat in user_stats]) if user_stats else 1
    
    analytics_data = {
        'total_scans': total_scans,
        'total_bags': total_bags,
        'parent_bags': parent_bags_count,
        'child_bags': child_bags_count,
        'active_users': active_users,
        'user_stats': user_stats,
        'max_user_scans': max_user_scans,
        'recent_scans': recent_scans,
        'scans_over_time': scan_data_7days,
        'location_data': [],
        'scan_data_7days': json.dumps(scan_data_7days),
        'user_scan_distribution': json.dumps([{
            'username': username,
            'count': count
        } for username, count in user_scan_distribution])
    }
    
    return render_template('analytics.html', analytics=analytics_data)

@app.route('/user_management')
@login_required
def user_management():
    """User management dashboard for admins"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('index'))
    
    users = User.query.order_by(User.created_at.desc()).all()
    
    # Get statistics for each user
    user_data = []
    for user in users:
        scan_count = Scan.query.filter(Scan.user_id == user.id).count()
        last_scan = Scan.query.filter(Scan.user_id == user.id).order_by(desc(Scan.timestamp)).first()
        
        user_data.append({
            'user': user,
            'scan_count': scan_count,
            'last_scan': last_scan.timestamp if last_scan else None
        })
    
    # Add user stats for the template
    user_stats = {
        'total_users': User.query.count(),
        'admin_users': User.query.filter(User.role == UserRole.ADMIN.value).count(),
        'verified_users': User.query.filter(User.verified == True).count()
    }
    
    return render_template('user_management.html', user_data=user_data, user_stats=user_stats)

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
        
        if username:
            user.username = username
        if email:
            user.email = email
        if role and role in [UserRole.ADMIN.value, UserRole.EMPLOYEE.value]:
            user.role = role
            
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
        if user.role == UserRole.EMPLOYEE.value:
            return jsonify({'success': False, 'message': 'User is already an employee'})
            
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot demote yourself'})
            
        user.role = UserRole.EMPLOYEE.value
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
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        
        # Check if user already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'error': 'Username already exists'})
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'success': False, 'error': 'Email already exists'})
        
        # Create new user
        user = User(
            username=data['username'],
            email=data['email'],
            role=data.get('role', UserRole.EMPLOYEE.value),
            verified=True
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User created successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

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
                parent_bag = Bag(
                    qr_id=f"PARENT_{i+1:03d}_{secrets.token_hex(4).upper()}",
                    type=BagType.PARENT.value,
                    name=f"Parent Bag {i+1}",
                    child_count=random.randint(1, 5)
                )
                db.session.add(parent_bag)
                db.session.flush()  # Get the ID
                
                # Create child bags for this parent
                for j in range(parent_bag.child_count):
                    child_bag = Bag(
                        qr_id=f"CHILD_{i+1:03d}_{j+1:02d}_{secrets.token_hex(3).upper()}",
                        type=BagType.CHILD.value,
                        name=f"Child Bag {i+1}-{j+1}",
                        parent_id=parent_bag.id
                    )
                    db.session.add(child_bag)
                    
                    # Create link
                    link = Link(parent_bag_id=parent_bag.id, child_bag_id=child_bag.id)
                    db.session.add(link)
            
            db.session.commit()
        
        # Create sample scans for the past 30 days
        bags = Bag.query.all()
        if bags and Scan.query.count() < 50:
            for _ in range(100):
                bag = random.choice(bags)
                scan = Scan(
                    timestamp=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                    user_id=current_user.id
                )
                
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

@app.route('/export/analytics.csv')
@login_required
def export_analytics_csv():
    """Export analytics data as CSV"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('index'))
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['Date', 'Total Scans', 'Parent Scans', 'Child Scans', 'Active Users'])
    
    # Get data for the past 30 days
    for i in range(30):
        date = datetime.now().date() - timedelta(days=i)
        
        total_scans = Scan.query.filter(func.date(Scan.timestamp) == date).count()
        parent_scans = Scan.query.filter(
            func.date(Scan.timestamp) == date,
            Scan.parent_bag_id.isnot(None)
        ).count()
        child_scans = Scan.query.filter(
            func.date(Scan.timestamp) == date,
            Scan.child_bag_id.isnot(None)
        ).count()
        
        # Count unique users who scanned on this date
        active_users = db.session.query(Scan.user_id).filter(
            func.date(Scan.timestamp) == date
        ).distinct().count()
        
        writer.writerow([date, total_scans, parent_scans, child_scans, active_users])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=analytics_{datetime.now().strftime("%Y%m%d")}.csv'
    
    return response

@app.route('/export/<format>')
@login_required
def export_data(format):
    """Export data in various formats"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('index'))
    
    if format == 'csv':
        return export_analytics_csv()
    else:
        flash('Unsupported export format.', 'error')
        return redirect(url_for('analytics'))

# Core application routes

@app.route('/', methods=['GET'])
def index():
    """Main dashboard page"""
    import logging
    logging.info(f"Index route - Session data: {dict(session)}")
    logging.info(f"Logged in status: {session.get('logged_in')}")
    
    # Stateless authentication check
    from stateless_auth import is_authenticated
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

# Login route is now defined in main.py

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

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
@limiter.limit("3 per minute")
def register():
    """User registration page with form validation"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        try:
            username = sanitize_input(form.username.data)
            email = sanitize_input(form.email.data).lower()
            
            # Create new user
            user = User(
                username=username,
                email=email,
                role=UserRole.EMPLOYEE.value,
                verified=True
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
            app.logger.error(f'Registration error: {str(e)}')
    
    return render_template('register.html', form=form)

@app.route('/promote_admin', methods=['GET', 'POST'])
@login_required
def promote_admin():
    """Self-promotion route disabled - only admins can promote users"""
    flash('Self-promotion is disabled. Contact an administrator for role changes.', 'info')
    return redirect(url_for('index'))

# Scanning workflow routes (simplified without location selection)

@app.route('/scan/parent')
@login_required
def scan_parent():
    """Scan parent bag QR code - Direct scan without location selection"""
    form = ScanParentForm()
    return render_template('scan_parent.html', form=form)

@app.route('/scan/parent', methods=['POST'])
@login_required
def process_parent_scan():
    """Process the parent bag QR code scan"""
    form = ScanParentForm()
    
    if form.validate_on_submit():
        try:
            qr_id = sanitize_input(getattr(form, 'qr_id', form).data).upper()
            
            if not validate_parent_qr_id(qr_id):
                flash('Invalid parent bag QR code format.', 'error')
                return render_template('scan_parent.html', form=form)
            
            # Look up the parent bag
            parent_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.PARENT.value).first()
            
            if not parent_bag:
                flash('Parent bag not found. Please check the QR code.', 'error')
                return render_template('scan_parent.html', form=form)
            
            # Record the scan
            scan = Scan(
                parent_bag_id=parent_bag.id,
                user_id=current_user.id,
                timestamp=datetime.utcnow()
            )
            
            db.session.add(scan)
            db.session.commit()
            
            # Store in session for the completion page
            session['last_scan'] = {
                'type': 'parent',
                'qr_id': qr_id,
                'bag_name': parent_bag.name,
                'timestamp': scan.timestamp.isoformat()
            }
            
            flash('Parent bag scanned successfully!', 'success')
            return redirect(url_for('scan_complete'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error processing scan. Please try again.', 'error')
            app.logger.error(f'Parent scan error: {str(e)}')
    
    return render_template('scan_parent.html', form=form)

@app.route('/scan/child')
@login_required
def scan_child():
    """Scan child bag QR code"""
    form = ScanChildForm()
    return render_template('scan_child.html', form=form)

@app.route('/scan/child', methods=['POST'])
@login_required
def process_child_scan():
    """Process the child bag QR code scan"""
    form = ScanChildForm()
    
    if form.validate_on_submit():
        try:
            qr_id = sanitize_input(getattr(form, 'qr_id', form).data).upper()
            
            if not validate_child_qr_id(qr_id):
                flash('Invalid child bag QR code format.', 'error')
                return render_template('scan_child.html', form=form)
            
            # Look up the child bag
            child_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.CHILD.value).first()
            
            if not child_bag:
                flash('Child bag not found. Please check the QR code.', 'error')
                return render_template('scan_child.html', form=form)
            
            # Record the scan
            scan = Scan(
                child_bag_id=child_bag.id,
                user_id=current_user.id,
                timestamp=datetime.utcnow()
            )
            
            db.session.add(scan)
            db.session.commit()
            
            # Get parent bag info if linked
            parent_bag = None
            link = Link.query.filter_by(child_bag_id=child_bag.id).first()
            if link:
                parent_bag = link.parent_bag
            
            # Store in session for the completion page
            session['last_scan'] = {
                'type': 'child',
                'qr_id': qr_id,
                'bag_name': child_bag.name,
                'parent_qr_id': parent_bag.qr_id if parent_bag else None,
                'parent_name': parent_bag.name if parent_bag else None,
                'timestamp': scan.timestamp.isoformat()
            }
            
            flash('Child bag scanned successfully!', 'success')
            return redirect(url_for('scan_complete'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error processing scan. Please try again.', 'error')
            app.logger.error(f'Child scan error: {str(e)}')
    
    return render_template('scan_child.html', form=form)

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
        qr_id = sanitize_input(getattr(form, 'qr_id', form).data).upper()
    elif url_qr_id:
        # If there's a QR ID in the URL, use it for lookup
        qr_id = sanitize_input(url_qr_id).upper()
    else:
        qr_id = None
    
    if qr_id:
        
        # Look up the bag (could be parent or child)
        bag = Bag.query.filter_by(qr_id=qr_id).first()
        
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
            flash('Bag not found. Please check the QR code.', 'error')
    
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
    """Optimized bag management with efficient filtering"""
    page = request.args.get('page', 1, type=int)
    bag_type = request.args.get('type', 'all')
    search_query = request.args.get('search', '').strip()
    
    # Build query
    query = Bag.query
    
    if bag_type != 'all':
        query = query.filter(Bag.type == bag_type)
    
    if search_query:
        query = query.filter(
            or_(
                Bag.qr_id.contains(search_query),
                Bag.name.contains(search_query)
            )
        )
    
    # Paginate results
    bags = query.order_by(desc(Bag.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Add stats for the template
    stats = {
        'total_bags': Bag.query.count(),
        'parent_bags': Bag.query.filter(Bag.type == BagType.PARENT.value).count(),
        'child_bags': Bag.query.filter(Bag.type == BagType.CHILD.value).count()
    }
    
    filters = {'type': bag_type}
    return render_template('bag_management.html', bags=bags, bag_type=bag_type, search_query=search_query, stats=stats, filters=filters)

# Bill management routes
@app.route('/bills')
@login_required
def bill_management():
    """Bill management dashboard with search functionality - admin only"""
    if not current_user.is_admin():
        flash('Admin access required for bill management.', 'error')
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

@app.route('/bill/create', methods=['POST'])
@login_required
def create_bill():
    """Create a new bill - admin only"""
    if not current_user.is_admin():
        flash('Admin access required to create bills.', 'error')
        return redirect(url_for('index'))
    form = BillCreationForm()
    
    if form.validate_on_submit():
        try:
            bill_id = sanitize_input(form.bill_id.data).upper()
            description = sanitize_input(getattr(form, 'description', form).data) if hasattr(form, 'description') and form.description.data else ''
            parent_bag_count = getattr(form, 'parent_bag_count', form).data or 1
            
            if not validate_bill_id(bill_id):
                flash('Invalid bill ID format.', 'error')
                return redirect(url_for('bill_management'))
            
            # Check if bill already exists
            existing_bill = Bill.query.filter_by(bill_id=bill_id).first()
            if existing_bill:
                flash('Bill ID already exists.', 'error')
                return redirect(url_for('bill_management'))
            
            # Create new bill
            bill = Bill(
                bill_id=bill_id,
                description=description,
                parent_bag_count=parent_bag_count,
                status='new'
            )
            
            db.session.add(bill)
            db.session.commit()
            
            flash('Bill created successfully!', 'success')
            return redirect(url_for('scan_bill_parent', bill_id=bill.id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error creating bill. Please try again.', 'error')
            app.logger.error(f'Bill creation error: {str(e)}')
    
    return redirect(url_for('bill_management'))

@app.route('/bill/<int:bill_id>/delete', methods=['POST'])
@login_required
def delete_bill(bill_id):
    """Delete a bill and all its bag links - admin only"""
    if not current_user.is_admin():
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
    """Complete bill scanning and mark as finished - admin only"""
    if not current_user.is_admin():
        flash('Admin access required to finish bills.', 'error')
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
    """Edit bill details - admin only"""
    if not current_user.is_admin():
        flash('Admin access required to edit bills.', 'error')
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
    """Remove a parent bag from a bill - admin only"""
    if not current_user.is_admin():
        flash('Admin access required to remove bags from bills.', 'error')
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
            return redirect(url_for('view_bill', bill_id=bill_id))
        
        # Find and remove the bill-bag link
        bill_bag = BillBag.query.filter_by(bill_id=bill_id, bag_id=parent_bag.id).first()
        if bill_bag:
            db.session.delete(bill_bag)
            db.session.commit()
            flash(f'Parent bag {parent_qr} removed from bill successfully.', 'success')
        else:
            flash('Bag link not found.', 'error')
        
        return redirect(url_for('view_bill', bill_id=bill_id))
        
    except Exception as e:
        db.session.rollback()
        flash('Error removing bag from bill.', 'error')
        app.logger.error(f'Remove bag from bill error: {str(e)}')
        return redirect(url_for('bill_management'))

@app.route('/bill/scan_parent')
@app.route('/bill/<int:bill_id>/scan_parent')
@login_required
def scan_bill_parent(bill_id=None):
    """Scan parent bags to add to bill - admin only"""
    if not current_user.is_admin():
        flash('Admin access required for bill operations.', 'error')
        return redirect(url_for('index'))
    if bill_id:
        bill = Bill.query.get_or_404(bill_id)
    else:
        # If no bill_id provided, redirect to bill management
        flash('Please select a bill first.', 'info')
        return redirect(url_for('bill_management'))
    
    form = ScanParentForm()
    
    # Get current parent bags linked to this bill
    linked_bags = db.session.query(Bag).join(BillBag, Bag.id == BillBag.bag_id).filter(BillBag.bill_id == bill.id).all()
    
    return render_template('scan_bill_parent.html', form=form, bill=bill, linked_bags=linked_bags)

@app.route('/process_bill_parent_scan', methods=['POST'])
@login_required
def process_bill_parent_scan():
    """Process a parent bag scan for bill linking - admin only"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required for bill operations.'})
    
    bill_id = request.form.get('bill_id')
    qr_code = request.form.get('qr_code')
    
    if not bill_id:
        return jsonify({'success': False, 'message': 'Bill ID missing.'})
    
    if not qr_code:
        return jsonify({'success': False, 'message': 'QR code missing.'})
    
    try:
        bill = Bill.query.get_or_404(bill_id)
        qr_id = sanitize_input(qr_code).upper()
        
        if not validate_parent_qr_id(qr_id):
            return jsonify({'success': False, 'message': 'Invalid parent bag QR code format.'})
        
        # Look up the parent bag
        parent_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.PARENT.value).first()
        
        if not parent_bag:
            return jsonify({'success': False, 'message': 'Parent bag not found. Please check the QR code.'})
        
        # Check if already linked to this bill
        existing_link = BillBag.query.filter_by(bill_id=bill.id, bag_id=parent_bag.id).first()
        if existing_link:
            return jsonify({'success': False, 'message': 'This parent bag is already linked to this bill.'})
        
        # Check if bill already has the maximum number of bags
        current_bag_count = BillBag.query.filter_by(bill_id=bill.id).count()
        if current_bag_count >= bill.parent_bag_count:
            return jsonify({'success': False, 'message': f'Bill already has the maximum number of parent bags ({bill.parent_bag_count}). Cannot add more bags.'})
        
        # Create bill-bag link
        bill_bag = BillBag(
            bill_id=bill.id,
            bag_id=parent_bag.id
        )
        
        db.session.add(bill_bag)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Parent bag {qr_id} linked to bill successfully!',
            'parent_qr': qr_id,
            'remaining_bags': bill.parent_bag_count - (current_bag_count + 1)
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Bill parent scan error: {str(e)}')
        return jsonify({'success': False, 'message': 'Error linking parent bag to bill.'})

@app.route('/bag/<qr_id>')
@login_required
def bag_details(qr_id):
    """Display detailed information about a specific bag"""
    bag = Bag.query.filter_by(qr_id=qr_id).first_or_404()
    
    # Get related information
    if bag.type == BagType.PARENT.value:
        child_bags = db.session.query(Bag).join(Link).filter(Link.parent_bag_id == bag.id).all()
        parent_bag = None
        bills = db.session.query(Bill).join(BillBag).filter(BillBag.bag_id == bag.id).all()
        scans = Scan.query.filter_by(parent_bag_id=bag.id).order_by(desc(Scan.timestamp)).all()
    else:
        child_bags = []
        link = Link.query.filter_by(child_bag_id=bag.id).first()
        parent_bag = link.parent_bag if link else None
        bills = []
        if parent_bag:
            bills = db.session.query(Bill).join(BillBag).filter(BillBag.bag_id == parent_bag.id).all()
        scans = Scan.query.filter_by(child_bag_id=bag.id).order_by(desc(Scan.timestamp)).all()
    
    return render_template('bag_detail.html',
                         bag=bag,
                         child_bags=child_bags,
                         parent_bag=parent_bag,
                         bills=bills,
                         scans=scans)

# API endpoints for dashboard data
@app.route('/api/stats')
@login_required
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
@login_required
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
