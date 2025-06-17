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
    Validate parent bag QR ID - accepts any format and extracts details.
    
    Args:
        qr_id (str): The QR ID to validate
        
    Returns:
        tuple: (is_valid, error_message, child_count)
    """
    if not qr_id:
        return False, "QR ID is required", None
    
    qr_id = qr_id.strip()
    
    # All formats are now accepted
    # No default limit on child bags - unlimited linking allowed
    child_count = None
    
    # Extract useful data depending on QR code format
    
    # Case 1: If traditional format P123-10 is used
    if '-' in qr_id and qr_id.upper().startswith('P'):
        parts = qr_id.split('-')
        if len(parts) == 2:
            try:
                parsed_count = int(parts[1])
                if parsed_count > 0:
                    child_count = parsed_count
            except ValueError:
                # Use default child count
                pass
    
    # Case 2: If it's a URL, check for parameters
    elif 'http' in qr_id.lower():
        # Try to extract any number that might indicate child count
        import re
        numbers = re.findall(r'\d+', qr_id)
        if numbers and len(numbers) > 0:
            try:
                # Use the first number as child count if it's positive
                num = int(numbers[0])
                if num > 0:  # Accept any positive number of child bags
                    child_count = num
            except ValueError:
                pass
    
    # Case 3: If it contains numbers elsewhere, try to use them
    else:
        import re
        numbers = re.findall(r'\d+', qr_id)
        if numbers and len(numbers) > 0:
            try:
                # Use the first number as child count if it's positive
                num = int(numbers[0])
                if num > 0:  # Accept any positive number of child bags
                    child_count = num
            except ValueError:
                pass
    
    return True, "Valid parent QR ID", child_count


def validate_child_qr_id(qr_id):
    """
    Validate child bag QR ID - accepts any format and extracts useful identifiers.
    
    Args:
        qr_id (str): The QR ID to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not qr_id:
        return False, "QR ID is required"
    
    qr_id = qr_id.strip()
    
    # Process the QR code to derive useful information
    
    # For URLs, use the last part of the path or a parameter as the identifier
    if 'http' in qr_id.lower():
        # Extract the last part of the URL path or a significant parameter
        try:
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(qr_id)
            path_parts = parsed_url.path.strip('/').split('/')
            
            # If there's a path component, use the last meaningful part
            if path_parts and path_parts[-1]:
                # Keep track of original QR but use a more compact identifier
                return True, "Valid child QR ID"
                
            # If there are query parameters, check for useful ones
            query_params = parse_qs(parsed_url.query)
            if query_params:
                # Often 'id', 'ref', 'product', etc. might be useful identifiers
                for param in ['id', 'ref', 'product', 'item']:
                    if param in query_params:
                        return True, "Valid child QR ID"
        except:
            # If URL parsing fails, just use the original QR code
            pass
    
    # All formats are accepted
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
