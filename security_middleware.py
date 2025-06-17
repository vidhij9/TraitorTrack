"""
Security middleware for the traitor track application.
Provides protection against common attacks and security monitoring.
"""
import re
import logging
from functools import wraps
from flask import request, abort, current_app, g, session

logger = logging.getLogger(__name__)

# Regular expressions for detecting potential attacks
SQL_INJECTION_PATTERN = re.compile(
    r"(?i)(select|update|insert|delete|drop|alter|create|truncate|union|exec|declare)\s+"
)
XSS_PATTERN = re.compile(r"(?i)<script|\b(on\w+)=")
PATH_TRAVERSAL_PATTERN = re.compile(r"\.\.[\\/]")


def check_request_security():
    """
    Check incoming requests for suspicious patterns.
    This function is designed to be called as a before_request handler.
    """
    # Skip security checks for static files
    if request.path.startswith('/static/'):
        return
    
    # Flag to determine if the request is suspicious
    is_suspicious = False
    reason = None
    
    # Request parameters (combined from all sources)
    params = {}
    params.update(request.args.to_dict())
    
    # Only check form data for non-GET requests
    if request.method != 'GET' and request.form:
        params.update(request.form.to_dict())
    
    # Check all parameters
    for param_name, param_value in params.items():
        if not isinstance(param_value, str):
            continue
            
        # SQL Injection check
        if SQL_INJECTION_PATTERN.search(param_value):
            is_suspicious = True
            reason = f"Potential SQL injection in parameter: {param_name}"
            break
            
        # XSS check
        if XSS_PATTERN.search(param_value):
            is_suspicious = True
            reason = f"Potential XSS in parameter: {param_name}"
            break
            
        # Path traversal check
        if PATH_TRAVERSAL_PATTERN.search(param_value):
            is_suspicious = True
            reason = f"Potential path traversal in parameter: {param_name}"
            break
    
    # URL path check for path traversal
    if PATH_TRAVERSAL_PATTERN.search(request.path):
        is_suspicious = True
        reason = "Potential path traversal in URL path"
    
    # Log and possibly block suspicious requests
    if is_suspicious:
        client_ip = request.remote_addr or 'unknown'
        user_id = session.get('user_id', 'anonymous')
        
        logger.warning(
            f"Security alert: {reason}. IP: {client_ip}, User: {user_id}, "
            f"Path: {request.path}, Method: {request.method}"
        )
        
        # Store the event in the app context for possible later use
        if not hasattr(g, 'security_events'):
            g.security_events = []
        g.security_events.append({
            'reason': reason,
            'ip': client_ip,
            'user': user_id,
            'path': request.path,
            'method': request.method,
            'params': list(params.keys())
        })
        
        # Block the request if in strict mode
        if current_app.config.get('SECURITY_STRICT_MODE', False):
            abort(403)  # Forbidden


def setup_security_middleware(app):
    """
    Set up security middleware on a Flask application.
    
    Args:
        app: The Flask application
    """
    # Register before_request handler
    app.before_request(check_request_security)
    
    # Set default security configuration
    app.config.setdefault('SECURITY_STRICT_MODE', False)
