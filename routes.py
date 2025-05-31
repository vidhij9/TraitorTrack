"""
Routes for TraceTrack application - Location functionality completely removed
"""
from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_file, abort, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
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
    
    return render_template('user_management.html', user_data=user_data)

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

@app.route('/')
def index():
    """Main dashboard page"""
    if not current_user.is_authenticated:
        return render_template('landing.html')
    
    # Dashboard data for logged-in users
    today = datetime.now().date()
    
    # User's scan activity today
    user_scans_today = Scan.query.filter(
        Scan.user_id == current_user.id,
        func.date(Scan.timestamp) == today
    ).count()
    
    # Recent scans by current user
    recent_scans = Scan.query.filter(Scan.user_id == current_user.id)\
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
@limiter.limit("5 per minute")
def login():
    """User login page with rate limiting and account lockout to prevent brute force attacks"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        username = sanitize_input(form.username.data)
        password = form.password.data
        
        # Check if account is locked
        is_locked, remaining_time = is_account_locked(username)
        if is_locked:
            flash(f'Account locked due to too many failed attempts. Try again in {remaining_time // 60} minutes.', 'error')
            return render_template('login.html', form=form)
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.verified:
                flash('Please verify your email address before logging in.', 'warning')
                return render_template('login.html', form=form)
            
            # Successful login
            reset_failed_attempts(username)
            login_user(user, remember=getattr(form, 'remember_me', None) and form.remember_me.data)
            track_login_activity(user.id, success=True)
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('index')
            
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page)
        else:
            # Failed login
            is_locked, attempts_remaining, lockout_time = record_failed_attempt(username)
            if user:
                track_login_activity(user.id, success=False)
            
            if is_locked:
                flash('Account locked due to too many failed attempts. Please try again later.', 'error')
            else:
                flash(f'Invalid credentials. {attempts_remaining} attempts remaining.', 'error')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

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
    """Allow users to promote themselves to admin with secret code"""
    form = PromoteToAdminForm()
    
    if form.validate_on_submit():
        secret_code = form.secret_code.data
        
        # Simple secret code check - in production, use environment variable
        if secret_code == "ADMIN2024":
            current_user.role = UserRole.ADMIN.value
            db.session.commit()
            flash('You have been promoted to admin!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid admin code.', 'error')
    
    return render_template('promote_admin.html', form=form)

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
    
    if form.validate_on_submit():
        qr_id = sanitize_input(getattr(form, 'qr_id', form).data).upper()
        
        # Look up the bag (could be parent or child)
        bag = Bag.query.filter_by(qr_id=qr_id).first()
        
        if bag:
            # Get related information based on bag type
            if bag.type == BagType.PARENT.value:
                # Get child bags
                child_bags = db.session.query(Bag).join(Link).filter(Link.parent_bag_id == bag.id).all()
                
                # Get bills this parent bag is linked to
                bills = db.session.query(Bill).join(BillBag).filter(BillBag.bag_id == bag.id).all()
                
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
                
                # Get bills through parent bag
                bills = []
                if parent_bag:
                    bills = db.session.query(Bill).join(BillBag).filter(BillBag.bag_id == parent_bag.id).all()
                
                bag_info = {
                    'bag': bag,
                    'type': 'child',
                    'child_bags': [],
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
    
    return render_template('bag_management.html', bags=bags, bag_type=bag_type, search_query=search_query)

# Bill management routes
@app.route('/bills')
@login_required
def bill_management():
    """Bill management dashboard with search functionality"""
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        bills = Bill.query.filter(
            or_(
                Bill.bill_id.contains(search_query),
                Bill.description.contains(search_query)
            )
        ).order_by(desc(Bill.created_at)).all()
    else:
        bills = Bill.query.order_by(desc(Bill.created_at)).limit(50).all()
    
    # Get parent bags count for each bill
    bill_data = []
    for bill in bills:
        parent_bags = db.session.query(Bag).join(BillBag).filter(BillBag.bill_id == bill.id).all()
        bill_data.append({
            'bill': bill,
            'parent_bags': parent_bags,
            'parent_count': len(parent_bags)
        })
    
    return render_template('bill_management.html', bill_data=bill_data, search_query=search_query)

@app.route('/bill/create', methods=['POST'])
@login_required
def create_bill():
    """Create a new bill"""
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
    """Delete a bill and all its bag links"""
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

@app.route('/bill/scan_parent')
@app.route('/bill/<int:bill_id>/scan_parent')
@login_required
def scan_bill_parent(bill_id=None):
    """Scan parent bags to add to bill"""
    if bill_id:
        bill = Bill.query.get_or_404(bill_id)
    else:
        # If no bill_id provided, redirect to bill management
        flash('Please select a bill first.', 'info')
        return redirect(url_for('bill_management'))
    
    form = ScanParentForm()
    
    # Get current parent bags linked to this bill
    linked_bags = db.session.query(Bag).join(BillBag).filter(BillBag.bill_id == bill.id).all()
    
    return render_template('scan_bill_parent.html', form=form, bill=bill, linked_bags=linked_bags)

@app.route('/bill/<int:bill_id>/scan_parent', methods=['POST'])
@login_required
def process_bill_parent_scan():
    """Process a parent bag scan for bill linking"""
    bill_id = request.form.get('bill_id')
    if not bill_id:
        flash('Bill ID missing.', 'error')
        return redirect(url_for('bill_management'))
    
    bill = Bill.query.get_or_404(bill_id)
    form = ScanParentForm()
    
    if form.validate_on_submit():
        try:
            qr_id = sanitize_input(getattr(form, 'qr_id', form).data).upper()
            
            if not validate_parent_qr_id(qr_id):
                flash('Invalid parent bag QR code format.', 'error')
                return redirect(url_for('scan_bill_parent', bill_id=bill_id))
            
            # Look up the parent bag
            parent_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.PARENT.value).first()
            
            if not parent_bag:
                flash('Parent bag not found. Please check the QR code.', 'error')
                return redirect(url_for('scan_bill_parent', bill_id=bill_id))
            
            # Check if already linked to this bill
            existing_link = BillBag.query.filter_by(bill_id=bill.id, bag_id=parent_bag.id).first()
            if existing_link:
                flash('This parent bag is already linked to this bill.', 'warning')
                return redirect(url_for('scan_bill_parent', bill_id=bill_id))
            
            # Create bill-bag link
            bill_bag = BillBag(
                bill_id=bill.id,
                bag_id=parent_bag.id
            )
            
            db.session.add(bill_bag)
            db.session.commit()
            
            flash(f'Parent bag {qr_id} linked to bill successfully!', 'success')
            return redirect(url_for('scan_bill_parent', bill_id=bill_id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error linking parent bag to bill.', 'error')
            app.logger.error(f'Bill parent scan error: {str(e)}')
    
    return redirect(url_for('scan_bill_parent', bill_id=bill_id))

@app.route('/bill/<int:bill_id>')
@login_required
def view_bill(bill_id):
    """View bill details with parent bags and child bags"""
    bill = Bill.query.get_or_404(bill_id)
    
    # Get all parent bags linked to this bill
    parent_bags = db.session.query(Bag).join(BillBag).filter(BillBag.bill_id == bill.id).all()
    
    # Get all child bags for these parent bags
    child_bags = []
    for parent_bag in parent_bags:
        children = db.session.query(Bag).join(Link).filter(Link.parent_bag_id == parent_bag.id).all()
        child_bags.extend(children)
    
    # Get scan history for all bags in this bill
    all_bag_ids = [bag.id for bag in parent_bags + child_bags]
    scans = Scan.query.filter(
        or_(
            Scan.parent_bag_id.in_([bag.id for bag in parent_bags]),
            Scan.child_bag_id.in_([bag.id for bag in child_bags])
        )
    ).order_by(desc(Scan.timestamp)).all()
    
    return render_template('view_bill.html', 
                         bill=bill, 
                         parent_bags=parent_bags, 
                         child_bags=child_bags,
                         scans=scans)

@app.route('/bag/<qr_id>')
@login_required
def bag_detail(qr_id):
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