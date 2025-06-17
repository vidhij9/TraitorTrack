"""
TraceTrack - Restructured Main Application
Clean, organized entry point for the application with proper separation of concerns.
"""

import os
import logging
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_required, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime

# Import restructured components
from src.core.app import create_app, db
from src.models import User, Bag, Scan, Bill, BillBag, Link, UserRole, BagType
from src.auth.auth import (
    login_user, is_authenticated, get_current_user, logout_user,
    require_auth, require_admin, cleanup_expired_tokens
)

# Create the application
app = create_app()

# Configure login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return User.query.get(int(user_id))

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login endpoint"""
    if request.method == 'GET':
        # Redirect if already authenticated
        if is_authenticated():
            return redirect(url_for('dashboard'))
        return render_template('login.html')
    
    # Handle POST request
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if not username or not password:
        flash('Please enter both username and password.', 'error')
        return render_template('login.html')
    
    success, message, user_data = login_user(username, password)
    
    if success:
        return redirect(url_for('dashboard'))
    else:
        flash(message, 'error')
        return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout endpoint"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/setup')
def setup():
    """Setup default admin user"""
    from werkzeug.security import generate_password_hash
    
    try:
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@tracetrack.com',
                password_hash=generate_password_hash('admin'),
                role=UserRole.ADMIN.value
            )
            db.session.add(admin)
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': 'Admin user created successfully. Username: admin, Password: admin'
            })
        else:
            admin.password_hash = generate_password_hash('admin')
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

# ============================================================================
# MAIN APPLICATION ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main landing page"""
    if is_authenticated():
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/dashboard')
@require_auth
def dashboard():
    """Main dashboard"""
    user = get_current_user()
    
    # Get summary statistics
    stats = {
        'total_bags': Bag.query.count(),
        'parent_bags': Bag.query.filter_by(type=BagType.PARENT.value).count(),
        'child_bags': Bag.query.filter_by(type=BagType.CHILD.value).count(),
        'total_scans': Scan.query.count(),
        'total_bills': Bill.query.count(),
        'recent_scans': Scan.query.order_by(Scan.timestamp.desc()).limit(10).all()
    }
    
    return render_template('dashboard.html', user=user, stats=stats)

@app.route('/scan')
@require_auth
def scan():
    """QR code scanning page"""
    return render_template('scan.html')

@app.route('/bags')
@require_auth
def bag_management():
    """Bag management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Build query with filters
    query = Bag.query
    
    # Filter by type
    bag_type = request.args.get('type')
    if bag_type and bag_type in ['parent', 'child']:
        query = query.filter_by(type=bag_type)
    
    # Search by QR code
    search = request.args.get('search')
    if search:
        query = query.filter(Bag.qr_id.ilike(f'%{search}%'))
    
    # Pagination
    bags = query.order_by(Bag.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('bag_management.html', bags=bags)

@app.route('/bills')
@require_auth
def bill_management():
    """Bill management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    bills = Bill.query.order_by(Bill.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('bill_management.html', bills=bills)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/stats')
@require_auth
def api_stats():
    """Get system statistics"""
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
@require_auth
def api_scans():
    """Get recent scans"""
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

@app.route('/api/scan', methods=['POST'])
@require_auth
def api_scan():
    """Process a QR code scan"""
    try:
        data = request.get_json()
        qr_code = data.get('qr_code')
        
        if not qr_code:
            return jsonify({'error': 'QR code is required'}), 400
        
        user = get_current_user()
        
        # Find the bag
        bag = Bag.query.filter_by(qr_id=qr_code).first()
        
        if not bag:
            return jsonify({'error': 'Bag not found'}), 404
        
        # Create scan record
        scan = Scan(
            qr_code=qr_code,
            user_id=user.id,
            parent_bag_id=bag.id if bag.type == BagType.PARENT.value else None,
            child_bag_id=bag.id if bag.type == BagType.CHILD.value else None,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        db.session.add(scan)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully scanned {bag.type} bag',
            'bag': {
                'id': bag.id,
                'qr_id': bag.qr_id,
                'type': bag.type,
                'name': bag.name
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ADMIN ROUTES
# ============================================================================

@app.route('/admin/users')
@require_admin
def admin_users():
    """User management for admins"""
    users = User.query.all()
    return render_template('admin/users.html', users=users)

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    return render_template('errors/403.html'), 403

# ============================================================================
# UTILITY ROUTES
# ============================================================================

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

# ============================================================================
# CONTEXT PROCESSORS
# ============================================================================

@app.context_processor
def inject_globals():
    """Inject global variables into templates"""
    return {
        'current_user': get_current_user(),
        'is_authenticated': is_authenticated(),
        'app_name': 'TraceTrack',
        'app_version': '2.0.0'
    }

# ============================================================================
# CLEANUP TASKS
# ============================================================================

@app.before_request
def before_request():
    """Execute before each request"""
    # Cleanup expired tokens periodically
    cleanup_expired_tokens()

# ============================================================================
# APPLICATION FACTORY
# ============================================================================

def create_application():
    """Create and configure the application"""
    return app

# For deployment
application = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
