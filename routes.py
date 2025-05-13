import logging
import re
import uuid
import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify, session, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from functools import wraps
from app import app, db
from models import User, UserRole, Bag, BagType, Link, Location, Scan
from template_utils import render_cached_template, cached_template
from cache_utils import invalidate_cache

def admin_required(func):
    """Decorator to restrict access to admin users only"""
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('You need administrator privileges to access this page.', 'danger')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return decorated_view

logger = logging.getLogger(__name__)

# Configuration for number of child bags expected per parent
CHILD_BAGS_PER_PARENT = 5  # Can be adjusted as needed

# QR code format validation pattern
PARENT_QR_PATTERN = re.compile(r'^P\d+-\d+$')
CHILD_QR_PATTERN = re.compile(r'^C\d+$')

@app.route('/')
@login_required
def index():
    """Home page - requires login"""
    # Using cached dashboard data
    return render_cached_template(
        'index.html',
        timeout=30,  # Cache dashboard for 30 seconds
        recent_scans=get_recent_scans(),
        total_parent_bags=get_parent_bag_count(),
        total_child_bags=get_child_bag_count(),
        total_scans=get_scan_count(),
        total_locations=get_location_count()
    )

# Cached data access functions for better performance
@cached_template(timeout=30)
def get_recent_scans():
    """Get recent scans with caching"""
    return Scan.query.order_by(Scan.timestamp.desc()).limit(5).all()

@cached_template(timeout=60)
def get_parent_bag_count():
    """Get parent bag count with caching"""
    return Bag.query.filter_by(type=BagType.PARENT.value).count()

@cached_template(timeout=60)
def get_child_bag_count():
    """Get child bag count with caching"""
    return Bag.query.filter_by(type=BagType.CHILD.value).count()

@cached_template(timeout=60)
def get_scan_count():
    """Get total scan count with caching"""
    return Scan.query.count()

