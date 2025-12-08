"""
IPT (Inter Party Transfer) Routes

Handles return ticket management for dealers/distributors returning
unsold parent bags to C&F points.
"""

import datetime
import secrets
import logging
from functools import wraps
from flask import (
    Blueprint, render_template, redirect, url_for, flash, 
    request, jsonify
)
from auth_utils import require_auth, is_authenticated, get_user_id, get_user_role
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length

from app import db, csrf, limiter

logger = logging.getLogger(__name__)
from models import (
    ReturnTicket, ReturnTicketBag, BillReturnEvent, 
    ReturnTicketStatus, DispatchArea, Bill
)

ipt_bp = Blueprint('ipt', __name__, url_prefix='/ipt')


@ipt_bp.before_request
def log_ipt_request():
    """Debug logging for IPT requests"""
    logger.info(f"IPT request: path={request.path}, is_authenticated={is_authenticated()}, user={get_user_id() or 'anonymous'}")


def role_required(roles):
    """Decorator to require specific user roles.
    
    Must be used AFTER @require_auth decorator since it assumes
    the user is already authenticated.
    
    For AJAX/API endpoints (detected via Accept header or X-Requested-With),
    returns JSON 403 instead of HTML redirect.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = get_user_role()
            if user_role not in roles:
                is_ajax = (
                    request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                    'application/json' in request.headers.get('Accept', '') or
                    request.content_type == 'application/json' or
                    request.is_json
                )
                if is_ajax:
                    return jsonify({
                        "success": False,
                        "error_type": "forbidden",
                        "message": "You do not have permission to access this resource."
                    }), 403
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


CF_LOCATION_CHOICES = [
    ('', 'Select Location...'),
    ('lucknow', 'Lucknow'),
    ('indore', 'Indore'),
    ('jaipur', 'Jaipur'),
    ('hisar', 'Hisar'),
    ('sri_ganganagar', 'Sri Ganganagar'),
    ('sangaria', 'Sangaria'),
    ('bathinda', 'Bathinda'),
    ('raipur', 'Raipur'),
    ('ranchi', 'Ranchi'),
    ('akola', 'Akola'),
]


class CreateReturnTicketForm(FlaskForm):
    """Form for creating a new return ticket"""
    cf_location = SelectField(
        'C&F Location',
        choices=CF_LOCATION_CHOICES,
        validators=[DataRequired(message="Please select a C&F location")]
    )
    notes = TextAreaField(
        'Notes (Optional)',
        validators=[Length(max=500)]
    )
    submit = SubmitField('Create Return Ticket')


class EditReturnTicketForm(FlaskForm):
    """Form for editing an existing return ticket"""
    cf_location = SelectField(
        'C&F Location',
        choices=CF_LOCATION_CHOICES,
        validators=[DataRequired(message="Please select a C&F location")]
    )
    notes = TextAreaField(
        'Notes (Optional)',
        validators=[Length(max=500)]
    )
    submit = SubmitField('Save Changes')


def generate_ticket_code():
    """Generate unique ticket code like RTN-20251207-XXXX"""
    date_part = datetime.datetime.utcnow().strftime('%Y%m%d')
    random_part = secrets.token_hex(2).upper()
    return f"RTN-{date_part}-{random_part}"


@ipt_bp.route('/')
@require_auth
@role_required(['admin', 'biller'])
def ipt_dashboard():
    """IPT dashboard - list return tickets"""
    logger.info(f"IPT dashboard accessed by user {get_user_id()} with role {get_user_role()}")
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = ReturnTicket.query
    
    if status_filter:
        query = query.filter(ReturnTicket.status == status_filter)
    
    tickets = query.order_by(ReturnTicket.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template(
        'ipt/dashboard.html',
        tickets=tickets,
        status_filter=status_filter
    )


@ipt_bp.route('/create', methods=['GET', 'POST'])
@require_auth
@role_required(['admin', 'biller'])
def create_ticket():
    """Create a new return ticket"""
    form = CreateReturnTicketForm()
    
    if form.validate_on_submit():
        ticket = ReturnTicket()
        ticket.ticket_code = generate_ticket_code()
        ticket.cf_location = form.cf_location.data
        ticket.notes = form.notes.data
        ticket.created_by_id = get_user_id()
        ticket.status = ReturnTicketStatus.OPEN.value
        db.session.add(ticket)
        db.session.commit()
        
        flash(f'Return ticket {ticket.ticket_code} created successfully!', 'success')
        return redirect(url_for('ipt.scan_returns', ticket_id=ticket.id))
    
    return render_template('ipt/create_ticket.html', form=form)


@ipt_bp.route('/scan/<int:ticket_id>', methods=['GET'])
@require_auth
@role_required(['admin', 'biller'])
def scan_returns(ticket_id):
    """Scanning page for return ticket"""
    ticket = ReturnTicket.query.get_or_404(ticket_id)
    
    if ticket.status != ReturnTicketStatus.OPEN.value:
        flash(f'Ticket is {ticket.status}. Cannot scan bags.', 'warning')
        return redirect(url_for('ipt.view_ticket', ticket_id=ticket_id))
    
    returned_bags = ReturnTicketBag.query.filter_by(
        return_ticket_id=ticket_id
    ).order_by(ReturnTicketBag.scanned_at.desc()).limit(50).all()
    
    return render_template(
        'ipt/scan_returns.html',
        ticket=ticket,
        returned_bags=returned_bags
    )


@ipt_bp.route('/scan/<int:ticket_id>/process', methods=['POST'])
@require_auth
@role_required(['admin', 'biller'])
@limiter.limit("60 per minute")
def process_scan(ticket_id):
    """Process a bag scan for return ticket (AJAX endpoint)"""
    from query_optimizer import query_optimizer
    
    ticket = ReturnTicket.query.get(ticket_id)
    if not ticket:
        return jsonify({"success": False, "error_type": "not_found", "message": "Ticket not found"}), 404
    
    qr_code = request.form.get('qr_code', '').strip()
    
    if not qr_code:
        return jsonify({"success": False, "error_type": "invalid_input", "message": "QR code is required"}), 400
    
    result = query_optimizer.ultra_fast_ipt_return_scan(
        ticket_id=ticket_id,
        qr_code=qr_code,
        user_id=get_user_id()
    )
    
    if result['success']:
        return jsonify(result), 200
    else:
        status_code = 400
        if result['error_type'] == 'ticket_not_found':
            status_code = 404
        elif result['error_type'] == 'ticket_closed':
            status_code = 403
        return jsonify(result), status_code


@ipt_bp.route('/ticket/<int:ticket_id>')
@require_auth
@role_required(['admin', 'biller'])
def view_ticket(ticket_id):
    """View return ticket details"""
    ticket = ReturnTicket.query.get_or_404(ticket_id)
    
    returned_bags = ReturnTicketBag.query.filter_by(
        return_ticket_id=ticket_id
    ).order_by(ReturnTicketBag.scanned_at.desc()).all()
    
    return render_template(
        'ipt/view_ticket.html',
        ticket=ticket,
        returned_bags=returned_bags
    )


@ipt_bp.route('/ticket/<int:ticket_id>/edit', methods=['GET', 'POST'])
@require_auth
@role_required(['admin', 'biller'])
def edit_ticket(ticket_id):
    """Edit an existing return ticket (only open tickets can be edited)"""
    ticket = ReturnTicket.query.get_or_404(ticket_id)
    
    if ticket.status != ReturnTicketStatus.OPEN.value:
        flash(f'Cannot edit a {ticket.status} ticket. Only open tickets can be edited.', 'warning')
        return redirect(url_for('ipt.view_ticket', ticket_id=ticket_id))
    
    form = EditReturnTicketForm(obj=ticket)
    
    if form.validate_on_submit():
        ticket.cf_location = form.cf_location.data
        ticket.notes = form.notes.data
        ticket.updated_at = datetime.datetime.utcnow()
        db.session.commit()
        
        flash(f'Ticket {ticket.ticket_code} updated successfully!', 'success')
        return redirect(url_for('ipt.view_ticket', ticket_id=ticket_id))
    
    return render_template('ipt/edit_ticket.html', form=form, ticket=ticket)


@ipt_bp.route('/ticket/<int:ticket_id>/finalize', methods=['POST'])
@require_auth
@role_required(['admin', 'biller'])
def finalize_ticket(ticket_id):
    """Finalize (commit) a return ticket"""
    ticket = ReturnTicket.query.get_or_404(ticket_id)
    
    if ticket.status != ReturnTicketStatus.OPEN.value:
        flash(f'Ticket is already {ticket.status}.', 'warning')
        return redirect(url_for('ipt.view_ticket', ticket_id=ticket_id))
    
    if ticket.bags_scanned_count == 0:
        flash('Cannot finalize an empty ticket. Scan at least one bag.', 'error')
        return redirect(url_for('ipt.scan_returns', ticket_id=ticket_id))
    
    ticket.status = ReturnTicketStatus.COMMITTED.value
    ticket.finalized_at = datetime.datetime.utcnow()
    db.session.commit()
    
    flash(f'Ticket {ticket.ticket_code} finalized with {ticket.bags_scanned_count} bags returned.', 'success')
    return redirect(url_for('ipt.view_ticket', ticket_id=ticket_id))


@ipt_bp.route('/ticket/<int:ticket_id>/cancel', methods=['POST'])
@require_auth
@role_required(['admin', 'biller'])
def cancel_ticket(ticket_id):
    """Cancel a return ticket (does NOT restore bags to bills)"""
    ticket = ReturnTicket.query.get_or_404(ticket_id)
    
    if ticket.status != ReturnTicketStatus.OPEN.value:
        flash(f'Ticket is already {ticket.status}.', 'warning')
        return redirect(url_for('ipt.view_ticket', ticket_id=ticket_id))
    
    if ticket.bags_scanned_count > 0:
        flash(
            f'Warning: {ticket.bags_scanned_count} bags have already been removed from their bills. '
            'They will remain unlinked and can be assigned to new bills.',
            'warning'
        )
    
    ticket.status = ReturnTicketStatus.CANCELLED.value
    ticket.finalized_at = datetime.datetime.utcnow()
    db.session.commit()
    
    flash(f'Ticket {ticket.ticket_code} cancelled.', 'info')
    return redirect(url_for('ipt.ipt_dashboard'))


@ipt_bp.route('/ticket/<int:ticket_id>/bags')
@require_auth
@role_required(['admin', 'biller'])
def ticket_bags_json(ticket_id):
    """Get list of returned bags for a ticket (JSON for AJAX updates)"""
    returned_bags = ReturnTicketBag.query.filter_by(
        return_ticket_id=ticket_id
    ).order_by(ReturnTicketBag.scanned_at.desc()).limit(100).all()
    
    bags_data = []
    for rtb in returned_bags:
        bags_data.append({
            'bag_qr': rtb.bag.qr_id if rtb.bag else 'Unknown',
            'original_bill_id': rtb.original_bill.bill_id if rtb.original_bill else 'None',
            'child_count': rtb.child_count_at_return,
            'scanned_at': rtb.scanned_at.strftime('%H:%M:%S') if rtb.scanned_at else ''
        })
    
    return jsonify({
        'bags': bags_data,
        'count': len(bags_data)
    })
