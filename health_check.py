"""
Comprehensive Health Check System
Provides detailed component-level health monitoring for TraitorTrack
"""

import logging
from datetime import datetime
from typing import Dict, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealthChecker:
    """Performs detailed component-level health checks"""
    
    def __init__(self, app, db):
        """
        Initialize health checker
        
        Args:
            app: Flask application instance
            db: SQLAlchemy database instance
        """
        self.app = app
        self.db = db
    
    def check_database(self) -> Tuple[HealthStatus, Dict[str, Any]]:
        """
        Check database connectivity and performance
        
        Returns:
            (status, details) tuple
        """
        try:
            from sqlalchemy import text
            import time
            
            # Test query execution time
            start_time = time.time()
            result = self.db.session.execute(text("SELECT 1")).scalar()
            query_time_ms = (time.time() - start_time) * 1000
            
            # Check pool health
            pool = self.db.engine.pool
            pool_size = pool.size()
            checked_out = pool.checkedout()
            usage_percent = (checked_out / pool_size * 100) if pool_size > 0 else 0
            
            # Determine status based on metrics
            if result == 1 and query_time_ms < 100 and usage_percent < 80:
                status = HealthStatus.HEALTHY
            elif result == 1 and query_time_ms < 500 and usage_percent < 95:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
            
            details = {
                'connected': True,
                'query_time_ms': round(query_time_ms, 2),
                'pool': {
                    'size': pool_size,
                    'checked_out': checked_out,
                    'usage_percent': round(usage_percent, 2)
                },
                'message': 'Database operational'
            }
            
            return status, details
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return HealthStatus.UNHEALTHY, {
                'connected': False,
                'error': str(e),
                'message': 'Database connection failed'
            }
    
    def check_cache(self) -> Tuple[HealthStatus, Dict[str, Any]]:
        """
        Check cache system health
        
        Returns:
            (status, details) tuple
        """
        try:
            from cache_utils import get_cache_stats
            
            cache_stats = get_cache_stats()
            
            # Parse hit rate
            hit_rate_str = cache_stats.get('hit_rate', '0%')
            hit_rate = float(hit_rate_str.rstrip('%'))
            
            # Determine status based on hit rate
            if hit_rate >= 60:
                status = HealthStatus.HEALTHY
            elif hit_rate >= 30:
                status = HealthStatus.DEGRADED
            elif cache_stats.get('hits', 0) == 0 and cache_stats.get('misses', 0) == 0:
                # No cache activity yet - still healthy
                status = HealthStatus.HEALTHY
            else:
                status = HealthStatus.DEGRADED
            
            details = {
                'enabled': True,
                'hit_rate': hit_rate,
                'total_hits': cache_stats.get('hits', 0),
                'total_misses': cache_stats.get('misses', 0),
                'entries': cache_stats.get('entries', 0),
                'message': f'Cache operational with {hit_rate}% hit rate'
            }
            
            return status, details
            
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return HealthStatus.DEGRADED, {
                'enabled': False,
                'error': str(e),
                'message': 'Cache system unavailable'
            }
    
    def check_email_service(self) -> Tuple[HealthStatus, Dict[str, Any]]:
        """
        Check email service configuration
        
        Returns:
            (status, details) tuple
        """
        try:
            import os
            
            sendgrid_key = os.environ.get('SENDGRID_API_KEY')
            
            if sendgrid_key and len(sendgrid_key) > 10:
                status = HealthStatus.HEALTHY
                details = {
                    'configured': True,
                    'provider': 'SendGrid',
                    'message': 'Email service configured'
                }
            else:
                status = HealthStatus.DEGRADED
                details = {
                    'configured': False,
                    'message': 'Email service not configured (optional)'
                }
            
            return status, details
            
        except Exception as e:
            logger.error(f"Email service health check failed: {e}")
            return HealthStatus.DEGRADED, {
                'configured': False,
                'error': str(e),
                'message': 'Email service check failed'
            }
    
    def check_session_management(self) -> Tuple[HealthStatus, Dict[str, Any]]:
        """
        Check session management system
        
        Returns:
            (status, details) tuple
        """
        try:
            import os
            from flask import session
            
            # Check session configuration
            secret_key = self.app.config.get('SECRET_KEY')
            session_type = self.app.config.get('SESSION_TYPE', 'filesystem')
            
            if secret_key and len(secret_key) > 10:
                status = HealthStatus.HEALTHY
                details = {
                    'configured': True,
                    'type': session_type,
                    'secure': self.app.config.get('SESSION_COOKIE_SECURE', False),
                    'httponly': self.app.config.get('SESSION_COOKIE_HTTPONLY', True),
                    'message': 'Session management operational'
                }
            else:
                status = HealthStatus.UNHEALTHY
                details = {
                    'configured': False,
                    'message': 'Session secret key not configured'
                }
            
            return status, details
            
        except Exception as e:
            logger.error(f"Session management health check failed: {e}")
            return HealthStatus.DEGRADED, {
                'configured': False,
                'error': str(e),
                'message': 'Session management check failed'
            }
    
    def check_rate_limiter(self) -> Tuple[HealthStatus, Dict[str, Any]]:
        """
        Check rate limiter status
        
        Returns:
            (status, details) tuple
        """
        try:
            from app import limiter
            
            if limiter and limiter.enabled:
                status = HealthStatus.HEALTHY
                details = {
                    'enabled': True,
                    'storage_type': 'memory',
                    'message': 'Rate limiting active'
                }
            else:
                status = HealthStatus.DEGRADED
                details = {
                    'enabled': False,
                    'message': 'Rate limiting disabled'
                }
            
            return status, details
            
        except Exception as e:
            logger.error(f"Rate limiter health check failed: {e}")
            return HealthStatus.DEGRADED, {
                'enabled': False,
                'error': str(e),
                'message': 'Rate limiter check failed'
            }
    
    def check_audit_logging(self) -> Tuple[HealthStatus, Dict[str, Any]]:
        """
        Check audit logging system
        
        Returns:
            (status, details) tuple
        """
        try:
            from sqlalchemy import text
            import time
            
            # Check if audit_log table exists and is writable
            start_time = time.time()
            result = self.db.session.execute(text("""
                SELECT COUNT(*) FROM audit_log 
                WHERE timestamp > NOW() - INTERVAL '1 hour'
            """)).scalar()
            query_time_ms = (time.time() - start_time) * 1000
            
            if result is not None and query_time_ms < 200:
                status = HealthStatus.HEALTHY
                details = {
                    'enabled': True,
                    'recent_events': result,
                    'query_time_ms': round(query_time_ms, 2),
                    'message': 'Audit logging operational'
                }
            else:
                status = HealthStatus.DEGRADED
                details = {
                    'enabled': True,
                    'message': 'Audit logging slow response'
                }
            
            return status, details
            
        except Exception as e:
            logger.error(f"Audit logging health check failed: {e}")
            return HealthStatus.UNHEALTHY, {
                'enabled': False,
                'error': str(e),
                'message': 'Audit logging system unavailable'
            }
    
    def get_comprehensive_health(self) -> Dict[str, Any]:
        """
        Perform all component health checks and return comprehensive status
        
        Returns:
            Dictionary with overall status and component details
        """
        components = {}
        
        # Run all component checks
        db_status, db_details = self.check_database()
        components['database'] = {'status': db_status.value, **db_details}
        
        cache_status, cache_details = self.check_cache()
        components['cache'] = {'status': cache_status.value, **cache_details}
        
        email_status, email_details = self.check_email_service()
        components['email'] = {'status': email_status.value, **email_details}
        
        session_status, session_details = self.check_session_management()
        components['session'] = {'status': session_status.value, **session_details}
        
        rate_limiter_status, rate_limiter_details = self.check_rate_limiter()
        components['rate_limiter'] = {'status': rate_limiter_status.value, **rate_limiter_details}
        
        audit_status, audit_details = self.check_audit_logging()
        components['audit_logging'] = {'status': audit_status.value, **audit_details}
        
        # Determine overall status
        statuses = [db_status, cache_status, session_status, rate_limiter_status, audit_status]
        # Email is optional, only count if configured
        if email_status == HealthStatus.HEALTHY:
            statuses.append(email_status)
        
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
            overall_message = "All systems operational"
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
            overall_message = "One or more critical systems are unhealthy"
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall_status = HealthStatus.DEGRADED
            overall_message = "System operational with degraded performance"
        else:
            overall_status = HealthStatus.UNKNOWN
            overall_message = "Health status unknown"
        
        return {
            'status': overall_status.value,
            'message': overall_message,
            'timestamp': datetime.now().isoformat(),
            'service': 'TraitorTrack',
            'version': '2.0',
            'components': components
        }


def get_health_checker(app, db):
    """
    Get or create health checker instance
    
    Args:
        app: Flask application
        db: SQLAlchemy database instance
        
    Returns:
        ComponentHealthChecker instance
    """
    return ComponentHealthChecker(app, db)
