"""
Health check and monitoring endpoints for production deployment
"""
import os
import time
import psutil
import logging
from flask import jsonify, Blueprint
from datetime import datetime, timedelta
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Create monitoring blueprint
monitoring_bp = Blueprint('monitoring', __name__)

# Store application start time
APP_START_TIME = datetime.utcnow()

def get_database_status(db):
    """Check database connectivity and performance"""
    try:
        start_time = time.time()
        result = db.session.execute(text("SELECT 1")).scalar()
        query_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Get connection pool stats
        pool = db.engine.pool
        pool_status = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow()
        }
        
        return {
            "status": "healthy" if result == 1 else "unhealthy",
            "query_time_ms": round(query_time, 2),
            "pool_status": pool_status
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "pool_status": {}
        }

def get_system_metrics():
    """Get system resource metrics"""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_gb = memory.available / (1024 ** 3)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_free_gb = disk.free / (1024 ** 3)
        
        # Process metrics
        process = psutil.Process()
        process_memory_mb = process.memory_info().rss / (1024 ** 2)
        process_cpu = process.cpu_percent(interval=0.1)
        process_threads = process.num_threads()
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "cores": cpu_count
            },
            "memory": {
                "percent": memory_percent,
                "available_gb": round(memory_available_gb, 2)
            },
            "disk": {
                "percent": disk_percent,
                "free_gb": round(disk_free_gb, 2)
            },
            "process": {
                "memory_mb": round(process_memory_mb, 2),
                "cpu_percent": process_cpu,
                "threads": process_threads
            }
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {str(e)}")
        return {}

def get_application_metrics(app, db):
    """Get application-specific metrics"""
    try:
        from models import User, Bag, Bill, Scan
        
        # Count entities
        with app.app_context():
            user_count = User.query.count()
            bag_count = Bag.query.count()
            bill_count = Bill.query.count()
            scan_count = Scan.query.count()
            
            # Recent activity (last hour)
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_scans = Scan.query.filter(Scan.timestamp >= one_hour_ago).count()
            recent_bills = Bill.query.filter(Bill.created_at >= one_hour_ago).count()
        
        # Calculate uptime
        uptime = datetime.utcnow() - APP_START_TIME
        uptime_seconds = int(uptime.total_seconds())
        uptime_hours = uptime_seconds // 3600
        uptime_minutes = (uptime_seconds % 3600) // 60
        
        return {
            "entities": {
                "users": user_count,
                "bags": bag_count,
                "bills": bill_count,
                "scans": scan_count
            },
            "recent_activity": {
                "scans_last_hour": recent_scans,
                "bills_last_hour": recent_bills
            },
            "uptime": {
                "hours": uptime_hours,
                "minutes": uptime_minutes,
                "total_seconds": uptime_seconds
            }
        }
    except Exception as e:
        logger.error(f"Failed to get application metrics: {str(e)}")
        return {}

@monitoring_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "TraceTrack API",
        "version": "1.0.0"
    }), 200

@monitoring_bp.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check - verifies all dependencies are working"""
    from app import app, db
    
    # Check database
    db_status = get_database_status(db)
    
    # Overall readiness
    is_ready = db_status["status"] == "healthy"
    
    response = {
        "ready": is_ready,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": db_status["status"]
        }
    }
    
    return jsonify(response), 200 if is_ready else 503

@monitoring_bp.route('/metrics', methods=['GET'])
def metrics():
    """Comprehensive metrics endpoint"""
    from app import app, db
    
    # Collect all metrics
    db_status = get_database_status(db)
    system_metrics = get_system_metrics()
    app_metrics = get_application_metrics(app, db)
    
    response = {
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "system": system_metrics,
        "application": app_metrics
    }
    
    return jsonify(response), 200

@monitoring_bp.route('/ping', methods=['GET'])
def ping():
    """Simple ping endpoint for load balancer health checks"""
    return "pong", 200

def register_monitoring_endpoints(app):
    """Register monitoring endpoints with the Flask app"""
    app.register_blueprint(monitoring_bp)
    logger.info("Monitoring endpoints registered at /health, /ready, /metrics, and /ping")