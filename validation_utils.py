"""
Utility functions for validating user inputs and QR codes.
Implements input sanitization and validation for security.
"""
import re
import bleach

# Regular expression patterns for validation
PARENT_QR_PATTERN = re.compile(r'^P\d+-\d+$')
CHILD_QR_PATTERN = re.compile(r'^C\d+$')
BILL_ID_PATTERN = re.compile(r'^[A-Z0-9]{6,20}$')


def validate_parent_qr_id(qr_id):
    """
    Validate parent bag QR ID format (e.g., 'P123-10').
    
    Args:
        qr_id (str): The QR ID to validate
        
    Returns:
        tuple: (is_valid, error_message, child_count)
    """
    if not qr_id:
        return False, "QR ID is required", None
    
    qr_id = qr_id.strip()
    
    # Check format using regex
    if not PARENT_QR_PATTERN.match(qr_id):
        return False, "Invalid QR code format. Parent bag QR code should be in format P123-10", None
    
    # Parse child count from QR code
    parts = qr_id.split('-')
    if len(parts) != 2:
        return False, "Invalid QR code format. Expected format: P123-10", None
    
    try:
        child_count = int(parts[1])
        if child_count <= 0:
            return False, "Parent bag must have at least one child", None
        return True, "Valid parent QR ID", child_count
    except ValueError:
        return False, "Invalid child count in QR code", None


def validate_child_qr_id(qr_id):
    """
    Validate child bag QR ID format (e.g., 'C123').
    
    Args:
        qr_id (str): The QR ID to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not qr_id:
        return False, "QR ID is required"
    
    qr_id = qr_id.strip()
    
    # Check format using regex
    if not CHILD_QR_PATTERN.match(qr_id):
        return False, "Invalid QR code format. Child bag QR code should be in format C123"
    
    return True, "Valid child QR ID"


def validate_bill_id(bill_id):
    """
    Validate bill ID format (6-20 alphanumeric characters).
    
    Args:
        bill_id (str): The bill ID to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not bill_id:
        return False, "Bill ID is required"
    
    bill_id = bill_id.strip().upper()
    
    # Check format using regex
    if not BILL_ID_PATTERN.match(bill_id):
        return False, "Invalid bill ID format. Should be 6-20 uppercase alphanumeric characters"
    
    return True, "Valid bill ID"


def sanitize_input(text, max_length=None):
    """
    Sanitize user input by removing HTML tags and limiting length.
    
    Args:
        text (str): The text to sanitize
        max_length (int, optional): Maximum allowed length
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Clean HTML tags
    clean_text = bleach.clean(text, strip=True)
    
    # Limit length if specified
    if max_length and len(clean_text) > max_length:
        clean_text = clean_text[:max_length]
        
    return clean_text


def validate_location_name(location_name):
    """
    Validate location name.
    
    Args:
        location_name (str): The location name to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not location_name:
        return False, "Location name is required"
    
    sanitized_name = sanitize_input(location_name, max_length=100)
    
    if len(sanitized_name) < 2:
        return False, "Location name must be at least 2 characters"
    
    return True, "Valid location name"