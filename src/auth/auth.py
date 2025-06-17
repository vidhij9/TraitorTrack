"""
Consolidated authentication system.
Combines the best features from multiple auth implementations.
"""

import os
import time
import logging
from datetime import datetime, timedelta
from flask import session, request, current_app
from werkzeug.security import check_password_hash
from ..models.user import User
from ..core.app import db

# Authentication token storage (in-memory for simplicity)
auth_tokens = {}
failed_attempts = {}

def create_auth_token(user):
    """Create a secure authentication token for a user"""
    import secrets
    token = secrets.token_urlsafe(32)
    
    auth_tokens[token] = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'created_at': time.time(),
        'expires_at': time.time() + 86400  # 24 hours
    }
    
    return token

def validate_auth_token(token):
    """Validate an authentication token"""
    if not token or token not in auth_tokens:
        return None
    
    token_data = auth_tokens[token]
    
    # Check if token is expired
    if time.time() > token_data['expires_at']:
        del auth_tokens[token]
        return None
    
    return token_data

def login_user(username, password):
    """
    Authenticate user with username and password.
    Returns (success, message, user_data)
    """
    try:
        # Check for account lockout
        if is_account_locked(username):
            return False, "Account temporarily locked due to too many failed attempts", None
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if not user:
            record_failed_attempt(username)
            return False, "Invalid username or password", None
        
        # Check password
        if not user.check_password(password):
            record_failed_attempt(username)
            return False, "Invalid username or password", None
        
        # Reset failed attempts on successful login
        reset_failed_attempts(username)
        
        # Create auth token
        token = create_auth_token(user)
        
        # Set session data
        session.permanent = True
        session['logged_in'] = True
        session['authenticated'] = True
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session['auth_token'] = token
        session['login_time'] = time.time()
        
        logging.info(f"User {username} logged in successfully")
        
        return True, "Login successful", {
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'token': token
        }
        
    except Exception as e:
        logging.error(f"Login error for {username}: {str(e)}")
        return False, "Login failed due to system error", None

def is_authenticated():
    """Check if current user is authenticated using multiple methods"""
    # Check session
    if session.get('logged_in') and session.get('authenticated'):
        # Verify token is still valid
        token = session.get('auth_token')
        if token and validate_auth_token(token):
            return True
    
    # Check token from cookies/headers
    token = request.cookies.get('auth_token') or request.headers.get('Authorization')
    if token and validate_auth_token(token):
        return True
    
    return False

def get_current_user():
    """Get current authenticated user data"""
    if not is_authenticated():
        return None
    
    # Try from session first
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    
    # Try from token
    token = session.get('auth_token') or request.cookies.get('auth_token')
    if token:
        token_data = validate_auth_token(token)
        if token_data:
            return User.query.get(token_data['user_id'])
    
    return None

def logout_user():
    """Logout current user"""
    # Remove token from storage
    token = session.get('auth_token')
    if token and token in auth_tokens:
        del auth_tokens[token]
    
    # Clear session
    session.clear()
    
    logging.info("User logged out")

def is_account_locked(username):
    """Check if account is locked due to failed attempts"""
    if username not in failed_attempts:
        return False
    
    attempt_data = failed_attempts[username]
    lockout_until = attempt_data.get('lockout_until', 0)
    
    if time.time() < lockout_until:
        return True
    
    # Lockout period expired, reset attempts
    if lockout_until > 0:
        reset_failed_attempts(username)
    
    return False

def record_failed_attempt(username):
    """Record a failed login attempt"""
    current_time = time.time()
    
    if username not in failed_attempts:
        failed_attempts[username] = {
            'count': 0,
            'first_attempt': current_time,
            'last_attempt': current_time,
            'lockout_until': 0
        }
    
    attempt_data = failed_attempts[username]
    attempt_data['count'] += 1
    attempt_data['last_attempt'] = current_time
    
    # Lock account after 5 failed attempts
    max_attempts = current_app.config.get('MAX_LOGIN_ATTEMPTS', 5)
    lockout_duration = current_app.config.get('LOCKOUT_DURATION', 900)  # 15 minutes
    
    if attempt_data['count'] >= max_attempts:
        attempt_data['lockout_until'] = current_time + lockout_duration
        logging.warning(f"Account {username} locked due to {attempt_data['count']} failed attempts")

def reset_failed_attempts(username):
    """Reset failed login attempts for a username"""
    if username in failed_attempts:
        del failed_attempts[username]

def require_auth(f):
    """Decorator to require authentication"""
    from functools import wraps
    from flask import redirect, url_for, flash
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to require admin role"""
    from functools import wraps
    from flask import abort
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('auth.login'))
        
        user = get_current_user()
        if not user or not user.is_admin():
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

# Cleanup function for expired tokens (call periodically)
def cleanup_expired_tokens():
    """Remove expired tokens from storage"""
    current_time = time.time()
    expired_tokens = [
        token for token, data in auth_tokens.items()
        if current_time > data['expires_at']
    ]
    
    for token in expired_tokens:
        del auth_tokens[token]
    
    if expired_tokens:
        logging.info(f"Cleaned up {len(expired_tokens)} expired tokens")
