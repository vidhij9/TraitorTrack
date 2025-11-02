"""
Password Reset Utilities for TraitorTrack

Provides secure password reset functionality with time-limited tokens
"""
import secrets
from datetime import datetime, timedelta
from models import User
from app import db
import logging

logger = logging.getLogger(__name__)

# Token expiration time (default: 1 hour)
RESET_TOKEN_EXPIRATION_HOURS = 1

def generate_reset_token():
    """
    Generate a secure random token for password reset.
    
    Returns:
        str: A secure random token (64 characters hex)
    """
    return secrets.token_urlsafe(48)

def create_password_reset_token(user):
    """
    Create a password reset token for the given user.
    
    Args:
        user: User model instance
    
    Returns:
        str: The generated reset token
    """
    if not user:
        return None
    
    # Generate secure token
    token = generate_reset_token()
    
    # Set token and expiration
    user.password_reset_token = token
    user.password_reset_token_expires = datetime.utcnow() + timedelta(hours=RESET_TOKEN_EXPIRATION_HOURS)
    
    try:
        db.session.commit()
        logger.info(f"Password reset token created for user: {user.username}")
        return token
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating password reset token: {e}")
        return None

def validate_reset_token(token):
    """
    Validate a password reset token and return the associated user.
    
    Args:
        token: The reset token to validate
    
    Returns:
        tuple: (user, error_message) 
               - user is the User object if valid, None if invalid
               - error_message describes why token is invalid (if applicable)
    """
    if not token:
        return None, "No reset token provided"
    
    # Find user with this token
    user = User.query.filter_by(password_reset_token=token).first()
    
    if not user:
        return None, "Invalid reset token"
    
    # Check if token has expired
    if not user.password_reset_token_expires:
        return None, "Reset token has no expiration date"
    
    if datetime.utcnow() > user.password_reset_token_expires:
        return None, "Reset token has expired. Please request a new password reset."
    
    return user, None

def clear_reset_token(user):
    """
    Clear the password reset token for a user.
    
    Args:
        user: User model instance
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not user:
        return False
    
    user.password_reset_token = None
    user.password_reset_token_expires = None
    
    try:
        db.session.commit()
        logger.info(f"Password reset token cleared for user: {user.username}")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing password reset token: {e}")
        return False

def send_password_reset_email(user, token, request_host):
    """
    Send password reset email to user.
    
    Args:
        user: User model instance
        token: The reset token
        request_host: The host URL for generating reset link
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        from email_utils import EmailService
        
        # Generate reset link
        reset_link = f"https://{request_host}/reset_password/{token}"
        
        # Send email using EmailService
        success, error = EmailService.send_password_reset_email(
            username=user.username,
            email=user.email,
            reset_link=reset_link
        )
        
        if success:
            logger.info(f"Password reset email sent to: {user.email}")
            return True, None
        else:
            error_msg = error or "Failed to send reset email"
            logger.error(f"Failed to send password reset email to {user.email}: {error_msg}")
            return False, f"Failed to send reset email: {error_msg}"
            
    except Exception as e:
        logger.error(f"Error sending password reset email: {e}")
        return False, f"Error sending reset email: {str(e)}"

def reset_password(user, new_password):
    """
    Reset user's password and clear reset token.
    
    Args:
        user: User model instance
        new_password: The new password (will be hashed)
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    if not user:
        return False, "Invalid user"
    
    if not new_password:
        return False, "Password is required"
    
    # Validate password complexity
    from password_utils import validate_password_complexity
    is_valid, error_message = validate_password_complexity(new_password)
    
    if not is_valid:
        return False, error_message
    
    try:
        # Set new password
        user.set_password(new_password)
        
        # Clear reset token
        user.password_reset_token = None
        user.password_reset_token_expires = None
        
        # Reset failed login attempts (fresh start with new password)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_failed_login = None
        
        db.session.commit()
        logger.info(f"Password successfully reset for user: {user.username}")
        return True, None
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting password: {e}")
        return False, "Failed to reset password. Please try again."
