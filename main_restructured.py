"""
TraceTrack - Clean and Organized Main Application
This version maintains full compatibility while providing better code organization.
"""

import os
import logging
import time
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import DeclarativeBase

# =============================================================================
# DATABASE SETUP
# =============================================================================

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# =============================================================================
# APPLICATION FACTORY
# =============================================================================

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-key-change-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 50,
        "max_overflow": 60,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_timeout": 20,
        "pool_use_lifo": True,
        "connect_args": {
            "keepalives": 1,
            "keepalives_idle": 60,
            "keepalives_interval": 10,
            "keepalives_count": 3,
            "options": "-c statement_timeout=90000"
        }
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Security headers
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize extensions
    db.init_app(app)
    
    # Setup logging
    if not app.debug:
        logging.basicConfig(level=logging.INFO)
        app.logger.setLevel(logging.INFO)
        app.logger.info('TraceTrack application startup')
    
    return app

# =============================================================================
# MODELS (Organized and Clean)
# =============================================================================

import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"

class BagType(enum.Enum):
    PARENT = "parent"
    CHILD = "child"

class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default=UserRole.EMPLOYEE.value)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    scans = db.relationship('Scan', backref='scanned_by', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        if not self.password_hash:
            return False
        try:
            return check_password_hash(self.password_hash, password)
        except Exception as e:
            logging.error(f"Password check error: {str(e)}")
            return False
    
    def is_admin(self):
        return self.role == UserRole.ADMIN.value
    
    def __repr__(self):
        return f"<User {self.username}>"

class Bag(db.Model):
    """Bag model for tracking parent and child bags"""
    __tablename__ = 'bag'
    
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(255), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    child_count = db.Column(db.Integer, nullable=True)
    parent_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_bag_qr_id', 'qr_id'),
        db.Index('idx_bag_type', 'type'),
    )
    
    def __repr__(self):
        return f"<Bag {self.qr_id} ({self.type})>"

class Scan(db.Model):
    """Scan model for tracking QR code scans"""
    __tablename__ = 'scan'
    
    id = db.Column(db.Integer, primary_key=True)
    qr_code = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=True)
    child_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_scan_qr_code', 'qr_code'),
        db.Index('idx_scan_timestamp', 'timestamp'),
        db.Index('idx_scan_user_id', 'user_id'),
    )
    
    def __repr__(self):
        return f"<Scan {self.qr_code} at {self.timestamp}>"

class Bill(db.Model):
    """Bill model for managing invoices"""
    __tablename__ = 'bill'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_contact = db.Column(db.String(100), nullable=True)
    total_amount = db.Column(db.Numeric(10, 2), nullable=True)
    status = db.Column(db.String(20), default='draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    scans = db.relationship('Scan', backref='bill', lazy='dynamic')
    creator = db.relationship('User', backref='created_bills')
    
    def __repr__(self):
        return f"<Bill {self.bill_number}>"

class BillBag(db.Model):
    """Association between bills and bags"""
    __tablename__ = 'bill_bag'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('bill_id', 'bag_id', name='unique_bill_bag'),
    )

class Link(db.Model):
    """Link model for parent-child bag relationships"""
    __tablename__ = 'link'
    
    id = db.Column(db.Integer, primary_key=True)
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=False)
    child_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('parent_bag_id', 'child_bag_id', name='unique_parent_child_link'),
    )
    
    creator = db.relationship('User', backref='created_links')

# =============================================================================
# AUTHENTICATION SYSTEM (Simplified and Robust)
# =============================================================================

# Simple in-memory session storage
auth_sessions = {}
failed_attempts = {}

def login_user_simple(username, password):
    """Authenticate user and create session"""
    try:
        # Check for account lockout
        if is_account_locked(username):
            return False, "Account temporarily locked due to failed attempts"
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            record_failed_attempt(username)
            return False, "Invalid username or password"
        
        # Reset failed attempts on success
        reset_failed_attempts(username)
        
        # Create session
        session_id = f"{user.id}_{int(time.time())}"
        auth_sessions[session_id] = {
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'created_at': time.time()
        }
        
        # Set session data
        session.permanent = True
        session['logged_in'] = True
        session['authenticated'] = True
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session['session_id'] = session_id
        
        logging.info(f"User {username} logged in successfully")
        return True, "Login successful"
        
    except Exception as e:
        logging.error(f"Login error: {str(e)}")
        return False, "Login failed due to system error"

def is_authenticated():
    """Check if user is authenticated"""
    if not session.get('logged_in') or not session.get('authenticated'):
        return False
    
    session_id = session.get('session_id')
    if session_id and session_id in auth_sessions:
        # Check session age (24 hours max)
        session_data = auth_sessions[session_id]
        if time.time() - session_data['created_at'] < 86400:
            return True
        else:
            # Clean up expired session
            del auth_sessions[session_id]
    
    return False

