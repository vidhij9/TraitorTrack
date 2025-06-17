"""
Enhanced error handling and alerting system for TraceTrack application.
Provides comprehensive error handling with user-friendly messages and logging.
"""

import logging
import traceback
from flask import render_template, request, jsonify, flash, redirect, url_for
from werkzeug.exceptions import HTTPException
import os

def setup_error_handlers(app):
    """Setup comprehensive error handlers for the application"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad request errors"""
        app.logger.warning(f"Bad request: {request.url} - {error}")
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Invalid request format',
                'message': 'Please check your request and try again.'
            }), 400
        flash('Invalid request. Please check your input and try again.', 'error')
        return render_template('error.html', 
                             error_code=400,
                             error_title='Bad Request',
                             error_message='The request could not be understood. Please check your input and try again.'), 400

    @app.errorhandler(403)
    def forbidden(error):
        """Handle forbidden access errors"""
        app.logger.warning(f"Forbidden access: {request.url} - User: {getattr(request, 'user', 'Unknown')}")
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Access forbidden',
                'message': 'You do not have permission to access this resource.'
            }), 403
        flash('Access denied. You do not have permission to view this page.', 'error')
        return render_template('error.html',
                             error_code=403,
                             error_title='Access Forbidden',
                             error_message='You do not have permission to access this resource.'), 403

    @app.errorhandler(404)
    def not_found(error):
        """Handle not found errors"""
        app.logger.info(f"Page not found: {request.url}")
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Resource not found',
                'message': 'The requested resource could not be found.'
            }), 404
        return render_template('error.html',
                             error_code=404,
                             error_title='Page Not Found',
                             error_message='The page you are looking for could not be found.'), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle internal server errors"""
        app.logger.error(f"Internal server error: {request.url} - {traceback.format_exc()}")
        
        # Rollback any database changes
        try:
            from app_clean import db
            db.session.rollback()
        except Exception as db_error:
            app.logger.error(f"Database rollback failed: {db_error}")
        
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'message': 'An unexpected error occurred. Please try again later.'
            }), 500
        
        flash('An unexpected error occurred. Please try again later.', 'error')
        return render_template('error.html',
                             error_code=500,
                             error_title='Server Error',
                             error_message='An unexpected error occurred. Our team has been notified.'), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        """Handle service unavailable errors"""
        app.logger.error(f"Service unavailable: {request.url} - {error}")
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Service unavailable',
                'message': 'The service is temporarily unavailable. Please try again later.'
            }), 503
        return render_template('error.html',
                             error_code=503,
                             error_title='Service Unavailable',
                             error_message='The service is temporarily unavailable. Please try again in a few minutes.'), 503

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle any unexpected errors"""
        app.logger.error(f"Unexpected error: {request.url} - {traceback.format_exc()}")
        
        # Rollback any database changes
        try:
            from app_clean import db
            db.session.rollback()
        except Exception as db_error:
            app.logger.error(f"Database rollback failed: {db_error}")
        
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Unexpected error',
                'message': 'An unexpected error occurred. Please try again later.'
            }), 500
        
        flash('An unexpected error occurred. Please try again later.', 'error')
        return render_template('error.html',
                             error_code=500,
                             error_title='Unexpected Error',
                             error_message='Something went wrong. Our team has been notified.'), 500

def setup_request_logging(app):
    """Setup request logging for monitoring"""
    
    @app.before_request
    def log_request_info():
        """Log request information for monitoring"""
        if not request.endpoint or request.endpoint.startswith('static'):
            return
        
        app.logger.info(f"Request: {request.method} {request.url} - IP: {request.remote_addr}")
    
    @app.after_request
    def log_response_info(response):
        """Log response information"""
        if not request.endpoint or request.endpoint.startswith('static'):
            return response
        
        if response.status_code >= 400:
            app.logger.warning(f"Response: {response.status_code} for {request.method} {request.url}")
        
        return response

def setup_health_monitoring(app):
    """Setup health monitoring endpoints"""
    
    @app.route('/health')
    def health_check():
        """Simple health check endpoint"""
        try:
            # Check database connection
            from app_clean import db
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            
            return jsonify({
                'status': 'healthy',
                'message': 'Application is running normally',
                'database': 'connected'
            }), 200
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'message': 'Database connection failed',
                'error': str(e)
            }), 503
    
    @app.route('/status')
    def status_check():
        """Detailed status check for monitoring"""
        try:
            from app_clean import db
            from models import User, Bag, Scan
            
            # Check database and get basic stats
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            user_count = User.query.count()
            bag_count = Bag.query.count()
            scan_count = Scan.query.count()
            
            return jsonify({
                'status': 'operational',
                'timestamp': os.environ.get('REPL_ID', 'development'),
                'database': 'connected',
                'stats': {
                    'users': user_count,
                    'bags': bag_count,
                    'scans': scan_count
                }
            }), 200
        except Exception as e:
            app.logger.error(f"Status check failed: {e}")
            return jsonify({
                'status': 'degraded',
                'error': str(e),
                'timestamp': os.environ.get('REPL_ID', 'development')
            }), 500
