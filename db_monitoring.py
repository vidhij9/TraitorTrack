"""
Database monitoring and health check module for traitor track.
Provides routes and tools for monitoring database performance and health.
"""
import logging
import time
from functools import wraps
from flask import Blueprint, jsonify, request, render_template, current_app
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_required, current_user

from app import app, db
from database_utils import check_database_connection, get_connection_pool_stats

logger = logging.getLogger(__name__)

# Create a blueprint for database monitoring endpoints
bp = Blueprint('db_monitoring', __name__, url_prefix='/admin/db')

def admin_required(f):
    """Decorator to restrict access to admin users only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({
                'error': 'Administrator privileges required',
                'status': 'error'
            }), 403
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/health')
@login_required
@admin_required
def health_check():
    """Check database health and connection pool status"""
    start_time = time.time()
    
    try:
        # Check database connection
        is_connected, error_message = check_database_connection()
        
        # Get connection pool statistics
        pool_stats = get_connection_pool_stats()
        
        # Run a simple timing test
        from sqlalchemy import text
        timing_start = time.time()
        count_result = db.session.query(db.func.count('*')).select_from(text('information_schema.tables')).scalar()
        query_time = time.time() - timing_start
        
        response_time = time.time() - start_time
        
        return jsonify({
            'status': 'healthy' if is_connected else 'unhealthy',
            'connection': {
                'connected': is_connected,
                'error': error_message
            },
            'pool': pool_stats,
            'timing': {
                'query_time': round(query_time * 1000, 2),  # ms
                'response_time': round(response_time * 1000, 2)  # ms
            },
            'tables_count': count_result
        })
    except Exception as e:
        logger.exception(f"Error in database health check: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'response_time': round((time.time() - start_time) * 1000, 2)  # ms
        }), 500

@bp.route('/dashboard')
@login_required
@admin_required
def db_dashboard():
    """Database monitoring dashboard for administrators"""
    try:
        # Get database connection status
        is_connected, error_message = check_database_connection()
        
        # Get connection pool stats
        pool_stats = get_connection_pool_stats()
        
        # Get table counts
        from sqlalchemy import text
        table_counts = {
            'users': db.session.query(db.func.count('*')).select_from(text('users')).scalar(),
            'bags': db.session.query(db.func.count('*')).select_from(text('bag')).scalar(),
            'scans': db.session.query(db.func.count('*')).select_from(text('scan')).scalar(),
            'locations': db.session.query(db.func.count('*')).select_from(text('location')).scalar()
        }
        
        # Get recent slow queries (if logging is enabled)
        slow_queries = []
        
        return render_template('db_dashboard.html',
                              is_connected=is_connected,
                              error_message=error_message,
                              pool_stats=pool_stats,
                              table_counts=table_counts,
                              slow_queries=slow_queries)
    except Exception as e:
        logger.exception(f"Error in database dashboard: {str(e)}")
        return render_template('error.html',
                              error_type="Database Error",
                              error_message="Could not load database dashboard",
                              detailed_error=str(e),
                              is_database_error=True)

# Register the blueprint with the app
app.register_blueprint(bp)

# Add endpoint directly to app for easy health check
@app.route('/api/db/health')
def api_db_health():
    """Public API endpoint for basic DB health check"""
    try:
        is_connected, _ = check_database_connection()
        return jsonify({
            'status': 'ok' if is_connected else 'error',
            'timestamp': time.time()
        })
    except Exception as e:
        logger.exception(f"API DB health check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Database health check failed'
        }), 500
