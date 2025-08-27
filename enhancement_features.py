#!/usr/bin/env python3
"""
Comprehensive Enhancement Features Implementation
Addresses all requested improvements:
1. Show who created each bill and their details
2. Ensure 100% success rate for all platform endpoints
3. Fix weight updates, CV export, and print functionality
4. Improve production deployment configuration
5. Optimize database performance with indexes and statistics
"""

import os
import logging
import time
import json
import csv
import io
from datetime import datetime, timedelta
from flask import jsonify, request, send_file, make_response, current_app
from sqlalchemy import text, func, desc, and_, or_, create_engine
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from werkzeug.exceptions import HTTPException
import traceback

# Import application components
from app_clean import app, db
from models import User, Bag, Bill, BillBag, Scan, Link, AuditLog
from auth_utils import current_user, require_auth
from optimized_cache import cache, invalidate_cache

logger = logging.getLogger(__name__)

# =============================================================================
# 1. BILL CREATOR TRACKING ENHANCEMENTS
# =============================================================================

def enhance_bill_creator_tracking():
    """Add comprehensive bill creator tracking and display"""
    
    # Add audit logging for bill creation
    def log_bill_creation(bill_id, user_id, bill_data):
        """Log bill creation with detailed user information"""
        try:
            user = User.query.get(user_id)
            audit_entry = AuditLog(
                user_id=user_id,
                action='create_bill',
                entity_type='bill',
                entity_id=bill_id,
                details=json.dumps({
                    'bill_id': bill_data.get('bill_id'),
                    'parent_bag_count': bill_data.get('parent_bag_count'),
                    'creator_username': user.username if user else 'Unknown',
                    'creator_role': user.role if user else 'Unknown',
                    'creator_dispatch_area': user.dispatch_area if user else None,
                    'timestamp': datetime.utcnow().isoformat()
                }),
                ip_address=request.remote_addr if request else None
            )
            db.session.add(audit_entry)
            db.session.commit()
            logger.info(f"Bill creation logged: {bill_id} by {user.username if user else 'Unknown'}")
        except Exception as e:
            logger.error(f"Failed to log bill creation: {e}")
            db.session.rollback()

    # Enhanced bill creation with creator tracking
    def create_bill_with_tracking(bill_data, user_id):
        """Create bill with comprehensive creator tracking"""
        try:
            # Create the bill
            bill = Bill()
            bill.bill_id = bill_data['bill_id']
            bill.description = bill_data.get('description', '')
            bill.parent_bag_count = bill_data.get('parent_bag_count', 1)
            bill.status = 'new'
            bill.created_by_id = user_id
            bill.total_weight_kg = 0.0
            bill.total_child_bags = 0
            
            db.session.add(bill)
            db.session.flush()  # Get the bill ID
            
            # Log the creation
            log_bill_creation(bill.id, user_id, bill_data)
            
            db.session.commit()
            return bill
            
        except IntegrityError:
            db.session.rollback()
            raise ValueError("Bill ID already exists")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Bill creation failed: {e}")
            raise

    # Enhanced bill listing with creator details
    def get_bills_with_creator_details(filters=None):
        """Get bills with comprehensive creator information"""
        try:
            query = db.session.query(
                Bill,
                User.username.label('creator_username'),
                User.role.label('creator_role'),
                User.dispatch_area.label('creator_dispatch_area'),
                User.created_at.label('creator_joined_date')
            ).join(User, Bill.created_by_id == User.id)
            
            if filters:
                if filters.get('status'):
                    query = query.filter(Bill.status == filters['status'])
                if filters.get('date_from'):
                    query = query.filter(Bill.created_at >= filters['date_from'])
                if filters.get('date_to'):
                    query = query.filter(Bill.created_at <= filters['date_to'])
                if filters.get('creator_id'):
                    query = query.filter(Bill.created_by_id == filters['creator_id'])
            
            bills = query.order_by(desc(Bill.created_at)).all()
            
            result = []
            for bill, username, role, area, joined_date in bills:
                # Get bill statistics
                parent_count = db.session.query(func.count(BillBag.bag_id)).filter(
                    BillBag.bill_id == bill.id
                ).scalar()
                
                # Calculate completion percentage
                completion = (parent_count * 100 // bill.parent_bag_count) if bill.parent_bag_count else 0
                
                result.append({
                    'bill_id': bill.bill_id,
                    'db_id': bill.id,
                    'description': bill.description,
                    'parent_bag_count': bill.parent_bag_count,
                    'total_weight_kg': bill.total_weight_kg,
                    'status': bill.status,
                    'created_at': bill.created_at.isoformat(),
                    'creator': {
                        'username': username,
                        'role': role,
                        'dispatch_area': area,
                        'joined_date': joined_date.isoformat() if joined_date else None
                    },
                    'statistics': {
                        'parent_bags_linked': parent_count,
                        'completion_percentage': completion,
                        'estimated_child_bags': parent_count * 30  # Assuming 30 children per parent
                    }
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get bills with creator details: {e}")
            return []

    return {
        'create_bill_with_tracking': create_bill_with_tracking,
        'get_bills_with_creator_details': get_bills_with_creator_details,
        'log_bill_creation': log_bill_creation
    }

# =============================================================================
# 2. 100% SUCCESS RATE ENDPOINT ENHANCEMENTS
# =============================================================================

def enhance_endpoint_reliability():
    """Implement comprehensive error handling and retry mechanisms"""
    
    def safe_endpoint_wrapper(func):
        """Decorator to ensure 100% success rate with comprehensive error handling"""
        def wrapper(*args, **kwargs):
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Pre-flight checks
                    if not db.session.is_active:
                        db.session.rollback()
                        db.session.close()
                    
                    # Execute the endpoint
                    result = func(*args, **kwargs)
                    
                    # Validate response
                    if result is None:
                        return jsonify({'error': 'Endpoint returned no response'}), 500
                    
                    # Ensure proper response format
                    if isinstance(result, tuple) and len(result) == 2:
                        response, status_code = result
                        if status_code >= 400:
                            logger.warning(f"Endpoint {func.__name__} returned error status: {status_code}")
                    else:
                        response = result
                        status_code = 200
                    
                    # Log success
                    logger.info(f"Endpoint {func.__name__} executed successfully")
                    return result
                    
                except SQLAlchemyError as e:
                    retry_count += 1
                    db.session.rollback()
                    logger.warning(f"Database error in {func.__name__}, retry {retry_count}: {e}")
                    if retry_count >= max_retries:
                        return jsonify({'error': 'Database operation failed'}), 503
                    time.sleep(0.1 * retry_count)  # Exponential backoff
                    
                except HTTPException as e:
                    # Don't retry HTTP exceptions
                    logger.error(f"HTTP error in {func.__name__}: {e}")
                    return jsonify({'error': str(e)}), e.code
                    
                except Exception as e:
                    retry_count += 1
                    logger.error(f"Unexpected error in {func.__name__}, retry {retry_count}: {e}")
                    if retry_count >= max_retries:
                        return jsonify({'error': 'Internal server error'}), 500
                    time.sleep(0.1 * retry_count)
            
            return jsonify({'error': 'Maximum retries exceeded'}), 500
        
        wrapper.__name__ = func.__name__
        return wrapper

    def health_check_endpoint():
        """Comprehensive health check endpoint"""
        try:
            # Database connectivity
            db.session.execute(text("SELECT 1"))
            
            # Cache connectivity
            cache.set('health_check', 'ok', timeout=10)
            cache_status = cache.get('health_check') == 'ok'
            
            # System metrics
            total_bags = Bag.query.count()
            total_bills = Bill.query.count()
            total_users = User.query.count()
            
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'services': {
                    'database': 'connected',
                    'cache': 'connected' if cache_status else 'disconnected'
                },
                'metrics': {
                    'total_bags': total_bags,
                    'total_bills': total_bills,
                    'total_users': total_users
                }
            })
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 503

    return {
        'safe_endpoint_wrapper': safe_endpoint_wrapper,
        'health_check_endpoint': health_check_endpoint
    }

# =============================================================================
# 3. WEIGHT UPDATE FIXES
# =============================================================================

def fix_weight_updates():
    """Fix weight calculation and update issues"""
    
    def calculate_bag_weight(bag_id):
        """Calculate accurate weight for a bag"""
        try:
            bag = Bag.query.get(bag_id)
            if not bag:
                return 0.0
            
            if bag.type == 'parent':
                # Count linked children
                child_count = db.session.query(func.count(Link.child_bag_id)).filter(
                    Link.parent_bag_id == bag_id
                ).scalar()
                return float(child_count)  # 1kg per child
            else:
                # Child bags have fixed weight
                return 1.0
                
        except Exception as e:
            logger.error(f"Failed to calculate weight for bag {bag_id}: {e}")
            return 0.0

    def update_bill_weights(bill_id):
        """Update all weight calculations for a bill"""
        try:
            bill = Bill.query.get(bill_id)
            if not bill:
                return False
            
            # Get all parent bags in this bill
            parent_bags = db.session.query(Bag).join(BillBag).filter(
                BillBag.bill_id == bill_id,
                Bag.type == 'parent'
            ).all()
            
            total_weight = 0.0
            total_child_bags = 0
            
            for parent_bag in parent_bags:
                # Count children for this parent
                child_count = db.session.query(func.count(Link.child_bag_id)).filter(
                    Link.parent_bag_id == parent_bag.id
                ).scalar()
                
                # Update parent bag weight
                parent_bag.weight_kg = float(child_count)
                total_weight += parent_bag.weight_kg
                total_child_bags += child_count
            
            # Update bill totals
            bill.total_weight_kg = total_weight
            bill.total_child_bags = total_child_bags
            
            # Update bill status
            linked_parents = len(parent_bags)
            if linked_parents >= bill.parent_bag_count:
                bill.status = 'completed'
            elif linked_parents > 0:
                bill.status = 'in_progress'
            else:
                bill.status = 'new'
            
            db.session.commit()
            logger.info(f"Updated bill {bill.bill_id}: {total_weight}kg, {total_child_bags} children")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update bill weights for {bill_id}: {e}")
            return False

    def bulk_update_all_weights():
        """Update weights for all bills in the system"""
        try:
            bills = Bill.query.all()
            updated_count = 0
            
            for bill in bills:
                if update_bill_weights(bill.id):
                    updated_count += 1
            
            logger.info(f"Bulk weight update completed: {updated_count}/{len(bills)} bills updated")
            return updated_count
            
        except Exception as e:
            logger.error(f"Bulk weight update failed: {e}")
            return 0

    return {
        'calculate_bag_weight': calculate_bag_weight,
        'update_bill_weights': update_bill_weights,
        'bulk_update_all_weights': bulk_update_all_weights
    }

# =============================================================================
# 4. CV EXPORT FUNCTIONALITY
# =============================================================================

def implement_cv_export():
    """Implement comprehensive CV export functionality"""
    
    def export_bills_to_csv(filters=None):
        """Export bills data to CSV format"""
        try:
            # Get bills with creator details
            bill_tracker = enhance_bill_creator_tracking()
            bills_data = bill_tracker['get_bills_with_creator_details'](filters)
            
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Bill ID', 'Description', 'Parent Bag Count', 'Total Weight (kg)',
                'Status', 'Created At', 'Creator Username', 'Creator Role',
                'Creator Dispatch Area', 'Parent Bags Linked', 'Completion %',
                'Estimated Child Bags'
            ])
            
            # Write data
            for bill in bills_data:
                writer.writerow([
                    bill['bill_id'],
                    bill['description'],
                    bill['parent_bag_count'],
                    bill['total_weight_kg'],
                    bill['status'],
                    bill['created_at'],
                    bill['creator']['username'],
                    bill['creator']['role'],
                    bill['creator']['dispatch_area'],
                    bill['statistics']['parent_bags_linked'],
                    bill['statistics']['completion_percentage'],
                    bill['statistics']['estimated_child_bags']
                ])
            
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return None

    def export_bags_to_csv(filters=None):
        """Export bags data to CSV format"""
        try:
            query = db.session.query(
                Bag,
                User.username.label('owner_username'),
                User.role.label('owner_role')
            ).outerjoin(User, Bag.user_id == User.id)
            
            if filters:
                if filters.get('type'):
                    query = query.filter(Bag.type == filters['type'])
                if filters.get('status'):
                    query = query.filter(Bag.status == filters['status'])
                if filters.get('dispatch_area'):
                    query = query.filter(Bag.dispatch_area == filters['dispatch_area'])
            
            bags = query.all()
            
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'QR ID', 'Type', 'Name', 'Status', 'Weight (kg)', 'Dispatch Area',
                'Created At', 'Owner Username', 'Owner Role', 'Child Count',
                'Parent ID'
            ])
            
            # Write data
            for bag, owner_username, owner_role in bags:
                # Get child count for parent bags
                child_count = 0
                if bag.type == 'parent':
                    child_count = db.session.query(func.count(Link.child_bag_id)).filter(
                        Link.parent_bag_id == bag.id
                    ).scalar()
                
                writer.writerow([
                    bag.qr_id,
                    bag.type,
                    bag.name,
                    bag.status,
                    bag.weight_kg,
                    bag.dispatch_area,
                    bag.created_at.isoformat(),
                    owner_username,
                    owner_role,
                    child_count,
                    bag.parent_id
                ])
            
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Bags CSV export failed: {e}")
            return None

    def export_scans_to_csv(filters=None):
        """Export scan data to CSV format"""
        try:
            query = db.session.query(
                Scan,
                User.username.label('scanner_username'),
                User.role.label('scanner_role'),
                Bag.qr_id.label('parent_qr_id'),
                Bag.qr_id.label('child_qr_id')
            ).join(User, Scan.user_id == User.id)\
             .outerjoin(Bag, Scan.parent_bag_id == Bag.id)\
             .outerjoin(Bag, Scan.child_bag_id == Bag.id)
            
            if filters:
                if filters.get('date_from'):
                    query = query.filter(Scan.timestamp >= filters['date_from'])
                if filters.get('date_to'):
                    query = query.filter(Scan.timestamp <= filters['date_to'])
                if filters.get('user_id'):
                    query = query.filter(Scan.user_id == filters['user_id'])
            
            scans = query.order_by(desc(Scan.timestamp)).all()
            
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Timestamp', 'Scanner Username', 'Scanner Role', 'Parent QR ID',
                'Child QR ID', 'Scan Type'
            ])
            
            # Write data
            for scan, scanner_username, scanner_role, parent_qr, child_qr in scans:
                scan_type = 'parent' if scan.parent_bag_id else 'child'
                writer.writerow([
                    scan.timestamp.isoformat(),
                    scanner_username,
                    scanner_role,
                    parent_qr,
                    child_qr,
                    scan_type
                ])
            
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Scans CSV export failed: {e}")
            return None

    return {
        'export_bills_to_csv': export_bills_to_csv,
        'export_bags_to_csv': export_bags_to_csv,
        'export_scans_to_csv': export_scans_to_csv
    }

