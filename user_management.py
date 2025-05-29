"""
User management system with role-based access control for TraceTrack.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import User, db
from forms import PromoteToAdminForm

user_bp = Blueprint('user_management', __name__)

def admin_required(f):
    """Decorator to restrict access to admin users only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def superuser_required(f):
    """Decorator to restrict access to superuser only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_superuser', False):
            flash('Superuser access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@user_bp.route('/users')
@admin_required
def manage_users():
    """User management dashboard for administrators."""
    users = User.query.all()
    return render_template('user_management.html', users=users)

@user_bp.route('/users/<int:user_id>/role', methods=['POST'])
@admin_required
def update_user_role():
    """Update user role (admin/employee)."""
    data = request.get_json()
    user_id = data.get('user_id')
    new_role = data.get('role')
    
    if new_role not in ['admin', 'employee']:
        return jsonify({'success': False, 'message': 'Invalid role'})
    
    user = User.query.get_or_404(user_id)
    user.is_admin = (new_role == 'admin')
    
    try:
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': f'User {user.username} role updated to {new_role}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@user_bp.route('/users/<int:user_id>/activate', methods=['POST'])
@admin_required
def toggle_user_status():
    """Activate or deactivate user account."""
    user = User.query.get_or_404(request.json.get('user_id'))
    user.is_active = not user.is_active
    
    try:
        db.session.commit()
        status = 'activated' if user.is_active else 'deactivated'
        return jsonify({
            'success': True,
            'message': f'User {user.username} {status}',
            'is_active': user.is_active
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@user_bp.route('/user/profile')
@login_required
def user_profile():
    """User profile page."""
    return render_template('user_profile.html', user=current_user)

@user_bp.route('/user/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information."""
    current_user.email = request.form.get('email', current_user.email)
    current_user.first_name = request.form.get('first_name', current_user.first_name)
    current_user.last_name = request.form.get('last_name', current_user.last_name)
    
    try:
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating profile.', 'danger')
    
    return redirect(url_for('user_management.user_profile'))

@user_bp.route('/permissions')
@admin_required
def manage_permissions():
    """Manage user permissions and access levels."""
    permissions = {
        'admin': {
            'description': 'Full system access',
            'capabilities': [
                'View all data',
                'Manage users',
                'Export reports',
                'System configuration',
                'Delete records'
            ]
        },
        'employee': {
            'description': 'Standard user access',
            'capabilities': [
                'Scan QR codes',
                'View assigned data',
                'Create bills',
                'Basic reporting'
            ]
        }
    }
    
    users_by_role = {
        'admin': User.query.filter_by(is_admin=True).all(),
        'employee': User.query.filter_by(is_admin=False).all()
    }
    
    return render_template('permissions.html', 
                         permissions=permissions, 
                         users_by_role=users_by_role)

@user_bp.route('/activity-log')
@admin_required
def activity_log():
    """View user activity log for security monitoring."""
    # This would integrate with the account_security.py module
    # to show login attempts, access patterns, etc.
    return render_template('activity_log.html')

@user_bp.route('/api/users/stats')
@admin_required
def user_statistics():
    """API endpoint for user statistics."""
    total_users = User.query.count()
    admin_count = User.query.filter_by(is_admin=True).count()
    active_users = User.query.filter_by(is_active=True).count() if hasattr(User, 'is_active') else total_users
    
    return jsonify({
        'total_users': total_users,
        'admin_count': admin_count,
        'employee_count': total_users - admin_count,
        'active_users': active_users,
        'inactive_users': total_users - active_users
    })