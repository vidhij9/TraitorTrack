"""
Complete routes for TraceTrack application with all functionality restored
"""
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import text
from app_clean import app, db
from models import User
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Authentication helper
def require_auth(f):
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('login.html')
        
        try:
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                session['logged_in'] = True
                session['user_id'] = user.id
                session['username'] = user.username
                session['user_role'] = user.role
                session.permanent = True
                
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Login failed. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        try:
            # Check if username or email already exists
            existing_user = User.query.filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing_user:
                flash('Username or email already exists', 'error')
                return render_template('register.html')
            
            # Create new user
            new_user = User()
            new_user.username = username
            new_user.email = email
            new_user.password_hash = generate_password_hash(password)
            new_user.role = 'user'
            new_user.verified = True
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

# ============================================================================
# MAIN APPLICATION ROUTES
# ============================================================================

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/dashboard')
@require_auth
def dashboard():
    """Main dashboard"""
    try:
        # Get basic statistics
        stats = {}
        stats['total_bags'] = db.session.execute(text("SELECT COUNT(*) FROM bag")).scalar() or 0
        stats['parent_bags'] = db.session.execute(text("SELECT COUNT(*) FROM bag WHERE type = 'parent'")).scalar() or 0
        stats['child_bags'] = db.session.execute(text("SELECT COUNT(*) FROM bag WHERE type = 'child'")).scalar() or 0
        stats['total_bills'] = db.session.execute(text("SELECT COUNT(*) FROM bill")).scalar() or 0
        stats['total_scans'] = db.session.execute(text("SELECT COUNT(*) FROM scan")).scalar() or 0
        
        # Today's scans
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        stats['today_scans'] = db.session.execute(text("""
            SELECT COUNT(*) FROM scan 
            WHERE timestamp >= :today AND timestamp < :tomorrow
        """), {'today': today, 'tomorrow': tomorrow}).scalar() or 0
        
        # Recent scans
        recent_scans = db.session.execute(text("""
            SELECT s.id, s.timestamp, s.parent_bag_id, s.child_bag_id, s.user_id
            FROM scan s
            ORDER BY s.timestamp DESC
            LIMIT 10
        """)).fetchall()
        
        # Recent parent bags
        recent_parent_bags = db.session.execute(text("""
            SELECT id, qr_id, type, name, child_count, parent_id, created_at, updated_at
            FROM bag 
            WHERE type = 'parent' 
            ORDER BY created_at DESC 
            LIMIT 10
        """)).fetchall()
        
        # Recent child bags
        recent_child_bags = db.session.execute(text("""
            SELECT id, qr_id, type, name, child_count, parent_id, created_at, updated_at
            FROM bag 
            WHERE type = 'child' 
            ORDER BY created_at DESC 
            LIMIT 10
        """)).fetchall()
        
        # Recent bills
        recent_bills = db.session.execute(text("""
            SELECT id, bill_id, description, parent_bag_count, status, created_at, updated_at
            FROM bill 
            ORDER BY created_at DESC 
            LIMIT 10
        """)).fetchall()
        
        return render_template('dashboard.html',
                             stats=stats,
                             recent_scans=recent_scans,
                             recent_parent_bags=recent_parent_bags,
                             recent_child_bags=recent_child_bags,
                             recent_bills=recent_bills)
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('Error loading dashboard', 'error')
        return render_template('dashboard.html', stats={}, recent_scans=[], recent_parent_bags=[], recent_child_bags=[], recent_bills=[])

# ============================================================================
# SCANNING ROUTES
# ============================================================================

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
            logger.error(f"Child lookup error: {str(e)}")
            flash('Search failed. Please try again.', 'error')
    
    return render_template('child_lookup.html', results=results, search_term=search_term)

# ============================================================================
# BAG MANAGEMENT ROUTES
# ============================================================================