@cached_template(timeout=60)
def get_location_count():
    """Get total location count with caching"""
    return Location.query.count()

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    # If user is already logged in, redirect to homepage
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Basic validation
        if not all([username, email, password, confirm_password]):
            flash('All fields are required!', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords must match!', 'danger')
            return render_template('register.html')
        
        # Check if username or email already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return render_template('register.html')
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered!', 'danger')
            return render_template('register.html')
        
        # Create new user with verification token
        verification_token = str(uuid.uuid4())
        new_user = User(
            username=username, 
            email=email,
            role=UserRole.EMPLOYEE.value,  # Default role is employee
            verification_token=verification_token,
            verified=False  # Require verification
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        # In a production environment, we would send an email with the verification link
        # For now, we'll just log it and auto-verify for convenience
        logger.info(f"Verification link for {username}: /verify/{verification_token}")
        
        # Auto-verify for development
        new_user.verified = True
        new_user.verification_token = None
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    # If user is already logged in, redirect to homepage
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Check if user is verified
            if not user.verified:
                flash('Your account is not verified. Please check your email for verification instructions.', 'warning')
                return render_template('login.html')
            
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        
        flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    # Clear any scanning session data
    session.pop('current_location_id', None)
    session.pop('current_parent_bag_id', None)
    session.pop('child_bags_scanned', None)
    
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/promote-to-admin', methods=['GET', 'POST'])
@login_required
def promote_to_admin():
    """Allow users to promote themselves to admin role with a secret code"""
    if request.method == 'POST':
        admin_code = request.form.get('admin_code')
        # The secret code is "tracetracksecret" - in production this would be more secure
        if admin_code == "tracetracksecret":
            current_user.role = UserRole.ADMIN.value
            db.session.commit()
            flash('You have been promoted to administrator!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid administrator code.', 'danger')
    
    return render_template('promote_to_admin.html')

@app.route('/locations', methods=['GET', 'POST'])
@login_required
def locations():
    """Location management page"""
    if request.method == 'POST':
        location_name = request.form.get('location_name')
        location_address = request.form.get('location_address')
        
        if not location_name:
            flash('Location name is required!', 'danger')
            return redirect(url_for('locations'))
        
        # Create new location
        location = Location(
            name=location_name,
            address=location_address
        )
        
        db.session.add(location)
        db.session.commit()
        
        flash('Location added successfully!', 'success')
        return redirect(url_for('locations'))
    
    # Get all locations
    all_locations = Location.query.all()
    return render_template('locations.html', locations=all_locations)

@app.route('/select_location', methods=['GET', 'POST'])
@login_required
def select_location():
    """Select a location before starting scanning process"""
    if request.method == 'POST':
        location_id = request.form.get('location_id')
        
        if not location_id:
            flash('Please select a location!', 'danger')
            return redirect(url_for('select_location'))
        
        # Store selected location in session
        session['current_location_id'] = location_id
        
        # Reset any existing scanning session data
        session.pop('current_parent_bag_id', None)
        session.pop('child_bags_scanned', None)
        
        flash('Location selected! You can now start scanning bags.', 'success')
        return redirect(url_for('scan_parent'))
    
    # Get all locations for selection
    locations = Location.query.all()
    return render_template('select_location.html', locations=locations)

@app.route('/scan_parent')
@login_required
def scan_parent():
    """Scan parent bag QR code"""
    # Ensure a location has been selected
    if 'current_location_id' not in session:
        flash('Please select a location first!', 'warning')
        return redirect(url_for('select_location'))
    
    # Get the current location
    location = Location.query.get(session['current_location_id'])
    if not location:
        flash('Invalid location! Please select a location again.', 'danger')
        return redirect(url_for('select_location'))
    
    return render_template('scan_parent.html', location=location)

@app.route('/process_parent_scan', methods=['POST'])
@login_required
def process_parent_scan():
    """Process parent bag scan"""
    if request.method == 'POST':
        qr_id = request.form.get('qr_id')
        notes = request.form.get('notes', '')
        
        if not qr_id:
            flash('QR code is required!', 'danger')
            return redirect(url_for('scan_parent'))
        
        # Validate parent QR code format (e.g., "P123-10")
        if not PARENT_QR_PATTERN.match(qr_id):
            flash('Invalid QR code format. Parent bag QR code should be in format P123-10', 'danger')
            return redirect(url_for('scan_parent'))
        
        # Parse child count from QR code
        parts = qr_id.split('-')
        if len(parts) != 2:
            flash('Invalid QR code format. Expected format: P123-10', 'danger')
            return redirect(url_for('scan_parent'))
        
        try:
            child_count = int(parts[1])
            if child_count <= 0:
                flash('Parent bag must have at least one child', 'danger')
                return redirect(url_for('scan_parent'))
        except ValueError:
            flash('Invalid child count in QR code', 'danger')
            return redirect(url_for('scan_parent'))
        
        # Ensure a location has been selected
        if 'current_location_id' not in session:
            flash('Please select a location first!', 'warning')
            return redirect(url_for('select_location'))
        
        location_id = session['current_location_id']
        
        # Check if parent bag exists, create if not
        parent_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.PARENT.value).first()
        
        if not parent_bag:
            # Create new parent bag
            parent_bag = Bag()
            parent_bag.qr_id = qr_id
            parent_bag.name = f"Parent Bag {qr_id}"  # Default name
            parent_bag.notes = notes
            parent_bag.type = BagType.PARENT.value
            parent_bag.child_count = child_count
            
            db.session.add(parent_bag)
            db.session.commit()
            logger.debug(f"Created new parent bag with QR ID: {qr_id}, expecting {child_count} children")
        
        # Record the scan
        try:
            scan = Scan()
            scan.parent_bag_id = parent_bag.id
            scan.user_id = current_user.id
            scan.location_id = location_id
            scan.scan_type = 'parent'
            scan.notes = notes
            
            db.session.add(scan)
            db.session.commit()
            
            # Store the parent bag ID in session
            session['current_parent_bag_id'] = parent_bag.id
            session['child_bags_scanned'] = []
            session['child_bags_expected'] = child_count  # Store expected count
            
            flash(f'Parent bag {qr_id} scanned successfully! Now scan {child_count} child bags.', 'success')
            return redirect(url_for('scan_child'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error recording parent bag scan: {str(e)}")
            flash(f'Error recording scan: {str(e)}', 'danger')
            return redirect(url_for('scan_parent'))
    
    return redirect(url_for('scan_parent'))

@app.route('/scan_child')
@login_required
@admin_required
def scan_child():
    """Scan child bag QR code (admin only)"""
    # Ensure a location and parent bag have been selected
    if 'current_location_id' not in session:
        flash('Please select a location first!', 'warning')
        return redirect(url_for('select_location'))
    
    if 'current_parent_bag_id' not in session:
        flash('Please scan a parent bag first!', 'warning')
        return redirect(url_for('scan_parent'))
    
    # Get the current location and parent bag
    location = Location.query.get(session['current_location_id'])
    parent_bag = Bag.query.filter_by(id=session['current_parent_bag_id'], type=BagType.PARENT.value).first()
    
    if not location or not parent_bag:
        flash('Invalid session data! Please start over.', 'danger')
        return redirect(url_for('select_location'))
    
    # Calculate progress
    child_bags_scanned = session.get('child_bags_scanned', [])
    child_bags_expected = session.get('child_bags_expected', parent_bag.child_count)
    bags_remaining = child_bags_expected - len(child_bags_scanned)
    progress_percentage = int((len(child_bags_scanned) / child_bags_expected) * 100) if child_bags_expected > 0 else 0
    
    return render_template('scan_child.html', 
                          location=location, 
                          parent_bag=parent_bag,
                          child_bags_scanned=child_bags_scanned,
                          bags_remaining=bags_remaining,
                          progress_percentage=progress_percentage,
                          total_expected=child_bags_expected)

@app.route('/process_child_scan', methods=['POST'])
@login_required
@admin_required
def process_child_scan():
    """Process child bag scan (admin only)"""
    if request.method == 'POST':
        qr_id = request.form.get('qr_id')
        notes = request.form.get('notes', '')
        
        if not qr_id:
            flash('QR code is required!', 'danger')
            return redirect(url_for('scan_child'))
        
        # Validate child QR code format (e.g., "C123")
        if not CHILD_QR_PATTERN.match(qr_id):
            flash('Invalid QR code format. Child bag QR code should be in format C123', 'danger')
            return redirect(url_for('scan_child'))
        
        # Ensure a location and parent bag have been selected
        if 'current_location_id' not in session or 'current_parent_bag_id' not in session:
            flash('Please start the scanning process from the beginning!', 'warning')
            return redirect(url_for('select_location'))
        
        location_id = session['current_location_id']
        parent_bag_id = session['current_parent_bag_id']
        
        # Check if this child bag was already scanned in this session
        child_bags_scanned = session.get('child_bags_scanned', [])
        if qr_id in child_bags_scanned:
            flash(f'Child bag {qr_id} was already scanned in this session!', 'warning')
            return redirect(url_for('scan_child'))
        
        # Check if child bag exists, create if not
        child_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.CHILD.value).first()
        
        if not child_bag:
            # Create new child bag
            child_bag = Bag()
            child_bag.qr_id = qr_id
            child_bag.name = f"Child Bag {qr_id}"  # Default name
            child_bag.parent_id = parent_bag_id
            child_bag.notes = notes
            child_bag.type = BagType.CHILD.value
            
            db.session.add(child_bag)
            db.session.commit()
            logger.debug(f"Created new child bag with QR ID: {qr_id}")
        else:
            # Update parent relationship if different
            if child_bag.parent_id != parent_bag_id:
                child_bag.parent_id = parent_bag_id
                db.session.commit()
                logger.debug(f"Updated child bag {qr_id} to parent {parent_bag_id}")
        
        # Record the scan
        try:
            scan = Scan()
            scan.child_bag_id = child_bag.id
            scan.user_id = current_user.id
            scan.location_id = location_id
            scan.scan_type = 'child'
            scan.notes = notes
            
            db.session.add(scan)
            db.session.commit()
            
            # Update session data
            child_bags_scanned.append(qr_id)
            session['child_bags_scanned'] = child_bags_scanned
            
            # Get the expected count from session or parent bag
            parent_bag = Bag.query.get(parent_bag_id)
            child_bags_expected = session.get('child_bags_expected', parent_bag.child_count if parent_bag else CHILD_BAGS_PER_PARENT)
            
            # Check if we've scanned all expected child bags
            if len(child_bags_scanned) >= child_bags_expected:
                flash('All child bags have been scanned successfully!', 'success')
                return redirect(url_for('scan_complete'))
            
            flash(f'Child bag {qr_id} scanned successfully! {child_bags_expected - len(child_bags_scanned)} more to go.', 'success')
            return redirect(url_for('scan_child'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error recording child bag scan: {str(e)}")
            flash(f'Error recording scan: {str(e)}', 'danger')
            return redirect(url_for('scan_child'))
    
    return redirect(url_for('scan_child'))

@app.route('/scan_complete')
@login_required
@admin_required
def scan_complete():
    """Scanning process complete page (admin only)"""
    # Ensure we have valid session data
    if 'current_parent_bag_id' not in session or 'child_bags_scanned' not in session:
        flash('Invalid session state! Please start over.', 'warning')
        return redirect(url_for('select_location'))
    
    parent_bag = Bag.query.filter_by(id=session['current_parent_bag_id'], type=BagType.PARENT.value).first()
    child_bags_count = len(session.get('child_bags_scanned', []))
    child_bags_expected = session.get('child_bags_expected', parent_bag.child_count if parent_bag else CHILD_BAGS_PER_PARENT)
    
    # Get all scanned child bags for this parent
    child_bags = []
    if parent_bag:
        child_bags = Bag.query.filter_by(parent_id=parent_bag.id, type=BagType.CHILD.value).all()
    
    # Clear session data for next scan
    session.pop('current_parent_bag_id', None)
    session.pop('child_bags_scanned', None)
    session.pop('child_bags_expected', None)
    
    return render_template('scan_complete.html', 
                          parent_bag=parent_bag,
                          child_bags=child_bags,
                          child_bags_count=child_bags_count,
                          expected_count=child_bags_expected)

@app.route('/parent_bags')
@login_required
@admin_required
def parent_bags():
    """List of all parent bags and their child bags (admin only)"""
    # Use cached template for better performance under high load
    return render_cached_template(
        'parent_bags.html', 
        timeout=30,  # Cache for 30 seconds
        parent_bags=get_all_parent_bags(),
        Scan=Scan
    )

@cached_template(timeout=30)
def get_all_parent_bags():
    """Get all parent bags with caching for better performance"""
    return Bag.query.filter_by(type=BagType.PARENT.value).all()

@app.route('/child_bags')
@login_required
@admin_required
def child_bags():
    """List of all child bags and their parent bag (admin only)"""
    child_bags = Bag.query.filter_by(type=BagType.CHILD.value).all()
    return render_template('child_bags.html', child_bags=child_bags, Scan=Scan)

@app.route('/bag/<qr_id>')
@login_required
@admin_required
def bag_detail(qr_id):
    """Bag detail page showing scan history (admin only)"""
    # Try to find the bag (could be parent or child)
    bag = Bag.query.filter_by(qr_id=qr_id).first_or_404()
    
    if bag.type == BagType.PARENT.value:
        # Get child bags associated with this parent
        child_bags = Bag.query.filter_by(parent_id=bag.id, type=BagType.CHILD.value).all()
        
        # Get scan history for this parent bag
        scans = Scan.query.filter_by(parent_bag_id=bag.id).order_by(Scan.timestamp.desc()).all()
        
        # Check if there's a bill linked to this parent bag
        link = Link.query.filter_by(parent_id=bag.id).first()
        
        return render_template('bag_detail.html', 
                              is_parent=True,
                              bag=bag, 
                              child_bags=child_bags,
                              scans=scans,
                              link=link,
                              Scan=Scan)
    else:
        # It's a child bag
        # Get scan history for this child bag
        scans = Scan.query.filter_by(child_bag_id=bag.id).order_by(Scan.timestamp.desc()).all()
        
        return render_template('bag_detail.html', 
                              is_parent=False,
                              bag=bag,
                              scans=scans,
                              Scan=Scan)

@app.route('/link_to_bill/<parent_qr_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def link_to_bill(parent_qr_id):
    """Link a parent bag to a bill ID (admin only)"""
    parent_bag = Bag.query.filter_by(qr_id=parent_qr_id, type=BagType.PARENT.value).first_or_404()
    
    # Check if bag is already linked to a bill
    existing_link = Link.query.filter_by(parent_id=parent_bag.id).first()
    
    if request.method == 'POST':
        bill_id = request.form.get('bill_id')
        
        if not bill_id:
            flash('Bill ID is required!', 'danger')
            return redirect(url_for('link_to_bill', parent_qr_id=parent_qr_id))
        
        try:
            if existing_link:
                # Update existing link
                existing_link.bill_id = bill_id
                db.session.commit()
                flash(f'Updated bill link for parent bag {parent_qr_id}', 'success')
            else:
                # Create new link
                link = Link()
                link.parent_id = parent_bag.id
                link.bill_id = bill_id
                
                # Mark the parent bag as linked
                parent_bag.linked = True
                
                db.session.add(link)
                db.session.commit()
                flash(f'Parent bag {parent_qr_id} linked to bill {bill_id}', 'success')
            
            return redirect(url_for('bag_detail', qr_id=parent_qr_id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error linking bag to bill: {str(e)}")
            flash(f'Error linking bag to bill: {str(e)}', 'danger')
    
    return render_template('link_to_bill.html', 
                          parent_bag=parent_bag,
                          existing_link=existing_link)

@app.route('/bill/<bill_id>')
@login_required
@admin_required
def bill_detail(bill_id):
    """Show all parent bags linked to a bill (admin only)"""
    links = Link.query.filter_by(bill_id=bill_id).all()
    
    if not links:
        flash(f'No bags found linked to bill {bill_id}', 'warning')
        return redirect(url_for('index'))
    
    parent_bags = []
    for link in links:
        parent_bag = Bag.query.filter_by(id=link.parent_id, type=BagType.PARENT.value).first()
        if parent_bag:
            parent_bags.append(parent_bag)
    
    return render_template('bill_detail.html', 
                          bill_id=bill_id,
                          parent_bags=parent_bags)

@app.route('/init_db')
def init_db():
    """Initialize the database with test data"""
    try:
        # Check if there are already users
        if User.query.count() > 0:
            flash('Database already contains data!', 'warning')
            return redirect(url_for('index'))
        
        # Create admin and employee users
        admin = User()
        admin.username = "admin"
        admin.email = "admin@example.com"
        admin.role = UserRole.ADMIN.value
        admin.verified = True
        admin.set_password("adminpass")
        
        employee = User()
        employee.username = "employee"
        employee.email = "employee@example.com"
        employee.role = UserRole.EMPLOYEE.value
        employee.verified = True
        employee.set_password("employeepass")
        
        db.session.add_all([admin, employee])
        
        # Create locations
        warehouse = Location()
        warehouse.name = "Warehouse A"
        warehouse.address = "123 Main St"
        
        distribution = Location()
        distribution.name = "Distribution Center"
        distribution.address = "456 State St"
        
        retail = Location()
        retail.name = "Retail Store"
        retail.address = "789 Market St"
        
        db.session.add_all([warehouse, distribution, retail])
        
        # Create some parent bags
        parent1 = Bag()
        parent1.qr_id = "P101-5"
        parent1.name = "Parent Bag P101"
        parent1.type = BagType.PARENT.value
        parent1.child_count = 5
        
        parent2 = Bag()
        parent2.qr_id = "P102-3"
        parent2.name = "Parent Bag P102"
        parent2.type = BagType.PARENT.value
        parent2.child_count = 3
        
        db.session.add_all([parent1, parent2])
        db.session.commit()
        
        # Create some child bags
        children = []
        for i in range(1, 6):
            child = Bag()
            child.qr_id = f"C10{i}"
            child.name = f"Child Bag C10{i}"
            child.type = BagType.CHILD.value
            child.parent_id = parent1.id
            children.append(child)
        
        for i in range(6, 9):
            child = Bag()
            child.qr_id = f"C10{i}"
            child.name = f"Child Bag C10{i}"
            child.type = BagType.CHILD.value
            child.parent_id = parent2.id
            children.append(child)
        
        db.session.add_all(children)
        
        # Create some sample scans
        scan1 = Scan()
        scan1.parent_bag_id = parent1.id
        scan1.user_id = admin.id
        scan1.location_id = warehouse.id
        scan1.scan_type = 'parent'
        scan1.notes = "Initial scan of parent bag"
        
        scan2 = Scan()
        scan2.parent_bag_id = parent2.id
        scan2.user_id = employee.id
        scan2.location_id = distribution.id
        scan2.scan_type = 'parent'
        
        scan3 = Scan()
        scan3.child_bag_id = children[0].id
        scan3.user_id = employee.id
        scan3.location_id = retail.id
        scan3.scan_type = 'child'
        
        db.session.add_all([scan1, scan2, scan3])
        
        # Create a bill link
        link = Link()
        link.parent_id = parent1.id
        link.bill_id = "BILL-1001"
        parent1.linked = True
        
        db.session.add(link)
        db.session.commit()
        
        flash('Database initialized with test data!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error initializing database: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/reset_db')
def reset_db():
    """Reset the database (for development only)"""
    try:
        # Import all models to ensure they're registered with SQLAlchemy
        import models
        from models import User, Bag, Link, Location, Scan
        
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        flash('Database has been reset!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error resetting database: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.context_processor
def utility_processor():
    """Utility functions available in templates"""
    def format_datetime(dt):
        if dt:
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return ''
    
    return dict(format_datetime=format_datetime)
