"""
Comprehensive Input Validation Utilities for TraceTrack
Provides reusable validators for forms, API endpoints, and user input
"""

import re
import bleach
from typing import Tuple, Optional, Any
from urllib.parse import urlparse

class ValidationError(Exception):
    """Custom validation error exception"""
    pass

class InputValidator:
    """Centralized input validation utilities"""
    
    # QR Code patterns
    QR_PARENT_PATTERN = r'^SB\d{5}$'  # Parent bags: SB followed by 5 digits
    QR_CHILD_PATTERN = r'^[A-Z0-9]{4,20}$'  # Child bags: 4-20 alphanumeric chars
    QR_MAX_LENGTH = 100
    
    # Text constraints
    MAX_TEXT_LENGTH = 1000
    MAX_SEARCH_LENGTH = 200
    MAX_DESCRIPTION_LENGTH = 2000
    
    # Numeric constraints
    MAX_PAGE_SIZE = 200
    MAX_OFFSET = 10000
    DEFAULT_PAGE_SIZE = 50
    
    @staticmethod
    def validate_qr_code(qr_id: str, bag_type: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Validate QR code format with type-specific rules
        
        Args:
            qr_id: QR code string to validate
            bag_type: Optional bag type ('parent' or 'child') for specific validation
            
        Returns:
            Tuple of (is_valid, cleaned_qr, error_message)
        """
        if not qr_id:
            return False, '', "QR code cannot be empty"
        
        # Trim and normalize
        qr_id = qr_id.strip().upper()
        
        # Length validation
        if len(qr_id) > InputValidator.QR_MAX_LENGTH:
            return False, qr_id, f"QR code too long (max {InputValidator.QR_MAX_LENGTH} characters)"
        
        if len(qr_id) < 4:
            return False, qr_id, "QR code too short (min 4 characters)"
        
        # XSS and injection prevention
        if any(char in qr_id for char in ['<', '>', '"', "'", '&', '%', ';', '--', '/*', '*/']):
            return False, qr_id, "QR code contains invalid characters"
        
        # Type-specific validation
        if bag_type == 'parent':
            if not re.match(InputValidator.QR_PARENT_PATTERN, qr_id):
                return False, qr_id, "Parent bag QR must be format SB##### (e.g., SB00001)"
        elif bag_type == 'child':
            if not re.match(InputValidator.QR_CHILD_PATTERN, qr_id):
                return False, qr_id, "Child bag QR must be 4-20 alphanumeric characters"
        
        return True, qr_id, "Valid QR code"
    
    @staticmethod
    def sanitize_search_query(query: str) -> str:
        """
        Sanitize search query to prevent injection attacks
        
        Args:
            query: Raw search query
            
        Returns:
            Sanitized search query
        """
        if not query:
            return ''
        
        # Trim whitespace
        query = query.strip()
        
        # Limit length
        if len(query) > InputValidator.MAX_SEARCH_LENGTH:
            query = query[:InputValidator.MAX_SEARCH_LENGTH]
        
        # Remove SQL injection characters
        dangerous_chars = ['--', '/*', '*/', ';', 'DROP', 'DELETE', 'INSERT', 'UPDATE', 'EXEC', 'UNION']
        query_upper = query.upper()
        for char in dangerous_chars:
            if char in query_upper:
                query = query.replace(char, '').replace(char.lower(), '')
        
        # HTML escape
        query = bleach.clean(query, tags=[], attributes={}, strip=True)
        
        return query
    
    @staticmethod
    def sanitize_html(text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize HTML content to prevent XSS
        
        Args:
            text: Raw HTML text
            max_length: Optional maximum length
            
        Returns:
            Sanitized text
        """
        if not text:
            return ''
        
        # Strip all HTML tags
        text = bleach.clean(text, tags=[], attributes={}, strip=True)
        
        # Limit length if specified
        if max_length and len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()
    
    @staticmethod
    def validate_pagination(page: Any, per_page: Any) -> Tuple[int, int]:
        """
        Validate and sanitize pagination parameters
        
        Args:
            page: Page number (any type)
            per_page: Items per page (any type)
            
        Returns:
            Tuple of (validated_page, validated_per_page)
        """
        # Convert to integers safely
        try:
            page = int(page) if page else 1
        except (ValueError, TypeError):
            page = 1
        
        try:
            per_page = int(per_page) if per_page else InputValidator.DEFAULT_PAGE_SIZE
        except (ValueError, TypeError):
            per_page = InputValidator.DEFAULT_PAGE_SIZE
        
        # Bounds checking
        page = max(1, page)
        per_page = max(1, min(per_page, InputValidator.MAX_PAGE_SIZE))
        
        # Calculate offset and check bounds
        offset = (page - 1) * per_page
        if offset > InputValidator.MAX_OFFSET:
            page = 1
            offset = 0
        
        return page, per_page
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """
        Validate email address format
        
        Args:
            email: Email address to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email cannot be empty"
        
        email = email.strip().lower()
        
        # RFC 5322 simplified regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "Invalid email format"
        
        if len(email) > 254:  # RFC 5321
            return False, "Email too long"
        
        return True, ""
    
    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """
        Validate username format
        
        Args:
            username: Username to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not username:
            return False, "Username cannot be empty"
        
        username = username.strip()
        
        if len(username) < 3:
            return False, "Username too short (min 3 characters)"
        
        if len(username) > 20:
            return False, "Username too long (max 20 characters)"
        
        # Alphanumeric and underscore only
        if not re.match(r'^[A-Za-z0-9_]+$', username):
            return False, "Username can only contain letters, numbers, and underscores"
        
        return True, ""
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """
        Validate URL format
        
        Args:
            url: URL to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "URL cannot be empty"
        
        url = url.strip()
        
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False, "Invalid URL format"
            
            if result.scheme not in ['http', 'https']:
                return False, "Only HTTP/HTTPS URLs allowed"
            
            return True, ""
        except Exception:
            return False, "Invalid URL format"
    
    @staticmethod
    def validate_numeric_range(value: Any, min_val: Optional[float] = None, 
                               max_val: Optional[float] = None, 
                               field_name: str = "Value") -> Tuple[bool, float, str]:
        """
        Validate numeric value is within range
        
        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            field_name: Name of field for error messages
            
        Returns:
            Tuple of (is_valid, validated_value, error_message)
        """
        try:
            num_val = float(value)
        except (ValueError, TypeError):
            return False, 0, f"{field_name} must be a number"
        
        if min_val is not None and num_val < min_val:
            return False, num_val, f"{field_name} must be at least {min_val}"
        
        if max_val is not None and num_val > max_val:
            return False, num_val, f"{field_name} must be at most {max_val}"
        
        return True, num_val, ""
    
    @staticmethod
    def validate_choice(value: str, choices: list, field_name: str = "Value") -> Tuple[bool, str]:
        """
        Validate value is in allowed choices
        
        Args:
            value: Value to validate
            choices: List of allowed values
            field_name: Name of field for error messages
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if value not in choices:
            return False, f"{field_name} must be one of: {', '.join(choices)}"
        
        return True, ""
    
    @staticmethod
    def validate_file_upload(filename: str, allowed_extensions: list, 
                            max_size_mb: int = 10) -> Tuple[bool, str]:
        """
        Validate file upload
        
        Args:
            filename: Name of uploaded file
            allowed_extensions: List of allowed file extensions (e.g., ['.csv', '.xlsx'])
            max_size_mb: Maximum file size in MB
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not filename:
            return False, "No file selected"
        
        # Check extension
        file_ext = filename.lower()[filename.rfind('.'):] if '.' in filename else ''
        if file_ext not in [ext.lower() for ext in allowed_extensions]:
            return False, f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
        
        # Prevent path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return False, "Invalid filename"
        
        return True, ""

# Convenience function for API endpoint validation
def validate_api_input(data: dict, required_fields: dict, optional_fields: dict = None) -> Tuple[bool, dict, str]:
    """
    Validate API endpoint input data
    
    Args:
        data: Input data dictionary
        required_fields: Dict of {field_name: validator_function}
        optional_fields: Optional dict of {field_name: validator_function}
        
    Returns:
        Tuple of (is_valid, validated_data, error_message)
    """
    validated = {}
    
    # Check required fields
    for field, validator in required_fields.items():
        if field not in data:
            return False, {}, f"Missing required field: {field}"
        
        value = data[field]
        if validator:
            is_valid, validated_value, error = validator(value)
            if not is_valid:
                return False, {}, f"Invalid {field}: {error}"
            validated[field] = validated_value
        else:
            validated[field] = value
    
    # Check optional fields
    if optional_fields:
        for field, validator in optional_fields.items():
            if field in data and data[field]:
                value = data[field]
                if validator:
                    is_valid, validated_value, error = validator(value)
                    if not is_valid:
                        return False, {}, f"Invalid {field}: {error}"
                    validated[field] = validated_value
                else:
                    validated[field] = value
    
    return True, validated, ""

def get_validated_request_data(request_obj) -> dict:
    """
    Extract and sanitize data from Flask request object
    Supports form data, JSON, and query parameters
    
    Args:
        request_obj: Flask request object (must be passed explicitly)
        
    Returns:
        Dictionary of sanitized request data
    """
    data = {}
    
    # Get data from appropriate source (use passed request_obj)
    if request_obj.json:
        data = dict(request_obj.json)
    elif request_obj.form:
        data = dict(request_obj.form)
    elif request_obj.args:
        data = dict(request_obj.args)
    
    # Sanitize all string values to prevent XSS
    sanitized_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            # Basic HTML sanitization for all string inputs
            sanitized_data[key] = InputValidator.sanitize_html(value)
        else:
            sanitized_data[key] = value
    
    return sanitized_data
