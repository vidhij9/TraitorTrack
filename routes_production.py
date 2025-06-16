"""
Production-safe routes for TraceTrack application
"""
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import text
from app_clean import app, db
from models import User
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

# Simple session-based authentication for production
def is_authenticated():
    """Check if user is authenticated"""
    return session.get('user_id') is not None and session.get('username') is not None

def require_auth(f):
    """Decorator to require authentication"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            session['next_url'] = request.url
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
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        logger.info(f"Login attempt for username: {username}")
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('simple_login.html', error='Please enter both username and password')
        
        try:
            user = User.query.filter_by(username=username).first()
            logger.info(f"User found: {user is not None}")
            
            if user and user.password_hash:
                logger.info(f"Checking password for user: {username}")
                password_valid = check_password_hash(user.password_hash, password)
                logger.info(f"Password valid: {password_valid}")
                
                if password_valid:
                    # Clear any existing session data
                    session.clear()
                    
                    # Set new session data
                    session['user_id'] = user.id
                    session['username'] = user.username
                    session['user_role'] = user.role
                    session.permanent = True
                    
                    logger.info(f"Login successful for user: {username}")
                    logger.info(f"Session data set: user_id={session.get('user_id')}, username={session.get('username')}")
                    
                    # Check for next URL
                    next_url = session.pop('next_url', None)
                    if next_url and next_url != url_for('login'):
                        return redirect(next_url)
                    
                    flash(f'Welcome, {user.username}!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    logger.warning(f"Invalid password for user: {username}")
                    flash('Invalid username or password', 'error')
            else:
                logger.warning(f"User not found or no password hash: {username}")
                flash('Invalid username or password', 'error')
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Login failed. Please try again.', 'error')
    
    return render_template('simple_login.html')

@app.route('/logout')
def logout():
    """User logout"""
    username = session.get('username', 'User')
    session.clear()
    flash(f'Goodbye, {username}!', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if is_authenticated():
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Basic validation
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        # Check if email already exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        try:
            # Create new user
            new_user = User()
            new_user.username = username
            new_user.email = email
            new_user.password_hash = generate_password_hash(password)
            new_user.role = 'user'  # Default role
            new_user.verified = True  # Auto-verify for now
            new_user.created_at = datetime.utcnow()
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('register.html')

# Main routes
@app.route('/')
def index():
    """Landing page"""
    # Always show landing page for now to break redirect loop
    return render_template('landing.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Main dashboard"""
    try:
        from models import User, Bag, Bill, Scan
        from datetime import datetime, timedelta
        
        # Get current user
        current_user = User.query.get(session.get('user_id'))
        if not current_user:
            flash('Session expired, please login again', 'error')
            return redirect(url_for('login'))
        
        # Get dashboard statistics
        total_parent_bags = Bag.query.filter_by(type='parent').count()
        total_child_bags = Bag.query.filter_by(type='child').count()
        total_bills = Bill.query.count()
        total_scans = Scan.query.count()
        
        # Get today's activity
        today = datetime.now().date()
        today_scans = Scan.query.filter(
            Scan.timestamp >= today,
            Scan.timestamp < today + timedelta(days=1)
        ).count()
        
        # Get recent scans (last 10)
        recent_scans = Scan.query.order_by(Scan.timestamp.desc()).limit(10).all()
        
        # Get recent parent bags (last 10)
        recent_parent_bags = Bag.query.filter_by(type='parent').order_by(Bag.created_at.desc()).limit(10).all()
        
        # Get recent child bags (last 10)
        recent_child_bags = Bag.query.filter_by(type='child').order_by(Bag.created_at.desc()).limit(10).all()
        
        # Get recent bills (last 10)
        recent_bills = Bill.query.order_by(Bill.created_at.desc()).limit(10).all()
        
        return render_template('dashboard.html',
                             current_user=current_user,
                             total_parent_bags=total_parent_bags,
                             total_child_bags=total_child_bags,
                             total_bills=total_bills,
                             total_scans=total_scans,
                             today_scans=today_scans,
                             recent_scans=recent_scans,
                             recent_parent_bags=recent_parent_bags,
                             recent_child_bags=recent_child_bags,
                             recent_bills=recent_bills)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('index'))

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

