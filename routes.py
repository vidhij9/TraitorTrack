import logging
from flask import render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import app, limiter, db
from models import User, UserRole
from account_security import is_account_locked, record_failed_attempt, reset_failed_attempts, track_login_activity

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"])
@limiter.limit("5/minute, 100/day", error_message="Too many login attempts, please try again later.")
def login():
    """User login page with rate limiting and account lockout to prevent brute force attacks"""
    # Add debug logging
    logging.debug("Login route accessed with method: %s", request.method)
    
    # If user is already logged in, redirect to homepage
    if current_user.is_authenticated:
        logging.debug("User already authenticated, redirecting to index")
        return redirect(url_for('index'))
    
    # Handle GET requests
    if request.method == 'GET':
        return render_template('login.html')
    
    # Process POST (login attempt)
    username = request.form.get('username')
    password = request.form.get('password')
    remember = 'remember' in request.form
    
    logging.debug("Login attempt for username: %s", username)
    
    # Check if the account is locked
    is_locked, remaining_time = is_account_locked(username)
    if is_locked:
        logging.debug("Account locked: %s", username)
        flash(f'Account temporarily locked. Try again in {remaining_time} seconds.', 'danger')
        return render_template('login.html')
    
    # Find the user
    user = User.query.filter_by(username=username).first()
    
    # Handle non-existent user
    if not user:
        logging.debug("User not found: %s", username)
        flash('Invalid username or password.', 'danger')
        return render_template('login.html')
    
    # Verify password
    logging.debug("User found: %s, verifying password", username)
    if not user.check_password(password):
        logging.debug("Invalid password for user: %s", username)
        # Record failed login attempt
        is_locked, attempts, lockout_time = record_failed_attempt(username)
        
        if is_locked:
            flash(f'Account locked due to too many failed attempts. Try again in {lockout_time}.', 'danger')
        else:
            flash(f'Invalid username or password. {attempts} attempts remaining before lockout.', 'danger')
        
        return render_template('login.html')
    
    # Check verification status
    if not user.verified:
        logging.debug("User not verified: %s", username)
        flash('Your account is not verified. Please check your email for verification instructions.', 'warning')
        return render_template('login.html')
    
    # Login successful
    logging.debug("Login successful for user: %s", username)
    
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

@app.route('/promote-to-admin', methods=['GET', 'POST'])
@login_required
def promote_to_admin():
    """Allow users to promote themselves to admin with secret code"""
    if current_user.is_admin():
        flash('You are already an admin.', 'info')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        secret_code = request.form.get('secret_code')
        
        if secret_code == 'tracetracksecret':
            current_user.role = UserRole.ADMIN.value
            db.session.commit()
            flash('You have been promoted to admin!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid secret code.', 'danger')
    
    return render_template('promote_admin.html')

@app.route('/')
def index():
    """Main dashboard page"""
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    return render_template('index.html', 
                           user=current_user,
                           is_admin=current_user.is_admin() if current_user.is_authenticated else False)

@app.route('/select_location', methods=['GET', 'POST'])
@login_required
def select_location():
    """Select location for scanning operations"""
    from models import Location
    
    locations = Location.query.all()
    
    if request.method == 'POST':
        location_id = request.form.get('location_id')
        if location_id:
            session['current_location_id'] = int(location_id)
            flash('Location selected successfully.', 'success')
            return redirect(url_for('scan_parent'))
        else:
            flash('Please select a location.', 'warning')
    
    # Clear any existing scanning session
    session.pop('current_parent_bag_id', None)
    session.pop('child_bags_scanned', None)
    
    return render_template('select_location.html', locations=locations)

@app.route('/scan_parent')
@login_required
def scan_parent():
    """Scan parent bag QR code"""
    # Ensure location is selected
    if 'current_location_id' not in session:
        flash('Please select a location first.', 'warning')
        return redirect(url_for('select_location'))
    
    return render_template('scan_parent.html')

@app.route('/process_parent_scan', methods=['POST'])
@login_required
def process_parent_scan():
    """Process the parent bag QR code scan"""
    from models import Bag, BagType, Scan, Location
    import re
    
    if 'current_location_id' not in session:
        return jsonify({'success': False, 'message': 'No location selected'})
    
    qr_code = request.form.get('qr_code')
    
    # Accept any QR code format - no validation required\    qr_code = qr_code.strip()
    
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
    
    # Extract the number of expected child bags from the parent QR code
    try:
        expected_child_count = int(qr_code.split('-')[1])
    except:
        expected_child_count = 5  # Default if parsing fails
    
    return jsonify({
        'success': True,
        'parent_id': parent_bag.id,
        'parent_qr': parent_bag.qr_id,
        'expected_child_count': expected_child_count,
        'message': f'Parent bag {qr_code} scanned successfully. Please scan {expected_child_count} child bags.'
    })