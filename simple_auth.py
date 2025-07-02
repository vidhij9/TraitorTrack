"""
Simple, reliable authentication system for production deployment
"""
import os
import hashlib
import logging
from datetime import datetime, timedelta
from flask import session, request, redirect, url_for, flash

logger = logging.getLogger(__name__)

def create_auth_session(user):
    """Create authenticated session for user"""
    try:
        # Clear any existing session data
        session.clear()
        
        # Set session data
        session.permanent = True
        session['authenticated'] = True
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_role'] = getattr(user.role, 'value', user.role) if hasattr(user, 'role') else 'user'
        session['dispatch_area'] = getattr(user, 'dispatch_area', None)  # Store dispatch area for area-based access control
        session['auth_time'] = datetime.now().timestamp()
        
        # Force session to save
        session.modified = True
        
        logger.info(f"Session created for user: {user.username}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        return False

def is_authenticated():
    """Check if user is authenticated - supports multiple session formats"""
    try:
        # Check for both session formats for compatibility
        authenticated = (
            session.get('authenticated', False) or 
            session.get('logged_in', False)
        )
        user_id = session.get('user_id')
        
        # Log current session state for debugging
        logger.info(f"Authentication check - Session data: {dict(session)}")
        logger.info(f"Authenticated: {authenticated}")
        
        if not all([authenticated, user_id]):
            logger.info("User not authenticated - missing authenticated flag or user_id")
            return False
            
        # Check if session has auth_time and validate it
        auth_time = session.get('auth_time')
        if auth_time:
            # Check if session is too old (24 hours)
            if datetime.now().timestamp() - auth_time > 86400:
                logger.info("Session expired - clearing")
                clear_auth_session()
                return False
        
        logger.info("User is authenticated")
        return True
        
    except Exception as e:
        logger.error(f"Authentication check failed: {e}")
        return False

def get_current_user():
    """Get current authenticated user"""
    if not is_authenticated():
        return None
        
    try:
        from models import User
        user_id = session.get('user_id')
        return User.query.get(user_id) if user_id else None
        
    except Exception as e:
        logger.error(f"Failed to get current user: {e}")
        return None

def clear_auth_session():
    """Clear authentication session"""
    try:
        session.clear()
        logger.info("Authentication session cleared")
        
    except Exception as e:
        logger.error(f"Failed to clear session: {e}")

def get_current_user_data():
    """Get current user data from session"""
    try:
        if is_authenticated():
            return {
                'user_id': session.get('user_id'),
                'username': session.get('username'),
                'user_role': session.get('user_role'),
                'auth_time': session.get('auth_time')
            }
        return None
    except Exception as e:
        logger.error(f"Error getting user data: {e}")
        return None

def require_auth(f):
    """Decorator to require authentication"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def login_user_simple(username, password):
    """Simple login function"""
    try:
        from models import User
        
        user = User.query.filter_by(username=username).first()
        if not user:
            logger.info(f"User not found: {username}")
            return False, "Invalid username or password"
            
        if not user.check_password(password):
            logger.info(f"Invalid password for user: {username}")
            return False, "Invalid username or password"
            
        if create_auth_session(user):
            logger.info(f"Login successful for user: {username}")
            return True, "Login successful"
        else:
            logger.error(f"Failed to create session for user: {username}")
            return False, "Login failed - session error"
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return False, "Login failed - system error"