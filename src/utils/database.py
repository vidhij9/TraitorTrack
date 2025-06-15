"""
Database utilities for connection management and health checks.
"""

import logging
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from ..core.app import db

def check_database_health():
    """Check database connection and basic functionality"""
    try:
        # Test basic connection
        result = db.session.execute(text('SELECT 1'))
        result.fetchone()
        
        return True, "Database connection healthy"
    except SQLAlchemyError as e:
        logging.error(f"Database health check failed: {str(e)}")
        return False, f"Database error: {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected database error: {str(e)}")
        return False, f"Unexpected error: {str(e)}"

def get_database_stats():
    """Get basic database statistics"""
    try:
        from ..models import User, Bag, Scan, Bill
        
        stats = {
            'users': User.query.count(),
            'bags': Bag.query.count(),
            'scans': Scan.query.count(),
            'bills': Bill.query.count()
        }
        
        return True, stats
    except Exception as e:
        logging.error(f"Failed to get database stats: {str(e)}")
        return False, {'error': str(e)}

def safe_db_operation(operation):
    """Safely execute database operations with rollback on error"""
    try:
        result = operation()
        db.session.commit()
        return True, result
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Database operation failed: {str(e)}")
        return False, str(e)
    except Exception as e:
        db.session.rollback()
        logging.error(f"Unexpected error in database operation: {str(e)}")
        return False, str(e)

def cleanup_old_records(model, date_field, days_old=90):
    """Clean up old records from database"""
    from datetime import datetime, timedelta
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        old_records = model.query.filter(date_field < cutoff_date)
        count = old_records.count()
        
        if count > 0:
            old_records.delete()
            db.session.commit()
            logging.info(f"Cleaned up {count} old records from {model.__tablename__}")
        
        return True, count
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to cleanup old records: {str(e)}")
        return False, str(e)