from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from models import User, Bag, Link, Scan, Bill, BillBag, PromotionRequest, UserRole, BagType, PromotionRequestStatus
from app import db
from sqlalchemy import desc, func, and_, or_
from datetime import datetime, timedelta
import csv
import io
import logging
import re
import html

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

def sanitize_input(text, max_length=500):
    """Sanitize user input to prevent XSS and limit length"""
    if not text:
        return ""
    # HTML escape the input
    sanitized = html.escape(str(text).strip())
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized

def validate_qr_format(qr_id):
    """Validate QR ID format"""
    if not qr_id:
        return False, "QR ID is required"
    # Allow alphanumeric characters and hyphens
    if not re.match(r'^[A-Za-z0-9-]+$', qr_id):
        return False, "QR ID contains invalid characters"
    if len(qr_id) > 50:
        return False, "QR ID is too long"
    return True, ""

@main_bp.route('/')
@login_required
def index():
    """Dashboard home page"""
    # Get recent activity stats
    recent_scans = Scan.query.order_by(Scan.timestamp.desc()).limit(10).all()
    total_parent_bags = Bag.query.filter_by(type=BagType.PARENT.value).count()
    total_child_bags = Bag.query.filter_by(type=BagType.CHILD.value).count()
    total_scans = Scan.query.count()
    
    # Get today's activity
    today = datetime.utcnow().date()
    today_scans = Scan.query.filter(
        func.date(Scan.timestamp) == today
    ).count()
    
    return render_template('dashboard.html',
                         recent_scans=recent_scans,
                         total_parent_bags=total_parent_bags,
                         total_child_bags=total_child_bags,
                         total_scans=total_scans,
                         today_scans=today_scans)

@main_bp.route('/scan_parent', methods=['GET', 'POST'])
@login_required
def scan_parent():
    """Scan parent bag"""
    if request.method == 'POST':
        qr_id = request.form.get('qr_id', '').strip()
        child_count = request.form.get('child_count', type=int)
        notes = request.form.get('notes', '').strip()
        
        # Validate and sanitize inputs
        is_valid, error_msg = validate_qr_format(qr_id)
        if not is_valid:
            flash(error_msg, 'error')
            return render_template('scan_parent.html')
        
        # Sanitize notes to prevent XSS
        notes = sanitize_input(notes, max_length=1000)
        
        # Check if parent bag already exists
        parent_bag = Bag.query.filter_by(qr_id=qr_id).first()
        
        if not parent_bag:
            # Create new parent bag
            parent_bag = Bag(
                qr_id=qr_id,
                type=BagType.PARENT.value,
                child_count=child_count or 0
            )
            db.session.add(parent_bag)
            db.session.flush()  # Get the ID
        
        # Create scan record
        scan = Scan(
            parent_bag_id=parent_bag.id,
            user_id=current_user.id,
            notes=notes
        )
        db.session.add(scan)
        
        try:
            db.session.commit()
            flash(f'Parent bag {qr_id} scanned successfully!', 'success')
            logger.info(f"Parent bag {qr_id} scanned by {current_user.username}")
            return redirect(url_for('main.scan_parent'))
        except Exception as e:
            db.session.rollback()
            flash('Error scanning parent bag. Please try again.', 'error')
            logger.error(f"Error scanning parent bag: {str(e)}")
    
    return render_template('scan_parent.html')

@main_bp.route('/scan_child', methods=['GET', 'POST'])
@login_required
def scan_child():
    """Scan child bag"""
    if request.method == 'POST':
        parent_qr_id = request.form.get('parent_qr_id', '').strip()
        child_qr_id = request.form.get('child_qr_id', '').strip()
        notes = request.form.get('notes', '').strip()
        
        # Validate and sanitize inputs
        is_valid_parent, error_msg = validate_qr_format(parent_qr_id)
        if not is_valid_parent:
            flash(f"Parent QR ID error: {error_msg}", 'error')
            return render_template('scan_child.html')
        
        is_valid_child, error_msg = validate_qr_format(child_qr_id)
        if not is_valid_child:
            flash(f"Child QR ID error: {error_msg}", 'error')
            return render_template('scan_child.html')
        
        # Sanitize notes to prevent XSS
        notes = sanitize_input(notes, max_length=1000)
        
        # Find parent bag
        parent_bag = Bag.query.filter_by(qr_id=parent_qr_id, type=BagType.PARENT.value).first()
        if not parent_bag:
            flash('Parent bag not found. Please scan the parent bag first.', 'error')
            return render_template('scan_child.html')
        
        # Check if child bag already exists
        child_bag = Bag.query.filter_by(qr_id=child_qr_id).first()
        
        if not child_bag:
            # Create new child bag
            child_bag = Bag(
                qr_id=child_qr_id,
                type=BagType.CHILD.value,
                parent_id=parent_bag.id
            )
            db.session.add(child_bag)
            db.session.flush()  # Get the ID
        
        # Create or update link
        link = Link.query.filter_by(parent_bag_id=parent_bag.id, child_bag_id=child_bag.id).first()
        if not link:
            link = Link(
                parent_bag_id=parent_bag.id,
                child_bag_id=child_bag.id,
                linked_by=current_user.id
            )
            db.session.add(link)
        
        # Create scan record
        scan = Scan(
            parent_bag_id=parent_bag.id,
            child_bag_id=child_bag.id,
            user_id=current_user.id,
            notes=notes
        )
        db.session.add(scan)
        
        try:
            db.session.commit()
            flash(f'Child bag {child_qr_id} linked to parent {parent_qr_id} successfully!', 'success')
            logger.info(f"Child bag {child_qr_id} linked to parent {parent_qr_id} by {current_user.username}")
            return redirect(url_for('main.scan_child'))
        except Exception as e:
            db.session.rollback()
            flash('Error scanning child bag. Please try again.', 'error')
            logger.error(f"Error scanning child bag: {str(e)}")
    
    return render_template('scan_child.html')

@main_bp.route('/bags')
@login_required
def bags():
    """View all bags"""
    page = request.args.get('page', 1, type=int)
    bag_type = request.args.get('type', 'all')
    
    query = Bag.query
    if bag_type != 'all':
        query = query.filter_by(type=bag_type)
    
    bags = query.order_by(Bag.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('bags.html', bags=bags, bag_type=bag_type)

@main_bp.route('/bag/<int:bag_id>')
@login_required
def bag_detail(bag_id):
    """View bag details"""
    bag = Bag.query.get_or_404(bag_id)
    
    # Get scan history
    if bag.type == BagType.PARENT.value:
        scans = Scan.query.filter_by(parent_bag_id=bag.id).order_by(Scan.timestamp.desc()).all()
        # Get linked child bags
        links = Link.query.filter_by(parent_bag_id=bag.id).all()
        child_bags = [link.child_bag for link in links]
    else:
        scans = Scan.query.filter_by(child_bag_id=bag.id).order_by(Scan.timestamp.desc()).all()
        child_bags = []
    
    return render_template('bag_detail.html', bag=bag, scans=scans, child_bags=child_bags)

@main_bp.route('/scans')
@login_required
def scans():
    """View scan history"""
    page = request.args.get('page', 1, type=int)
    
    scans = Scan.query.order_by(Scan.timestamp.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('scans.html', scans=scans)

@main_bp.route('/bills', methods=['GET', 'POST'])
@login_required
def bills():
    """Manage bills"""
    if request.method == 'POST':
        bill_id = request.form.get('bill_id', '').strip()
        bag_qr_ids = request.form.get('bag_qr_ids', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not bill_id:
            flash('Bill ID is required.', 'error')
            return render_template('bills.html')
        
        # Check if bill already exists
        existing_bill = Bill.query.filter_by(bill_id=bill_id).first()
        if existing_bill:
            flash('Bill ID already exists.', 'error')
            return render_template('bills.html')
        
        # Create new bill
        bill = Bill(
            bill_id=bill_id,
            created_by=current_user.id,
            notes=notes
        )
        db.session.add(bill)
        db.session.flush()  # Get the ID
        
        # Add bags to bill
        if bag_qr_ids:
            qr_ids = [qr.strip() for qr in bag_qr_ids.split(',') if qr.strip()]
            for qr_id in qr_ids:
                bag = Bag.query.filter_by(qr_id=qr_id).first()
                if bag:
                    bill_bag = BillBag(bill_id=bill.id, bag_id=bag.id)
                    db.session.add(bill_bag)
        
        try:
            db.session.commit()
            flash(f'Bill {bill_id} created successfully!', 'success')
            logger.info(f"Bill {bill_id} created by {current_user.username}")
        except Exception as e:
            db.session.rollback()
            flash('Error creating bill. Please try again.', 'error')
            logger.error(f"Error creating bill: {str(e)}")
    
    # Get all bills
    page = request.args.get('page', 1, type=int)
    bills = Bill.query.order_by(Bill.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('bills.html', bills=bills)

@main_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    user_scans = Scan.query.filter_by(user_id=current_user.id).order_by(Scan.timestamp.desc()).limit(10).all()
    total_scans = Scan.query.filter_by(user_id=current_user.id).count()
    
    return render_template('profile.html', user_scans=user_scans, total_scans=total_scans)

@main_bp.route('/admin/users')
@login_required
def admin_users():
    """Admin user management"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('main.index'))
    
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users)

@main_bp.route('/export/scans')
@login_required
def export_scans():
    """Export scan data as CSV"""
    if not current_user.is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('main.index'))
    
    # Create CSV data
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Scan ID', 'Parent Bag QR', 'Child Bag QR', 'User', 'Timestamp', 'Notes'])
    
    # Write data
    scans = Scan.query.order_by(Scan.timestamp.desc()).all()
    for scan in scans:
        writer.writerow([
            scan.id,
            scan.parent_bag.qr_id if scan.parent_bag else '',
            scan.child_bag.qr_id if scan.child_bag else '',
            scan.user.username,
            scan.timestamp.isoformat() if scan.timestamp else '',
            scan.notes or ''
        ])
    
    output.seek(0)
    
    # Create response
    response = send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'scans_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
    )
    
    return response