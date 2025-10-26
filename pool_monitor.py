"""
Database Connection Pool Monitor
Provides active monitoring and alerting for database connection pool health.
Enhanced with configurable thresholds, email notifications, and trend analysis.
"""

import logging
import time
import os
from threading import Thread, Event
from typing import Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PoolMonitor:
    """Monitors database connection pool and raises alerts on threshold violations"""
    
    # Configurable alert thresholds (percentage of max connections)
    # Can be overridden via environment variables
    WARNING_THRESHOLD = float(os.environ.get('POOL_WARNING_THRESHOLD', '0.70'))  # Default: 70%
    CRITICAL_THRESHOLD = float(os.environ.get('POOL_CRITICAL_THRESHOLD', '0.85'))  # Default: 85%
    DANGER_THRESHOLD = float(os.environ.get('POOL_DANGER_THRESHOLD', '0.95'))  # Default: 95%
    
    # Monitoring interval (seconds)
    CHECK_INTERVAL = int(os.environ.get('POOL_CHECK_INTERVAL', '30'))  # Default: 30s
    
    # Alert cooldown to prevent spam
    ALERT_COOLDOWN = int(os.environ.get('POOL_ALERT_COOLDOWN', '300'))  # Default: 5 minutes
    
    def __init__(self, db_engine, enabled=True):
        """
        Initialize pool monitor
        
        Args:
            db_engine: SQLAlchemy engine with connection pool
            enabled: Whether monitoring is enabled (default: True)
        """
        self.db_engine = db_engine
        self.enabled = enabled
        self.stop_event = Event()
        self.monitor_thread = None
        self.last_alert_time = {}
        self.stats_history = []
        self.max_history_size = 100
        
    def start(self):
        """Start pool monitoring in background thread"""
        if not self.enabled:
            logger.info("Pool monitoring is disabled")
            return
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            logger.warning("Pool monitor already running")
            return
        
        self.stop_event.clear()
        self.monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"Pool monitor started - checking every {self.CHECK_INTERVAL}s")
    
    def stop(self):
        """Stop pool monitoring"""
        if not self.monitor_thread:
            return
        
        self.stop_event.set()
        self.monitor_thread.join(timeout=5)
        logger.info("Pool monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop - runs in background thread"""
        while not self.stop_event.is_set():
            try:
                self._check_pool_health()
            except Exception as e:
                logger.error(f"Pool monitor error: {e}")
            
            # Wait for next check or stop event
            self.stop_event.wait(self.CHECK_INTERVAL)
    
    def _check_pool_health(self):
        """Check pool health and raise alerts if needed"""
        try:
            stats = self.get_pool_stats()
            
            if not stats:
                return
            
            # Calculate usage percentage
            usage_percent = stats.get('usage_percent', 0)
            
            # Store in history
            stats['timestamp'] = datetime.now()
            self.stats_history.append(stats)
            if len(self.stats_history) > self.max_history_size:
                self.stats_history.pop(0)
            
            # Check thresholds and raise alerts
            if usage_percent >= self.DANGER_THRESHOLD * 100:
                self._raise_alert('DANGER', stats)
            elif usage_percent >= self.CRITICAL_THRESHOLD * 100:
                self._raise_alert('CRITICAL', stats)
            elif usage_percent >= self.WARNING_THRESHOLD * 100:
                self._raise_alert('WARNING', stats)
            else:
                # Log healthy status periodically (every 10 checks)
                if len(self.stats_history) % 10 == 0:
                    logger.debug(f"Pool health OK - {usage_percent:.1f}% used "
                               f"({stats['checked_out']}/{stats['configured_max']} connections)")
        
        except Exception as e:
            logger.error(f"Error checking pool health: {e}")
    
    def _raise_alert(self, level: str, stats: Dict):
        """
        Raise pool usage alert with logging and optional email notification
        
        Args:
            level: Alert level ('WARNING', 'CRITICAL', 'DANGER')
            stats: Current pool statistics
        """
        # Check cooldown to prevent alert spam
        now = datetime.now()
        last_alert = self.last_alert_time.get(level)
        
        if last_alert:
            time_since_last = (now - last_alert).total_seconds()
            if time_since_last < self.ALERT_COOLDOWN:
                return  # Skip alert (in cooldown period)
        
        # Update last alert time
        self.last_alert_time[level] = now
        
        # Log alert
        usage_percent = stats['usage_percent']
        checked_out = stats['checked_out']
        configured_max = stats['configured_max']
        overflow = stats['overflow']
        
        log_message = (
            f"[{level}] Database connection pool usage: {usage_percent:.1f}% "
            f"({checked_out}/{configured_max} connections, overflow={overflow})"
        )
        
        if level == 'DANGER':
            logger.critical(log_message)
            logger.critical("IMMEDIATE ACTION REQUIRED: Pool nearly exhausted - "
                          "new connections will fail!")
            self._send_alert_email(level, stats, log_message)
        elif level == 'CRITICAL':
            logger.error(log_message)
            logger.error("Pool usage critical - consider scaling or optimizing queries")
            self._send_alert_email(level, stats, log_message)
        else:  # WARNING
            logger.warning(log_message)
            logger.warning("Pool usage high - monitor for continued growth")
            # Optional: Send email for WARNING level too
            # self._send_alert_email(level, stats, log_message)
    
    def _send_alert_email(self, level: str, stats: Dict, log_message: str):
        """
        Send email alert for connection pool issues (CRITICAL and DANGER levels only)
        
        Args:
            level: Alert level
            stats: Pool statistics
            log_message: Alert message
        """
        # Only send emails for CRITICAL and DANGER alerts
        # Skip if email notifications are disabled
        email_enabled = os.environ.get('POOL_EMAIL_ALERTS', 'true').lower() == 'true'
        if not email_enabled:
            return
        
        try:
            from email_utils import send_admin_alert_email
            
            # Prepare email content
            subject = f"[{level}] TraceTrack Database Connection Pool Alert"
            
            # Build detailed message with recommendations
            recommendations = []
            if level == 'DANGER':
                recommendations = [
                    'Scale up database connection limits immediately',
                    'Add more application workers',
                    'Investigate and kill long-running queries',
                    'Review code for connection leaks'
                ]
            elif level == 'CRITICAL':
                recommendations = [
                    'Monitor pool usage trends closely',
                    'Review active queries for optimization opportunities',
                    'Consider scaling database resources',
                    'Check for connection leaks in application code'
                ]
            
            message = f"""
            <h2 style="color: {'#dc3545' if level == 'DANGER' else '#ffc107'};">{level} Alert: Connection Pool Saturation</h2>
            
            <p><strong>Alert Message:</strong> {log_message}</p>
            
            <h3>Current Pool Statistics:</h3>
            <ul>
                <li><strong>Usage:</strong> {stats['usage_percent']:.1f}%</li>
                <li><strong>Checked Out:</strong> {stats['checked_out']}/{stats['configured_max']}</li>
                <li><strong>Overflow Connections:</strong> {stats['overflow']}</li>
                <li><strong>Available:</strong> {stats['configured_max'] - stats['checked_out']}</li>
            </ul>
            
            <h3>Recommended Actions:</h3>
            <ol>
            {''.join(f'<li>{rec}</li>' for rec in recommendations)}
            </ol>
            
            <p><em>This is an automated alert from TraceTrack pool monitoring system.</em></p>
            """
            
            send_admin_alert_email(subject, message)
            logger.info(f"Alert email sent for {level} pool usage")
            
        except Exception as e:
            logger.error(f"Failed to send pool alert email: {e}")
    
    def get_pool_stats(self) -> Optional[Dict]:
        """
        Get current connection pool statistics
        
        Returns:
            Dictionary with pool stats or None if unavailable
        """
        try:
            pool = self.db_engine.pool
            
            # Get pool metrics
            size = pool.size()
            checked_in = pool.checkedin()
            checked_out = pool.checkedout()
            overflow = pool.overflow()
            
            # Calculate configured max (base + overflow)
            # From app.py: pool_size=25, max_overflow=15
            configured_max = 25 + 15  # 40 per worker
            
            # Calculate usage percentage
            usage_percent = (checked_out / configured_max * 100) if configured_max > 0 else 0
            
            return {
                'size': size,
                'checked_in': checked_in,
                'checked_out': checked_out,
                'overflow': overflow,
                'configured_max': configured_max,
                'total_connections': checked_out + checked_in,
                'usage_percent': round(usage_percent, 2)
            }
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return None
    
    def get_stats_history(self, minutes: int = 10) -> list:
        """
        Get pool statistics history
        
        Args:
            minutes: Number of minutes of history to return
            
        Returns:
            List of pool stats dictionaries
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [
            stats for stats in self.stats_history
            if stats.get('timestamp', datetime.min) >= cutoff_time
        ]
    
    def get_usage_trend(self, minutes: int = 10) -> Dict:
        """
        Analyze pool usage trend over time
        
        Args:
            minutes: Number of minutes to analyze
            
        Returns:
            Dictionary with trend analysis
        """
        recent_stats = self.get_stats_history(minutes=minutes)
        
        if len(recent_stats) < 3:
            return {
                'trend': 'insufficient_data',
                'message': 'Not enough historical data for trend analysis',
                'prediction': None
            }
        
        # Calculate average usage over time
        usage_values = [s.get('usage_percent', 0) for s in recent_stats]
        
        if not usage_values:
            return {
                'trend': 'no_data',
                'message': 'No usage data available',
                'prediction': None
            }
        
        # Simple linear trend: compare first half to second half
        mid_point = len(usage_values) // 2
        first_half_avg = sum(usage_values[:mid_point]) / len(usage_values[:mid_point])
        second_half_avg = sum(usage_values[mid_point:]) / len(usage_values[mid_point:])
        
        trend_diff = second_half_avg - first_half_avg
        
        # Determine trend direction
        if trend_diff > 5:
            trend = 'increasing'
            message = f'Pool usage increasing ({trend_diff:+.1f}% over {minutes} min)'
        elif trend_diff < -5:
            trend = 'decreasing'
            message = f'Pool usage decreasing ({trend_diff:+.1f}% over {minutes} min)'
        else:
            trend = 'stable'
            message = f'Pool usage stable (±{abs(trend_diff):.1f}% over {minutes} min)'
        
        # Simple prediction: if increasing, estimate time to critical threshold
        prediction = None
        if trend == 'increasing' and second_half_avg < self.CRITICAL_THRESHOLD * 100:
            # Rough estimate: how long until critical threshold at current rate
            rate_per_minute = trend_diff / minutes
            headroom = (self.CRITICAL_THRESHOLD * 100) - second_half_avg
            if rate_per_minute > 0:
                minutes_to_critical = headroom / rate_per_minute
                prediction = {
                    'minutes_to_critical': round(minutes_to_critical, 1),
                    'message': f'May reach critical in ~{round(minutes_to_critical)} minutes at current rate'
                }
        
        return {
            'trend': trend,
            'message': message,
            'first_half_avg': round(first_half_avg, 2),
            'second_half_avg': round(second_half_avg, 2),
            'prediction': prediction
        }
    
    def get_health_summary(self) -> Dict:
        """
        Get comprehensive pool health summary with trend analysis
        
        Returns:
            Dictionary with health status, recommendations, and trends
        """
        current_stats = self.get_pool_stats()
        
        if not current_stats:
            return {
                'status': 'unknown',
                'message': 'Unable to fetch pool statistics',
                'trend_analysis': None
            }
        
        usage_percent = current_stats['usage_percent']
        
        # Determine health status
        if usage_percent >= self.DANGER_THRESHOLD * 100:
            status = 'danger'
            message = 'Pool nearly exhausted - immediate action required'
            recommendations = [
                'Scale up database connection limits',
                'Add more application workers',
                'Optimize slow queries',
                'Review connection leaks in code'
            ]
        elif usage_percent >= self.CRITICAL_THRESHOLD * 100:
            status = 'critical'
            message = 'Pool usage critically high'
            recommendations = [
                'Monitor for continued growth',
                'Review active queries for optimization',
                'Consider scaling database resources'
            ]
        elif usage_percent >= self.WARNING_THRESHOLD * 100:
            status = 'warning'
            message = 'Pool usage elevated'
            recommendations = [
                'Monitor pool usage trends',
                'Review query performance'
            ]
        else:
            status = 'healthy'
            message = 'Pool operating normally'
            recommendations = []
        
        # Add trend analysis
        trend_analysis = self.get_usage_trend(minutes=10)
        
        # Add configured thresholds for transparency
        thresholds = {
            'warning': f'{self.WARNING_THRESHOLD * 100:.0f}%',
            'critical': f'{self.CRITICAL_THRESHOLD * 100:.0f}%',
            'danger': f'{self.DANGER_THRESHOLD * 100:.0f}%'
        }
        
        return {
            'status': status,
            'message': message,
            'recommendations': recommendations,
            'current_stats': current_stats,
            'history_available': len(self.stats_history),
            'trend_analysis': trend_analysis,
            'thresholds': thresholds
        }


# Global monitor instance (initialized in app.py)
pool_monitor: Optional[PoolMonitor] = None


def get_pool_monitor() -> Optional[PoolMonitor]:
    """Get the global pool monitor instance"""
    return pool_monitor


def init_pool_monitor(db_engine, enabled=True):
    """
    Initialize and start the global pool monitor
    
    Args:
        db_engine: SQLAlchemy engine
        enabled: Whether to enable monitoring (default: True)
    """
    global pool_monitor
    
    pool_monitor = PoolMonitor(db_engine, enabled=enabled)
    pool_monitor.start()
    
    return pool_monitor
