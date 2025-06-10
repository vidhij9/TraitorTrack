"""
Asynchronous processing module for traitor track application.
Implements background processing for better responsiveness.
"""

import logging
import time
from datetime import datetime
from task_queue import async_task
from models import Bag, BagType, Scan, User, Location
from app import db
from cache_utils import invalidate_cache

logger = logging.getLogger(__name__)

@async_task
def process_scan_async(scan_data):
    """
    Process scan data asynchronously to improve UI responsiveness.
    
    Args:
        scan_data: Dictionary with scan information
    
    Returns:
        dict: Processing result
    """
    start_time = time.time()
    logger.info(f"Starting async processing of scan for {scan_data.get('qr_id')}")
    
    try:
        # Record the scan in the database
        scan = Scan()
        scan.user_id = scan_data['user_id']
        scan.location_id = scan_data['location_id']
        scan.scan_type = scan_data['scan_type']
        scan.notes = scan_data.get('notes', '')
        
        # Process based on scan type
        if scan_data['scan_type'] == 'parent':
            parent_bag = Bag.query.filter_by(
                qr_id=scan_data['qr_id'], 
                type=BagType.PARENT.value
            ).first()
            
            if parent_bag:
                scan.parent_bag_id = parent_bag.id
            else:
                # Create new parent bag if it doesn't exist
                parent_bag = Bag()
                parent_bag.qr_id = scan_data['qr_id']
                parent_bag.type = BagType.PARENT.value
                parent_bag.name = scan_data.get('name', f"Batch {scan_data['qr_id']}")
                parent_bag.child_count = scan_data.get('child_count', 5)
                
                db.session.add(parent_bag)
                db.session.flush()  # Get ID without committing
                
                scan.parent_bag_id = parent_bag.id
                
        elif scan_data['scan_type'] == 'child':
            child_bag = Bag.query.filter_by(
                qr_id=scan_data['qr_id'], 
                type=BagType.CHILD.value
            ).first()
            
            if child_bag:
                scan.child_bag_id = child_bag.id
                
                # Update parent relationship if needed
                if scan_data.get('parent_id') and (child_bag.parent_id != scan_data['parent_id']):
                    child_bag.parent_id = scan_data['parent_id']
            else:
                # Create new child bag if it doesn't exist
                child_bag = Bag()
                child_bag.qr_id = scan_data['qr_id']
                child_bag.type = BagType.CHILD.value
                child_bag.name = scan_data.get('name', f"Package {scan_data['qr_id']}")
                child_bag.parent_id = scan_data.get('parent_id')
                
                db.session.add(child_bag)
                db.session.flush()  # Get ID without committing
                
                scan.child_bag_id = child_bag.id
        
        # Add scan to the session
        db.session.add(scan)
        
        # Commit all changes
        db.session.commit()
        
        # Invalidate caches for updated data
        invalidate_cache(namespace='dashboard')
        invalidate_cache(namespace='statistics')
        
        if scan_data['scan_type'] == 'parent':
            invalidate_cache(namespace='parent_bags')
        else:
            invalidate_cache(namespace='child_bags')
        
        # Record scan success
        end_time = time.time()
        processing_time = end_time - start_time
        logger.info(f"Successfully processed scan for {scan_data.get('qr_id')} in {processing_time:.2f}s")
        
        return {
            'success': True,
            'scan_id': scan.id,
            'processing_time': processing_time,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        # Log error details
        end_time = time.time()
        processing_time = end_time - start_time
        logger.exception(f"Error processing scan: {str(e)}")
        
        # Rollback transaction
        db.session.rollback()
        
        return {
            'success': False,
            'error': str(e),
            'processing_time': processing_time,
            'timestamp': datetime.utcnow().isoformat()
        }

@async_task
def generate_analytics_report(parameters):
    """
    Generate analytics report asynchronously.
    
    Args:
        parameters: Dictionary of report parameters
    
    Returns:
        dict: Report data
    """
    start_time = time.time()
    logger.info(f"Starting analytics report generation: {parameters}")
    
    try:
        # Calculate date range
        days = parameters.get('days', 30)
        
        # Your analytics code here
        # ...
        
        # Simulate some processing time
        time.sleep(1)
        
        # Return report data
        end_time = time.time()
        return {
            'success': True,
            'report_data': {
                'title': 'TraceTrack Analytics Report',
                'generated_at': datetime.utcnow().isoformat(),
                'period_days': days,
                'processing_time': end_time - start_time,
                # Add actual report data here
            }
        }
    
    except Exception as e:
        logger.exception(f"Error generating analytics report: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }