"""
Ultra-simple authentication that works in all deployment environments
Uses URL parameters and local storage as backup to cookies
"""
from flask import request, redirect, url_for, session
from functools import wraps
import hashlib
import time
import logging

# Simple authentication store
AUTH_STORE = {}

def create_simple_auth_key(user):
    """Create a simple authentication key"""
    timestamp = str(int(time.time()))
    user_data = f"{user.id}-{user.username}-{timestamp}"
    auth_key = hashlib.md5(user_data.encode()).hexdigest()
    
    # Store user data
    AUTH_STORE[auth_key] = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'created': time.time()
    }
    
    logging.info(f"Created auth key {auth_key[:8]} for {user.username}")
    return auth_key

def check_auth_key(auth_key):
    """Check if auth key is valid"""
    if not auth_key:
        return False
    
    if auth_key in AUTH_STORE:
        user_data = AUTH_STORE[auth_key]
        # Check if not expired (24 hours)
        if time.time() - user_data['created'] < 86400:
            return True
        else:
            # Clean up expired key
            del AUTH_STORE[auth_key]
    
    return False

def get_user_from_auth_key(auth_key):
    """Get user data from auth key"""
    if auth_key and auth_key in AUTH_STORE:
        return AUTH_STORE[auth_key]
    return None

def is_authenticated_simple():
    """Check authentication using multiple methods"""
    # Method 1: Check URL parameter
    auth_key = request.args.get('auth')
    if auth_key and check_auth_key(auth_key):
        return True
    
    # Method 2: Check form data
    auth_key = request.form.get('auth_key')
    if auth_key and check_auth_key(auth_key):
        return True
    
    # Method 3: Check cookies
    auth_key = request.cookies.get('simple_auth')
    if auth_key and check_auth_key(auth_key):
        return True
    
    # Method 4: Check headers
    auth_key = request.headers.get('X-Auth-Key')
    if auth_key and check_auth_key(auth_key):
        return True
    
    # Method 5: Check session as final fallback
    if session.get('simple_auth_key'):
        auth_key = session.get('simple_auth_key')
        if check_auth_key(auth_key):
            return True
    
    return False

def get_current_user_simple():
    """Get current user data"""
    # Try all auth methods
    auth_key = (request.args.get('auth') or 
                request.form.get('auth_key') or 
                request.cookies.get('simple_auth') or 
                request.headers.get('X-Auth-Key') or
                session.get('simple_auth_key'))
    
    if auth_key:
        return get_user_from_auth_key(auth_key)
    
    return None

def login_user_deployment(user):
    """Login user with multiple storage methods"""
    auth_key = create_simple_auth_key(user)
    
    # Store in session
    session['simple_auth_key'] = auth_key
    session['logged_in'] = True
    session['user_id'] = user.id
    session.permanent = True
    
    # Create response with auth key in URL
    redirect_url = url_for('index', auth=auth_key)
    
    from flask import make_response
    response = make_response(redirect(redirect_url))
    
    # Set cookies with different configurations
    response.set_cookie('simple_auth', auth_key, max_age=86400, path='/')
    response.set_cookie('auth_backup', auth_key, max_age=86400, httponly=False, secure=False, path='/')
    
    logging.info(f"Login completed for {user.username} with key {auth_key[:8]}")
    return response

def require_auth_deployment(f):
    """Authentication decorator for deployment"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated_simple():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def cleanup_expired_auth():
    """Clean up expired authentication keys"""
    current_time = time.time()
    expired_keys = [key for key, data in AUTH_STORE.items() 
                   if current_time - data['created'] > 86400]
    
    for key in expired_keys:
        del AUTH_STORE[key]
    
    logging.info(f"Cleaned up {len(expired_keys)} expired auth keys")