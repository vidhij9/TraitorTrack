"""
Basic authentication system that works reliably in deployment
"""
from flask import request, session, redirect, url_for, render_template
from functools import wraps
import logging

# Simple in-memory session store as fallback
active_sessions = {}

def create_session_token():
    """Create a simple session token"""
    import secrets
    return secrets.token_urlsafe(32)

def login_user_basic(user):
    """Basic login with both session and token storage"""
    # Clear any existing session
    session.clear()
    
    # Create session token
    token = create_session_token()
    
    # Store in Flask session
    session.permanent = True
    session['auth_token'] = token
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session['logged_in'] = True
    
    # Also store in memory as backup
    active_sessions[token] = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role
    }
    
    logging.info(f"User {user.username} logged in with token {token[:8]}...")
    return token

def is_user_authenticated():
    """Check if user is authenticated using multiple methods"""
    # Method 1: Check traditional Flask session (backward compatibility)
    if session.get('logged_in') and session.get('user_id'):
        return True
    
    # Method 2: Check new token-based session
    if session.get('logged_in') and session.get('auth_token'):
        token = session.get('auth_token')
        if token in active_sessions:
            return True
    
    # Method 3: Check for auth token in request headers (for API calls)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.replace('Bearer ', '')
        if token in active_sessions:
            return True
    
    return False

def get_current_user_info():
    """Get current user information"""
    token = session.get('auth_token')
    if token and token in active_sessions:
        return active_sessions[token]
    return None

def logout_user_basic():
    """Logout user and clean up sessions"""
    token = session.get('auth_token')
    if token and token in active_sessions:
        del active_sessions[token]
    session.clear()
    logging.info("User logged out")

def require_auth_basic(f):
    """Authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_user_authenticated():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function