# API Endpoints
@app.route('/api/scan', methods=['POST'])
@require_auth
def api_scan():
    """Process QR code scan"""
    try:
        from models import Bag, Scan
        
        data = request.get_json()
        qr_id = data.get('qr_id', '').strip()
        location = data.get('location', '')
        notes = data.get('notes', '')
        
        if not qr_id:
            return jsonify({'success': False, 'message': 'QR ID is required'})
        
        # Find the bag
        bag = Bag.query.filter_by(qr_id=qr_id).first()
        if not bag:
            return jsonify({'success': False, 'message': 'Bag not found'})
        
        # Create scan record
        scan = Scan()
        if bag.type == 'parent':
            scan.parent_bag_id = bag.id
        else:
            scan.child_bag_id = bag.id
        scan.user_id = session.get('user_id')
        scan.timestamp = datetime.utcnow()
        
        db.session.add(scan)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully scanned {bag.type} bag: {qr_id}',
            'bag': {
                'id': bag.id,
                'qr_id': bag.qr_id,
                'type': bag.type,
                'status': bag.status
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Scan API error: {e}")
        return jsonify({'success': False, 'message': 'Scan failed'})

@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    """Get dashboard statistics"""
    try:
        from models import Bag, Bill, Scan
        from datetime import datetime, timedelta
        
        # Basic counts
        stats = {
            'total_parent_bags': Bag.query.filter_by(type='parent').count(),
            'total_child_bags': Bag.query.filter_by(type='child').count(),
            'total_bills': Bill.query.count(),
            'total_scans': Scan.query.count()
        }
        
        # Today's activity
        today = datetime.now().date()
        stats['today_scans'] = Scan.query.filter(
            Scan.timestamp >= today,
            Scan.timestamp < today + timedelta(days=1)
        ).count()
        
        # This week's activity
        week_ago = datetime.now() - timedelta(days=7)
        stats['week_scans'] = Scan.query.filter(Scan.timestamp >= week_ago).count()
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Dashboard stats API error: {e}")
        return jsonify({'error': 'Failed to load statistics'})

@app.route('/api/recent-scans')
def api_recent_scans():
    """Get recent scans"""
    try:
        from models import Scan, User, Bag
        
        limit = request.args.get('limit', 10, type=int)
        scans = Scan.query.order_by(Scan.timestamp.desc()).limit(limit).all()
        
        scan_data = []
        for scan in scans:
            # Get the bag (either parent or child)
            bag = None
            bag_type = 'unknown'
            if scan.parent_bag_id:
                bag = Bag.query.get(scan.parent_bag_id)
                bag_type = 'parent'
            elif scan.child_bag_id:
                bag = Bag.query.get(scan.child_bag_id)
                bag_type = 'child'
            
            user = User.query.get(scan.user_id) if scan.user_id else None
            
            scan_data.append({
                'id': scan.id,
                'qr_id': bag.qr_id if bag else 'unknown',
                'timestamp': scan.timestamp.isoformat() if scan.timestamp else None,
                'bag_type': bag_type,
                'scanned_by': user.username if user else 'unknown'
            })
        
        return jsonify(scan_data)
        
    except Exception as e:
        logger.error(f"Recent scans API error: {e}")
        return jsonify([])

# Analytics route
@app.route('/analytics')
@require_auth
def analytics():
    """Analytics dashboard"""
    try:
        from models import Bag, Bill, Scan, User
        from datetime import datetime, timedelta
        
        # Get comprehensive analytics data
        analytics_data = {
            'total_scans': Scan.query.count(),
            'total_parent_bags': Bag.query.filter_by(type='parent').count(),
            'total_child_bags': Bag.query.filter_by(type='child').count(),
            'total_bills': Bill.query.count(),
            'total_users': User.query.count(),
        }
        
        # Get recent activity
        week_ago = datetime.now() - timedelta(days=7)
        analytics_data['week_scans'] = Scan.query.filter(Scan.timestamp >= week_ago).count()
        
        # Get daily scan counts for the past week
        daily_scans = []
        for i in range(7):
            day = datetime.now().date() - timedelta(days=i)
            day_scans = Scan.query.filter(
                Scan.timestamp >= day,
                Scan.timestamp < day + timedelta(days=1)
            ).count()
            daily_scans.append({
                'date': day.isoformat(),
                'scans': day_scans
            })
        
        analytics_data['daily_scans'] = list(reversed(daily_scans))
        
        return render_template('analytics.html', analytics=analytics_data)
        
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        flash('Error loading analytics', 'error')
        return redirect(url_for('dashboard'))

# ============================================================================
# SCANNING ROUTES
# ============================================================================

@app.route('/scan')
@require_auth
def scan():
    """QR code scanning page"""
    return render_template('scan.html')

@app.route('/scan-parent')
@require_auth
def scan_parent():
    """Scan parent bags"""
    return render_template('scan_parent.html')

@app.route('/scan-child')
@require_auth
def scan_child():
    """Scan child bags"""
    return render_template('scan_child.html')

@app.route('/child-lookup')
@require_auth
def child_lookup():
    """Child bag lookup and search"""
    search_term = request.args.get('search', '').strip()
    results = []
    
    if search_term:
        try:
            # Search in child bags
            child_bags = db.session.execute(text("""
                SELECT b.qr_id, b.name, b.type, b.created_at, pb.qr_id as parent_qr_id, pb.name as parent_name
                FROM bag b
                LEFT JOIN bag pb ON b.parent_id = pb.id
                WHERE b.type = 'child' AND (b.qr_id ILIKE :search OR b.name ILIKE :search)
                ORDER BY b.created_at DESC
                LIMIT 50
            """), {'search': f'%{search_term}%'}).fetchall()
            
            results = [dict(row._mapping) for row in child_bags]
            
        except Exception as e:
            app.logger.error(f"Child lookup error: {str(e)}")
            flash('Search failed. Please try again.', 'error')
    
    return render_template('child_lookup.html', results=results, search_term=search_term)

# ============================================================================
# BILL MANAGEMENT ROUTES
# ============================================================================

@app.route('/create-bill', methods=['GET', 'POST'])
@require_auth
def create_bill():
    """Create a new bill"""
    if request.method == 'POST':
        bill_id = request.form.get('bill_id', '').strip()
        description = request.form.get('description', '').strip()
        parent_bag_count = request.form.get('parent_bag_count', type=int)
        
        if not bill_id or not parent_bag_count:
            flash('Bill ID and parent bag count are required.', 'error')
            return render_template('create_bill.html')
        
        try:
            # Check if bill ID already exists
            existing_bill = db.session.execute(text("""
                SELECT id FROM bill WHERE bill_id = :bill_id
            """), {'bill_id': bill_id}).fetchone()
            
            if existing_bill:
                flash('Bill ID already exists. Please use a different ID.', 'error')
                return render_template('create_bill.html')
            
            # Create new bill
            db.session.execute(text("""
                INSERT INTO bill (bill_id, description, parent_bag_count, status, created_at, updated_at)
                VALUES (:bill_id, :description, :parent_bag_count, 'draft', :created_at, :updated_at)
            """), {
                'bill_id': bill_id,
                'description': description,
                'parent_bag_count': parent_bag_count,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            
            db.session.commit()
            
            # Get the created bill ID
            new_bill = db.session.execute(text("""
                SELECT id FROM bill WHERE bill_id = :bill_id
            """), {'bill_id': bill_id}).fetchone()
            
            flash('Bill created successfully!', 'success')
            return redirect(url_for('scan_bill_parent', bill_id=new_bill.id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Create bill error: {str(e)}")
            flash('Failed to create bill. Please try again.', 'error')
    
    return render_template('create_bill.html')

@app.route('/scan-bill-parent/<int:bill_id>')
@require_auth
def scan_bill_parent(bill_id):
    """Scan parent bags for a bill"""
    try:
        # Get bill details
        bill = db.session.execute(text("""
            SELECT * FROM bill WHERE id = :bill_id
        """), {'bill_id': bill_id}).fetchone()
        
        if not bill:
            flash('Bill not found.', 'error')
            return redirect(url_for('bill_management'))
        
        # Get already scanned parent bags for this bill
        scanned_bags = db.session.execute(text("""
            SELECT bb.*, b.qr_id, b.name 
            FROM bill_bag bb
            JOIN bag b ON bb.parent_bag_id = b.id
            WHERE bb.bill_id = :bill_id
            ORDER BY bb.created_at DESC
        """), {'bill_id': bill_id}).fetchall()
        
        return render_template('scan_bill_parent.html', bill=bill, scanned_bags=scanned_bags)
        
    except Exception as e:
        app.logger.error(f"Scan bill parent error: {str(e)}")
        flash('Error loading bill details.', 'error')
        return redirect(url_for('bill_management'))

@app.route('/view-bill/<int:bill_id>')
@require_auth
def view_bill(bill_id):
    """View bill details"""
    try:
        # Get bill details
        bill = db.session.execute(text("""
            SELECT * FROM bill WHERE id = :bill_id
        """), {'bill_id': bill_id}).fetchone()
        
        if not bill:
            flash('Bill not found.', 'error')
            return redirect(url_for('bill_management'))
        
        # Get associated parent bags
        parent_bags = db.session.execute(text("""
            SELECT bb.*, b.qr_id, b.name, b.child_count
            FROM bill_bag bb
            JOIN bag b ON bb.parent_bag_id = b.id
            WHERE bb.bill_id = :bill_id
            ORDER BY bb.created_at DESC
        """), {'bill_id': bill_id}).fetchall()
        
        return render_template('view_bill.html', bill=bill, parent_bags=parent_bags)
        
    except Exception as e:
        app.logger.error(f"View bill error: {str(e)}")
        flash('Error loading bill details.', 'error')
        return redirect(url_for('bill_management'))

# ============================================================================
# USER MANAGEMENT ROUTES
# ============================================================================

@app.route('/user-management')
@require_auth
def user_management():
    """User management page - Admin only"""
    if session.get('user_role') != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template('user_management.html', users=users)
    except Exception as e:
        app.logger.error(f"User management error: {str(e)}")
        return render_template('user_management.html', users=[])

@app.route('/admin/promotions')
@require_auth
def admin_promotions():
    """Admin promotion requests management"""
    if session.get('user_role') != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get promotion requests from database
        pending_requests = db.session.execute(text("""
            SELECT pr.*, u.username, u.email 
            FROM promotion_request pr
            JOIN "user" u ON pr.user_id = u.id
            WHERE pr.status = 'pending'
            ORDER BY pr.requested_at DESC
        """)).fetchall()
        
        all_requests = db.session.execute(text("""
            SELECT pr.*, u.username, u.email 
            FROM promotion_request pr
            JOIN "user" u ON pr.user_id = u.id
            ORDER BY pr.requested_at DESC
            LIMIT 50
        """)).fetchall()
        
        return render_template('admin_promotions.html', 
                             pending_requests=pending_requests,
                             all_requests=all_requests)
    except Exception as e:
        app.logger.error(f"Admin promotions error: {str(e)}")
        return render_template('admin_promotions.html', pending_requests=[], all_requests=[])

@app.route('/request-promotion', methods=['GET', 'POST'])
@require_auth
def request_promotion():
    """Request promotion to admin"""
    if session.get('user_role') == 'admin':
        flash('You are already an admin.', 'info')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        reason = request.form.get('reason', '').strip()
        
        if not reason:
            flash('Please provide a reason for your promotion request.', 'error')
            return render_template('request_promotion.html')
        
        try:
            # Check if user already has a pending request
            existing_request = db.session.execute(text("""
                SELECT id FROM promotion_request 
                WHERE user_id = :user_id AND status = 'pending'
            """), {'user_id': session.get('user_id')}).fetchone()
            
            if existing_request:
                flash('You already have a pending promotion request.', 'warning')
                return redirect(url_for('dashboard'))
            
            # Create new promotion request
            db.session.execute(text("""
                INSERT INTO promotion_request (user_id, requested_role, reason, status, requested_at)
                VALUES (:user_id, 'admin', :reason, 'pending', :requested_at)
            """), {
                'user_id': session.get('user_id'),
                'reason': reason,
                'requested_at': datetime.utcnow()
            })
            
            db.session.commit()
            flash('Promotion request submitted successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Promotion request error: {str(e)}")
            flash('Failed to submit promotion request. Please try again.', 'error')
    
    return render_template('request_promotion.html')

# ============================================================================
# API ROUTES FOR SCANNING AND DATA PROCESSING
# ============================================================================

@app.route('/api/scan', methods=['POST'])
@require_auth
def api_scan():
    """Process QR code scan"""
    try:
        data = request.get_json()
        qr_code = data.get('qr_code', '').strip()
        
        if not qr_code:
            return jsonify({'error': 'QR code is required'}), 400
        
        # Check if it's a parent bag
        parent_bag = db.session.execute(text("""
            SELECT * FROM bag WHERE qr_id = :qr_id AND type = 'parent'
        """), {'qr_id': qr_code}).fetchone()
        
        if parent_bag:
            # Record scan
            db.session.execute(text("""
                INSERT INTO scan (parent_bag_id, user_id, timestamp)
                VALUES (:bag_id, :user_id, :timestamp)
            """), {
                'bag_id': parent_bag.id,
                'user_id': session.get('user_id'),
                'timestamp': datetime.utcnow()
            })
            db.session.commit()
            
            return jsonify({
                'type': 'parent',
                'bag': dict(parent_bag._mapping),
                'message': 'Parent bag scanned successfully'
            })
        
        # Check if it's a child bag
        child_bag = db.session.execute(text("""
            SELECT c.*, p.qr_id as parent_qr_id, p.name as parent_name
            FROM bag c
            LEFT JOIN bag p ON c.parent_id = p.id
            WHERE c.qr_id = :qr_id AND c.type = 'child'
        """), {'qr_id': qr_code}).fetchone()
        
        if child_bag:
            # Record scan
            db.session.execute(text("""
                INSERT INTO scan (child_bag_id, user_id, timestamp)
                VALUES (:bag_id, :user_id, :timestamp)
            """), {
                'bag_id': child_bag.id,
                'user_id': session.get('user_id'),
                'timestamp': datetime.utcnow()
            })
            db.session.commit()
            
            return jsonify({
                'type': 'child',
                'bag': dict(child_bag._mapping),
                'message': 'Child bag scanned successfully'
            })
        
        return jsonify({'error': 'QR code not found in system'}), 404
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Scan API error: {str(e)}")
        return jsonify({'error': 'Scan failed'}), 500

@app.route('/api/scan-bill-parent', methods=['POST'])
@require_auth
def api_scan_bill_parent():
    """Scan parent bag for a bill"""
    try:
        data = request.get_json()
        qr_code = data.get('qr_code', '').strip()
        bill_id = data.get('bill_id')
        
        if not qr_code or not bill_id:
            return jsonify({'error': 'QR code and bill ID are required'}), 400
        
        # Check if parent bag exists
        parent_bag = db.session.execute(text("""
            SELECT * FROM bag WHERE qr_id = :qr_id AND type = 'parent'
        """), {'qr_id': qr_code}).fetchone()
        
        if not parent_bag:
            return jsonify({'error': 'Parent bag not found'}), 404
        
        # Check if already added to this bill
        existing_link = db.session.execute(text("""
            SELECT id FROM bill_bag WHERE bill_id = :bill_id AND parent_bag_id = :bag_id
        """), {'bill_id': bill_id, 'bag_id': parent_bag.id}).fetchone()
        
        if existing_link:
            return jsonify({'error': 'Parent bag already added to this bill'}), 400
        
        # Add parent bag to bill
        db.session.execute(text("""
            INSERT INTO bill_bag (bill_id, parent_bag_id, created_at)
            VALUES (:bill_id, :bag_id, :created_at)
        """), {
            'bill_id': bill_id,
            'bag_id': parent_bag.id,
            'created_at': datetime.utcnow()
        })
        
        db.session.commit()
        
        return jsonify({
            'message': 'Parent bag added to bill successfully',
            'bag': dict(parent_bag._mapping)
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Scan bill parent API error: {str(e)}")
        return jsonify({'error': 'Failed to add parent bag to bill'}), 500

logger.info("Production routes loaded successfully")