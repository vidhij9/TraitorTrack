"""
Analytics and Monitoring Routes for Enterprise Dashboard
"""

import os
import json
from flask import Blueprint, render_template, jsonify, request, g, session
from datetime import datetime, timedelta
from sqlalchemy import func, text
from models import db, User, Bag, Scan, Bill
from auth_utils import admin_required, require_auth
from performance_monitoring import monitor, DatabaseAnalytics, alert_manager
from enterprise_cache import cache, QueryCache
from database_scaling import db_scaler
import logging

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.before_request
def track_analytics_request():
    """Track all analytics requests for monitoring"""
    g.request_start = datetime.utcnow()

@analytics_bp.after_request
def log_analytics_request(response):
    """Log analytics request performance"""
    if hasattr(g, 'request_start'):
        duration = (datetime.utcnow() - g.request_start).total_seconds()
        if duration > 2:
            logger.warning(f"Slow analytics request: {request.path} took {duration:.2f}s")
    return response

@analytics_bp.route('/dashboard')
@require_auth
@admin_required
def dashboard():
    """Main analytics dashboard with real-time monitoring"""
    try:
        # Get comprehensive analytics
        system_metrics = monitor.get_system_metrics()
        analytics_data = monitor.get_analytics_dashboard()
        db_health = db_scaler.get_health_metrics()
        cache_stats = cache.get_stats()
        
        # Get business metrics
        business_metrics = _get_business_metrics()
        
        return render_template('analytics_dashboard.html',
                             system_metrics=system_metrics,
                             analytics=analytics_data,
                             db_health=db_health,
                             cache_stats=cache_stats,
                             business_metrics=business_metrics)
    except Exception as e:
        logger.error(f"Analytics dashboard error: {e}")
        return render_template('error.html', error="Failed to load analytics dashboard"), 500