def get_current_user():
    """Get current authenticated user"""
    if not is_authenticated():
        return None
    
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    
    return None

def clear_auth_session():
    """Clear authentication session"""
    session_id = session.get('session_id')
    if session_id and session_id in auth_sessions:
        del auth_sessions[session_id]
    
    session.clear()

def is_account_locked(username):
    """Check if account is locked"""
    if username not in failed_attempts:
        return False
    
    attempt_data = failed_attempts[username]
    lockout_until = attempt_data.get('lockout_until', 0)
    
    return time.time() < lockout_until

def record_failed_attempt(username):
    """Record failed login attempt"""
    current_time = time.time()
    
    if username not in failed_attempts:
        failed_attempts[username] = {
            'count': 0,
            'first_attempt': current_time,
            'lockout_until': 0
        }
    
    attempt_data = failed_attempts[username]
    attempt_data['count'] += 1
    
    # Lock after 5 failed attempts for 15 minutes
    if attempt_data['count'] >= 5:
        attempt_data['lockout_until'] = current_time + 900  # 15 minutes

def reset_failed_attempts(username):
    """Reset failed attempts"""
    if username in failed_attempts:
        del failed_attempts[username]

# =============================================================================
# CREATE APPLICATION INSTANCE
# =============================================================================

app = create_app()

# =============================================================================
# ROUTES (Organized by Function)
# =============================================================================

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'GET':
        if is_authenticated():
            return redirect(url_for('dashboard'))
        return render_template('login.html')
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if not username or not password:
        flash('Please enter both username and password.', 'error')
        return render_template('login.html')
    
    success, message = login_user_simple(username, password)
    
    if success:
        return redirect(url_for('dashboard'))
    else:
        flash(message, 'error')
        return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    clear_auth_session()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/setup')
def setup():
    """Setup default admin user"""
    try:
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@tracetrack.com',
                role=UserRole.ADMIN.value
            )
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': 'Admin user created. Username: admin, Password: admin'
            })
        else:
            admin.set_password('admin')
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': 'Admin password updated. Username: admin, Password: admin'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Setup failed: {str(e)}'
        })

# Main Application Routes
@app.route('/')
def index():
    """Main landing page"""
    if is_authenticated():
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/dashboard')
def dashboard():
    """Main dashboard"""
    if not is_authenticated():
        return redirect(url_for('login'))
    
    user = get_current_user()
    
    # Get statistics
    stats = {
        'total_bags': Bag.query.count(),
        'parent_bags': Bag.query.filter_by(type=BagType.PARENT.value).count(),
        'child_bags': Bag.query.filter_by(type=BagType.CHILD.value).count(),
        'total_scans': Scan.query.count(),
        'total_bills': Bill.query.count(),
        'recent_scans': Scan.query.order_by(Scan.timestamp.desc()).limit(10).all()
    }
    
    return render_template('dashboard.html', user=user, stats=stats)

# API Routes
@app.route('/api/stats')
def api_stats():
    """Get system statistics"""
    if not is_authenticated():
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        stats = {
            'total_bags': Bag.query.count(),
            'parent_bags': Bag.query.filter_by(type=BagType.PARENT.value).count(),
            'child_bags': Bag.query.filter_by(type=BagType.CHILD.value).count(),
            'total_scans': Scan.query.count(),
            'total_bills': Bill.query.count(),
            'users': User.query.count()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scans')
def api_scans():
    """Get recent scans"""
    if not is_authenticated():
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        limit = request.args.get('limit', 10, type=int)
        scans = Scan.query.order_by(Scan.timestamp.desc()).limit(limit).all()
        
        scan_data = []
        for scan in scans:
            scan_data.append({
                'id': scan.id,
                'qr_code': scan.qr_code,
                'timestamp': scan.timestamp.isoformat(),
                'user': scan.scanned_by.username if scan.scanned_by else 'Unknown'
            })
        
        return jsonify(scan_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error Handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500

@app.errorhandler(403)
def forbidden(error):
    return render_template('error.html', 
                         error_code=403, 
                         error_message="Access forbidden"), 403

# Health Check
@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# Context Processors
@app.context_processor
def inject_globals():
    """Inject global template variables"""
    return {
        'current_user': get_current_user(),
        'is_authenticated': is_authenticated(),
        'app_name': 'TraceTrack',
        'app_version': '2.0.0'
    }

# Request Handlers
@app.before_request
def before_request():
    """Log requests"""
    if app.debug:
        app.logger.info(f'Request: {request.method} {request.url} - IP: {request.remote_addr}')

@app.after_request
def after_request(response):
    """Add security headers"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    if request.endpoint and 'login' not in request.endpoint:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response

# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

with app.app_context():
    db.create_all()
    
    # Create default admin if none exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@tracetrack.com',
            role=UserRole.ADMIN.value
        )
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        logging.info('Default admin user created')

# =============================================================================
# APPLICATION EXPORT
# =============================================================================

# For deployment
application = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)