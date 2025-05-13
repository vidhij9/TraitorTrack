"""
Template utilities for improved rendering performance.
Implements fragment caching for frequent template components.
"""

import hashlib
import logging
import time
from functools import wraps
from flask import g, render_template, current_app

logger = logging.getLogger(__name__)

# Global template fragment cache
_template_cache = {}

def cached_template(timeout=60):
    """
    Decorator for caching template fragments.
    
    Args:
        timeout (int): Cache expiration time in seconds
        
    Returns:
        Decorated function that implements fragment caching
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Don't cache in debug mode unless explicitly allowed
            if current_app.debug and not current_app.config.get('CACHE_IN_DEBUG', False):
                return f(*args, **kwargs)
                
            # Create cache key from function and arguments
            key_parts = [f.__name__]
            # Add arguments to key
            for arg in args:
                key_parts.append(str(arg))
            # Add keyword arguments to key (sorted for consistency)
            for k in sorted(kwargs.keys()):
                key_parts.append(f"{k}:{kwargs[k]}")
            
            # Create a hash of the key parts for the cache key
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Check cache
            if cache_key in _template_cache:
                timestamp, html = _template_cache[cache_key]
                if time.time() < timestamp + timeout:
                    logger.debug(f"Template cache hit for {f.__name__}")
                    return html
            
            # Cache miss, render the template
            html = f(*args, **kwargs)
            _template_cache[cache_key] = (time.time(), html)
            logger.debug(f"Template cached: {f.__name__}")
            return html
        return wrapper
    return decorator

def render_cached_template(template_name, timeout=60, **context):
    """
    Render a template with caching.
    
    Args:
        template_name (str): Name of the template to render
        timeout (int): Cache expiration time in seconds
        **context: Template context variables
        
    Returns:
        str: Rendered template HTML
    """
    # Don't cache in debug mode unless explicitly allowed
    if current_app.debug and not current_app.config.get('CACHE_IN_DEBUG', False):
        return render_template(template_name, **context)
        
    # Create cache key from template and context
    key_parts = [template_name]
    
    # Add user-specific info if available
    if hasattr(g, 'user') and g.user:
        key_parts.append(f"user:{g.user.id}")
    
    # Add context variables to key (sorted for consistency)
    for k in sorted(context.keys()):
        # Skip complex objects that can't be easily serialized
        if isinstance(context[k], (str, int, float, bool, type(None))):
            key_parts.append(f"{k}:{context[k]}")
    
    # Create a hash of the key parts for the cache key
    cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
    
    # Check cache
    if cache_key in _template_cache:
        timestamp, html = _template_cache[cache_key]
        if time.time() < timestamp + timeout:
            logger.debug(f"Template cache hit for {template_name}")
            return html
    
    # Cache miss, render the template
    html = render_template(template_name, **context)
    _template_cache[cache_key] = (time.time(), html)
    logger.debug(f"Template cached: {template_name}")
    return html

def clear_template_cache():
    """Clear the template fragment cache."""
    _template_cache.clear()
    logger.debug("Template cache cleared")