"""
Production-safe routes for TraceTrack application
"""
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from app_clean import app, db
from models import User, Bag, BagType, Link, Scan, Bill, PromotionRequest
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

# Simple session-based authentication for production
def is_authenticated():
    """Check if user is authenticated"""
    return 'user_id' in session and 'username' in session

def require_auth(f):
    """Decorator to require authentication"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def is_admin():
    """Check if current user is admin"""
    return session.get('user_role') == 'admin'

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if is_authenticated():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('simple_login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            session.permanent = True
            
            flash(f'Welcome, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('simple_login.html')

@app.route('/logout')
def logout():
    """User logout"""
    username = session.get('username', 'User')
    session.clear()
    flash(f'Goodbye, {username}!', 'info')
    return redirect(url_for('login'))

# Main routes
@app.route('/')
def index():
    """Landing page"""
    if not is_authenticated():
        return render_template('landing.html')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@require_auth
def dashboard():
    """Main dashboard"""
    try:
        # Get dashboard statistics
        parent_bags = Bag.query.filter_by(type='parent').count()
        child_bags = Bag.query.filter_by(type='child').count()
        total_scans = Scan.query.count()
        total_bills = Bill.query.count()
        
        # Get recent scans
        recent_scans = Scan.query.order_by(Scan.scanned_at.desc()).limit(10).all()
        
        return render_template('dashboard.html', 
                             parent_bags=parent_bags,
                             child_bags=child_bags,
                             total_scans=total_scans,
                             total_bills=total_bills,
                             recent_scans=recent_scans)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('Error loading dashboard', 'error')
        return render_template('dashboard.html', 
                             parent_bags=0, child_bags=0, 
                             total_scans=0, total_bills=0, 
                             recent_scans=[])

@app.route('/scan')
@require_auth
def scan():
    """QR code scanning page"""
    return render_template('scan.html')

@app.route('/bag-management')
@require_auth
def bag_management():
    """Bag management page"""
    parent_bags = Bag.query.filter_by(type='parent').order_by(Bag.created_at.desc()).limit(50).all()
    child_bags = Bag.query.filter_by(type='child').order_by(Bag.created_at.desc()).limit(50).all()
    
    return render_template('bag_management.html', 
                         parent_bags=parent_bags, 
                         child_bags=child_bags)

@app.route('/bill-management')
@require_auth
def bill_management():
    """Bill management page"""
    bills = Bill.query.order_by(Bill.created_at.desc()).limit(50).all()
    return render_template('bill_management.html', bills=bills)

# Setup route
@app.route('/setup')
def setup():
    """Initial setup"""
    try:
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            # Create admin user
            admin = User()
            admin.username = 'admin'
            admin.email = 'admin@tracetrack.com'
            admin.password_hash = generate_password_hash('admin')
            admin.role = 'admin'
            admin.verified = True
            
            db.session.add(admin)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Admin user created successfully! Login with admin/admin'
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Admin user already exists'
            })
    except Exception as e:
        logger.error(f"Setup error: {e}")
        return jsonify({
            'success': False,
            'message': f'Setup failed: {str(e)}'
        })

# Health check
@app.route('/production-health')
def production_health_check():
    """Production health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'environment': 'production'
    })

logger.info("Production routes loaded successfully")