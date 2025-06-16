"""
TraceTrack - Complete Production Application
Consolidates all tested features into a single, deployment-ready application.
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
import qrcode
from io import BytesIO
import base64
import json
from sqlalchemy import text, func, desc, and_, or_

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define database model base class
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

# Create Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "production-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Production-ready session configuration
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Will be True in HTTPS production
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_DOMAIN=None,
    SESSION_COOKIE_PATH='/',
    SESSION_COOKIE_NAME='tracetrack_session',
    PERMANENT_SESSION_LIFETIME=86400,  # 24 hours
    SESSION_REFRESH_EACH_REQUEST=True,
    WTF_CSRF_TIME_LIMIT=3600  # 1 hour CSRF token validity
)

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_size": 20,
    "max_overflow": 30
}

# Initialize extensions with app
db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)
limiter.init_app(app)

# Login manager configuration
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

class ParentBag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(100), unique=True, nullable=False)
    bag_type = db.Column(db.String(50), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='active')
    
    # Relationships
    children = db.relationship('ChildBag', backref='parent', lazy='dynamic', cascade='all, delete-orphan')
    scans = db.relationship('Scan', backref='parent_bag', lazy='dynamic')
    creator = db.relationship('User', backref='created_parent_bags')

class ChildBag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(100), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('parent_bag.id'), nullable=False)
    bag_type = db.Column(db.String(50), nullable=False)
    weight = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='active')
    
    # Relationships
    scans = db.relationship('Scan', backref='child_bag', lazy='dynamic')
    creator = db.relationship('User', backref='created_child_bags')

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='active')
    
    # Relationships
    bags = db.relationship('BillBag', backref='bill', lazy='dynamic', cascade='all, delete-orphan')
    creator = db.relationship('User', backref='created_bills')

class BillBag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('parent_bag.id'), nullable=False)
    child_bag_id = db.Column(db.Integer, db.ForeignKey('child_bag.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    parent_bag = db.relationship('ParentBag', backref='bill_associations')
    child_bag = db.relationship('ChildBag', backref='bill_associations')

class Scan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(100), nullable=False)
    scan_type = db.Column(db.String(20), nullable=False)  # 'parent' or 'child'
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('parent_bag.id'), nullable=True)
    child_bag_id = db.Column(db.Integer, db.ForeignKey('child_bag.id'), nullable=True)
    scanned_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)
    location = db.Column(db.String(200))
    notes = db.Column(db.Text)
    
    # Relationships
    scanner = db.relationship('User', backref='scans')

class PromotionRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requested_role = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='promotion_requests')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_promotions')

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Request handlers
@app.before_request
def before_request():
    """Execute before each request"""
    # Skip authentication for static files and public endpoints
    if request.endpoint in ['static', 'login', 'register', 'health_check', 'production_health']:
        return
    
    # Update last activity for authenticated users
    if current_user.is_authenticated:
        current_user.last_login = datetime.utcnow()
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            db.session.rollback()

@app.after_request
def after_request(response):
    """Execute after each request"""
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Add cache control for authenticated pages
    if current_user.is_authenticated:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response

# Template context processors
@app.context_processor
def inject_globals():
    """Inject global variables into templates"""
    return {
        'current_user': current_user,
        'datetime': datetime,
        'app_name': 'TraceTrack',
        'app_version': '1.0.0'
    }

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    username = current_user.username
    logout_user()
    flash(f'Goodbye, {username}!', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not all([username, email, password, confirm_password]):
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create user
        user = User()
        user.username = username
        user.email = email
        user.set_password(password)
        user.verified = True  # Auto-verify for now
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Main Application Routes
@app.route('/')
def index():
    """Landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    try:
        # Get dashboard statistics
        stats = {
            'total_parent_bags': ParentBag.query.filter_by(status='active').count(),
            'total_child_bags': ChildBag.query.filter_by(status='active').count(),
            'total_bills': Bill.query.filter_by(status='active').count(),
            'total_scans': Scan.query.count(),
            'recent_scans': Scan.query.order_by(desc(Scan.scanned_at)).limit(10).all()
        }
        
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('Error loading dashboard', 'error')
        return render_template('dashboard.html', stats={})

@app.route('/scan')
@login_required
def scan():
    """QR code scanning page"""
    return render_template('scan.html')

@app.route('/bag-management')
@login_required
def bag_management():
    """Bag management page"""
    parent_bags = ParentBag.query.filter_by(status='active').order_by(desc(ParentBag.created_at)).limit(50).all()
    child_bags = ChildBag.query.filter_by(status='active').order_by(desc(ChildBag.created_at)).limit(50).all()
    
    return render_template('bag_management.html', 
                         parent_bags=parent_bags, 
                         child_bags=child_bags)

@app.route('/bill-management')
@login_required
def bill_management():
    """Bill management page"""
    bills = Bill.query.filter_by(status='active').order_by(desc(Bill.created_at)).limit(50).all()
    return render_template('bill_management.html', bills=bills)