@app.route('/bag-management')
@require_auth
def bag_management():
    """Bag management page"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Get parent bags
        parent_bags = db.session.execute(text("""
            SELECT * FROM bag WHERE type = 'parent' 
            ORDER BY created_at DESC 
            LIMIT :limit OFFSET :offset
        """), {'limit': per_page, 'offset': (page - 1) * per_page}).fetchall()
        
        # Get child bags
        child_bags = db.session.execute(text("""
            SELECT * FROM bag WHERE type = 'child' 
            ORDER BY created_at DESC 
            LIMIT :limit OFFSET :offset
        """), {'limit': per_page, 'offset': (page - 1) * per_page}).fetchall()
        
        return render_template('bag_management.html', 
                             parent_bags=parent_bags,
                             child_bags=child_bags,
                             page=page)
        
    except Exception as e:
        logger.error(f"Bag management error: {str(e)}")
        return render_template('bag_management.html', parent_bags=[], child_bags=[], page=1)

# ============================================================================
# BILL MANAGEMENT ROUTES
# ============================================================================

@app.route('/bill-management')
@require_auth
def bill_management():
    """Bill management page"""
    try:
        search_bill_id = request.args.get('search_bill_id', '').strip()
        status_filter = request.args.get('status_filter', 'all')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        query = "SELECT id, bill_id, description, parent_bag_count, status, created_at, updated_at FROM bill WHERE 1=1"
        params = {}
        
        if search_bill_id:
            query += " AND bill_id ILIKE :search_term"
            params['search_term'] = f'%{search_bill_id}%'
            
        if status_filter != 'all':
            query += " AND status = :status"
            params['status'] = status_filter
            
        query += " ORDER BY created_at DESC"
        
        # Get total count for pagination
        count_query = f"SELECT COUNT(*) FROM ({query}) as subquery"
        total = db.session.execute(text(count_query), params).scalar()
        
        # Add pagination
        offset = (page - 1) * per_page
        query += f" LIMIT {per_page} OFFSET {offset}"
        
        bills = db.session.execute(text(query), params).fetchall()
        
        # Convert to list of dicts for template
        bills_data = []
        for bill in bills:
            # Get parent bag count for this bill
            parent_count = db.session.execute(text("""
                SELECT COUNT(DISTINCT parent_bag_id) FROM bill_bag WHERE bill_id = :bill_id
            """), {'bill_id': bill.id}).scalar() or 0
            
            bills_data.append({
                'bill': bill,
                'parent_count': parent_count
            })
        
        # Pagination info
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page,
            'has_prev': page > 1,
            'has_next': page * per_page < total
        }
        
        return render_template('bill_management.html', 
                             bills_data=bills_data, 
                             pagination=pagination,
                             search_bill_id=search_bill_id,
                             status_filter=status_filter)
    except Exception as e:
        logger.error(f"Bill management error: {str(e)}")
        return render_template('bill_management.html', bills_data=[], pagination={})

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
            logger.error(f"Create bill error: {str(e)}")
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
        logger.error(f"Scan bill parent error: {str(e)}")
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
        logger.error(f"View bill error: {str(e)}")
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
        logger.error(f"User management error: {str(e)}")
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
        logger.error(f"Admin promotions error: {str(e)}")
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
            logger.error(f"Promotion request error: {str(e)}")
            flash('Failed to submit promotion request. Please try again.', 'error')
    
    return render_template('request_promotion.html')

# ============================================================================
# ANALYTICS ROUTES
# ============================================================================

@app.route('/analytics')
@require_auth
def analytics():
    """Analytics page"""
    try:
        # Get comprehensive analytics data
        stats = {}
        
        # Basic counts
        stats['total_bags'] = db.session.execute(text("SELECT COUNT(*) FROM bag")).scalar() or 0
        stats['parent_bags'] = db.session.execute(text("SELECT COUNT(*) FROM bag WHERE type = 'parent'")).scalar() or 0
        stats['child_bags'] = db.session.execute(text("SELECT COUNT(*) FROM bag WHERE type = 'child'")).scalar() or 0
        stats['total_bills'] = db.session.execute(text("SELECT COUNT(*) FROM bill")).scalar() or 0
        stats['total_scans'] = db.session.execute(text("SELECT COUNT(*) FROM scan")).scalar() or 0
        stats['total_users'] = db.session.execute(text("SELECT COUNT(*) FROM \"user\"")).scalar() or 0
        
        # Date-based analytics
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        stats['today_scans'] = db.session.execute(text("""
            SELECT COUNT(*) FROM scan 
            WHERE DATE(timestamp) = :today
        """), {'today': today}).scalar() or 0
        
        stats['yesterday_scans'] = db.session.execute(text("""
            SELECT COUNT(*) FROM scan 
            WHERE DATE(timestamp) = :yesterday
        """), {'yesterday': yesterday}).scalar() or 0
        
        stats['week_scans'] = db.session.execute(text("""
            SELECT COUNT(*) FROM scan 
            WHERE timestamp >= :week_ago
        """), {'week_ago': week_ago}).scalar() or 0
        
        stats['month_scans'] = db.session.execute(text("""
            SELECT COUNT(*) FROM scan 
            WHERE timestamp >= :month_ago
        """), {'month_ago': month_ago}).scalar() or 0
        
        return render_template('analytics.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        flash('Error loading analytics', 'error')
        return redirect(url_for('dashboard'))

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/scan-qr', methods=['POST'])
@require_auth
def api_scan_qr():
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
        logger.error(f"Scan API error: {str(e)}")
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
        logger.error(f"Scan bill parent API error: {str(e)}")
        return jsonify({'error': 'Failed to add parent bag to bill'}), 500

@app.route('/api/stats')
@require_auth
def api_stats():
    """Get system statistics"""
    try:
        stats = {}
        stats['total_bags'] = db.session.execute(text("SELECT COUNT(*) FROM bag")).scalar() or 0
        stats['parent_bags'] = db.session.execute(text("SELECT COUNT(*) FROM bag WHERE type = 'parent'")).scalar() or 0
        stats['child_bags'] = db.session.execute(text("SELECT COUNT(*) FROM bag WHERE type = 'child'")).scalar() or 0
        stats['total_bills'] = db.session.execute(text("SELECT COUNT(*) FROM bill")).scalar() or 0
        stats['total_scans'] = db.session.execute(text("SELECT COUNT(*) FROM scan")).scalar() or 0
        
        # Today's scans
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        stats['today_scans'] = db.session.execute(text("""
            SELECT COUNT(*) FROM scan 
            WHERE timestamp >= :today AND timestamp < :tomorrow
        """), {'today': today, 'tomorrow': tomorrow}).scalar() or 0
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'error': 'Failed to get statistics'})

@app.route('/api/scans')
@require_auth
def api_scans():
    """Get recent scans"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        scans = db.session.execute(text("""
            SELECT s.id, s.timestamp, s.parent_bag_id, s.child_bag_id, s.user_id
            FROM scan s
            ORDER BY s.timestamp DESC
            LIMIT :limit
        """), {'limit': limit}).fetchall()
        
        scan_list = []
        for scan in scans:
            scan_list.append({
                'id': scan.id,
                'timestamp': scan.timestamp.isoformat() if scan.timestamp else None,
                'parent_bag_id': scan.parent_bag_id,
                'child_bag_id': scan.child_bag_id,
                'user_id': scan.user_id
            })
        
        return jsonify(scan_list)
        
    except Exception as e:
        logger.error(f"Recent scans error: {e}")
        return jsonify({'error': 'Failed to get recent scans'})

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

# Import the missing timedelta
from datetime import timedelta

logger.info("Complete routes loaded successfully")