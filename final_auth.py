"""
Final authentication solution that works without database changes
Uses file-based session storage for deployment reliability
"""
import os
import json
import time
import hashlib
from flask import request, session, redirect, url_for, make_response
from functools import wraps
import logging

# Session storage directory
SESSION_DIR = "/tmp/tracetrack_sessions"

def ensure_session_dir():
    """Ensure session directory exists"""
    try:
        os.makedirs(SESSION_DIR, exist_ok=True)
        return True
    except:
        return False

def create_session_file(user):
    """Create session file for user"""
    if not ensure_session_dir():
        return None
    
    # Create unique session ID
    timestamp = str(int(time.time()))
    session_data = f"{user.id}-{user.username}-{timestamp}"
    session_id = hashlib.md5(session_data.encode()).hexdigest()
    
    # Create session data
    user_data = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'created': time.time(),
        'expires': time.time() + 86400  # 24 hours
    }
    
    # Save to file
    try:
        session_file = os.path.join(SESSION_DIR, f"session_{session_id}.json")
        with open(session_file, 'w') as f:
            json.dump(user_data, f)
        
        logging.info(f"Created session file for {user.username}: {session_id[:8]}")
        return session_id
    except Exception as e:
        logging.error(f"Failed to create session file: {e}")
        return None

def verify_session_file(session_id):
    """Verify session file exists and is valid"""
    if not session_id:
        return None
    
    try:
        session_file = os.path.join(SESSION_DIR, f"session_{session_id}.json")
        
        if not os.path.exists(session_file):
            return None
        
        with open(session_file, 'r') as f:
            user_data = json.load(f)
        
        # Check expiration
        if time.time() > user_data.get('expires', 0):
            # Clean up expired session
            os.remove(session_file)
            return None
        
        return user_data
    except Exception as e:
        logging.error(f"Failed to verify session: {e}")
        return None

def get_session_id_from_request():
    """Get session ID from various sources"""
    # Check URL parameter (most reliable for deployment)
    session_id = request.args.get('s')
    if session_id:
        return session_id
    
    # Check form data
    session_id = request.form.get('session_id')
    if session_id:
        return session_id
    
    # Check cookies
    session_id = request.cookies.get('app_session')
    if session_id:
        return session_id
    
    # Check Flask session as fallback
    session_id = session.get('file_session_id')
    if session_id:
        return session_id
    
    return None

def is_authenticated_final():
    """Check if user is authenticated via file session"""
    session_id = get_session_id_from_request()
    if session_id:
        user_data = verify_session_file(session_id)
        return user_data is not None
    return False

def get_current_user_final():
    """Get current user data from file session"""
    session_id = get_session_id_from_request()
    if session_id:
        return verify_session_file(session_id)
    return None

def login_user_final(user):
    """Final login method using file-based sessions"""
    session_id = create_session_file(user)
    
    if not session_id:
        return redirect(url_for('login', error='Login failed'))
    
    # Store in Flask session for backup
    session.clear()
    session.permanent = True
    session['file_session_id'] = session_id
    session['logged_in'] = True
    session['user_id'] = user.id
    
    # Redirect with session ID in URL for maximum compatibility
    redirect_url = url_for('index', s=session_id)
    response = make_response(redirect(redirect_url))
    
    # Set multiple cookies with different configurations
    response.set_cookie('app_session', session_id, max_age=86400, httponly=False, secure=False, path='/')
    response.set_cookie('backup_session', session_id, max_age=86400, httponly=False, secure=False, samesite='Lax', path='/')
    
    logging.info(f"Final login success for {user.username}")
    return response

def cleanup_expired_sessions():
    """Clean up expired session files"""
    if not os.path.exists(SESSION_DIR):
        return
    
    try:
        current_time = time.time()
        cleaned = 0
        
        for filename in os.listdir(SESSION_DIR):
            if filename.startswith('session_') and filename.endswith('.json'):
                filepath = os.path.join(SESSION_DIR, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    if current_time > data.get('expires', 0):
                        os.remove(filepath)
                        cleaned += 1
                except:
                    # Remove corrupted files
                    os.remove(filepath)
                    cleaned += 1
        
        if cleaned > 0:
            logging.info(f"Cleaned up {cleaned} expired sessions")
    except Exception as e:
        logging.error(f"Failed to cleanup sessions: {e}")

def require_auth_final(f):
    """Final authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated_final():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function