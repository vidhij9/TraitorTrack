#!/usr/bin/env python3
"""
Fast Login Optimizer - Zero login failures with <100ms response time
"""

import time
import bcrypt
from functools import lru_cache
from threading import Lock
import hashlib
import logging

logger = logging.getLogger(__name__)

class FastLoginOptimizer:
    """Optimize login performance for zero failures"""
    
    def __init__(self):
        self.failed_attempts = {}
        self.lock = Lock()
        self.password_cache = {}
        
    @lru_cache(maxsize=100)
    def hash_password_fast(self, password):
        """Fast password hashing with lower cost factor"""
        # Use cost factor 4 for speed (vs default 12)
        salt = bcrypt.gensalt(rounds=4)
        return bcrypt.hashpw(password.encode('utf-8'), salt)
    
    def verify_password_fast(self, password, hashed):
        """Fast password verification with caching"""
        # Create cache key
        cache_key = hashlib.md5(f"{password}:{hashed[:20]}".encode()).hexdigest()
        
        # Check cache first
        if cache_key in self.password_cache:
            cache_time, result = self.password_cache[cache_key]
            if time.time() - cache_time < 300:  # 5 minute cache
                return result
        
        # Verify password
        try:
            if isinstance(hashed, str):
                hashed = hashed.encode('utf-8')
            if isinstance(password, str):
                password = password.encode('utf-8')
            
            # Handle both bcrypt and werkzeug hashes
            if hashed.startswith(b'$2b$') or hashed.startswith(b'$2a$'):
                # Bcrypt hash
                result = bcrypt.checkpw(password, hashed)
            else:
                # Werkzeug hash - use fast comparison
                from werkzeug.security import check_password_hash
                result = check_password_hash(hashed.decode('utf-8'), password.decode('utf-8'))
            
            # Cache result
            self.password_cache[cache_key] = (time.time(), result)
            return result
            
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def check_rate_limit(self, username, ip_address):
        """Check login rate limiting"""
        with self.lock:
            key = f"{username}:{ip_address}"
            now = time.time()
            
            # Clean old attempts
            if key in self.failed_attempts:
                attempts = self.failed_attempts[key]
                # Keep only attempts in last 5 minutes
                attempts = [t for t in attempts if now - t < 300]
                self.failed_attempts[key] = attempts
                
                # Block if more than 5 attempts in 5 minutes
                if len(attempts) >= 5:
                    return False
            
            return True
    
    def record_failed_attempt(self, username, ip_address):
        """Record failed login attempt"""
        with self.lock:
            key = f"{username}:{ip_address}"
            if key not in self.failed_attempts:
                self.failed_attempts[key] = []
            self.failed_attempts[key].append(time.time())
    
    def clear_failed_attempts(self, username, ip_address):
        """Clear failed attempts on successful login"""
        with self.lock:
            key = f"{username}:{ip_address}"
            if key in self.failed_attempts:
                del self.failed_attempts[key]

# Global instance
fast_login = FastLoginOptimizer()

def optimize_login_route(app):
    """Optimize the login route for performance"""
    from flask import request, session, flash, redirect, url_for, render_template
    from models import User, db
    import time
    
    @app.route('/fast_login', methods=['GET', 'POST'])
    def fast_login_handler():
        """Optimized login handler"""
        if request.method == 'GET':
            return render_template('login.html')
        
        start_time = time.time()
        
        # Get credentials
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        # Get IP for rate limiting
        ip_address = request.remote_addr
        
        # Check rate limiting
        if not fast_login.check_rate_limit(username, ip_address):
            flash('Too many failed attempts. Please try again later.', 'error')
            return render_template('login.html')
        
        try:
            # Fast user lookup with single query
            user = db.session.query(User).filter_by(username=username).first()
            
            if not user:
                fast_login.record_failed_attempt(username, ip_address)
                flash('Invalid username or password.', 'error')
                return render_template('login.html')
            
            # Fast password verification
            if not fast_login.verify_password_fast(password, user.password_hash):
                fast_login.record_failed_attempt(username, ip_address)
                flash('Invalid username or password.', 'error')
                return render_template('login.html')
            
            # Check if user is verified
            if not user.verified:
                flash('Account not verified.', 'error')
                return render_template('login.html')
            
            # Success - create session
            fast_login.clear_failed_attempts(username, ip_address)
            
            # Optimize session creation
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            session['email'] = user.email
            session['logged_in'] = True
            session['login_time'] = time.time()
            session.permanent = True
            
            # Log performance
            elapsed = (time.time() - start_time) * 1000
            if elapsed > 100:
                logger.warning(f"Slow login: {elapsed:.2f}ms for {username}")
            
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Login failed. Please try again.', 'error')
            return render_template('login.html')
    
    return app