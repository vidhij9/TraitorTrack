"""
Password validation and account lockout utilities for TraitorTrack
"""
import re
from datetime import datetime, timedelta

# Password complexity requirements (simplified for user convenience)
MIN_PASSWORD_LENGTH = 8
REQUIRE_UPPERCASE = False
REQUIRE_LOWERCASE = False
REQUIRE_NUMBER = False
REQUIRE_SPECIAL_CHAR = False

# Account lockout settings
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

def validate_password_complexity(password):
    """
    Validate password meets complexity requirements.
    
    Requirements:
    - Minimum 8 characters (simple and easy to remember)
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
    
    if REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if REQUIRE_NUMBER and not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if REQUIRE_SPECIAL_CHAR and not re.search(r'[!@#$%^&*()_+=\-\[\]{};:\'",.<>?/\\|`~]', password):
        return False, "Password must contain at least one special character (!@#$%^&* etc.)"
    
    return True, "Password is valid"

def is_account_locked(user, db=None):
    """
    Check if a user account is currently locked due to failed login attempts.
    
    Args:
        user: User model instance
        db: Database session (optional, required to reset expired locks)
    
    Returns:
        tuple: (is_locked: bool, unlock_time: datetime or None, minutes_remaining: int or None)
    """
    if not user:
        return False, None, None
    
    # Check if account has a lock expiration time
    if not user.locked_until:
        return False, None, None
    
    now = datetime.utcnow()
    
    # Check if lock has expired
    if user.locked_until <= now:
        # Lock has expired, reset failed attempts and lock status
        if db:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_failed_login = None
            db.session.commit()
        return False, None, None
    
    # Account is still locked
    minutes_remaining = int((user.locked_until - now).total_seconds() / 60)
    return True, user.locked_until, minutes_remaining

def record_failed_login(user, db):
    """
    Record a failed login attempt and lock account if threshold is reached.
    
    Args:
        user: User model instance
        db: Database session
    
    Returns:
        tuple: (should_lock: bool, attempts_remaining: int or None, lock_duration: int or None)
    """
    if not user:
        return False, None, None
    
    # Increment failed attempts
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    user.last_failed_login = datetime.utcnow()
    
    # Check if we should lock the account
    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        # Lock the account
        user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        db.session.commit()
        return True, 0, LOCKOUT_DURATION_MINUTES
    
    # Not locked yet
    attempts_remaining = MAX_FAILED_ATTEMPTS - user.failed_login_attempts
    db.session.commit()
    return False, attempts_remaining, None

def record_successful_login(user, db):
    """
    Record a successful login and reset failed attempt counter.
    
    Args:
        user: User model instance
        db: Database session
    """
    if not user:
        return
    
    # Reset failed login attempts and unlock account
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_failed_login = None
    db.session.commit()

def get_password_requirements_text():
    """
    Get a user-friendly text description of password requirements.
    
    Returns:
        str: Description of password requirements
    """
    requirements = []
    requirements.append(f"at least {MIN_PASSWORD_LENGTH} characters")
    
    if REQUIRE_UPPERCASE:
        requirements.append("one uppercase letter")
    if REQUIRE_LOWERCASE:
        requirements.append("one lowercase letter")
    if REQUIRE_NUMBER:
        requirements.append("one number")
    if REQUIRE_SPECIAL_CHAR:
        requirements.append("one special character (!@#$%^&* etc.)")
    
    return "Password must contain: " + ", ".join(requirements) + "."
