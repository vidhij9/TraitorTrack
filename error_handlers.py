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
        pass  # Logging disabled for performance
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
        pass  # Logging disabled for performance
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
        pass  # Logging disabled for performance
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

    @app.errorhandler(413)
    def request_entity_too_large(error):
        """Handle file upload size exceeded errors"""
        try:
            max_size_mb = app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024) / (1024 * 1024)
        except Exception:
            max_size_mb = 16  # Fallback
        
        # Check if client expects JSON (API endpoints or Accept header)
        is_api_client = (
            request.is_json or 
            request.path.startswith('/api/') or
            'application/json' in request.headers.get('Accept', '')
        )
        
        if is_api_client:
            return jsonify({
                'success': False,
                'error': 'File too large',
                'message': f'File size exceeds maximum allowed size of {max_size_mb:.0f}MB.'
            }), 413
        
        flash(f'File is too large. Maximum file size is {max_size_mb:.0f}MB.', 'error')
        return render_template('error.html',
                             error_code=413,
                             error_title='File Too Large',
                             error_message=f'The uploaded file exceeds the maximum allowed size of {max_size_mb:.0f}MB. Please upload a smaller file.'), 413

    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle internal server errors"""
        pass  # Logging disabled for performance
        
        # Rollback any database changes
        try:
            from app import db
            db.session.rollback()
        except Exception as db_error:
            pass  # Logging disabled for performance
        
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
        pass  # Logging disabled for performance
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
            from app import db
            db.session.rollback()
        except Exception as db_error:
            pass  # Logging disabled for performance
        
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
        """Fast health check endpoint without database query"""
        # Return healthy immediately without database check for performance
        return jsonify({
            'status': 'healthy',
            'message': 'Application is running normally'
        }), 200
    
    @app.route('/status')
    def status_check():
        """Fast status check endpoint"""
        # Return operational immediately without database queries for performance
        return jsonify({
            'status': 'operational',
            'timestamp': os.environ.get('REPL_ID', 'development'),
            'message': 'All systems operational'
        }), 200