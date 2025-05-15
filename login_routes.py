import logging
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app_new import app, limiter
from models_new import User, UserRole
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