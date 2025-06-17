"""
Working authentication system for deployment environment
Uses multiple fallback methods to ensure reliability
"""
import os
import json
import time
import hashlib
from flask import request, session, redirect, url_for, make_response
from functools import wraps
import logging

# Simple file-based session storage
AUTH_DIR = "/tmp/auth_sessions"

def ensure_auth_dir():
    """Ensure auth directory exists"""
    try:
        os.makedirs(AUTH_DIR, exist_ok=True)
        return True
    except:
        return False

def create_auth_session(user):
    """Create authentication session with multiple methods"""
    if not ensure_auth_dir():
        logging.error("Could not create auth directory")
        return None
    
    # Create session ID
    session_data = f"{user.id}-{user.username}-{int(time.time())}"
    session_id = hashlib.md5(session_data.encode()).hexdigest()
    
    # User data
    user_info = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'created': time.time(),
        'expires': time.time() + 86400  # 24 hours
    }
    
    # Save to file
    try:
        auth_file = os.path.join(AUTH_DIR, f"auth_{session_id}.json")
        with open(auth_file, 'w') as f:
            json.dump(user_info, f)
        
        # Set Flask session data
        session.clear()
        session.permanent = True
        session['auth_session_id'] = session_id
        session['logged_in'] = True
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_role'] = user.role
        
        logging.info(f"Auth session created for {user.username}: {session_id[:8]}")
        return session_id
        
    except Exception as e:
        logging.error(f"Failed to create auth session: {e}")
        return None

def get_auth_session():
    """Get current authentication session"""
    # Check Flask session first
    if session.get('logged_in') and session.get('user_id'):
        return {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('user_role'),
            'valid': True
        }
    
    # Check file-based session
    session_id = session.get('auth_session_id') or request.args.get('s')
    if session_id:
        try:
            auth_file = os.path.join(AUTH_DIR, f"auth_{session_id}.json")
            if os.path.exists(auth_file):
                with open(auth_file, 'r') as f:
                    user_data = json.load(f)
                
                # Check expiration
                if time.time() < user_data.get('expires', 0):
                    return user_data
                else:
                    # Clean up expired
                    os.remove(auth_file)
        except:
            pass
    
    return None

def is_authenticated_working():
    """Check if user is authenticated"""
    auth_data = get_auth_session()
    return auth_data is not None

def login_user_working(user):
    """Login user with working authentication"""
    session_id = create_auth_session(user)
    
    if not session_id:
        return redirect(url_for('login', error='Login failed'))
    
    # Create response with session ID in URL for maximum compatibility
    redirect_url = url_for('index', s=session_id)
    response = make_response(redirect(redirect_url))
    
    # Set cookies with various configurations
    response.set_cookie('auth_session', session_id, max_age=86400, httponly=False, secure=False, path='/')
    
    logging.info(f"Working login success for {user.username}")
    return response

def require_auth_working(f):
    """Working authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated_working():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_working():
    """Get current user info"""
    return get_auth_session()

def logout_user_working():
    """Logout user"""
    session_id = session.get('auth_session_id')
    if session_id:
        try:
            auth_file = os.path.join(AUTH_DIR, f"auth_{session_id}.json")
            if os.path.exists(auth_file):
                os.remove(auth_file)
        except:
            pass
    
    session.clear()
    logging.info("User logged out")
