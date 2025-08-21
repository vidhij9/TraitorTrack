"""
Performance Patches for TraceTrack
Apply runtime optimizations to improve response times
"""

import time
from functools import wraps
from flask import g, request
from optimized_cache import cache, cached

def apply_performance_patches(app):
    """Apply performance optimizations to Flask app"""
    
    # 1. Add request timing
    @app.before_request
    def before_request():
        g.start_time = time.time()
        g.db_queries = 0
    
    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            response.headers['X-Response-Time'] = f"{elapsed:.3f}s"
            
            # Log slow requests
            if elapsed > 2.0:
                import logging
                logging.warning(f"Slow request: {elapsed:.2f}s for {request.path}")
        
        return response
    
    # 2. Cache static responses
    @app.after_request
    def add_cache_headers(response):
        # Cache static files
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=3600'
        
        # Cache API responses briefly
        elif request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'private, max-age=60'
        
        return response
    
    # 3. Optimize session handling
    @app.before_request  
    def optimize_session():
        from flask import session, request
        
        # Skip session updates for static files
        if request.path.startswith('/static/'):
            return
        
        # Lazy load user data
        if 'user_id' in session and 'user_cached' not in g:
            user_id = session['user_id']
            
            # Try to get from cache first
            cache_key = f"user:{user_id}"
            user_data = cache.get(cache_key)
            
            if not user_data:
                # Load from database
                from models import User
                user = User.query.get(user_id)
                if user:
                    user_data = {
                        'id': user.id,
                        'username': user.username,
                        'role': user.role,
                        'dispatch_area': user.dispatch_area
                    }
                    # Cache for 5 minutes
                    cache.set(cache_key, user_data, ttl=300)
            
            g.user_cached = user_data
    
    # 4. Connection pool warmup
    def warmup_connections():
        """Warmup database connections"""
        try:
            from app_clean import db
            # Execute simple query to establish connections
            db.session.execute("SELECT 1")
            db.session.commit()
        except:
            pass
    
    # Run warmup
    with app.app_context():
        warmup_connections()
    
    return app

def optimize_route(func):
    """Decorator to optimize route performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Apply query optimizations
        from query_optimizer import QueryOptimizer
        from app_clean import db
        
        try:
            QueryOptimizer.optimize_session(db.session)
        except:
            pass
        
        # Execute route
        result = func(*args, **kwargs)
        
        return result
    
    return wrapper

def cached_route(ttl=60):
    """Cache entire route response"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            
            # Generate cache key from URL and args
            cache_key = f"route:{request.path}:{str(args)}:{str(kwargs)}"
            
            # Try cache first
            cached_response = cache.get(cache_key)
            if cached_response:
                return cached_response
            
            # Execute route
            response = func(*args, **kwargs)
            
            # Cache response
            cache.set(cache_key, response, ttl=ttl)
            
            return response
        
        return wrapper
    return decorator

# Monkey-patch slow functions
def patch_slow_functions():
    """Replace slow functions with optimized versions"""
    
    # Patch werkzeug password hashing to use fast auth
    try:
        from werkzeug import security
        from fast_auth import FastAuth
        
        # Replace slow functions
        original_generate = security.generate_password_hash
        original_check = security.check_password_hash
        
        def fast_generate(password, method='pbkdf2:sha256', salt_length=8):
            """Use fast bcrypt instead of slow pbkdf2"""
            return FastAuth.hash_password(password)
        
        def fast_check(pwhash, password):
            """Use fast verification"""
            # For scrypt hashes, use original werkzeug function
            if pwhash and pwhash.startswith('scrypt:'):
                return original_check(pwhash, password)
            # For bcrypt hashes, use FastAuth
            return FastAuth.verify_password(password, pwhash)
        
        security.generate_password_hash = fast_generate
        security.check_password_hash = fast_check
        
        print("✅ Patched werkzeug password functions for speed")
    except Exception as e:
        print(f"⚠️  Could not patch password functions: {e}")

# Apply patches on import
patch_slow_functions()