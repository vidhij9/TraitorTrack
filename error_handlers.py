"""
Enhanced error handling and alerting system for TraitorTrack application.
Provides comprehensive error handling with user-friendly messages and logging.
"""

import logging
import traceback
from datetime import datetime
from flask import render_template, request, jsonify, flash, redirect, url_for
from werkzeug.exceptions import HTTPException
import os

def setup_error_handlers(app):
    """Setup comprehensive error handlers for the application with request ID tracking"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad request errors (including CSRF)"""
        from request_tracking import get_request_id
        from datetime import datetime
        
        request_id = get_request_id()
        
        # CSRF-specific handling
        if 'CSRF' in str(error) or 'csrf' in str(error.description or '').lower():
            if request.is_json or request.path.startswith('/api/') or request.path.startswith('/process_'):
                return jsonify({
                    'success': False,
                    'message': 'Security token expired. Please refresh the page and try again.',
                    'error_code': 400,
                    'request_id': request_id
                }), 400
        
        # Generic bad request handling
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Invalid request format',
                'message': 'Please check your request and try again.',
                'error_code': 400,
                'request_id': request_id
            }), 400
        
        flash('Invalid request. Please check your input and try again.', 'error')
        return render_template('error.html', 
                             error_code=400,
                             error_title='Bad Request',
                             error_message='The request could not be understood. Please check your input and try again.',
                             request_id=request_id,
                             timestamp=datetime.utcnow().isoformat()), 400

    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized errors"""
        from request_tracking import get_request_id
        from datetime import datetime
        
        request_id = get_request_id()
        app.logger.warning(f"[{request_id}] 401 Unauthorized: {request.path}")
        
        # If it's an AJAX/API request, return JSON
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'message': 'Authentication required. Please log in to continue.',
                'error_code': 401,
                'request_id': request_id
            }), 401
        
        # Render error page for web requests
        return render_template(
            'errors/401.html',
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat()
        ), 401

    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden errors"""
        from request_tracking import get_request_id
        from datetime import datetime
        
        request_id = get_request_id()
        app.logger.warning(f"[{request_id}] 403 Forbidden: {request.path}")
        
        # If it's an AJAX/API request, return JSON
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'message': 'Access forbidden. You do not have permission to access this resource.',
                'error_code': 403,
                'request_id': request_id
            }), 403
        
        # Render error page for web requests
        return render_template(
            'errors/403.html',
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat()
        ), 403

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors"""
        from request_tracking import get_request_id
        from datetime import datetime
        
        request_id = get_request_id()
        app.logger.info(f"[{request_id}] 404 Not Found: {request.path}")
        
        # If it's an AJAX/API request, return JSON
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'message': 'Resource not found.',
                'error_code': 404,
                'request_id': request_id
            }), 404
        
        # Render error page for web requests
        return render_template(
            'errors/404.html',
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat()
        ), 404

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
        """Handle 500 Internal Server errors"""
        from request_tracking import get_request_id
        from datetime import datetime
        
        request_id = get_request_id()
        app.logger.error(f"[{request_id}] 500 Internal Server Error: {request.path} - {str(error)}", exc_info=True)
        
        # Rollback any pending database transactions
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        
        # If it's an AJAX/API request, return JSON
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'message': 'An internal server error occurred. Please try again later.',
                'error_code': 500,
                'request_id': request_id
            }), 500
        
        # Render error page for web requests
        return render_template(
            'errors/500.html',
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat()
        ), 500

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
        app.logger.error(f"Unexpected error: {request.url} - {str(error)}", exc_info=True)
        
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
        """
        Comprehensive health check endpoint for production monitoring
        
        Query Parameters:
            check_db (bool): If 'true', performs database connectivity check
            check_redis (bool): If 'true', performs Redis connectivity check
            detailed (bool): If 'true', returns detailed system metrics
        
        Returns:
            200: All systems healthy
            503: One or more critical systems unhealthy
        """
        from flask import request
        import time
        
        # Parse query parameters
        check_db = request.args.get('check_db', 'false').lower() == 'true'
        check_redis = request.args.get('check_redis', 'false').lower() == 'true'
        detailed = request.args.get('detailed', 'false').lower() == 'true'
        
        is_production = os.environ.get('REPLIT_DEPLOYMENT') == '1' or os.environ.get('ENVIRONMENT') == 'production'
        
        response_data = {
            'status': 'healthy',
            'message': 'Application is running normally',
            'timestamp': datetime.now().isoformat(),
            'environment': 'production' if is_production else 'development'
        }
        
        # In production, always check critical services
        if is_production:
            check_db = True
            check_redis = True
        
        # Database connectivity check
        if check_db:
            try:
                from app import db
                from sqlalchemy import text
                
                start_time = time.time()
                result = db.session.execute(text("SELECT 1")).scalar()
                query_time_ms = (time.time() - start_time) * 1000
                
                if result == 1:
                    response_data['database'] = {
                        'connected': True,
                        'query_time_ms': round(query_time_ms, 2)
                    }
                    
                    # Add detailed database metrics if requested
                    if detailed:
                        pool = db.engine.pool
                        response_data['database']['pool'] = {
                            'size': pool.size(),
                            'checked_in': pool.checkedin(),
                            'overflow': pool.overflow(),
                            'checked_out': pool.checkedout()
                        }
                else:
                    response_data['status'] = 'unhealthy'
                    response_data['message'] = 'Database query returned unexpected result'
                    response_data['database'] = {'connected': False}
                    return jsonify(response_data), 503
                    
            except Exception as e:
                app.logger.error(f"Database health check failed: {str(e)}", exc_info=True)
                response_data['status'] = 'unhealthy'
                response_data['message'] = 'Database connection failed'
                response_data['database'] = {
                    'connected': False,
                    'error': str(e)
                }
                return jsonify(response_data), 503
        
        # Redis connectivity check
        if check_redis:
            try:
                from app import redis_client, redis_available
                
                if not redis_available or redis_client is None:
                    if is_production:
                        # Redis is critical in production
                        response_data['status'] = 'unhealthy'
                        response_data['message'] = 'Redis is unavailable (required in production)'
                        response_data['redis'] = {'connected': False}
                        return jsonify(response_data), 503
                    else:
                        # Redis is optional in development
                        response_data['redis'] = {
                            'connected': False,
                            'warning': 'Redis unavailable (acceptable in development)'
                        }
                else:
                    start_time = time.time()
                    redis_client.ping()
                    ping_time_ms = (time.time() - start_time) * 1000
                    
                    response_data['redis'] = {
                        'connected': True,
                        'ping_time_ms': round(ping_time_ms, 2)
                    }
                    
                    # Add detailed Redis metrics if requested
                    if detailed:
                        info = redis_client.info('stats')
                        response_data['redis']['stats'] = {
                            'total_connections': info.get('total_connections_received', 0),
                            'total_commands': info.get('total_commands_processed', 0),
                            'keyspace_hits': info.get('keyspace_hits', 0),
                            'keyspace_misses': info.get('keyspace_misses', 0)
                        }
                    
            except Exception as e:
                app.logger.error(f"Redis health check failed: {str(e)}", exc_info=True)
                if is_production:
                    response_data['status'] = 'unhealthy'
                    response_data['message'] = 'Redis connection failed (critical in production)'
                    response_data['redis'] = {
                        'connected': False,
                        'error': str(e)
                    }
                    return jsonify(response_data), 503
                else:
                    response_data['redis'] = {
                        'connected': False,
                        'warning': 'Redis connection failed (acceptable in development)',
                        'error': str(e)
                    }
        
        # Add system resource metrics if detailed
        if detailed:
            try:
                import psutil
                process = psutil.Process()
                
                response_data['system'] = {
                    'memory_mb': round(process.memory_info().rss / 1024 / 1024, 2),
                    'cpu_percent': process.cpu_percent(interval=0.1),
                    'open_files': len(process.open_files()),
                    'num_threads': process.num_threads()
                }
            except Exception as e:
                app.logger.warning(f"Failed to collect system metrics: {str(e)}")
        
        return jsonify(response_data), 200
    
    @app.route('/status')
    def status_check():
        """Fast status check endpoint"""
        # Return operational immediately without database queries for performance
        return jsonify({
            'status': 'operational',
            'timestamp': datetime.now().isoformat(),
            'environment': os.environ.get('REPL_ID', 'development'),
            'message': 'All systems operational'
        }), 200