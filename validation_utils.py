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
    Validate parent bag QR ID - accepts any format.
    
    Args:
        qr_id (str): The QR ID to validate
        
    Returns:
        tuple: (is_valid, error_message, child_count)
    """
    if not qr_id:
        return False, "QR ID is required", None
    
    qr_id = qr_id.strip()
    
    # All formats are now accepted
    # Default to 5 child bags if format doesn't specify
    child_count = 5
    
    # If the old format is used, try to extract child count
    if '-' in qr_id:
        parts = qr_id.split('-')
        if len(parts) == 2:
            try:
                parsed_count = int(parts[1])
                if parsed_count > 0:
                    child_count = parsed_count
            except ValueError:
                # Use default child count
                pass
    
    return True, "Valid parent QR ID", child_count


def validate_child_qr_id(qr_id):
    """
    Validate child bag QR ID - accepts any format.
    
    Args:
        qr_id (str): The QR ID to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not qr_id:
        return False, "QR ID is required"
    
    qr_id = qr_id.strip()
    
    # All formats are now accepted
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