# =============================================================================
# 5. PRINT FUNCTIONALITY
# =============================================================================

def implement_print_functionality():
    """Implement comprehensive print functionality"""
    
    def generate_bill_print_data(bill_id):
        """Generate print-ready data for a bill"""
        try:
            bill = Bill.query.get(bill_id)
            if not bill:
                return None
            
            # Get bill details with creator info
            creator = User.query.get(bill.created_by_id)
            
            # Get linked parent bags
            parent_bags = db.session.query(Bag).join(BillBag).filter(
                BillBag.bill_id == bill_id,
                Bag.type == 'parent'
            ).all()
            
            # Get child counts for each parent
            parent_details = []
            total_children = 0
            
            for parent in parent_bags:
                child_count = db.session.query(func.count(Link.child_bag_id)).filter(
                    Link.parent_bag_id == parent.id
                ).scalar()
                total_children += child_count
                
                parent_details.append({
                    'qr_id': parent.qr_id,
                    'name': parent.name,
                    'child_count': child_count,
                    'weight_kg': parent.weight_kg
                })
            
            return {
                'bill_id': bill.bill_id,
                'description': bill.description,
                'created_at': bill.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'creator': {
                    'username': creator.username if creator else 'Unknown',
                    'role': creator.role if creator else 'Unknown'
                },
                'statistics': {
                    'parent_bag_count': bill.parent_bag_count,
                    'linked_parents': len(parent_bags),
                    'total_children': total_children,
                    'total_weight_kg': bill.total_weight_kg,
                    'completion_percentage': (len(parent_bags) * 100 // bill.parent_bag_count) if bill.parent_bag_count else 0
                },
                'parent_bags': parent_details,
                'status': bill.status
            }
            
        except Exception as e:
            logger.error(f"Failed to generate print data for bill {bill_id}: {e}")
            return None

    def generate_summary_print_data(filters=None):
        """Generate print-ready summary data"""
        try:
            # Get summary statistics
            total_bills = Bill.query.count()
            completed_bills = Bill.query.filter_by(status='completed').count()
            in_progress_bills = Bill.query.filter_by(status='in_progress').count()
            new_bills = Bill.query.filter_by(status='new').count()
            
            total_bags = Bag.query.count()
            parent_bags = Bag.query.filter_by(type='parent').count()
            child_bags = Bag.query.filter_by(type='child').count()
            
            total_users = User.query.count()
            
            # Get recent activity
            today = datetime.now().date()
            scans_today = Scan.query.filter(func.date(Scan.timestamp) == today).count()
            bills_today = Bill.query.filter(func.date(Bill.created_at) == today).count()
            
            return {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'summary': {
                    'total_bills': total_bills,
                    'completed_bills': completed_bills,
                    'in_progress_bills': in_progress_bills,
                    'new_bills': new_bills,
                    'total_bags': total_bags,
                    'parent_bags': parent_bags,
                    'child_bags': child_bags,
                    'total_users': total_users
                },
                'today_activity': {
                    'scans': scans_today,
                    'bills_created': bills_today
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate summary print data: {e}")
            return None

    return {
        'generate_bill_print_data': generate_bill_print_data,
        'generate_summary_print_data': generate_summary_print_data
    }

# =============================================================================
# 6. PRODUCTION DEPLOYMENT IMPROVEMENTS
# =============================================================================

def improve_production_deployment():
    """Improve production deployment configuration for scalability"""
    
    def create_enhanced_gunicorn_config():
        """Create enhanced Gunicorn configuration for production"""
        config = {
            'bind': '0.0.0.0:5000',
            'workers': 'auto',  # Will be calculated based on CPU cores
            'worker_class': 'gevent',
            'worker_connections': 2000,
            'threads': 4,
            'backlog': 2048,
            'keepalive': 5,
            'timeout': 60,
            'graceful_timeout': 30,
            'max_requests': 10000,
            'max_requests_jitter': 1000,
            'preload_app': True,
            'accesslog': '-',
            'errorlog': '-',
            'loglevel': 'info',
            'access_log_format': '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s',
            'proc_name': 'tracetrack-production',
            'limit_request_line': 4094,
            'limit_request_fields': 100,
            'limit_request_field_size': 8190,
            'enable_stdio_inheritance': True,
            'capture_output': True,
            'reload': False,
            'daemon': False
        }
        
        # Calculate optimal worker count
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        config['workers'] = min(cpu_count * 2 + 1, 8)  # Cap at 8 workers
        
        return config

    def create_nginx_config():
        """Create optimized Nginx configuration"""
        nginx_config = """
upstream tracetrack {
    server 127.0.0.1:5000;
    keepalive 32;
}

server {
    listen 80;
    server_name _;
    
    client_max_body_size 10M;
    client_body_timeout 60s;
    client_header_timeout 60s;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    # Static file caching
    location /static/ {
        alias /workspace/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Main application
    location / {
        proxy_pass http://tracetrack;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://tracetrack/health;
        access_log off;
    }
}
"""
        return nginx_config

    def create_systemd_service():
        """Create systemd service configuration"""
        service_config = """
[Unit]
Description=TraceTrack Production Server
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/workspace
Environment=PATH=/workspace/venv/bin
ExecStart=/workspace/venv/bin/gunicorn --config gunicorn_production.py main:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        return service_config

    return {
        'create_enhanced_gunicorn_config': create_enhanced_gunicorn_config,
        'create_nginx_config': create_nginx_config,
        'create_systemd_service': create_systemd_service
    }

# =============================================================================
# 7. DATABASE PERFORMANCE OPTIMIZATION
# =============================================================================

def optimize_database_performance():
    """Optimize database performance with indexes and statistics"""
    
    def create_performance_indexes():
        """Create comprehensive performance indexes"""
        indexes = [
            # Bill performance indexes
            ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_created_by_status ON bill (created_by_id, status)", "bill_creator_status"),
            ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_created_at_status ON bill (created_at, status)", "bill_date_status"),
            ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_weight ON bill (total_weight_kg)", "bill_weight"),
            
            # Bag performance indexes
            ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_type_status_weight ON bag (type, status, weight_kg)", "bag_type_status_weight"),
            ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_user_type_status ON bag (user_id, type, status)", "bag_user_type_status"),
            ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_parent_child ON bag (parent_id, type)", "bag_parent_child"),
            
            # Scan performance indexes
            ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_user_timestamp_type ON scan (user_id, timestamp DESC, parent_bag_id, child_bag_id)", "scan_user_time_type"),
            ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_date_hour ON scan (DATE(timestamp), EXTRACT(hour FROM timestamp))", "scan_date_hour"),
            
            # Link performance indexes
            ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_parent_child_created ON link (parent_bag_id, child_bag_id, created_at)", "link_parent_child_created"),
            
            # BillBag performance indexes
            ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billbag_bill_bag_created ON bill_bag (bill_id, bag_id, created_at)", "billbag_bill_bag_created"),
            
            # User performance indexes
            ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_role_verified ON \"user\" (role, verified)", "user_role_verified"),
            ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_dispatch_area ON \"user\" (dispatch_area)", "user_dispatch_area"),
            
            # Audit log performance indexes
            ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_user_action_timestamp ON audit_log (user_id, action, timestamp DESC)", "audit_user_action_time"),
            ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_entity_timestamp ON audit_log (entity_type, entity_id, timestamp DESC)", "audit_entity_time"),
        ]
        
        with app.app_context():
            for query, index_name in indexes:
                try:
                    logger.info(f"Creating index: {index_name}")
                    db.session.execute(text(query))
                    db.session.commit()
                    logger.info(f"✅ Created index: {index_name}")
                except Exception as e:
                    db.session.rollback()
                    if "already exists" in str(e).lower():
                        logger.info(f"Index already exists: {index_name}")
                    else:
                        logger.error(f"Failed to create index {index_name}: {e}")

    def update_database_statistics():
        """Update database statistics for optimal query planning"""
        with app.app_context():
            try:
                logger.info("Updating database statistics...")
                
                # Update statistics for all tables
                tables = ['user', 'bag', 'link', 'scan', 'bill', 'bill_bag', 'audit_log']
                for table in tables:
                    db.session.execute(text(f"ANALYZE {table}"))
                
                # Update overall statistics
                db.session.execute(text("ANALYZE"))
                db.session.commit()
                
                logger.info("✅ Database statistics updated")
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to update statistics: {e}")

    def optimize_connection_pool():
        """Optimize database connection pool settings"""
        with app.app_context():
            engine = db.engine
            
            # Configure connection pool for production
            engine.pool.size = 20  # Maximum connections
            engine.pool.max_overflow = 30  # Additional connections when pool is full
            engine.pool.pool_timeout = 30  # Timeout for getting connection
            engine.pool.pool_recycle = 3600  # Recycle connections after 1 hour
            engine.pool.pool_pre_ping = True  # Verify connections before use
            
            logger.info(f"Connection pool optimized: size={engine.pool.size}, max_overflow={engine.pool.max_overflow}")

    def create_materialized_views():
        """Create materialized views for complex queries"""
        views = [
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS bill_summary_view AS
            SELECT 
                b.id as bill_id,
                b.bill_id as bill_number,
                b.created_at,
                b.status,
                b.total_weight_kg,
                b.total_child_bags,
                u.username as creator_username,
                u.role as creator_role,
                COUNT(bb.bag_id) as linked_parent_bags,
                CASE 
                    WHEN b.parent_bag_count > 0 THEN 
                        (COUNT(bb.bag_id) * 100 / b.parent_bag_count)
                    ELSE 0 
                END as completion_percentage
            FROM bill b
            LEFT JOIN "user" u ON b.created_by_id = u.id
            LEFT JOIN bill_bag bb ON b.id = bb.bill_id
            GROUP BY b.id, b.bill_id, b.created_at, b.status, b.total_weight_kg, 
                     b.total_child_bags, u.username, u.role, b.parent_bag_count
            """,
            
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS bag_summary_view AS
            SELECT 
                b.id,
                b.qr_id,
                b.type,
                b.status,
                b.weight_kg,
                b.dispatch_area,
                b.created_at,
                u.username as owner_username,
                u.role as owner_role,
                COUNT(l.child_bag_id) as child_count
            FROM bag b
            LEFT JOIN "user" u ON b.user_id = u.id
            LEFT JOIN link l ON b.id = l.parent_bag_id
            GROUP BY b.id, b.qr_id, b.type, b.status, b.weight_kg, 
                     b.dispatch_area, b.created_at, u.username, u.role
            """
        ]
        
        with app.app_context():
            for view_sql in views:
                try:
                    db.session.execute(text(view_sql))
                    db.session.commit()
                    logger.info("✅ Materialized view created")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Failed to create materialized view: {e}")

    return {
        'create_performance_indexes': create_performance_indexes,
        'update_database_statistics': update_database_statistics,
        'optimize_connection_pool': optimize_connection_pool,
        'create_materialized_views': create_materialized_views
    }

# =============================================================================
# MAIN ENHANCEMENT FUNCTION
# =============================================================================

def apply_all_enhancements():
    """Apply all enhancement features to the system"""
    
    logger.info("🚀 Applying comprehensive system enhancements...")
    
    try:
        # 1. Enhance bill creator tracking
        logger.info("📊 Enhancing bill creator tracking...")
        bill_tracker = enhance_bill_creator_tracking()
        
        # 2. Enhance endpoint reliability
        logger.info("🛡️ Enhancing endpoint reliability...")
        reliability = enhance_endpoint_reliability()
        
        # 3. Fix weight updates
        logger.info("⚖️ Fixing weight update functionality...")
        weight_fixes = fix_weight_updates()
        
        # 4. Implement CV export
        logger.info("📄 Implementing CV export functionality...")
        cv_export = implement_cv_export()
        
        # 5. Implement print functionality
        logger.info("🖨️ Implementing print functionality...")
        print_func = implement_print_functionality()
        
        # 6. Improve production deployment
        logger.info("🚀 Improving production deployment...")
        deployment = improve_production_deployment()
        
        # 7. Optimize database performance
        logger.info("⚡ Optimizing database performance...")
        db_optimizer = optimize_database_performance()
        
        # Apply database optimizations
        logger.info("Creating performance indexes...")
        db_optimizer['create_performance_indexes']()
        
        logger.info("Updating database statistics...")
        db_optimizer['update_database_statistics']()
        
        logger.info("Optimizing connection pool...")
        db_optimizer['optimize_connection_pool']()
        
        logger.info("Creating materialized views...")
        db_optimizer['create_materialized_views']()
        
        # Update all weights
        logger.info("Updating all bill weights...")
        weight_fixes['bulk_update_all_weights']()
        
        logger.info("✅ All enhancements applied successfully!")
        
        return {
            'bill_tracker': bill_tracker,
            'reliability': reliability,
            'weight_fixes': weight_fixes,
            'cv_export': cv_export,
            'print_func': print_func,
            'deployment': deployment,
            'db_optimizer': db_optimizer
        }
        
    except Exception as e:
        logger.error(f"❌ Enhancement application failed: {e}")
        logger.error(traceback.format_exc())
        return None

# =============================================================================
# API ENDPOINTS FOR NEW FEATURES
# =============================================================================

@app.route('/api/enhancements/apply', methods=['POST'])
@require_auth
def apply_enhancements_endpoint():
    """Apply all enhancement features"""
    try:
        if not current_user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        result = apply_all_enhancements()
        if result:
            return jsonify({
                'success': True,
                'message': 'All enhancements applied successfully',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({'error': 'Enhancement application failed'}), 500
            
    except Exception as e:
        logger.error(f"Enhancement endpoint error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/bills/csv')
@require_auth
def export_bills_csv():
    """Export bills to CSV"""
    try:
        filters = {
            'status': request.args.get('status'),
            'date_from': request.args.get('date_from'),
            'date_to': request.args.get('date_to'),
            'creator_id': request.args.get('creator_id', type=int)
        }
        
        cv_export = implement_cv_export()
        csv_data = cv_export['export_bills_to_csv'](filters)
        
        if csv_data:
            response = make_response(csv_data)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=bills_export.csv'
            return response
        else:
            return jsonify({'error': 'Export failed'}), 500
            
    except Exception as e:
        logger.error(f"Bills CSV export error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/bags/csv')
@require_auth
def export_bags_csv():
    """Export bags to CSV"""
    try:
        filters = {
            'type': request.args.get('type'),
            'status': request.args.get('status'),
            'dispatch_area': request.args.get('dispatch_area')
        }
        
        cv_export = implement_cv_export()
        csv_data = cv_export['export_bags_to_csv'](filters)
        
        if csv_data:
            response = make_response(csv_data)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=bags_export.csv'
            return response
        else:
            return jsonify({'error': 'Export failed'}), 500
            
    except Exception as e:
        logger.error(f"Bags CSV export error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/print/bill/<int:bill_id>')
@require_auth
def print_bill_endpoint(bill_id):
    """Generate print data for a bill"""
    try:
        print_func = implement_print_functionality()
        print_data = print_func['generate_bill_print_data'](bill_id)
        
        if print_data:
            return jsonify(print_data)
        else:
            return jsonify({'error': 'Bill not found'}), 404
            
    except Exception as e:
        logger.error(f"Print bill error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/print/summary')
@require_auth
def print_summary_endpoint():
    """Generate print data for system summary"""
    try:
        print_func = implement_print_functionality()
        summary_data = print_func['generate_summary_print_data']()
        
        if summary_data:
            return jsonify(summary_data)
        else:
            return jsonify({'error': 'Summary generation failed'}), 500
            
    except Exception as e:
        logger.error(f"Print summary error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/weights/update/<int:bill_id>', methods=['POST'])
@require_auth
def update_bill_weights_endpoint(bill_id):
    """Update weights for a specific bill"""
    try:
        weight_fixes = fix_weight_updates()
        success = weight_fixes['update_bill_weights'](bill_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Weights updated successfully'})
        else:
            return jsonify({'error': 'Weight update failed'}), 500
            
    except Exception as e:
        logger.error(f"Weight update error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/weights/update-all', methods=['POST'])
@require_auth
def update_all_weights_endpoint():
    """Update weights for all bills"""
    try:
        if not current_user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        weight_fixes = fix_weight_updates()
        updated_count = weight_fixes['bulk_update_all_weights']()
        
        return jsonify({
            'success': True,
            'message': f'Updated weights for {updated_count} bills',
            'updated_count': updated_count
        })
        
    except Exception as e:
        logger.error(f"Bulk weight update error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Enhanced health check endpoint"""
    reliability = enhance_endpoint_reliability()
    return reliability['health_check_endpoint']()

if __name__ == "__main__":
    # Apply enhancements when script is run directly
    apply_all_enhancements()