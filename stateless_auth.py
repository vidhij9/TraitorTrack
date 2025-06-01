"""
Stateless authentication system that works in any deployment environment
"""
import jwt
import os
import time
from functools import wraps
from flask import request, redirect, url_for, make_response
import logging

# Use environment secret or fallback
JWT_SECRET = os.environ.get("SESSION_SECRET", "fallback-secret-key")
TOKEN_EXPIRY = 86400  # 24 hours

def create_auth_token(user):
    """Create a JWT token for authentication"""
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': int(time.time()) + TOKEN_EXPIRY,
        'iat': int(time.time())
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    logging.info(f"Created auth token for user {user.username}")
    return token

def verify_auth_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logging.info("Token expired")
        return None
    except jwt.InvalidTokenError:
        logging.info("Invalid token")
        return None

def get_user_from_request():
    """Get user data from request (cookies or headers)"""
    # Check cookie first
    token = request.cookies.get('auth_token')
    
    # Check Authorization header as fallback
    if not token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
    
    if token:
        user_data = verify_auth_token(token)
        if user_data:
            return user_data
    
    return None

def is_authenticated():
    """Check if user is authenticated"""
    user_data = get_user_from_request()
    return user_data is not None

def require_auth(f):
    """Authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def login_user_stateless(user):
    """Login user and return response with auth token"""
    token = create_auth_token(user)
    
    # Create response that sets multiple types of cookies for maximum compatibility
    response = make_response(redirect(url_for('index')))
    
    # Set primary auth cookie
    response.set_cookie('auth_token', token,
                       max_age=TOKEN_EXPIRY,
                       httponly=False,
                       secure=False,
                       samesite=None,
                       path='/')
    
    # Set backup cookies with different names
    response.set_cookie('user_session', token,
                       max_age=TOKEN_EXPIRY,
                       httponly=False,
                       secure=False,
                       samesite='Lax',
                       path='/')
    
    response.set_cookie('app_auth', token,
                       max_age=TOKEN_EXPIRY,
                       httponly=False,
                       secure=False,
                       path='/')
    
    logging.info(f"Set auth cookies for user {user.username}")
    return response

def logout_user_stateless():
    """Logout user by clearing cookies"""
    response = make_response(redirect(url_for('login')))
    
    # Clear all auth cookies
    response.set_cookie('auth_token', '', expires=0, path='/')
    response.set_cookie('user_session', '', expires=0, path='/')
    response.set_cookie('app_auth', '', expires=0, path='/')
    
    logging.info("Cleared auth cookies")
    return response

def get_current_user():
    """Get current user data"""
    return get_user_from_request()