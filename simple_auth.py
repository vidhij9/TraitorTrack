"""
Simple and reliable session-based authentication system
"""
from flask import session, redirect, url_for, current_app
from functools import wraps
import hashlib
import time

def create_session(user):
    """Create a user session with all necessary data"""
    session.clear()
    session.permanent = True
    session['user_id'] = user.id
    session['username'] = user.username
    session['user_role'] = user.role
    session['dispatch_area'] = user.dispatch_area
    session['email'] = user.email
    session['logged_in'] = True
    session['login_time'] = time.time()
    # Create a session hash for validation
    session['session_hash'] = hashlib.md5(f"{user.id}{user.username}{time.time()}".encode()).hexdigest()
    return True

def clear_session():
    """Clear all session data"""
    session.clear()
    return True

def is_logged_in():
    """Check if user is logged in"""
    return session.get('logged_in', False) and session.get('user_id') is not None

def get_current_user_id():
    """Get current user ID from session"""
    if is_logged_in():
        return session.get('user_id')
    return None

def get_current_username():
    """Get current username from session"""
    if is_logged_in():
        return session.get('username')
    return None

def get_current_user_role():
    """Get current user role from session"""
    if is_logged_in():
        return session.get('user_role')
    return None

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for('login'))
        if get_current_user_role() != 'admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

class SimpleUser:
    """Simple user object for templates"""
    def __init__(self):
        self.id = get_current_user_id()
        self.username = get_current_username()
        self.role = get_current_user_role()
        self.dispatch_area = session.get('dispatch_area')
        self.email = session.get('email')
        self.is_authenticated = is_logged_in()
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_biller(self):
        return self.role == 'biller'
    
    def is_dispatcher(self):
        return self.role == 'dispatcher'

# Create a simple current_user object
def get_current_user():
    """Get current user object"""
    if is_logged_in():
        return SimpleUser()
    return None