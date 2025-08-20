"""
Fix for header issues and performance optimization
"""
from flask import make_response
import functools

def limit_headers(response):
    """Limit the number of headers to prevent issues with concurrent requests"""
    # Remove duplicate headers
    unique_headers = {}
    for key, value in response.headers.items():
        if key not in unique_headers:
            unique_headers[key] = value
    
    # Clear and reset headers
    response.headers.clear()
    for key, value in unique_headers.items():
        response.headers[key] = value
    
    return response

def optimize_response(func):
    """Decorator to optimize response headers"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        
        # If response is a tuple, extract the response object
        if isinstance(response, tuple):
            response_obj = response[0]
        else:
            response_obj = response
        
        # Ensure it's a proper response object
        if not hasattr(response_obj, 'headers'):
            response_obj = make_response(response_obj)
        
        # Apply header limiting
        response_obj = limit_headers(response_obj)
        
        return response_obj
    
    return wrapper

def setup_app_fixes(app):
    """Apply fixes to Flask app"""
    
    @app.after_request
    def fix_headers(response):
        """Fix header issues in responses"""
        # Limit headers to prevent "too many headers" error
        header_count = len(response.headers)
        if header_count > 50:
            # Remove non-essential headers
            essential_headers = [
                'Content-Type', 'Content-Length', 'Cache-Control',
                'X-Content-Type-Options', 'X-Frame-Options',
                'Set-Cookie', 'Location'
            ]
            
            new_headers = {}
            for header in essential_headers:
                if header in response.headers:
                    new_headers[header] = response.headers[header]
            
            response.headers.clear()
            for key, value in new_headers.items():
                response.headers[key] = value
        
        return response