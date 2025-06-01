"""
Simple authentication system to replace Flask-Login
"""
from flask import session, request, redirect, url_for, flash
from functools import wraps
from models import User

def login_required(f):
    """Decorator to require login for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        if session.get('user_role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current user from session"""
    if session.get('logged_in'):
        return {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('user_role'),
            'is_admin': session.get('user_role') == 'admin'
        }
    return None

def login_user(user):
    """Log in a user"""
    session.permanent = True
    session['user_id'] = user.id
    session['username'] = user.username
    session['user_role'] = user.role
    session['logged_in'] = True
    return True

def logout_user():
    """Log out current user"""
    session.clear()
    return True