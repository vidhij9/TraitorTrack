"""
Account security module for handling login attempts, lockouts, and security-related features.
"""
import time
from datetime import datetime, timedelta
from flask import request, session

# In-memory store of failed login attempts - in a production application, 
# this would be stored in a database or Redis
# Structure: {ip_address: {'attempts': count, 'last_attempt': timestamp, 'locked_until': timestamp}}
failed_login_attempts = {}

# Constants
MAX_LOGIN_ATTEMPTS = 5  # Maximum number of failed login attempts before lockout
LOCKOUT_DURATION = 15 * 60  # Lockout duration in seconds (15 minutes)
ATTEMPT_WINDOW = 30 * 60  # Time window to count failed attempts (30 minutes)


def get_client_ip():
    """Get the client IP address from the request."""
    # Use remote_addr as a simple approach for now
    return request.remote_addr or 'unknown'


def is_account_locked(username):
    """
    Check if a user account is locked.
    
    Args:
        username (str): The username to check
        
    Returns:
        tuple: (is_locked, remaining_time_seconds)
    """
    ip = get_client_ip()
    key = f"{ip}:{username}"
    
    if key in failed_login_attempts:
        record = failed_login_attempts[key]
        
        # If there's a locked_until timestamp and it's in the future
        if 'locked_until' in record and record['locked_until'] > time.time():
            remaining_time = record['locked_until'] - time.time()
            return True, int(remaining_time)
            
    return False, 0


def record_failed_attempt(username):
    """
    Record a failed login attempt for a username.
    
    Args:
        username (str): The username with the failed attempt
        
    Returns:
        tuple: (is_locked, attempts_remaining, lockout_time)
    """
    ip = get_client_ip()
    key = f"{ip}:{username}"
    current_time = time.time()
    
    # Initialize or get the record
    if key not in failed_login_attempts:
        failed_login_attempts[key] = {
            'attempts': 0,
            'last_attempt': current_time
        }
    
    record = failed_login_attempts[key]
    
    # Reset attempts if the last attempt was outside the window
    if current_time - record['last_attempt'] > ATTEMPT_WINDOW:
        record['attempts'] = 0
    
    # Increment attempts and update timestamp
    record['attempts'] += 1
    record['last_attempt'] = current_time
    
    # Check if account should be locked
    if record['attempts'] >= MAX_LOGIN_ATTEMPTS:
        lock_until = current_time + LOCKOUT_DURATION
        record['locked_until'] = lock_until
        return True, 0, format_lockout_time(lock_until)
    
    return False, MAX_LOGIN_ATTEMPTS - record['attempts'], None


def reset_failed_attempts(username):
    """
    Reset failed login attempts for a username after successful login.
    
    Args:
        username (str): The username to reset attempts for
    """
    ip = get_client_ip()
    key = f"{ip}:{username}"
    
    if key in failed_login_attempts:
        del failed_login_attempts[key]


def format_lockout_time(timestamp):
    """
    Format a lockout timestamp into a human-readable string.
    
    Args:
        timestamp (float): Unix timestamp of lockout expiry
        
    Returns:
        str: Human-readable lockout time (e.g., "15 minutes")
    """
    lockout_time = datetime.fromtimestamp(timestamp)
    now = datetime.now()
    diff = lockout_time - now
    
    minutes = diff.seconds // 60
    
    if minutes < 1:
        return "1 minute"
    return f"{minutes} minutes"


def track_login_activity(user_id, success=True):
    """
    Track login activity for security monitoring.
    
    Args:
        user_id (int): The ID of the user
        success (bool): Whether the login was successful
    """
    # Store login information in session for the user's awareness
    if success:
        session['last_login'] = datetime.now().isoformat()
        
        # Store previous login info if available
        if 'current_login' in session:
            session['previous_login'] = session['current_login']
            
        session['current_login'] = {
            'timestamp': datetime.now().isoformat(),
            'ip': get_client_ip(),
            'user_agent': request.user_agent.string if request.user_agent else 'Unknown'
        }