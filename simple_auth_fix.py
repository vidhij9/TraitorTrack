"""
Simple authentication fix for production deployment
"""
from flask import session, request, redirect, url_for, render_template
from functools import wraps
import logging

def require_auth(f):
    """Simple authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def login_user(user):
    """Simple login function"""
    session.clear()
    session['authenticated'] = True
    session['user_id'] = user.id
    session['username'] = user.username
    session['user_role'] = user.role
    session.permanent = True
    logging.info(f"User {user.username} logged in successfully")

def logout_user():
    """Simple logout function"""
    session.clear()
    logging.info("User logged out")

def is_authenticated():
    """Check if user is authenticated"""
    return session.get('authenticated', False)

def get_current_user_id():
    """Get current user ID"""
    return session.get('user_id')

def is_admin():
    """Check if current user is admin"""
    return session.get('user_role') == 'admin'