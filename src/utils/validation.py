"""
Data validation utilities for form inputs and API requests.
"""

import re
from flask import request, jsonify

def validate_qr_code(qr_code):
    """Validate QR code format"""
    if not qr_code or not isinstance(qr_code, str):
        return False, "QR code is required"
    
    qr_code = qr_code.strip()
    
    if len(qr_code) < 3:
        return False, "QR code too short"
    
    if len(qr_code) > 255:
        return False, "QR code too long"
    
    # Allow alphanumeric characters, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', qr_code):
        return False, "QR code contains invalid characters"
    
    return True, "Valid"

def validate_username(username):
    """Validate username format"""
    if not username or not isinstance(username, str):
        return False, "Username is required"
    
    username = username.strip()
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(username) > 64:
        return False, "Username too long"
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, "Valid"

def validate_email(email):
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False, "Email is required"
    
    email = email.strip().lower()
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Invalid email format"
    
    return True, "Valid"

def validate_password(password):
    """Validate password strength"""
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if len(password) > 128:
        return False, "Password too long"
    
    # Check for at least one letter and one number
    if not re.search(r'[a-zA-Z]', password):
        return False, "Password must contain at least one letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    return True, "Valid"

def validate_required_fields(data, required_fields):
    """Validate that all required fields are present"""
    missing_fields = []
    
    for field in required_fields:
        if field not in data or not data[field] or str(data[field]).strip() == '':
            missing_fields.append(field)
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, "Valid"

def sanitize_input(text, max_length=None):
    """Sanitize text input to prevent XSS"""
    if not text:
        return ""
    
    # Basic HTML tag removal
    text = re.sub(r'<[^>]+>', '', str(text))
    
    # Remove potentially dangerous characters
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    text = text.replace('"', '&quot;').replace("'", '&#x27;')
    
    # Trim whitespace
    text = text.strip()
    
    # Enforce maximum length
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text

def validate_json_request():
    """Decorator to validate JSON request format"""
    def decorator(f):
        from functools import wraps
        
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Request must be JSON'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid JSON data'}), 400
            
            return f(*args, **kwargs)
        return wrapper
    return decorator
