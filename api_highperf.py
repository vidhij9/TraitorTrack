"""
High-performance API routes for TraceTrack
Optimized for 50+ concurrent users and 800,000+ bags
"""

from flask import Blueprint, jsonify, request
from app_clean import db, limiter
from models import User, Bag, Bill, BillBag, Scan, Link, BagType
from ultra_cache import cache, cached_result, invalidate_pattern
from sqlalchemy import text
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

# Create optimized API blueprint
api_bp = Blueprint('api_highperf', __name__, url_prefix='/api')

# Helper function for fast JSON responses
def fast_json_response(data, status=200):
    """Create a fast JSON response"""
    response = jsonify(data)
    response.status_code = status
    return response

# Health check endpoint - no database access
@api_bp.route('/health', methods=['GET'])
def health_check():
    """Ultra-fast health check"""
    return fast_json_response({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

# Optimized scan parent endpoint
@api_bp.route('/scan_parent', methods=['POST'])
@limiter.limit("1000 per minute")
def scan_parent():
    """Optimized parent bag scanning"""
    try:
        data = request.get_json()
        if not data:
            return fast_json_response({'error': 'No data provided'}, 400)
        
        qr_id = data.get('qr_id', '').strip()
        if not qr_id:
            return fast_json_response({'error': 'QR ID required'}, 400)
        
        # Check cache first
        cache_key = f"parent_bag:{qr_id}"
        cached_bag = cache.get(cache_key)
        
        if cached_bag:
            return fast_json_response({'status': 'success', 'bag_id': cached_bag, 'cached': True})
        
        # Quick database check using optimized query
        bag = db.session.query(Bag).filter_by(qr_id=qr_id, type=BagType.PARENT.value).first()
        
        if not bag:
            # Create new parent bag
            bag = Bag()
            bag.qr_id = qr_id
            bag.type = BagType.PARENT.value
            bag.name = data.get('name', f'Parent {qr_id}')
            bag.child_count = data.get('child_count', 0)
            db.session.add(bag)
            db.session.commit()
        
        # Cache the result
        cache.set(cache_key, bag.id)
        
        return fast_json_response({
            'status': 'success',
            'bag_id': bag.id,
            'qr_id': bag.qr_id,
            'cached': False
        })
        
    except Exception as e:
        logger.error(f"Error in scan_parent: {str(e)}")
        db.session.rollback()
        return fast_json_response({'error': 'Processing error'}, 500)

# Optimized scan child endpoint
@api_bp.route('/scan_child', methods=['POST'])
@limiter.limit("1000 per minute")
def scan_child():
    """Optimized child bag scanning"""
    try:
        data = request.get_json()
        if not data:
            return fast_json_response({'error': 'No data provided'}, 400)
        
        parent_qr = data.get('parent_qr', '').strip()
        child_qrs = data.get('child_qrs', [])
        
        if not parent_qr or not child_qrs:
            return fast_json_response({'error': 'Parent QR and child QRs required'}, 400)
        
        # Get parent bag (from cache if possible)
        cache_key = f"parent_bag:{parent_qr}"
        parent_id = cache.get(cache_key)
        
        if not parent_id:
            parent_bag = db.session.query(Bag).filter_by(qr_id=parent_qr, type=BagType.PARENT.value).first()
            if not parent_bag:
                return fast_json_response({'error': 'Parent bag not found'}, 404)
            parent_id = parent_bag.id
            cache.set(cache_key, parent_id)
        
        # Process child bags in batch
        processed = []
        for child_qr in child_qrs[:30]:  # Limit to 30 children
            child_qr = child_qr.strip()
            if not child_qr:
                continue
            
            # Check if child exists
            child_bag = db.session.query(Bag).filter_by(qr_id=child_qr).first()
            if not child_bag:
                # Create new child bag
                child_bag = Bag()
                child_bag.qr_id = child_qr
                child_bag.type = BagType.CHILD.value
                child_bag.parent_id = parent_id
                db.session.add(child_bag)
            
            # Create link if doesn't exist
            existing_link = db.session.query(Link).filter_by(
                parent_bag_id=parent_id,
                child_bag_id=child_bag.id
            ).first()
            
            if not existing_link:
                link = Link()
                link.parent_bag_id = parent_id
                link.child_bag_id = child_bag.id
                db.session.add(link)
            
            processed.append(child_qr)
        
        # Commit all changes at once
        db.session.commit()
        
        # Invalidate related caches
        invalidate_pattern(f"parent_bag:{parent_qr}")
        
        return fast_json_response({
            'status': 'success',
            'parent_qr': parent_qr,
            'processed_children': len(processed),
            'child_qrs': processed
        })
        
    except Exception as e:
        logger.error(f"Error in scan_child: {str(e)}")
        db.session.rollback()
        return fast_json_response({'error': 'Processing error'}, 500)

# Optimized bill creation endpoint
@api_bp.route('/create_bill', methods=['POST'])
@limiter.limit("500 per minute")
def create_bill():
    """Optimized bill creation"""
    try:
        data = request.get_json()
        if not data:
            return fast_json_response({'error': 'No data provided'}, 400)
        
        bill_id = data.get('bill_id', '').strip()
        if not bill_id:
            return fast_json_response({'error': 'Bill ID required'}, 400)
        
        # Check if bill exists
        existing_bill = db.session.query(Bill).filter_by(bill_id=bill_id).first()
        if existing_bill:
            return fast_json_response({
                'status': 'exists',
                'bill_id': existing_bill.id,
                'bill_number': existing_bill.bill_id
            })
        
        # Create new bill
        bill = Bill()
        bill.bill_id = bill_id
        bill.description = data.get('description', '')
        bill.parent_bag_count = data.get('parent_bag_count', 1)
        bill.status = 'new'
        
        db.session.add(bill)
        db.session.commit()
        
        return fast_json_response({
            'status': 'created',
            'bill_id': bill.id,
            'bill_number': bill.bill_id
        })
        
    except Exception as e:
        logger.error(f"Error in create_bill: {str(e)}")
        db.session.rollback()
        return fast_json_response({'error': 'Processing error'}, 500)

# Optimized link bill to bag endpoint
@api_bp.route('/link_bill_bag', methods=['POST'])
@limiter.limit("500 per minute")
def link_bill_bag():
    """Link bill to parent bag"""
    try:
        data = request.get_json()
        if not data:
            return fast_json_response({'error': 'No data provided'}, 400)
        
        bill_id = data.get('bill_id')
        bag_qr = data.get('bag_qr', '').strip()
        
        if not bill_id or not bag_qr:
            return fast_json_response({'error': 'Bill ID and bag QR required'}, 400)
        
        # Get bill and bag
        bill = db.session.query(Bill).filter_by(id=bill_id).first()
        if not bill:
            return fast_json_response({'error': 'Bill not found'}, 404)
        
        bag = db.session.query(Bag).filter_by(qr_id=bag_qr, type=BagType.PARENT.value).first()
        if not bag:
            return fast_json_response({'error': 'Parent bag not found'}, 404)
        
        # Check if link exists
        existing_link = db.session.query(BillBag).filter_by(
            bill_id=bill.id,
            bag_id=bag.id
        ).first()
        
        if existing_link:
            return fast_json_response({'status': 'already_linked'})
        
        # Create link
        bill_bag = BillBag()
        bill_bag.bill_id = bill.id
        bill_bag.bag_id = bag.id
        
        db.session.add(bill_bag)
        db.session.commit()
        
        return fast_json_response({'status': 'linked'})
        
    except Exception as e:
        logger.error(f"Error in link_bill_bag: {str(e)}")
        db.session.rollback()
        return fast_json_response({'error': 'Processing error'}, 500)

# Optimized query endpoint
@api_bp.route('/query_bills', methods=['GET'])
@limiter.limit("100 per minute")
@cached_result(ttl=30, key_prefix='bills_query')
def query_bills():
    """Query bills with caching"""
    try:
        # Use raw SQL for speed
        query = text("""
            SELECT b.id, b.bill_id, b.description, b.status, 
                   COUNT(DISTINCT bb.bag_id) as bag_count
            FROM bill b
            LEFT JOIN bill_bag bb ON b.id = bb.bill_id
            GROUP BY b.id, b.bill_id, b.description, b.status
            ORDER BY b.created_at DESC
            LIMIT 100
        """)
        
        result = db.session.execute(query)
        bills = []
        for row in result:
            bills.append({
                'id': row[0],
                'bill_id': row[1],
                'description': row[2],
                'status': row[3],
                'bag_count': row[4]
            })
        
        return fast_json_response({'bills': bills})
        
    except Exception as e:
        logger.error(f"Error in query_bills: {str(e)}")
        return fast_json_response({'error': 'Query error'}, 500)

# System stats endpoint with caching
@api_bp.route('/stats', methods=['GET'])
@limiter.limit("1000 per minute")
@cached_result(ttl=10, key_prefix='system_stats')
def system_stats():
    """Get system statistics with caching"""
    try:
        # Use optimized count queries
        stats = {
            'total_bags': db.session.query(Bag).count(),
            'parent_bags': db.session.query(Bag).filter_by(type=BagType.PARENT.value).count(),
            'child_bags': db.session.query(Bag).filter_by(type=BagType.CHILD.value).count(),
            'total_bills': db.session.query(Bill).count(),
            'total_scans': db.session.query(Scan).count(),
            'total_links': db.session.query(Link).count()
        }
        
        return fast_json_response(stats)
        
    except Exception as e:
        logger.error(f"Error in system_stats: {str(e)}")
        return fast_json_response({'error': 'Stats error'}, 500)

# Register the optimized API blueprint
def register_api(app):
    """Register the high-performance API with the app"""
    app.register_blueprint(api_bp)
    logger.info("High-performance API registered")