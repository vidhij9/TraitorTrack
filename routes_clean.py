import logging
import re
from flask import render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from app_clean import app, db, limiter
from models import User, UserRole, Bag, BagType, Link, Location, Scan, Bill, BillBag
from account_security import is_account_locked, record_failed_attempt, reset_failed_attempts, track_login_activity
from validation_utils import validate_parent_qr_id, validate_child_qr_id, validate_bill_id, sanitize_input

# Main routes
@app.route('/')
def index():
    """Main dashboard page"""
    stats = {
        'parent_bags': Bag.query.filter_by(type=BagType.PARENT.value).count(),
        'child_bags': Bag.query.filter_by(type=BagType.CHILD.value).count(),
        'bills': Bill.query.count(),
        'total_scans': Scan.query.count()
    }
    
    recent_scans = []
    if current_user.is_authenticated:
        recent_scans = Scan.query.order_by(Scan.timestamp.desc()).limit(10).all()
    
    return render_template('index.html', 
                           user=current_user,
                           is_admin=current_user.is_admin() if current_user.is_authenticated else False,
                           stats=stats,
                           recent_scans=recent_scans)

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"])
@limiter.limit("5/minute, 100/day", error_message="Too many login attempts, please try again later.")
def login():
    """User login page with rate limiting and account lockout to prevent brute force attacks"""
    from forms import LoginForm
    import traceback
    
    # If user is already logged in, redirect to homepage
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    
    try:
        # Handle login attempts
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data
            remember = form.remember.data
            
            logging.debug(f"Login attempt for username: {username}")
            
            try:
                # Check if the account is locked
                is_locked, remaining_time = is_account_locked(username)
                if is_locked:
                    flash(f'Account temporarily locked. Try again in {remaining_time} seconds.', 'danger')
                    return render_template('login.html', form=form, login_attempts={'is_locked': True, 'lockout_time': remaining_time})
            except Exception as e:
                logging.error(f"Error checking account lock: {str(e)}")
                logging.error(traceback.format_exc())
            
            try:
                # Find the user
                user = User.query.filter_by(username=username).first()
                
                # Handle non-existent user
                if not user:
                    flash('Invalid username or password.', 'danger')
                    return render_template('login.html', form=form)
            except Exception as e:
                logging.error(f"Error finding user: {str(e)}")
                logging.error(traceback.format_exc())
            
            try:
                # Verify password
                if not user.check_password(password):
                    # Record failed login attempt
                    is_locked, attempts, lockout_time = record_failed_attempt(username)
                    
                    if is_locked:
                        flash(f'Account locked due to too many failed attempts. Try again in {lockout_time}.', 'danger')
                        login_attempts = {'is_locked': True, 'lockout_time': lockout_time}
                    else:
                        flash(f'Invalid username or password. {attempts} attempts remaining before lockout.', 'danger')
                        login_attempts = {'attempts_remaining': attempts}
                    
                    return render_template('login.html', form=form, login_attempts=login_attempts)
            except Exception as e:
                logging.error(f"Error verifying password: {str(e)}")
                logging.error(traceback.format_exc())
            
            try:
                # Check verification status
                if not user.verified:
                    flash('Your account is not verified. Please check your email for verification instructions.', 'warning')
                    return render_template('login.html', form=form)
            except Exception as e:
                logging.error(f"Error checking verification: {str(e)}")
                logging.error(traceback.format_exc())
            
            try:
                # Login successful
                
                # Reset failed attempts on successful login
                reset_failed_attempts(username)
                
                # Clear session before login to prevent session fixation
                session.clear()
                
                # Login user with Flask-Login
                login_user(user, remember=remember)
                
                # Set session as permanent to respect the configured lifetime
                session.permanent = True
                
                # Track login activity
                track_login_activity(user.id, success=True)
                
                # Redirect to appropriate page
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('index'))
            except Exception as e:
                logging.error(f"Error during login process: {str(e)}")
                logging.error(traceback.format_exc())
                flash('An error occurred during login. Please try again.', 'danger')
    except Exception as e:
        logging.error(f"Uncaught exception in login route: {str(e)}")
        logging.error(traceback.format_exc())
        flash('An unexpected error occurred. Please try again later.', 'danger')
    
    return render_template('login.html', form=form)

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page with form validation"""
    from forms import RegistrationForm
    
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            verified=True  # Auto-verify for testing
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/promote_admin', methods=['GET', 'POST'])
@login_required
def promote_admin():
    """Allow users to promote themselves to admin with secret code"""
    from forms import PromoteToAdminForm
    
    if current_user.is_admin():
        flash('You are already an admin.', 'info')
        return redirect(url_for('index'))
    
    form = PromoteToAdminForm()
    
    if form.validate_on_submit():
        secret_code = form.secret_code.data
        
        if secret_code == 'tracetracksecret':
            current_user.role = UserRole.ADMIN.value
            db.session.commit()
            flash('You have been promoted to admin!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid secret code.', 'danger')
    
    return render_template('promote_admin.html', form=form)

# Workflow A: Parent-Child Scanning
@app.route('/select_location', methods=['GET', 'POST'])
@login_required
def select_location():
    """Select location for scanning operations"""
    from forms import LocationSelectionForm
    import traceback
    
    try:
        # Get all locations
        locations = Location.query.all()
        
        # Create form and set choices
        form = LocationSelectionForm()
        form.location.choices = [(loc.id, loc.name) for loc in locations]
        
        if form.validate_on_submit():
            location_id = form.location.data
            session['current_location_id'] = location_id
            flash('Location selected successfully.', 'success')
            return redirect(url_for('scan_parent'))
            
        # If POST request but form validation failed
        elif request.method == 'POST':
            # Check for direct form submission
            location_id = request.form.get('location_id')
            if location_id:
                try:
                    location_id = int(location_id)
                    # Verify location exists
                    location = Location.query.get(location_id)
                    if location:
                        session['current_location_id'] = location_id
                        flash('Location selected successfully.', 'success')
                        return redirect(url_for('scan_parent'))
                except Exception as e:
                    logging.error(f"Error processing location selection: {str(e)}")
                    logging.error(traceback.format_exc())
            
            flash('Please select a valid location.', 'warning')
        
        # Clear any existing scanning session
        session.pop('current_parent_bag_id', None)
        session.pop('child_bags_scanned', None)
        
        return render_template('select_location.html', locations=locations, form=form)
    except Exception as e:
        logging.error(f"Error in select_location: {str(e)}")
        logging.error(traceback.format_exc())
        flash('An error occurred while loading locations. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/scan_parent')
@login_required
def scan_parent():
    """Scan parent bag QR code"""
    # Ensure location is selected
    if 'current_location_id' not in session:
        flash('Please select a location first.', 'warning')
        return redirect(url_for('select_location'))
    
    return render_template('scan_parent.html')

@app.route('/process_parent_scan', methods=['POST'])
@login_required
def process_parent_scan():
    """Process the parent bag QR code scan"""
    if 'current_location_id' not in session:
        return jsonify({'success': False, 'message': 'No location selected'})
    
    qr_code = request.form.get('qr_code')
    if not qr_code:
        return jsonify({'success': False, 'message': 'No QR code provided'})
    
    # Clean up the QR code
    qr_code = qr_code.strip()
    
    # Validate the QR code using the improved validator that handles any format
    is_valid, message, child_count = validate_parent_qr_id(qr_code)
    if not is_valid:
        return jsonify({'success': False, 'message': message})
    
    # Look up or create the parent bag
    parent_bag = Bag.query.filter_by(qr_id=qr_code, type=BagType.PARENT.value).first()
    
    if not parent_bag:
        # Create new parent bag
        parent_bag = Bag(qr_id=qr_code, type=BagType.PARENT.value)
        db.session.add(parent_bag)
        db.session.commit()
    
    # Record the scan
    location = Location.query.get(session['current_location_id'])
    scan = Scan(parent_bag_id=parent_bag.id, location_id=location.id, user_id=current_user.id)
    db.session.add(scan)
    db.session.commit()
    
    # Store parent bag ID in session
    session['current_parent_bag_id'] = parent_bag.id
    session['child_bags_scanned'] = []
    
    # Use the improved validate_parent_qr_id function to get child count
    is_valid, message, expected_child_count = validate_parent_qr_id(qr_code)
    # Update parent bag with the extracted child count
    parent_bag.child_count = expected_child_count
    db.session.commit()
    
    return jsonify({
        'success': True,
        'parent_id': parent_bag.id,
        'parent_qr': parent_bag.qr_id,
        'expected_child_count': expected_child_count,
        'message': f'Parent bag {qr_code} scanned successfully. Please scan {expected_child_count} child bags.'
    })

@app.route('/scan_child')
@login_required
def scan_child():
    """Scan child bag QR code"""
    # Ensure parent bag is scanned
    if 'current_parent_bag_id' not in session:
        flash('Please scan a parent bag first.', 'warning')
        return redirect(url_for('scan_parent'))
    
    parent_bag = Bag.query.get(session['current_parent_bag_id'])
    
    # Initialize child bags scanned list if not already in session
    if 'child_bags_scanned' not in session:
        session['child_bags_scanned'] = []
    
    # Calculate expected child count from parent QR
    try:
        expected_child_count = int(parent_bag.qr_id.split('-')[1])
    except:
        expected_child_count = 5  # Default
    
    # Get scanned child bag IDs
    scanned_child_ids = session.get('child_bags_scanned', [])
    
    return render_template('scan_child.html', 
                           parent_bag=parent_bag,
                           expected_child_count=expected_child_count,
                           scanned_child_count=len(scanned_child_ids))

@app.route('/process_child_scan', methods=['POST'])
@login_required
def process_child_scan():
    """Process the child bag QR code scan"""
    if 'current_parent_bag_id' not in session:
        return jsonify({'success': False, 'message': 'No parent bag selected'})
    
    qr_code = request.form.get('qr_code', '').strip()
    if not qr_code:
        return jsonify({'success': False, 'message': 'No QR code provided'})
    
    # Validate the QR code using the improved validator that handles any format
    is_valid, message = validate_child_qr_id(qr_code)
    if not is_valid:
        return jsonify({'success': False, 'message': message})
    
    # Check if this child bag is already scanned in this session
    child_bags_scanned = session.get('child_bags_scanned', [])
    if qr_code in child_bags_scanned:
        return jsonify({'success': False, 'message': f'Child bag {qr_code} already scanned'})
    
    # Look up or create the child bag - accepting any QR code format
    child_bag = Bag.query.filter_by(qr_id=qr_code).first()
    
    if not child_bag:
        # Create new child bag with any QR format
        child_bag = Bag(qr_id=qr_code, type=BagType.CHILD.value)
        db.session.add(child_bag)
        db.session.commit()
    elif child_bag.type != BagType.CHILD.value:
        # If the bag exists but isn't marked as a child bag, update it
        child_bag.type = BagType.CHILD.value
        db.session.commit()
    
    # Record the scan
    location_id = session['current_location_id']
    parent_bag_id = session['current_parent_bag_id']
    
    scan = Scan(child_bag_id=child_bag.id, location_id=location_id, user_id=current_user.id)
    db.session.add(scan)
    
    # Link parent to child
    link = Link.query.filter_by(parent_bag_id=parent_bag_id, child_bag_id=child_bag.id).first()
    if not link:
        link = Link(parent_bag_id=parent_bag_id, child_bag_id=child_bag.id)
        db.session.add(link)
    
    db.session.commit()
    
    # Update session data
    child_bags_scanned.append(qr_code)
    session['child_bags_scanned'] = child_bags_scanned
    
    # Get parent information
    parent_bag = Bag.query.get(parent_bag_id)
    
    # Calculate expected child count from parent QR
    try:
        expected_child_count = int(parent_bag.qr_id.split('-')[1])
    except:
        expected_child_count = 5  # Default
    
    # Check if all expected child bags are scanned
    all_scanned = len(child_bags_scanned) >= expected_child_count
    
    return jsonify({
        'success': True,
        'child_id': child_bag.id,
        'child_qr': child_bag.qr_id,
        'scanned_count': len(child_bags_scanned),
        'expected_count': expected_child_count,
        'all_scanned': all_scanned,
        'message': f'Child bag {qr_code} linked to parent successfully.'
    })

@app.route('/scan_complete')
@login_required
def scan_complete():
    """Completion page for scanning workflow"""
    # Clear scanning session data
    parent_bag_id = session.pop('current_parent_bag_id', None)
    child_bags = session.pop('child_bags_scanned', [])
    
    if not parent_bag_id:
        flash('No scanning session found.', 'warning')
        return redirect(url_for('index'))
    
    # Get parent and child bag info for display
    parent_bag = Bag.query.get(parent_bag_id)
    child_bags_info = []
    
    for child_id in child_bags:
        # Get the child bag by its ID (numeric) not by its QR code (string)
        try:
            # Ensure we're querying with a numeric ID
            if isinstance(child_id, str) and not child_id.isdigit():
                # If it's a QR code, find the bag by QR code instead
                child_bag = Bag.query.filter_by(qr_id=child_id).first()
            else:
                child_bag = Bag.query.get(child_id)
                
            if child_bag:
                child_bags_info.append(child_bag)
        except Exception as e:
            app.logger.error(f"Error retrieving child bag {child_id}: {str(e)}")
            
    return render_template('scan_complete.html', 
                          parent_bag=parent_bag,
                          child_bags=child_bags_info,
                          scan_count=len(child_bags_info))

@app.route('/finish_scanning')
@login_required
def finish_scanning():
    """Complete the scanning process"""
    if 'current_parent_bag_id' not in session:
        flash('No parent bag was scanned', 'warning')
        return redirect(url_for('index'))
    
    parent_bag_id = session['current_parent_bag_id']
    parent_bag = Bag.query.get(parent_bag_id)
    
    if not parent_bag:
        flash('Parent bag not found', 'danger')
        return redirect(url_for('index'))
    
    child_bags_scanned = session.get('child_bags_scanned', [])
    
    # Clear scanning session
    session.pop('current_parent_bag_id', None)
    session.pop('child_bags_scanned', None)
    
    flash(f'Scanning completed. Parent bag {parent_bag.qr_id} linked to {len(child_bags_scanned)} child bags.', 'success')
    return redirect(url_for('index'))

# Workflow B: Bill Management
@app.route('/bill_management')
@login_required
def bill_management():
    """Bill management dashboard"""
    bills = Bill.query.order_by(Bill.created_at.desc()).all()
    return render_template('bill_management.html', bills=bills)

@app.route('/create_bill', methods=['GET', 'POST'])
@login_required
def create_bill():
    """Create a new bill"""
    if request.method == 'POST':
        bill_id = request.form.get('bill_id', '').strip()
        
        if not bill_id:
            flash('Bill ID is required', 'danger')
            return render_template('create_bill.html')
        
        # Check if bill_id already exists
        existing_bill = Bill.query.filter_by(bill_id=bill_id).first()
        if existing_bill:
            flash(f'Bill ID {bill_id} already exists', 'danger')
            return render_template('create_bill.html')
        
        # Create new bill
        bill = Bill(bill_id=bill_id)
        db.session.add(bill)
        db.session.commit()
        
        # Store bill in session for scanning parent bags
        session['current_bill_id'] = bill.id
        
        flash(f'Bill {bill_id} created successfully. Please scan parent bags to add to this bill.', 'success')
        return redirect(url_for('scan_bill_parent'))
    
    return render_template('create_bill.html')

@app.route('/scan_bill_parent')
@login_required
def scan_bill_parent():
    """Scan parent bags to add to bill"""
    # Ensure bill is selected
    if 'current_bill_id' not in session:
        flash('Please create or select a bill first', 'warning')
        return redirect(url_for('bill_management'))
    
    bill = Bill.query.get(session['current_bill_id'])
    
    # Get parent bags already linked to this bill
    linked_parent_bags = db.session.query(Bag).join(BillBag, Bag.id == BillBag.bag_id).filter(BillBag.bill_id == bill.id).all()
    
    return render_template('scan_bill_parent.html', 
                           bill=bill,
                           linked_parent_bags=linked_parent_bags)

@app.route('/process_bill_parent_scan', methods=['POST'])
@login_required
def process_bill_parent_scan():
    """Process a parent bag scan for bill linking"""
    if 'current_bill_id' not in session:
        return jsonify({'success': False, 'message': 'No bill selected'})
    
    qr_code = request.form.get('qr_code')
    if not qr_code:
        return jsonify({'success': False, 'message': 'No QR code provided'})
    
    # Clean up the QR code
    qr_code = qr_code.strip()
    
    # Validate the QR code using the improved validator that handles any format
    is_valid, message, child_count = validate_parent_qr_id(qr_code)
    if not is_valid:
        return jsonify({'success': False, 'message': message})
    
    # Look up or create the parent bag
    parent_bag = Bag.query.filter_by(qr_id=qr_code, type=BagType.PARENT.value).first()
    
    if not parent_bag:
        # Create new parent bag
        parent_bag = Bag(qr_id=qr_code, type=BagType.PARENT.value)
        db.session.add(parent_bag)
        db.session.commit()
    
    # Link parent bag to bill
    bill_id = session['current_bill_id']
    bill = Bill.query.get(bill_id)
    
    # Check if already linked
    existing_link = BillBag.query.filter_by(bill_id=bill_id, bag_id=parent_bag.id).first()
    if existing_link:
        return jsonify({
            'success': False,
            'message': f'Parent bag {qr_code} already linked to bill {bill.bill_id}'
        })
    
    # Create new link
    bill_bag = BillBag(bill_id=bill_id, bag_id=parent_bag.id)
    db.session.add(bill_bag)
    db.session.commit()
    
    # Get updated count of linked bags
    linked_count = BillBag.query.filter_by(bill_id=bill_id).count()
    
    return jsonify({
        'success': True,
        'parent_id': parent_bag.id,
        'parent_qr': parent_bag.qr_id,
        'bill_id': bill.bill_id,
        'linked_count': linked_count,
        'message': f'Parent bag {qr_code} linked to bill {bill.bill_id} successfully'
    })

@app.route('/remove_bag_from_bill', methods=['POST'])
@login_required
def remove_bag_from_bill():
    """Remove a parent bag from a bill"""
    parent_qr = request.form.get('parent_qr')
    bill_id = request.form.get('bill_id')
    
    if not parent_qr or not bill_id:
        return jsonify({
            'success': False,
            'message': 'Missing parent_qr or bill_id'
        })
    
    # Get bill and parent bag
    bill = Bill.query.get(bill_id)
    parent_bag = Bag.query.filter_by(qr_id=parent_qr).first()
    
    if not bill or not parent_bag:
        return jsonify({
            'success': False,
            'message': 'Bill or parent bag not found'
        })
    
    # Find and remove the link
    bill_bag = BillBag.query.filter_by(bill_id=bill.id, bag_id=parent_bag.id).first()
    
    if bill_bag:
        db.session.delete(bill_bag)
        db.session.commit()
        
        # Get updated count
        parent_count = BillBag.query.filter_by(bill_id=bill.id).count()
        
        return jsonify({
            'success': True,
            'parent_count': parent_count,
            'message': f'Parent bag {parent_qr} removed from bill {bill.bill_id}'
        })
    else:
        return jsonify({
            'success': False,
            'message': f'Parent bag {parent_qr} not linked to bill {bill.bill_id}'
        })

@app.route('/finish_bill')
@login_required
def finish_bill():
    """Complete the bill creation process"""
    if 'current_bill_id' not in session:
        flash('No bill was selected', 'warning')
        return redirect(url_for('bill_management'))
    
    bill_id = session['current_bill_id']
    bill = Bill.query.get(bill_id)
    
    if not bill:
        flash('Bill not found', 'danger')
        return redirect(url_for('bill_management'))
    
    # Get count of linked parent bags
    linked_count = BillBag.query.filter_by(bill_id=bill_id).count()
    
    # Clear bill session
    session.pop('current_bill_id', None)
    
    flash(f'Bill {bill.bill_id} finalized with {linked_count} parent bags linked.', 'success')
    return redirect(url_for('bill_management'))

# Workflow C: Child Bag Lookup
@app.route('/child_lookup', methods=['GET', 'POST'])
@login_required
def child_lookup():
    """Look up parent bag and bill from child bag QR code"""
    if request.method == 'POST':
        qr_code = request.form.get('qr_code', '').strip()
        
        if not qr_code:
            flash('Please enter a child bag QR code', 'warning')
            return render_template('child_lookup.html')
        
        # Accept any QR code format - no validation required
        qr_code = qr_code.strip()
        
        # Look up the child bag
        child_bag = Bag.query.filter_by(qr_id=qr_code, type=BagType.CHILD.value).first()
        
        if not child_bag:
            flash(f'Child bag {qr_code} not found', 'danger')
            return render_template('child_lookup.html')
        
        # Find linked parent bag
        link = Link.query.filter_by(child_bag_id=child_bag.id).first()
        
        if not link:
            flash(f'Child bag {qr_code} is not linked to any parent bag', 'warning')
            return render_template('child_lookup.html', child_bag=child_bag)
        
        # Get parent bag
        parent_bag = Bag.query.get(link.parent_bag_id)
        
        # Find bill linked to parent bag
        bill_bag = BillBag.query.filter_by(bag_id=parent_bag.id).first()
        bill = Bill.query.get(bill_bag.bill_id) if bill_bag else None
        
        # Get scan history
        child_scans = Scan.query.filter_by(child_bag_id=child_bag.id).order_by(Scan.timestamp.desc()).all()
        
        return render_template('child_lookup_result.html',
                              child_bag=child_bag,
                              parent_bag=parent_bag,
                              bill=bill,
                              child_scans=child_scans)
    
    return render_template('child_lookup.html')