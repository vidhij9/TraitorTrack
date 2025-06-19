"""
Comprehensive duplicate prevention system for QR codes across bags and bills.
Ensures no QR code can be used for multiple purposes throughout the system.
"""

from app_clean import db
from models import Bag, Bill, BagType
from sqlalchemy import func
import logging

class DuplicatePreventionError(Exception):
    """Custom exception for duplicate prevention violations"""
    pass

def check_qr_code_uniqueness(qr_id, exclude_bag_id=None, exclude_bill_id=None):
    """
    Check if a QR code is unique across the entire system.
    
    Args:
        qr_id (str): The QR code to check
        exclude_bag_id (int, optional): Bag ID to exclude from check (for updates)
        exclude_bill_id (int, optional): Bill ID to exclude from check (for updates)
        
    Returns:
        tuple: (is_unique, conflict_type, conflict_details)
    """
    qr_id = qr_id.strip()
    
    # Check for existing bags with this QR code
    bag_query = Bag.query.filter_by(qr_id=qr_id)
    if exclude_bag_id:
        bag_query = bag_query.filter(Bag.id != exclude_bag_id)
    
    existing_bag = bag_query.first()
    if existing_bag:
        return False, 'bag', {
            'type': existing_bag.type,
            'qr_id': existing_bag.qr_id,
            'id': existing_bag.id,
            'name': existing_bag.name
        }
    
    # Check for existing bills with this ID
    bill_query = Bill.query.filter_by(bill_id=qr_id)
    if exclude_bill_id:
        bill_query = bill_query.filter(Bill.id != exclude_bill_id)
    
    existing_bill = bill_query.first()
    if existing_bill:
        return False, 'bill', {
            'bill_id': existing_bill.bill_id,
            'id': existing_bill.id,
            'description': existing_bill.description
        }
    
    return True, None, None

def validate_new_bag_qr_code(qr_id, bag_type):
    """
    Validate that a QR code can be used for a new bag.
    
    Args:
        qr_id (str): The QR code to validate
        bag_type (str): The type of bag (parent or child)
        
    Returns:
        tuple: (is_valid, error_message)
    """
    qr_id = qr_id.strip()
    
    if not qr_id:
        return False, "QR code cannot be empty"
    
    # Check for any existing usage
    is_unique, conflict_type, conflict_details = check_qr_code_uniqueness(qr_id)
    
    if not is_unique:
        if conflict_type == 'bag':
            return False, f"QR code '{qr_id}' is already used by a {conflict_details['type']} bag (ID: {conflict_details['id']})"
        elif conflict_type == 'bill':
            return False, f"QR code '{qr_id}' is already used as a bill ID (Bill: {conflict_details['bill_id']})"
    
    return True, None

