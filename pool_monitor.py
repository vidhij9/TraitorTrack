"""
Database Connection Pool Monitor
Provides active monitoring and alerting for database connection pool health.
"""

import logging
import time
from threading import Thread, Event
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PoolMonitor:
    """Monitors database connection pool and raises alerts on threshold violations"""
    
    # Alert thresholds (percentage of max connections)
    WARNING_THRESHOLD = 0.70  # 70% usage
    CRITICAL_THRESHOLD = 0.85  # 85% usage
    DANGER_THRESHOLD = 0.95   # 95% usage
    
    # Monitoring interval (seconds)
    CHECK_INTERVAL = 30  # Check every 30 seconds
    
    # Alert cooldown to prevent spam
    ALERT_COOLDOWN = 300  # 5 minutes between similar alerts
    
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
        Raise pool usage alert
        
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
        elif level == 'CRITICAL':
            logger.error(log_message)
            logger.error("Pool usage critical - consider scaling or optimizing queries")
        else:  # WARNING
            logger.warning(log_message)
            logger.warning("Pool usage high - monitor for continued growth")
    
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
    
    def get_health_summary(self) -> Dict:
        """
        Get comprehensive pool health summary
        
        Returns:
            Dictionary with health status and recommendations
        """
        current_stats = self.get_pool_stats()
        
        if not current_stats:
            return {
                'status': 'unknown',
                'message': 'Unable to fetch pool statistics'
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
        
        return {
            'status': status,
            'message': message,
            'recommendations': recommendations,
            'current_stats': current_stats,
            'history_available': len(self.stats_history)
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
