"""
Production Authentication Fix for TraceTrack
Handles all production-specific authentication and redirection issues
"""

import os
import time
import logging
from flask import session, request, redirect, url_for, flash
from functools import wraps
from werkzeug.security import check_password_hash

logger = logging.getLogger(__name__)

def create_production_session(user):
    """Create a production-ready session with proper security"""
    try:
        # Clear any existing session data
        session.clear()
        
        # Set session data with production-safe values
        session.permanent = True
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_role'] = user.role
        session['authenticated'] = True
        session['auth_time'] = time.time()
        
        # Production session flags
        session['_permanent'] = True
        session['_fresh'] = True
        
        logger.info(f"Production session created for user: {user.username}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create production session: {e}")
        return False

def production_login_handler(username, password):
    """Handle production login with enhanced security and error handling"""
    try:
        from models import User
        from account_security import is_account_locked, record_failed_attempt, reset_failed_attempts
        
        # Check for account lockout first
        is_locked, remaining_time = is_account_locked(username)
        if is_locked:
            logger.warning(f"Login attempt on locked account: {username}")
            return False, f"Account temporarily locked. Try again in {remaining_time//60} minutes."
        
        # Find user with enhanced validation
        user = User.query.filter_by(username=username).first()
        if not user:
            record_failed_attempt(username)
            logger.warning(f"Login attempt for non-existent user: {username}")
            return False, "Invalid username or password"
            
        # Check password with enhanced validation
        if not user.check_password(password):
            record_failed_attempt(username)
            logger.warning(f"Invalid password for user: {username}")
            return False, "Invalid username or password"
        
        # Reset failed attempts on successful login
        reset_failed_attempts(username)
        logger.info(f"Successful login for user: {username}")
        return True, "Login successful"
            
        # Create production session
        if create_production_session(user):
            logger.info(f"Production login successful for user: {username}")
            return True, "Login successful"
        else:
            return False, "Session creation failed"
            
    except Exception as e:
        logger.error(f"Production login error: {e}")
        return False, "Login system error"

def is_production_authenticated():
    """Check if user is authenticated in production environment"""
    try:
        # Multiple authentication checks for production reliability
        checks = [
            session.get('authenticated') == True,
            session.get('user_id') is not None,
            session.get('username') is not None,
            session.get('auth_time') is not None
        ]
        
        return all(checks)
        
    except Exception as e:
        logger.error(f"Production auth check error: {e}")
        return False

def production_logout():
    """Handle production logout with cleanup"""
    try:
        username = session.get('username', 'unknown')
        session.clear()
        logger.info(f"Production logout for user: {username}")
        return True
        
    except Exception as e:
        logger.error(f"Production logout error: {e}")
        return False

def require_production_auth(f):
    """Production authentication decorator with proper redirects"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_production_authenticated():
            # Store the original URL for redirect after login
            session['next_url'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_production_user_data():
    """Get current user data for production templates"""
    try:
        if is_production_authenticated():
            return {
                'id': session.get('user_id'),
                'username': session.get('username'),
                'role': session.get('user_role'),
                'authenticated': True,
                'is_admin': session.get('user_role') == 'admin'
            }
        return {'authenticated': False}
        
    except Exception as e:
        logger.error(f"Error getting production user data: {e}")
        return {'authenticated': False}