def validate_new_bill_id(bill_id):
    """
    Validate that a bill ID can be used for a new bill.
    
    Args:
        bill_id (str): The bill ID to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    bill_id = bill_id.strip()
    
    if not bill_id:
        return False, "Bill ID cannot be empty"
    
    # Check for any existing usage
    is_unique, conflict_type, conflict_details = check_qr_code_uniqueness(bill_id)
    
    if not is_unique:
        if conflict_type == 'bag':
            return False, f"ID '{bill_id}' is already used by a {conflict_details['type']} bag (QR: {conflict_details['qr_id']})"
        elif conflict_type == 'bill':
            return False, f"Bill ID '{bill_id}' already exists (ID: {conflict_details['id']})"
    
    return True, None

def find_duplicate_qr_codes():
    """
    Find all duplicate QR codes in the system for cleanup.
    
    Returns:
        dict: Dictionary with duplicate information
    """
    duplicates = {
        'bag_duplicates': [],
        'cross_duplicates': [],
        'bill_duplicates': []
    }
    
    # Find bags with duplicate QR codes
    bag_duplicates = db.session.query(
        Bag.qr_id,
        func.count(Bag.id).label('count')
    ).group_by(Bag.qr_id).having(func.count(Bag.id) > 1).all()
    
    for qr_id, count in bag_duplicates:
        bags = Bag.query.filter_by(qr_id=qr_id).all()
        duplicates['bag_duplicates'].append({
            'qr_id': qr_id,
            'count': count,
            'bags': [{
                'id': bag.id,
                'type': bag.type,
                'name': bag.name,
                'created_at': bag.created_at
            } for bag in bags]
        })
    
    # Find QR codes used in both bags and bills
    all_bag_qr_codes = set(bag.qr_id for bag in Bag.query.all())
    all_bill_ids = set(bill.bill_id for bill in Bill.query.all())
    
    cross_conflicts = all_bag_qr_codes.intersection(all_bill_ids)
    for qr_id in cross_conflicts:
        bags = Bag.query.filter_by(qr_id=qr_id).all()
        bills = Bill.query.filter_by(bill_id=qr_id).all()
        
        duplicates['cross_duplicates'].append({
            'qr_id': qr_id,
            'bags': [{
                'id': bag.id,
                'type': bag.type,
                'name': bag.name
            } for bag in bags],
            'bills': [{
                'id': bill.id,
                'description': bill.description
            } for bill in bills]
        })
    
    # Find bills with duplicate IDs
    bill_duplicates = db.session.query(
        Bill.bill_id,
        func.count(Bill.id).label('count')
    ).group_by(Bill.bill_id).having(func.count(Bill.id) > 1).all()
    
    for bill_id, count in bill_duplicates:
        bills = Bill.query.filter_by(bill_id=bill_id).all()
        duplicates['bill_duplicates'].append({
            'bill_id': bill_id,
            'count': count,
            'bills': [{
                'id': bill.id,
                'description': bill.description,
                'created_at': bill.created_at
            } for bill in bills]
        })
    
    return duplicates

def get_system_integrity_report():
    """
    Generate a comprehensive system integrity report.
    
    Returns:
        dict: System integrity statistics and issues
    """
    duplicates = find_duplicate_qr_codes()
    
    total_bags = Bag.query.count()
    total_bills = Bill.query.count()
    unique_bag_qr_codes = db.session.query(func.count(func.distinct(Bag.qr_id))).scalar()
    unique_bill_ids = db.session.query(func.count(func.distinct(Bill.bill_id))).scalar()
    
    report = {
        'summary': {
            'total_bags': total_bags,
            'total_bills': total_bills,
            'unique_bag_qr_codes': unique_bag_qr_codes,
            'unique_bill_ids': unique_bill_ids,
            'has_duplicates': any([
                duplicates['bag_duplicates'],
                duplicates['cross_duplicates'],
                duplicates['bill_duplicates']
            ])
        },
        'duplicates': duplicates,
        'integrity_score': calculate_integrity_score(duplicates, total_bags, total_bills)
    }
    
    return report

def calculate_integrity_score(duplicates, total_bags, total_bills):
    """
    Calculate system integrity score (0-100).
    
    Args:
        duplicates (dict): Duplicate information
        total_bags (int): Total number of bags
        total_bills (int): Total number of bills
        
    Returns:
        float: Integrity score percentage
    """
    if total_bags == 0 and total_bills == 0:
        return 100.0
    
    total_items = total_bags + total_bills
    duplicate_count = (
        len(duplicates['bag_duplicates']) +
        len(duplicates['cross_duplicates']) +
        len(duplicates['bill_duplicates'])
    )
    
    if duplicate_count == 0:
        return 100.0
    
    # Calculate score based on percentage of duplicates
    duplicate_percentage = (duplicate_count / total_items) * 100
    score = max(0, 100 - duplicate_percentage)
    
    return round(score, 2)

def log_duplicate_attempt(qr_id, attempted_type, existing_type, user_id=None):
    """
    Log duplicate QR code attempts for security monitoring.
    
    Args:
        qr_id (str): The QR code that was attempted
        attempted_type (str): What type was attempted (bag/bill)
        existing_type (str): What type already exists
        user_id (int, optional): User who attempted the action
    """
    logging.warning(
        f"Duplicate QR code attempt - QR: {qr_id}, "
        f"Attempted: {attempted_type}, Existing: {existing_type}, "
        f"User: {user_id or 'Unknown'}"
    )