# API Routes
@app.route('/api/scan', methods=['POST'])
@login_required
@csrf.exempt
def api_scan():
    """Process QR code scan"""
    try:
        data = request.get_json()
        qr_id = data.get('qr_id', '').strip()
        
        if not qr_id:
            return jsonify({'success': False, 'message': 'QR ID is required'})
        
        # Check if it's a parent bag
        parent_bag = ParentBag.query.filter_by(qr_id=qr_id, status='active').first()
        if parent_bag:
            # Record scan
            scan = Scan()
            scan.qr_id = qr_id
            scan.scan_type = 'parent'
            scan.parent_bag_id = parent_bag.id
            scan.scanned_by = current_user.id
            scan.location = data.get('location', '')
            scan.notes = data.get('notes', '')
            
            db.session.add(scan)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'type': 'parent',
                'bag': {
                    'qr_id': parent_bag.qr_id,
                    'bag_type': parent_bag.bag_type,
                    'origin': parent_bag.origin,
                    'destination': parent_bag.destination,
                    'created_at': parent_bag.created_at.isoformat(),
                    'children_count': parent_bag.children.count()
                }
            })
        
        # Check if it's a child bag
        child_bag = ChildBag.query.filter_by(qr_id=qr_id, status='active').first()
        if child_bag:
            # Record scan
            scan = Scan()
            scan.qr_id = qr_id
            scan.scan_type = 'child'
            scan.child_bag_id = child_bag.id
            scan.parent_bag_id = child_bag.parent_id
            scan.scanned_by = current_user.id
            scan.location = data.get('location', '')
            scan.notes = data.get('notes', '')
            
            db.session.add(scan)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'type': 'child',
                'bag': {
                    'qr_id': child_bag.qr_id,
                    'bag_type': child_bag.bag_type,
                    'weight': child_bag.weight,
                    'created_at': child_bag.created_at.isoformat(),
                    'parent': {
                        'qr_id': child_bag.parent.qr_id,
                        'bag_type': child_bag.parent.bag_type,
                        'origin': child_bag.parent.origin,
                        'destination': child_bag.parent.destination
                    }
                }
            })
        
        return jsonify({'success': False, 'message': 'QR code not found'})
        
    except Exception as e:
        logger.error(f"Scan error: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Scan processing error'})

@app.route('/api/stats')
@login_required
def api_stats():
    """Get system statistics"""
    try:
        stats = {
            'parent_bags': ParentBag.query.filter_by(status='active').count(),
            'child_bags': ChildBag.query.filter_by(status='active').count(),
            'bills': Bill.query.filter_by(status='active').count(),
            'scans': Scan.query.count(),
            'users': User.query.filter_by(is_active=True).count()
        }
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'error': 'Unable to fetch statistics'})

@app.route('/api/scans/recent')
@login_required
def api_recent_scans():
    """Get recent scans"""
    try:
        limit = request.args.get('limit', 20, type=int)
        scans = Scan.query.order_by(desc(Scan.scanned_at)).limit(limit).all()
        
        result = []
        for scan in scans:
            scan_data = {
                'id': scan.id,
                'qr_id': scan.qr_id,
                'type': scan.scan_type,
                'scanned_at': scan.scanned_at.isoformat(),
                'scanner': scan.scanner.username,
                'location': scan.location,
                'notes': scan.notes
            }
            
            if scan.parent_bag:
                scan_data['parent_bag'] = {
                    'qr_id': scan.parent_bag.qr_id,
                    'bag_type': scan.parent_bag.bag_type,
                    'origin': scan.parent_bag.origin,
                    'destination': scan.parent_bag.destination
                }
            
            if scan.child_bag:
                scan_data['child_bag'] = {
                    'qr_id': scan.child_bag.qr_id,
                    'bag_type': scan.child_bag.bag_type,
                    'weight': scan.child_bag.weight
                }
            
            result.append(scan_data)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Recent scans error: {e}")
        return jsonify({'error': 'Unable to fetch recent scans'})

# Admin Routes
@app.route('/admin/users')
@login_required
def admin_users():
    """User management for admins"""
    if not current_user.is_admin():
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users)

# Health Check Routes
@app.route('/health')
def health_check():
    """Basic health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@app.route('/production-health')
def production_health():
    """Production health check with database connectivity"""
    try:
        # Test database connection
        db.session.execute(text("SELECT 1")).scalar()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'environment': 'production'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Setup endpoint for initial deployment
@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """Initial setup endpoint"""
    try:
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            # Create admin user
            admin = User()
            admin.username = 'admin'
            admin.email = 'admin@tracetrack.com'
            admin.set_password('admin')
            admin.role = 'admin'
            admin.verified = True
            
            db.session.add(admin)
            db.session.commit()
            
            message = "Admin user created successfully! Login with admin/admin"
        else:
            message = "Admin user already exists"
        
        return jsonify({
            'success': True,
            'message': message,
            'redirect': '/login'
        })
        
    except Exception as e:
        logger.error(f"Setup error: {e}")
        return jsonify({
            'success': False,
            'message': f'Setup failed: {str(e)}'
        })

# Error Handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500

@app.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    return render_template('error.html', 
                         error_code=403, 
                         error_message="Access forbidden"), 403

# Initialize database
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

# Export app for gunicorn
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)