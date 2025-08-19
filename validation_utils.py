"""
Validation utilities for the TraceTrack application.
"""

import re
from markupsafe import escape

def validate_parent_qr_id(qr_id):
    """Validate parent QR ID format."""
    if not qr_id:
        return False
    # Basic validation - alphanumeric with optional dashes/underscores
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, str(qr_id)))

def validate_child_qr_id(qr_id):
    """Validate child QR ID format."""
    if not qr_id:
        return False
    # Basic validation - alphanumeric with optional dashes/underscores
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, str(qr_id)))

def validate_bill_id(bill_id):
    """Validate bill ID is a positive integer."""
    try:
        bill_id = int(bill_id)
        return bill_id > 0
    except (ValueError, TypeError):
        return False

def sanitize_input(input_string):
    """Sanitize user input to prevent XSS attacks."""
    if input_string is None:
        return None
    # Use Flask's escape to prevent XSS
    return escape(str(input_string))