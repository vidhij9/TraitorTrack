"""
Utility functions for password validation, security, and handling.
Implements password strength validation and security best practices.
"""
import re
import string
from email_validator import validate_email, EmailNotValidError


def validate_password_strength(password):
    """
    Validate password strength according to security standards.
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter 
    - At least one digit
    - At least one special character
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    # Check for at least one uppercase letter
    if not any(char in string.ascii_uppercase for char in password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for at least one lowercase letter
    if not any(char in string.ascii_lowercase for char in password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for at least one digit
    if not any(char in string.digits for char in password):
        return False, "Password must contain at least one digit"
    
    # Check for at least one special character
    special_chars = string.punctuation
    if not any(char in special_chars for char in password):
        return False, "Password must contain at least one special character"
    
    # Check if password is in common passwords list (would use an actual list in production)
    common_passwords = ["Password123!", "Admin123!", "Welcome1!", "Passw0rd!"]
    if password in common_passwords:
        return False, "This password is too common and easily guessed"
    
    return True, "Password meets strength requirements"


def validate_email_address(email):
    """
    Validate email format and deliverability.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    try:
        # Validate and normalize email
        validation = validate_email(email, check_deliverability=False)
        normalized_email = validation.normalized
        return True, normalized_email
    except EmailNotValidError as e:
        return False, str(e)


def validate_username(username):
    """
    Validate username format.
    
    Requirements:
    - 3-20 characters
    - Only letters, numbers, and underscores
    - Must start with a letter
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"
    
    if len(username) < 3 or len(username) > 20:
        return False, "Username must be between 3 and 20 characters"
    
    # Username must start with a letter and contain only letters, numbers, and underscores
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username):
        return False, "Username must start with a letter and contain only letters, numbers, and underscores"
    
    return True, "Username is valid"