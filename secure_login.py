"""
Bulletproof login system for deployment environments
"""
from flask import session, request, redirect, url_for, render_template, make_response
from functools import wraps
import hashlib
import time
import os
import logging

# Global session store for absolute reliability
ACTIVE_SESSIONS = {}
SESSION_TIMEOUT = 86400  # 24 hours

def generate_session_id():
    """Generate a unique session ID"""
    timestamp = str(time.time())
    random_data = os.urandom(32).hex()
    return hashlib.sha256(f"{timestamp}{random_data}".encode()).hexdigest()

def create_secure_session(user):
    """Create a secure session with multiple storage methods"""
    session_id = generate_session_id()
    
    # Store in global dictionary
    ACTIVE_SESSIONS[session_id] = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'created_at': time.time(),
        'last_activity': time.time()
    }
    
    # Store in Flask session with multiple keys for redundancy
    session.permanent = True
    session.clear()
    session['session_id'] = session_id
    session['logged_in'] = True
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session['login_time'] = time.time()
    
    logging.info(f"Created secure session {session_id[:8]} for user {user.username}")
    return session_id

def is_session_valid(session_id=None):
    """Check if session is valid using multiple verification methods"""
    if not session_id:
        session_id = session.get('session_id')
    
    if not session_id:
        return False
    
    # Check global session store
    if session_id in ACTIVE_SESSIONS:
        session_data = ACTIVE_SESSIONS[session_id]
        
        # Check timeout
        if time.time() - session_data['last_activity'] > SESSION_TIMEOUT:
            cleanup_session(session_id)
            return False
        
        # Update last activity
        session_data['last_activity'] = time.time()
        return True
    
    return False

def get_session_user(session_id=None):
    """Get user data from session"""
    if not session_id:
        session_id = session.get('session_id')
    
    if session_id and session_id in ACTIVE_SESSIONS:
        return ACTIVE_SESSIONS[session_id]
    
    # Fallback to Flask session
    if session.get('logged_in') and session.get('user_id'):
        return {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('role')
        }
    
    return None

def cleanup_session(session_id=None):
    """Clean up session data"""
    if not session_id:
        session_id = session.get('session_id')
    
    if session_id and session_id in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[session_id]
    
    session.clear()
    logging.info(f"Cleaned up session {session_id[:8] if session_id else 'unknown'}")

def is_user_logged_in():
    """Check if user is logged in with multiple fallback methods"""
    # Method 1: Check session ID in global store
    session_id = session.get('session_id')
    if session_id and is_session_valid(session_id):
        return True
    
    # Method 2: Check Flask session directly
    if session.get('logged_in') and session.get('user_id'):
        login_time = session.get('login_time', 0)
        if time.time() - login_time < SESSION_TIMEOUT:
            return True
    
    # Method 3: Check for cookie-based session
    cookie_session = request.cookies.get('secure_session')
    if cookie_session and cookie_session in ACTIVE_SESSIONS:
        return True
    
    return False

def require_login(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_user_logged_in():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def cleanup_expired_sessions():
    """Clean up expired sessions"""
    current_time = time.time()
    expired_sessions = []
    
    for session_id, data in ACTIVE_SESSIONS.items():
        if current_time - data['last_activity'] > SESSION_TIMEOUT:
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        del ACTIVE_SESSIONS[session_id]
    
    logging.info(f"Cleaned up {len(expired_sessions)} expired sessions")