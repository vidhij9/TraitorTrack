"""
Ultimate authentication solution for problematic deployment environments
This approach bypasses ALL session/cookie issues by using a simple database-backed system
"""
from flask import request, redirect, url_for, make_response
from functools import wraps
import hashlib
import time
import logging

def create_auth_session(user):
    """Create authentication session in database"""
    try:
        from app_clean import db
        from models import User
        
        # Create unique session token
        timestamp = str(int(time.time()))
        session_data = f"{user.id}-{user.username}-{timestamp}"
        session_token = hashlib.sha256(session_data.encode()).hexdigest()
        
        # Store directly in user record
        user.session_token = session_token
        user.session_expires = time.time() + 86400  # 24 hours
        db.session.commit()
        
        logging.info(f"Created DB session for {user.username}: {session_token[:8]}")
        return session_token
        
    except Exception as e:
        logging.error(f"Failed to create DB session: {e}")
        return None

def verify_auth_session(session_token):
    """Verify authentication session from database"""
    if not session_token:
        return None
    
    try:
        from models import User
        
        user = User.query.filter_by(session_token=session_token).first()
        if user and hasattr(user, 'session_expires'):
            if time.time() < user.session_expires:
                return user
            else:
                # Session expired, clear it
                user.session_token = None
                user.session_expires = None
                from app_clean import db
                db.session.commit()
        
        return None
        
    except Exception as e:
        logging.error(f"Failed to verify session: {e}")
        return None

def get_auth_token_from_request():
    """Get auth token from various sources in request"""
    # Check URL parameter first (most reliable for deployment)
    token = request.args.get('token')
    if token:
        return token
    
    # Check form data
    token = request.form.get('auth_token')
    if token:
        return token
    
    # Check cookies as fallback
    token = request.cookies.get('auth_session')
    if token:
        return token
    
    return None

def is_user_authenticated():
    """Check if user is authenticated via database lookup"""
    token = get_auth_token_from_request()
    if token:
        user = verify_auth_session(token)
        return user is not None
    return False

def get_current_user():
    """Get current authenticated user"""
    token = get_auth_token_from_request()
    if token:
        return verify_auth_session(token)
    return None

def login_user_ultimate(user):
    """Ultimate login method that works in any environment"""
    session_token = create_auth_session(user)
    
    if not session_token:
        return redirect(url_for('login', error='Login failed'))
    
    # Redirect with token in URL for maximum compatibility
    redirect_url = url_for('index', token=session_token)
    response = make_response(redirect(redirect_url))
    
    # Also set cookie as backup
    response.set_cookie('auth_session', session_token, 
                       max_age=86400, 
                       httponly=False, 
                       secure=False, 
                       samesite=None,
                       path='/')
    
    logging.info(f"Ultimate login success for {user.username}")
    return response

def logout_user_ultimate():
    """Ultimate logout method"""
    token = get_auth_token_from_request()
    if token:
        user = verify_auth_session(token)
        if user:
            user.session_token = None
            user.session_expires = None
            from app_clean import db
            db.session.commit()
    
    response = make_response(redirect(url_for('login')))
    response.set_cookie('auth_session', '', expires=0, path='/')
    
    logging.info("Ultimate logout completed")
    return response

def require_auth_ultimate(f):
    """Ultimate authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_user_authenticated():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function