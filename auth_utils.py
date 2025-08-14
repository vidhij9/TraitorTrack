"""
Centralized authentication utilities - consolidates all duplicate auth functions
"""
from flask import session, redirect, url_for
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def is_authenticated():
    """Unified authentication check - single source of truth"""
    return (
        session.get('logged_in', False) or 
        session.get('authenticated', False)
    ) and session.get('user_id') is not None

def require_auth(f):
    """Decorator to require authentication - unified version"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect('/login')
        if not is_admin():
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

def get_user_role():
    """Get current user role from session"""
    return session.get('user_role')

def get_user_id():
    """Get current user ID from session"""
    return session.get('user_id')

def get_username():
    """Get current username from session"""
    return session.get('username')

def get_dispatch_area():
    """Get current user's dispatch area"""
    return session.get('dispatch_area')

def get_email():
    """Get current user's email from database"""
    user_id = get_user_id()
    if user_id:
        from models import User
        user = User.query.get(user_id)
        if user:
            return user.email
    return None

def is_admin():
    """Check if current user is admin"""
    return session.get('user_role') == 'admin'

def is_biller():
    """Check if current user is a biller"""
    return session.get('user_role') == 'biller'

def is_dispatcher():
    """Check if current user is a dispatcher"""
    return session.get('user_role') == 'dispatcher'

def can_edit_bills():
    """Check if current user can edit bills"""
    role = session.get('user_role')
    return role in ['admin', 'biller']

def can_manage_users():
    """Check if current user can manage other users"""
    return session.get('user_role') == 'admin'

def can_access_area(area):
    """Check if user can access a specific dispatch area"""
    role = session.get('user_role')
    if role in ['admin', 'biller']:
        return True
    if role == 'dispatcher':
        return session.get('dispatch_area') == area
    return False

class CurrentUser:
    """Unified current user object for the application"""
    @property
    def id(self):
        return get_user_id()
    
    @property
    def username(self):
        return get_username()
    
    @property
    def role(self):
        return get_user_role()
    
    @property
    def dispatch_area(self):
        return get_dispatch_area()
    
    @property
    def email(self):
        return get_email()
    
    @property
    def is_authenticated(self):
        return is_authenticated()
    
    def is_admin(self):
        return is_admin()
    
    def is_biller(self):
        return is_biller()
    
    def is_dispatcher(self):
        return is_dispatcher()
    
    def can_edit_bills(self):
        return can_edit_bills()
    
    def can_manage_users(self):
        return can_manage_users()
    
    def can_access_area(self, area):
        return can_access_area(area)
    
    def check_password(self, password):
        """Check if the provided password is correct"""
        from models import User
        from werkzeug.security import check_password_hash
        user_id = self.id
        if user_id:
            user = User.query.get(user_id)
            if user and user.password_hash:
                return check_password_hash(user.password_hash, password)
        return False
    
    def set_password(self, password):
        """Set a new password for the user"""
        from models import User, db
        from werkzeug.security import generate_password_hash
        user_id = self.id
        if user_id:
            user = User.query.get(user_id)
            if user:
                user.password_hash = generate_password_hash(password)
                db.session.commit()
                return True
        return False

# Single instance to be used throughout the application
current_user = CurrentUser()