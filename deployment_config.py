"""
Deployment configuration for TraceTrack application.
Ensures proper configuration for production deployment.
"""

import os
import logging
from logging.handlers import RotatingFileHandler

def configure_for_deployment(app):
    """Configure the application for production deployment"""
    
    # Production logging configuration
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Configure file handler for application logs
        file_handler = RotatingFileHandler('logs/tracetrack.log', 
                                         maxBytes=10240000, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('TraceTrack application startup')
    
    # Environment-specific configurations
    if os.environ.get('REPLIT_DEPLOYMENT') == '1':
        # Replit deployment specific settings
        app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_DOMAIN=os.environ.get('REPLIT_DEV_DOMAIN'),
            PREFERRED_URL_SCHEME='https',
            WTF_CSRF_SSL_STRICT=True,  # Enable strict CSRF for production
            WTF_CSRF_TIME_LIMIT=7200,  # 2 hours CSRF token validity
        )
        app.logger.info('Configured for Replit deployment')
    else:
        # Development settings
        app.config.update(
            WTF_CSRF_SSL_STRICT=False,
            WTF_CSRF_TIME_LIMIT=None,
        )
    
    # Database optimization for production
    app.config['SQLALCHEMY_ENGINE_OPTIONS'].update({
        'pool_size': 20,
        'max_overflow': 30,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'pool_timeout': 20
    })
    
    # Security headers for production
    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        if app.config.get('PREFERRED_URL_SCHEME') == 'https':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    return app

def get_environment_config():
    """Get environment-specific configuration"""
    config = {
        'database_url': os.environ.get('DATABASE_URL'),
        'secret_key': os.environ.get('SESSION_SECRET'),
        'debug': os.environ.get('FLASK_DEBUG', '0') == '1',
        'port': int(os.environ.get('PORT', 5000)),
        'host': os.environ.get('HOST', '0.0.0.0')
    }
    
    # Validate required environment variables
    required_vars = ['DATABASE_URL', 'SESSION_SECRET']
    missing_vars = [var for var in required_vars if not config.get(var.lower().replace('_', ''))]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    return config

def setup_monitoring_alerts(app):
    """Setup basic monitoring and alerting"""
    
    @app.route('/deployment-status')
    def deployment_status():
        """Deployment status endpoint for monitoring"""
        try:
            from app_clean import db
            from models import User, Bag, Scan
            from sqlalchemy import text
            
            # Check database connectivity
            db.session.execute(text('SELECT 1'))
            
            # Get basic metrics
            user_count = User.query.count()
            bag_count = Bag.query.count()
            scan_count = Scan.query.count()
            
            return {
                'status': 'healthy',
                'database': 'connected',
                'environment': os.environ.get('REPLIT_DEPLOYMENT', 'development'),
                'metrics': {
                    'users': user_count,
                    'bags': bag_count,
                    'scans': scan_count
                }
            }
        except Exception as e:
            app.logger.error(f"Deployment status check failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }, 500