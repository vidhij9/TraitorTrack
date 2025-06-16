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
    """Handle production login with proper error handling"""
    try:
        from models import User
        
        # Find user
        user = User.query.filter_by(username=username).first()
        if not user:
            logger.warning(f"Login attempt for non-existent user: {username}")
            return False, "Invalid username or password"
            
        # Check password
        if not check_password_hash(user.password_hash, password):
            logger.warning(f"Invalid password for user: {username}")
            return False, "Invalid username or password"
            
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
        # Support multiple session formats for compatibility
        authenticated = (
            session.get('authenticated') == True or 
            session.get('logged_in') == True
        )
        
        user_id = session.get('user_id')
        username = session.get('username')
        
        # Log authentication check for debugging
        logger.info(f"Production auth check - authenticated: {authenticated}, user_id: {user_id}, username: {username}")
        
        # Essential checks - user must be authenticated and have valid ID
        if not authenticated or not user_id:
            logger.info("Production auth failed - missing authentication or user_id")
            return False
            
        logger.info("Production auth successful")
        return True
        
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