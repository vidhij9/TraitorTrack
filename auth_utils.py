"""
Centralized authentication utilities - consolidates all duplicate auth functions
"""
from flask import session, redirect, url_for
from functools import wraps
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)

# Session timeout configuration (in seconds)
SESSION_ABSOLUTE_TIMEOUT = int(os.environ.get('SESSION_ABSOLUTE_TIMEOUT', 3600))  # 1 hour default
SESSION_INACTIVITY_TIMEOUT = int(os.environ.get('SESSION_INACTIVITY_TIMEOUT', 1800))  # 30 minutes default
SESSION_WARNING_TIME = int(os.environ.get('SESSION_WARNING_TIME', 300))  # 5 minutes before timeout

# Aliases for compatibility
def is_logged_in():
    """Alias for is_authenticated"""
    return is_authenticated()

def create_session(user_id, username, role, dispatch_area=None, email=None):
    """
    Create a new user session with activity tracking.
    
    Optimized to use Unix timestamps (floats) instead of ISO strings
    for better performance (avoids datetime parsing overhead).
    """
    import time
    
    session['user_id'] = user_id
    session['username'] = username
    session['user_role'] = role
    session['dispatch_area'] = dispatch_area
    session['authenticated'] = True
    session['logged_in'] = True  # Backward compatibility (some routes still check this)
    
    # Store email in session to avoid DB queries (optimization)
    if email:
        session['email'] = email
    
    # Session is non-permanent (expires on browser close) - security feature
    session.permanent = False
    
    # Session timeout tracking (using Unix timestamps for performance)
    now_timestamp = time.time()  # Float seconds since epoch (faster than ISO)
    session['created_at'] = now_timestamp
    session['last_activity'] = now_timestamp

def update_session_activity():
    """
    Update the last activity timestamp.
    
    Optimized to use Unix timestamp (float) instead of ISO string.
    """
    import time
    if is_authenticated():
        session['last_activity'] = time.time()

def check_session_timeout():
    """
    Check if session has expired due to absolute timeout or inactivity.
    
    Optimized to use Unix timestamps (floats) instead of ISO string parsing.
    This avoids expensive datetime.fromisoformat() calls on every auth check.
    
    Returns (is_valid, reason) tuple.
    - is_valid: True if session is still valid, False if expired
    - reason: None if valid, 'absolute' or 'inactivity' if expired
    """
    import time
    if not is_authenticated():
        return True, None  # No session to check
    
    now = time.time()
    
    # Check absolute timeout (using Unix timestamps for speed)
    created_at = session.get('created_at')
    if created_at:
        try:
            # Handle both new (float) and legacy (ISO string) formats for compatibility
            if isinstance(created_at, str):
                # Legacy format - convert once and update
                created_at = datetime.fromisoformat(created_at).timestamp()
                session['created_at'] = created_at  # Upgrade to new format
            
            session_age = now - created_at
            
            if session_age > SESSION_ABSOLUTE_TIMEOUT:
                return False, 'absolute'
        except (ValueError, TypeError, AttributeError):
            # Invalid timestamp, treat as expired
            return False, 'absolute'
    
    # Check inactivity timeout (using Unix timestamps for speed)
    last_activity = session.get('last_activity')
    if last_activity:
        try:
            # Handle both new (float) and legacy (ISO string) formats for compatibility
            if isinstance(last_activity, str):
                # Legacy format - convert once and update
                last_activity = datetime.fromisoformat(last_activity).timestamp()
                session['last_activity'] = last_activity  # Upgrade to new format
            
            inactive_time = now - last_activity
            
            if inactive_time > SESSION_INACTIVITY_TIMEOUT:
                return False, 'inactivity'
        except (ValueError, TypeError, AttributeError):
            # Invalid timestamp, treat as expired
            return False, 'inactivity'
    
    return True, None

def get_session_time_remaining():
    """
    Get time remaining until session expires (in seconds).
    
    Optimized to use Unix timestamps (floats) instead of ISO string parsing.
    Returns the minimum of absolute timeout and inactivity timeout.
    """
    import time
    if not is_authenticated():
        return 0
    
    now = time.time()
    
    # Calculate time remaining for absolute timeout (using Unix timestamps)
    created_at = session.get('created_at')
    absolute_remaining = SESSION_ABSOLUTE_TIMEOUT
    if created_at:
        try:
            # Handle both new (float) and legacy (ISO string) formats
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at).timestamp()
                session['created_at'] = created_at  # Upgrade to new format
            
            session_age = now - created_at
            absolute_remaining = max(0, SESSION_ABSOLUTE_TIMEOUT - session_age)
        except (ValueError, TypeError, AttributeError):
            absolute_remaining = 0
    
    # Calculate time remaining for inactivity timeout (using Unix timestamps)
    last_activity = session.get('last_activity')
    inactivity_remaining = SESSION_INACTIVITY_TIMEOUT
    if last_activity:
        try:
            # Handle both new (float) and legacy (ISO string) formats
            if isinstance(last_activity, str):
                last_activity = datetime.fromisoformat(last_activity).timestamp()
                session['last_activity'] = last_activity  # Upgrade to new format
            
            inactive_time = now - last_activity
            inactivity_remaining = max(0, SESSION_INACTIVITY_TIMEOUT - inactive_time)
        except (ValueError, TypeError, AttributeError):
            inactivity_remaining = 0
    
    # Return the minimum (whichever expires first)
    return min(absolute_remaining, inactivity_remaining)

def should_show_timeout_warning():
    """Check if we should show a timeout warning to the user"""
    time_remaining = get_session_time_remaining()
    return 0 < time_remaining <= SESSION_WARNING_TIME

def clear_session():
    """Clear the current session"""
    session.clear()

def get_current_user():
    """Get current user object"""
    return CurrentUser()

def get_current_user_id():
    """Get current user ID"""
    return get_user_id()

def get_current_username():
    """Get current username"""
    return get_username()

def get_current_user_role():
    """Get current user role"""
    return get_user_role()

def login_required(f):
    """Alias for require_auth decorator"""
    return require_auth(f)

def is_authenticated():
    """
    Unified authentication check - single source of truth.
    
    Optimized to use single 'authenticated' key (removed redundant 'logged_in' check)
    for faster session lookups.
    """
    return session.get('authenticated', False) and session.get('user_id') is not None

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
    """
    Get current user's email.
    
    Optimized to use session storage instead of database query.
    Email is now stored in session during login (see create_session).
    """
    # Try session first (optimization - avoids DB query)
    email = session.get('email')
    if email:
        return email
    
    # Fallback to database query for legacy sessions
    user_id = get_user_id()
    if user_id:
        from models import User
        user = User.query.get(user_id)
        if user and user.email:
            # Cache in session for future requests
            session['email'] = user.email
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