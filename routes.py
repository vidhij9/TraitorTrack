import logging
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app import app, db
from models import User, Product, Location, Scan

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Home page"""
    # Get some recent scan statistics for display
    recent_scans = Scan.query.order_by(Scan.timestamp.desc()).limit(5).all()
    total_products = Product.query.count()
    total_scans = Scan.query.count()
    total_locations = Location.query.count()
    
    return render_template('index.html', 
                          recent_scans=recent_scans,
                          total_products=total_products,
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
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
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
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard for visualizing tracking data"""
    return render_template('dashboard.html')

@app.route('/scan')
@login_required
def scan():
    """QR code scanning page"""
    # Get all available locations for the scan form
    locations = Location.query.all()
    return render_template('scan.html', locations=locations)

@app.route('/log_scan', methods=['POST'])
@login_required
def log_scan():
    """Process a product scan"""
    if request.method == 'POST':
        qr_id = request.form.get('qr_id')
        location_id = request.form.get('location_id')
        status = request.form.get('status')
        notes = request.form.get('notes')
        
        logger.debug(f"Processing scan for QR ID: {qr_id} at location: {location_id}")
        
        # Validate input
        if not qr_id or not location_id or not status:
            flash('QR code, location, and status are required!', 'danger')
            return redirect(url_for('scan'))
        
        # Check if product exists
        product = Product.query.filter_by(qr_id=qr_id).first()
        
        if not product:
            # Create new product if it doesn't exist
            product = Product(
                qr_id=qr_id,
                name=f"Product {qr_id}",  # Default name
                description="Newly scanned product"
            )
            db.session.add(product)
            db.session.commit()
            logger.debug(f"Created new product with QR ID: {qr_id}")
        
        # Create the scan record
        try:
            scan = Scan(
                product_id=product.id,
                user_id=current_user.id,
                location_id=location_id,
                status=status,
                notes=notes
            )
            
            db.session.add(scan)
            db.session.commit()
            
            flash('Scan recorded successfully!', 'success')
            return redirect(url_for('product_detail', qr_id=qr_id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error recording scan: {str(e)}")
            flash(f'Error recording scan: {str(e)}', 'danger')
            return redirect(url_for('scan'))
    
    return redirect(url_for('scan'))

@app.route('/product/<qr_id>')
def product_detail(qr_id):
    """Product detail page showing scan history"""
    product = Product.query.filter_by(qr_id=qr_id).first_or_404()
    
    # Get scan history for this product, ordered by timestamp
    scans = Scan.query.filter_by(product_id=product.id).order_by(Scan.timestamp.desc()).all()
    
    return render_template('product_detail.html', product=product, scans=scans)

@app.route('/locations')
@login_required
def locations():
    """List of locations"""
    locations = Location.query.all()
    return render_template('locations.html', locations=locations)

@app.context_processor
def utility_processor():
    """Utility functions available in templates"""
    def format_datetime(dt):
        if dt:
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return ''
    
    return dict(format_datetime=format_datetime)
