"""
Enterprise-grade Performance Monitoring and Analytics System
Handles 50+ lakh bags and 1000+ concurrent users with real-time monitoring
"""

import os
import time
import psutil
import logging
import json
# Redis removed for simplification
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict, deque
from threading import Lock, Thread
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import g, request, current_app
from sqlalchemy import text, func
from models import db, User, Bag, Scan, Bill
# Alert config simplified

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Real-time performance monitoring with alerting capabilities"""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: deque(maxlen=1000))
        self.alerts = deque(maxlen=100)
        self.lock = Lock()
        self.thresholds = {
            'response_time': 2.0,  # seconds
            'db_query_time': 1.0,  # seconds
            'error_rate': 0.05,  # 5%
            'memory_usage': 85,  # percentage
            'cpu_usage': 80,  # percentage
            'concurrent_users': 900,  # users
            'db_connections': 200,  # connections
        }
        self.alert_cooldown = {}  # Prevent alert spam
    
    def track_request(self, func):
        """Decorator to track request performance"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            g.request_start_time = start_time
            
            try:
                result = func(*args, **kwargs)
                status = 'success'
                return result
            except Exception as e:
                status = 'error'
                logger.error(f"Request error: {str(e)}")
                raise
            finally:
                duration = time.time() - start_time
                self._record_request_metric(duration, status)
                
                # Check for performance issues
                if duration > self.thresholds['response_time']:
                    self._trigger_alert('slow_response', {
                        'endpoint': request.endpoint,
                        'duration': duration,
                        'threshold': self.thresholds['response_time']
                    })
        
        return wrapper
    
    def track_db_query(self, query_name):
        """Decorator to track database query performance"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self._record_db_metric(query_name, duration)
                    
                    if duration > self.thresholds['db_query_time']:
                        self._trigger_alert('slow_query', {
                            'query': query_name,
                            'duration': duration,
                            'threshold': self.thresholds['db_query_time']
                        })
            
            return wrapper
        return decorator
    
    def _record_request_metric(self, duration, status):
        """Record request metrics"""
        with self.lock:
            timestamp = datetime.utcnow()
            metric = {
                'timestamp': timestamp.isoformat(),
                'duration': duration,
                'status': status,
                'endpoint': request.endpoint,
                'method': request.method,
                'ip': request.remote_addr
            }
            
            self.metrics['requests'].append(metric)
            
            # Store in Redis if available
            if None:
                try:
                    key = f"metrics:request:{timestamp.strftime('%Y%m%d%H')}"
                    None.lpush(key, json.dumps(metric))
                    None.expire(key, 86400)  # Keep for 24 hours
                except Exception as e:
                    logger.error(f"Failed to store metric in Redis: {e}")
    
    def _record_db_metric(self, query_name, duration):
        """Record database query metrics"""
        with self.lock:
            timestamp = datetime.utcnow()
            metric = {
                'timestamp': timestamp.isoformat(),
                'query': query_name,
                'duration': duration
            }
            
            self.metrics['db_queries'].append(metric)
            
            if None:
                try:
                    key = f"metrics:db:{timestamp.strftime('%Y%m%d%H')}"
                    None.lpush(key, json.dumps(metric))
                    None.expire(key, 86400)
                except Exception as e:
                    logger.error(f"Failed to store DB metric in Redis: {e}")
    
    def _trigger_alert(self, alert_type, details):
        """Trigger an alert with cooldown to prevent spam"""
        cooldown_key = f"{alert_type}:{details.get('endpoint', details.get('query', 'unknown'))}"
        current_time = time.time()
        
        # Check cooldown (5 minutes)
        if cooldown_key in self.alert_cooldown:
            if current_time - self.alert_cooldown[cooldown_key] < 300:
                return
        
        self.alert_cooldown[cooldown_key] = current_time
        
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': alert_type,
            'details': details,
            'severity': self._get_severity(alert_type)
        }
        
        with self.lock:
            self.alerts.append(alert)
        
        # Send alert notification
        self._send_alert_notification(alert)
        
        logger.warning(f"Alert triggered: {alert_type} - {details}")
    
    def _get_severity(self, alert_type):
        """Determine alert severity"""
        severity_map = {
            'slow_response': 'warning',
            'slow_query': 'warning',
            'high_error_rate': 'critical',
            'high_memory': 'critical',
            'high_cpu': 'critical',
            'db_connection_limit': 'critical'
        }
        return severity_map.get(alert_type, 'info')
    
    def _send_alert_notification(self, alert):
        """Send alert via email or webhook using alert_config"""
        # Use the alert configuration system to send notifications
        alert_type = alert['severity']
        title = f"{alert['type'].replace('_', ' ').title()}"
        message = f"Alert triggered at {alert['timestamp']}"
        
        # Add details to message
        if alert['details']:
            details_str = ", ".join([f"{k}: {v}" for k, v in alert['details'].items()])
            message += f"\nDetails: {details_str}"
        
        # Send through configured channels
        alert_config.send_alert(alert_type, title, message, alert['details'])
        
        # Also log it
        if alert['severity'] == 'critical':
            logger.critical(f"CRITICAL ALERT: {alert}")
        else:
            logger.warning(f"Alert: {alert}")
    
    def get_system_metrics(self):
        """Get current system metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get database metrics
            db_stats = self._get_database_stats()
            
            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used_gb': memory.used / (1024**3),
                    'memory_total_gb': memory.total / (1024**3),
                    'disk_percent': disk.percent,
                    'disk_used_gb': disk.used / (1024**3),
                    'disk_total_gb': disk.total / (1024**3)
                },
                'database': db_stats,
                'application': self._get_application_stats()
            }
            
            # Check for system issues
            if cpu_percent > self.thresholds['cpu_usage']:
                self._trigger_alert('high_cpu', {'usage': cpu_percent})
            
            if memory.percent > self.thresholds['memory_usage']:
                self._trigger_alert('high_memory', {'usage': memory.percent})
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return None
    
    def _get_database_stats(self):
        """Get database performance statistics"""
        try:
            with db.engine.connect() as conn:
                # Get connection stats
                result = conn.execute(text("""
                    SELECT 
                        numbackends as active_connections,
                        xact_commit as transactions_committed,
                        xact_rollback as transactions_rolled_back,
                        blks_read as blocks_read,
                        blks_hit as blocks_hit,
                        tup_returned as rows_returned,
                        tup_fetched as rows_fetched,
                        tup_inserted as rows_inserted,
                        tup_updated as rows_updated,
                        tup_deleted as rows_deleted
                    FROM pg_stat_database 
                    WHERE datname = current_database()
                """)).first()
                
                if result:
                    stats = dict(result._mapping)
                    
                    # Calculate cache hit ratio
                    if stats['blocks_read'] + stats['blocks_hit'] > 0:
                        stats['cache_hit_ratio'] = (
                            stats['blocks_hit'] / 
                            (stats['blocks_read'] + stats['blocks_hit']) * 100
                        )
                    else:
                        stats['cache_hit_ratio'] = 0
                    
                    # Check connection limit
                    if stats['active_connections'] > self.thresholds['db_connections']:
                        self._trigger_alert('db_connection_limit', {
                            'connections': stats['active_connections'],
                            'threshold': self.thresholds['db_connections']
                        })
                    
                    return stats
                    
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
        
        return {}
    
    def _get_application_stats(self):
        """Get application-level statistics"""
        try:
            # Calculate request statistics
            recent_requests = list(self.metrics['requests'])[-100:]  # Last 100 requests
            
            if recent_requests:
                total_requests = len(recent_requests)
                error_requests = sum(1 for r in recent_requests if r['status'] == 'error')
                avg_response_time = sum(r['duration'] for r in recent_requests) / total_requests
                
                error_rate = error_requests / total_requests
                
                # Check error rate threshold
                if error_rate > self.thresholds['error_rate']:
                    self._trigger_alert('high_error_rate', {
                        'rate': error_rate * 100,
                        'threshold': self.thresholds['error_rate'] * 100
                    })
                
                return {
                    'total_requests': total_requests,
                    'error_rate': error_rate * 100,
                    'avg_response_time': avg_response_time,
                    'requests_per_minute': self._calculate_rpm()
                }
            
        except Exception as e:
            logger.error(f"Failed to get application stats: {e}")
        
        return {}
    
    def _calculate_rpm(self):
        """Calculate requests per minute"""
        try:
            one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
            recent_requests = [
                r for r in self.metrics['requests'] 
                if datetime.fromisoformat(r['timestamp']) > one_minute_ago
            ]
            return len(recent_requests)
        except:
            return 0
    
    def get_analytics_dashboard(self):
        """Get comprehensive analytics for dashboard"""
        try:
            # Get time-based analytics
            now = datetime.utcnow()
            
            analytics = {
                'real_time': {
                    'active_users': self._get_active_users(),
                    'current_rpm': self._calculate_rpm(),
                    'system_health': self._get_system_health()
                },
                'today': self._get_daily_analytics(now.date()),
                'weekly': self._get_weekly_analytics(),
                'alerts': list(self.alerts)[-10:],  # Last 10 alerts
                'performance_trends': self._get_performance_trends()
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to generate analytics dashboard: {e}")
            return {}
    
    def _get_active_users(self):
        """Get count of active users in last 5 minutes"""
        try:
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
            active_users = set()
            
            for metric in self.metrics['requests']:
                if datetime.fromisoformat(metric['timestamp']) > five_minutes_ago:
                    active_users.add(metric.get('ip'))
            
            return len(active_users)
            
        except Exception as e:
            logger.error(f"Failed to get active users: {e}")
            return 0
    
    def _get_system_health(self):
        """Calculate overall system health score"""
        try:
            metrics = self.get_system_metrics()
            if not metrics:
                return 'unknown'
            
            health_score = 100
            
            # Deduct points for high resource usage
            cpu = metrics['system']['cpu_percent']
            memory = metrics['system']['memory_percent']
            
            if cpu > 80:
                health_score -= 20
            elif cpu > 60:
                health_score -= 10
            
            if memory > 85:
                health_score -= 20
            elif memory > 70:
                health_score -= 10
            
            # Check error rate
            app_stats = metrics.get('application', {})
            if app_stats.get('error_rate', 0) > 5:
                health_score -= 30
            elif app_stats.get('error_rate', 0) > 2:
                health_score -= 15
            
            if health_score >= 80:
                return 'healthy'
            elif health_score >= 60:
                return 'degraded'
            else:
                return 'critical'
                
        except Exception as e:
            logger.error(f"Failed to calculate system health: {e}")
            return 'unknown'
    
    def _get_daily_analytics(self, date):
        """Get analytics for a specific day"""
        try:
            # This would query from database for production
            # For now, return sample structure
            return {
                'total_scans': 0,
                'unique_users': 0,
                'bags_processed': 0,
                'avg_response_time': 0,
                'peak_concurrent_users': 0
            }
        except Exception as e:
            logger.error(f"Failed to get daily analytics: {e}")
            return {}
    
    def _get_weekly_analytics(self):
        """Get weekly analytics trends"""
        try:
            return {
                'total_scans': 0,
                'growth_rate': 0,
                'top_users': [],
                'busiest_hours': []
            }
        except Exception as e:
            logger.error(f"Failed to get weekly analytics: {e}")
            return {}
    
    def _get_performance_trends(self):
        """Get performance trend data for charts"""
        try:
            # Get last hour of data
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            trends = {
                'response_times': [],
                'error_rates': [],
                'rpm': []
            }
            
            # Sample data points every 5 minutes
            for i in range(12):
                time_point = one_hour_ago + timedelta(minutes=i*5)
                
                # Get metrics for this time window
                window_start = time_point
                window_end = time_point + timedelta(minutes=5)
                
                window_requests = [
                    r for r in self.metrics['requests']
                    if window_start <= datetime.fromisoformat(r['timestamp']) < window_end
                ]
                
                if window_requests:
                    avg_response = sum(r['duration'] for r in window_requests) / len(window_requests)
                    error_count = sum(1 for r in window_requests if r['status'] == 'error')
                    error_rate = (error_count / len(window_requests)) * 100
                    
                    trends['response_times'].append({
                        'time': time_point.isoformat(),
                        'value': avg_response
                    })
                    trends['error_rates'].append({
                        'time': time_point.isoformat(),
                        'value': error_rate
                    })
                    trends['rpm'].append({
                        'time': time_point.isoformat(),
                        'value': len(window_requests) * 12  # Extrapolate to per minute
                    })
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to get performance trends: {e}")
            return {}


# Global monitor instance
monitor = PerformanceMonitor()

# Simple alert manager for compatibility
class AlertManager:
    def __init__(self):
        self.alerts = []
    
    def send_alert(self, alert_type, data):
        """Simple alert logging"""
        logger.warning(f"Alert: {alert_type} - {data}")
        self.alerts.append({'type': alert_type, 'data': data, 'timestamp': datetime.now()})

alert_manager = AlertManager()


class DatabaseAnalytics:
    """Advanced database analytics for 50+ lakh bags"""
    
    @staticmethod
    def get_bag_distribution():
        """Get distribution of bags across areas and types"""
        try:
            result = db.session.query(
                Bag.dispatch_area,
                Bag.type,
                func.count(Bag.id).label('count')
            ).group_by(
                Bag.dispatch_area,
                Bag.type
            ).all()
            
            distribution = {}
            for row in result:
                area = row.dispatch_area or 'unassigned'
                if area not in distribution:
                    distribution[area] = {}
                distribution[area][row.type] = row.count
            
            return distribution
            
        except Exception as e:
            logger.error(f"Failed to get bag distribution: {e}")
            return {}
    
    @staticmethod
    def get_scan_patterns():
        """Analyze scanning patterns for optimization"""
        try:
            # Get hourly scan patterns
            result = db.session.query(
                func.date_trunc('hour', Scan.timestamp).label('hour'),
                func.count(Scan.id).label('count')
            ).filter(
                Scan.timestamp >= datetime.utcnow() - timedelta(days=7)
            ).group_by('hour').all()
            
            patterns = {
                'hourly': [{'hour': str(r.hour), 'count': r.count} for r in result]
            }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to get scan patterns: {e}")
            return {}
    
    @staticmethod
    def get_user_performance():
        """Get user performance metrics"""
        try:
            result = db.session.query(
                User.username,
                User.role,
                func.count(Scan.id).label('scan_count'),
                func.avg(
                    func.extract('epoch', Scan.timestamp - Scan.timestamp)
                ).label('avg_scan_time')
            ).outerjoin(
                Scan, User.id == Scan.user_id
            ).group_by(
                User.id, User.username, User.role
            ).order_by(
                func.count(Scan.id).desc()
            ).limit(20).all()
            
            return [
                {
                    'username': r.username,
                    'role': r.role,
                    'scan_count': r.scan_count,
                    'avg_scan_time': r.avg_scan_time
                }
                for r in result
            ]
            
        except Exception as e:
            logger.error(f"Failed to get user performance: {e}")
            return []


class AlertManager:
    """Manage and send alerts for critical events"""
    
    def __init__(self):
        self.email_enabled = bool(os.environ.get('SMTP_SERVER'))
        self.webhook_url = os.environ.get('ALERT_WEBHOOK_URL')
        
    def send_alert(self, alert_type, message, severity='warning'):
        """Send alert through configured channels"""
        
        # Log the alert
        if severity == 'critical':
            logger.critical(f"ALERT [{alert_type}]: {message}")
        elif severity == 'error':
            logger.error(f"ALERT [{alert_type}]: {message}")
        else:
            logger.warning(f"ALERT [{alert_type}]: {message}")
        
        # Send email if configured
        if self.email_enabled:
            self._send_email_alert(alert_type, message, severity)
        
        # Send webhook if configured
        if self.webhook_url:
            self._send_webhook_alert(alert_type, message, severity)
    
    def _send_email_alert(self, alert_type, message, severity):
        """Send email alert"""
        try:
            smtp_server = os.environ.get('SMTP_SERVER')
            smtp_port = int(os.environ.get('SMTP_PORT', 587))
            smtp_user = os.environ.get('SMTP_USER')
            smtp_pass = os.environ.get('SMTP_PASS')
            alert_email = os.environ.get('ALERT_EMAIL')
            
            if not all([smtp_server, smtp_user, smtp_pass, alert_email]):
                return
            
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = alert_email
            msg['Subject'] = f"[{severity.upper()}] TraceTrack Alert: {alert_type}"
            
            body = f"""
            Alert Type: {alert_type}
            Severity: {severity}
            Time: {datetime.utcnow().isoformat()}
            
            Message:
            {message}
            
            Please check the system immediately if this is a critical alert.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
                
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_webhook_alert(self, alert_type, message, severity):
        """Send webhook alert"""
        try:
            import requests
            
            payload = {
                'alert_type': alert_type,
                'message': message,
                'severity': severity,
                'timestamp': datetime.utcnow().isoformat(),
                'system': 'TraceTrack'
            }
            
            requests.post(self.webhook_url, json=payload, timeout=5)
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")


# Global alert manager
alert_manager = AlertManager()