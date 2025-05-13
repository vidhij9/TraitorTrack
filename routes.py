import logging
import re
import uuid
import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app import app, db
from models import User, UserRole, Bag, BagType, Link, Location, Scan

logger = logging.getLogger(__name__)

# Configuration for number of child bags expected per parent
CHILD_BAGS_PER_PARENT = 5  # Can be adjusted as needed

# QR code format validation pattern
PARENT_QR_PATTERN = re.compile(r'^P\d+-\d+$')
CHILD_QR_PATTERN = re.compile(r'^C\d+$')

@app.route('/')
def index():
    """Home page"""
    # Get statistics for display
    recent_scans = Scan.query.order_by(Scan.timestamp.desc()).limit(5).all()
    total_parent_bags = Bag.query.filter_by(type=BagType.PARENT.value).count()
    total_child_bags = Bag.query.filter_by(type=BagType.CHILD.value).count()
    total_scans = Scan.query.count()
    total_locations = Location.query.count()
    
    return render_template('index.html', 
                          recent_scans=recent_scans,
                          total_parent_bags=total_parent_bags,
                          total_child_bags=total_child_bags,
                          total_scans=total_scans,
                          total_locations=total_locations)

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
        
        # Ensure a location has been selected
        if 'current_location_id' not in session:
            flash('Please select a location first!', 'warning')
            return redirect(url_for('select_location'))
        
        location_id = session['current_location_id']
        
        # Check if parent bag exists, create if not
        parent_bag = ParentBag.query.filter_by(qr_id=qr_id).first()
        
        if not parent_bag:
            # Create new parent bag
            parent_bag = ParentBag(
                qr_id=qr_id,
                name=f"Parent Bag {qr_id}",  # Default name
                notes=notes
            )
            db.session.add(parent_bag)
            db.session.commit()
            logger.debug(f"Created new parent bag with QR ID: {qr_id}")
        
        # Record the scan
        try:
            scan = Scan(
                parent_bag_id=parent_bag.id,
                user_id=current_user.id,
                location_id=location_id,
                scan_type='parent',
                notes=notes
            )
            
            db.session.add(scan)
            db.session.commit()
            
            # Store the parent bag ID in session
            session['current_parent_bag_id'] = parent_bag.id
            session['child_bags_scanned'] = []
            
            flash(f'Parent bag {qr_id} scanned successfully! Now scan child bags.', 'success')
            return redirect(url_for('scan_child'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error recording parent bag scan: {str(e)}")
            flash(f'Error recording scan: {str(e)}', 'danger')
            return redirect(url_for('scan_parent'))
    
    return redirect(url_for('scan_parent'))

@app.route('/scan_child')
@login_required
def scan_child():
    """Scan child bag QR code"""
    # Ensure a location and parent bag have been selected
    if 'current_location_id' not in session:
        flash('Please select a location first!', 'warning')
        return redirect(url_for('select_location'))
    
    if 'current_parent_bag_id' not in session:
        flash('Please scan a parent bag first!', 'warning')
        return redirect(url_for('scan_parent'))
    
    # Get the current location and parent bag
    location = Location.query.get(session['current_location_id'])
    parent_bag = ParentBag.query.get(session['current_parent_bag_id'])
    
    if not location or not parent_bag:
        flash('Invalid session data! Please start over.', 'danger')
        return redirect(url_for('select_location'))
    
    # Calculate progress
    child_bags_scanned = session.get('child_bags_scanned', [])
    bags_remaining = CHILD_BAGS_PER_PARENT - len(child_bags_scanned)
    progress_percentage = int((len(child_bags_scanned) / CHILD_BAGS_PER_PARENT) * 100)
    
    return render_template('scan_child.html', 
                          location=location, 
                          parent_bag=parent_bag,
                          child_bags_scanned=child_bags_scanned,
                          bags_remaining=bags_remaining,
                          progress_percentage=progress_percentage,
                          total_expected=CHILD_BAGS_PER_PARENT)

@app.route('/process_child_scan', methods=['POST'])
@login_required
def process_child_scan():
    """Process child bag scan"""
    if request.method == 'POST':
        qr_id = request.form.get('qr_id')
        notes = request.form.get('notes', '')
        
        if not qr_id:
            flash('QR code is required!', 'danger')
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
        child_bag = ChildBag.query.filter_by(qr_id=qr_id).first()
        
        if not child_bag:
            # Create new child bag
            child_bag = ChildBag(
                qr_id=qr_id,
                name=f"Child Bag {qr_id}",  # Default name
                parent_id=parent_bag_id,
                notes=notes
            )
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
            scan = Scan(
                child_bag_id=child_bag.id,
                user_id=current_user.id,
                location_id=location_id,
                scan_type='child',
                notes=notes
            )
            
            db.session.add(scan)
            db.session.commit()
            
            # Update session data
            child_bags_scanned.append(qr_id)
            session['child_bags_scanned'] = child_bags_scanned
            
            # Check if we've scanned all expected child bags
            if len(child_bags_scanned) >= CHILD_BAGS_PER_PARENT:
                flash('All child bags have been scanned successfully!', 'success')
                return redirect(url_for('scan_complete'))
            
            flash(f'Child bag {qr_id} scanned successfully! {CHILD_BAGS_PER_PARENT - len(child_bags_scanned)} more to go.', 'success')
            return redirect(url_for('scan_child'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error recording child bag scan: {str(e)}")
            flash(f'Error recording scan: {str(e)}', 'danger')
            return redirect(url_for('scan_child'))
    
    return redirect(url_for('scan_child'))

@app.route('/scan_complete')
@login_required
def scan_complete():
    """Scanning process complete page"""
    # Ensure we have valid session data
    if 'current_parent_bag_id' not in session or 'child_bags_scanned' not in session:
        flash('Invalid session state! Please start over.', 'warning')
        return redirect(url_for('select_location'))
    
    parent_bag = ParentBag.query.get(session['current_parent_bag_id'])
    child_bags_count = len(session.get('child_bags_scanned', []))
    
    # Clear session data for next scan
    session.pop('current_parent_bag_id', None)
    session.pop('child_bags_scanned', None)
    
    return render_template('scan_complete.html', 
                          parent_bag=parent_bag,
                          child_bags_count=child_bags_count)

@app.route('/parent_bags')
def parent_bags():
    """List of all parent bags and their child bags"""
    parent_bags = ParentBag.query.all()
    return render_template('parent_bags.html', parent_bags=parent_bags)

@app.route('/child_bags')
def child_bags():
    """List of all child bags and their parent bag"""
    child_bags = ChildBag.query.all()
    return render_template('child_bags.html', child_bags=child_bags)

@app.route('/bag/<qr_id>')
def bag_detail(qr_id):
    """Bag detail page showing scan history"""
    parent_bag = ParentBag.query.filter_by(qr_id=qr_id).first()
    
    if parent_bag:
        # Get child bags associated with this parent
        child_bags = ChildBag.query.filter_by(parent_id=parent_bag.id).all()
        
        # Get scan history for this parent bag
        scans = Scan.query.filter_by(parent_bag_id=parent_bag.id).order_by(Scan.timestamp.desc()).all()
        
        return render_template('bag_detail.html', 
                              is_parent=True,
                              bag=parent_bag, 
                              child_bags=child_bags,
                              scans=scans)
    else:
        # Check if it's a child bag
        child_bag = ChildBag.query.filter_by(qr_id=qr_id).first_or_404()
        
        # Get scan history for this child bag
        scans = Scan.query.filter_by(child_bag_id=child_bag.id).order_by(Scan.timestamp.desc()).all()
        
        return render_template('bag_detail.html', 
                              is_parent=False,
                              bag=child_bag,
                              scans=scans)

@app.context_processor
def utility_processor():
    """Utility functions available in templates"""
    def format_datetime(dt):
        if dt:
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return ''
    
    return dict(format_datetime=format_datetime)