@analytics_bp.route('/api/metrics/realtime')
@require_auth
@admin_required
def realtime_metrics():
    """API endpoint for real-time metrics updates"""
    try:
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'system': monitor.get_system_metrics(),
            'active_users': monitor._get_active_users(),
            'rpm': monitor._calculate_rpm(),
            'health': monitor._get_system_health(),
            'alerts': list(monitor.alerts)[-5:]  # Last 5 alerts
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Real-time metrics error: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/metrics/performance')
@require_auth
@admin_required
def performance_metrics():
    """Get detailed performance metrics"""
    try:
        # Time range from query params
        hours = int(request.args.get('hours', 24))
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get performance data
        perf_data = {
            'response_times': _get_response_time_metrics(start_time),
            'database': _get_database_metrics(start_time),
            'cache': cache.get_stats(),
            'errors': _get_error_metrics(start_time)
        }
        
        return jsonify(perf_data)
        
    except Exception as e:
        logger.error(f"Performance metrics error: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/metrics/bags')
@require_auth
@admin_required
@cache.cache('bag_metrics', ttl=300)
def bag_metrics():
    """Get bag distribution and statistics"""
    try:
        metrics = {
            'distribution': DatabaseAnalytics.get_bag_distribution(),
            'totals': _get_bag_totals(),
            'growth': _get_bag_growth_metrics(),
            'scan_patterns': DatabaseAnalytics.get_scan_patterns()
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Bag metrics error: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/metrics/users')
@require_auth
@admin_required
def user_metrics():
    """Get user activity and performance metrics"""
    try:
        metrics = {
            'performance': DatabaseAnalytics.get_user_performance(),
            'activity': _get_user_activity_metrics(),
            'roles': _get_user_role_distribution()
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"User metrics error: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/alerts')
@require_auth
@admin_required
def get_alerts():
    """Get system alerts"""
    try:
        limit = int(request.args.get('limit', 50))
        alerts = list(monitor.alerts)[-limit:]
        
        return jsonify({
            'alerts': alerts,
            'total': len(monitor.alerts)
        })
        
    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/alerts/acknowledge/<alert_id>', methods=['POST'])
@require_auth
@admin_required
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    try:
        # Implementation would mark alert as acknowledged
        return jsonify({'status': 'acknowledged', 'alert_id': alert_id})
        
    except Exception as e:
        logger.error(f"Acknowledge alert error: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connectivity
        db.session.execute(text('SELECT 1'))
        
        # Check cache
        cache_healthy = cache.redis_client is not None
        
        # Get system health
        system_health = monitor._get_system_health()
        
        health_status = {
            'status': 'healthy' if system_health == 'healthy' else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {
                'database': 'healthy',
                'cache': 'healthy' if cache_healthy else 'degraded',
                'system': system_health
            }
        }
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

# Helper functions

def _get_business_metrics():
    """Get core business metrics"""
    try:
        # Use cached queries for better performance
        total_bags = QueryCache.cached_count(Bag)
        parent_bags = QueryCache.cached_count(Bag, type='parent')
        child_bags = QueryCache.cached_count(Bag, type='child')
        total_users = QueryCache.cached_count(User)
        total_scans = QueryCache.cached_count(Scan)
        total_bills = QueryCache.cached_count(Bill)
        
        # Calculate derived metrics
        today = datetime.utcnow().date()
        today_scans = db.session.query(func.count(Scan.id)).filter(
            func.date(Scan.timestamp) == today
        ).scalar() or 0
        
        return {
            'total_bags': total_bags,
            'parent_bags': parent_bags,
            'child_bags': child_bags,
            'total_users': total_users,
            'total_scans': total_scans,
            'total_bills': total_bills,
            'today_scans': today_scans,
            'link_rate': (child_bags / parent_bags * 100) if parent_bags > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Failed to get business metrics: {e}")
        return {}

def _get_response_time_metrics(start_time):
    """Get response time metrics"""
    try:
        # This would query from stored metrics in production
        # For now, return sample data
        return {
            'avg': 0.5,
            'p50': 0.3,
            'p95': 1.2,
            'p99': 2.5,
            'max': 5.0
        }
    except Exception as e:
        logger.error(f"Failed to get response time metrics: {e}")
        return {}

def _get_database_metrics(start_time):
    """Get database performance metrics"""
    try:
        db_health = db_scaler.get_health_metrics()
        
        return {
            'connections': db_health.get('active_connections', 0),
            'active_queries': db_health.get('active_queries', 0),
            'avg_query_duration': db_health.get('avg_query_duration', 0),
            'cache_hit_ratio': 95.0  # Would calculate from pg_stat_database
        }
        
    except Exception as e:
        logger.error(f"Failed to get database metrics: {e}")
        return {}

def _get_error_metrics(start_time):
    """Get error rate metrics"""
    try:
        # Calculate from application metrics
        app_stats = monitor._get_application_stats()
        
        return {
            'error_rate': app_stats.get('error_rate', 0),
            'total_errors': 0,  # Would query from logs
            'top_errors': []  # Would aggregate from logs
        }
        
    except Exception as e:
        logger.error(f"Failed to get error metrics: {e}")
        return {}

def _get_bag_totals():
    """Get bag totals by various dimensions"""
    try:
        # By area
        area_totals = db.session.query(
            Bag.dispatch_area,
            func.count(Bag.id).label('count')
        ).group_by(Bag.dispatch_area).all()
        
        return {
            'by_area': {area or 'unassigned': count for area, count in area_totals}
        }
        
    except Exception as e:
        logger.error(f"Failed to get bag totals: {e}")
        return {}

def _get_bag_growth_metrics():
    """Get bag growth metrics over time"""
    try:
        # Daily growth for last 30 days
        growth_data = db.session.query(
            func.date(Bag.created_at).label('date'),
            func.count(Bag.id).label('count')
        ).filter(
            Bag.created_at >= datetime.utcnow() - timedelta(days=30)
        ).group_by('date').all()
        
        return [{'date': str(date), 'count': count} for date, count in growth_data]
        
    except Exception as e:
        logger.error(f"Failed to get bag growth metrics: {e}")
        return []

def _get_user_activity_metrics():
    """Get user activity metrics"""
    try:
        # Active users by hour
        active_by_hour = db.session.query(
            func.date_trunc('hour', Scan.timestamp).label('hour'),
            func.count(func.distinct(Scan.user_id)).label('active_users')
        ).filter(
            Scan.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).group_by('hour').all()
        
        return {
            'hourly_active': [
                {'hour': str(hour), 'users': users} 
                for hour, users in active_by_hour
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get user activity metrics: {e}")
        return {}

def _get_user_role_distribution():
    """Get distribution of users by role"""
    try:
        role_dist = db.session.query(
            User.role,
            func.count(User.id).label('count')
        ).group_by(User.role).all()
        
        return {role: count for role, count in role_dist}
        
    except Exception as e:
        logger.error(f"Failed to get user role distribution: {e}")
        return {}