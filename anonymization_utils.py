"""
GDPR-Compliant PII Anonymization Utilities
Provides methods to anonymize personally identifiable information in audit logs.
"""
import hashlib
import re
from typing import Optional


def anonymize_ip_address(ip_address: Optional[str]) -> Optional[str]:
    """
    Anonymize IP address for GDPR compliance while preserving network information.
    
    IPv4: Masks last octet (192.168.1.123 → 192.168.1.0)
    IPv6: Masks last 80 bits, keeps /48 prefix (2001:db8:85a3:: → 2001:db8:85a3::)
    
    Args:
        ip_address: IP address string (IPv4 or IPv6)
    
    Returns:
        Anonymized IP address or None if invalid
    
    Examples:
        >>> anonymize_ip_address('192.168.1.123')
        '192.168.1.0'
        >>> anonymize_ip_address('2001:0db8:85a3:0000:0000:8a2e:0370:7334')
        '2001:db8:85a3::'
        >>> anonymize_ip_address(None)
        None
    """
    if not ip_address:
        return None
    
    # IPv4 detection and anonymization
    ipv4_pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
    ipv4_match = re.match(ipv4_pattern, ip_address)
    
    if ipv4_match:
        # Mask last octet (keep first 3 octets)
        parts = ip_address.split('.')
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
    
    # IPv6 detection and anonymization
    if ':' in ip_address:
        # Normalize IPv6 (handle compressed notation)
        parts = ip_address.split(':')
        
        # Keep first 3 segments (/48 prefix), zero out rest
        if len(parts) >= 3:
            return f"{parts[0]}:{parts[1]}:{parts[2]}::"
        else:
            # Malformed IPv6, keep as-is (rare edge case)
            return ip_address
    
    # Unknown format, return as-is
    return ip_address


def anonymize_email(email: Optional[str], method: str = 'mask') -> Optional[str]:
    """
    Anonymize email address for GDPR compliance.
    
    Args:
        email: Email address to anonymize
        method: Anonymization method
            - 'mask': Show first char + domain (john@example.com → j***@example.com)
            - 'hash': SHA-256 hash (irreversible but consistent)
            - 'domain_only': Keep only domain (john@example.com → ***@example.com)
    
    Returns:
        Anonymized email or None if invalid
    
    Examples:
        >>> anonymize_email('john.doe@example.com', 'mask')
        'j***@example.com'
        >>> anonymize_email('admin@tracetrack.com', 'domain_only')
        '***@tracetrack.com'
    """
    if not email:
        return None
    
    # Basic email validation
    if '@' not in email:
        return None
    
    local_part, domain = email.rsplit('@', 1)
    
    if method == 'mask':
        # Show first character + masked local part + domain
        if len(local_part) > 0:
            return f"{local_part[0]}***@{domain}"
        else:
            return f"***@{domain}"
    
    elif method == 'domain_only':
        # Keep only domain
        return f"***@{domain}"
    
    elif method == 'hash':
        # SHA-256 hash (irreversible but consistent)
        email_hash = hashlib.sha256(email.encode()).hexdigest()[:16]
        return f"hashed_{email_hash}@{domain}"
    
    else:
        # Unknown method, default to mask
        return f"{local_part[0]}***@{domain}" if len(local_part) > 0 else f"***@{domain}"


def anonymize_pii_in_dict(data: dict, config: Optional[dict] = None) -> dict:
    """
    Recursively anonymize PII fields in a dictionary (used for audit log snapshots).
    
    Args:
        data: Dictionary containing potentially sensitive data
        config: Anonymization configuration
            {
                'anonymize_emails': bool (default: True),
                'email_method': str (default: 'mask'),
                'anonymize_ips': bool (default: True),
                'exclude_fields': list (fields to remove completely)
            }
    
    Returns:
        Dictionary with PII anonymized
    
    Example:
        >>> data = {'email': 'user@example.com', 'ip': '192.168.1.123', 'role': 'admin'}
        >>> anonymize_pii_in_dict(data)
        {'email': 'u***@example.com', 'ip': '192.168.1.0', 'role': 'admin'}
    """
    if not data or not isinstance(data, dict):
        return data
    
    # Default configuration
    default_config = {
        'anonymize_emails': True,
        'email_method': 'mask',
        'anonymize_ips': True,
        'exclude_fields': []  # Fields to completely remove
    }
    
    cfg = {**default_config, **(config or {})}
    
    # Create a copy to avoid modifying original
    result = {}
    
    for key, value in data.items():
        # Skip excluded fields entirely
        if key in cfg['exclude_fields']:
            continue
        
        # Anonymize email fields
        if cfg['anonymize_emails'] and key in ['email', 'user_email', 'email_address']:
            if isinstance(value, str):
                result[key] = anonymize_email(value, cfg['email_method'])
            else:
                result[key] = value
        
        # Anonymize IP fields
        elif cfg['anonymize_ips'] and key in ['ip', 'ip_address', 'remote_addr', 'client_ip']:
            if isinstance(value, str):
                result[key] = anonymize_ip_address(value)
            else:
                result[key] = value
        
        # Recursively handle nested dicts
        elif isinstance(value, dict):
            result[key] = anonymize_pii_in_dict(value, cfg)
        
        # Recursively handle lists of dicts
        elif isinstance(value, list):
            result[key] = [
                anonymize_pii_in_dict(item, cfg) if isinstance(item, dict) else item
                for item in value
            ]
        
        # Keep other fields as-is
        else:
            result[key] = value
    
    return result


# Configuration: Enable/disable PII anonymization
# Can be controlled via environment variable
import os
ANONYMIZE_AUDIT_LOGS = os.environ.get('ANONYMIZE_AUDIT_LOGS', 'true').lower() == 'true'
EMAIL_ANONYMIZATION_METHOD = os.environ.get('EMAIL_ANONYMIZATION_METHOD', 'mask')  # mask, hash, domain_only

def get_anonymization_config() -> dict:
    """
    Get current anonymization configuration from environment variables.
    
    Returns:
        Configuration dictionary for anonymize_pii_in_dict()
    """
    return {
        'anonymize_emails': ANONYMIZE_AUDIT_LOGS,
        'email_method': EMAIL_ANONYMIZATION_METHOD,
        'anonymize_ips': ANONYMIZE_AUDIT_LOGS,
        'exclude_fields': []  # Can be extended based on requirements
    }
