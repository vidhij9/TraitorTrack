"""
Bulk Import Utilities for TraceTrack
Provides CSV and Excel import functionality with comprehensive validation

FEATURES:
- Import bags (parent and child) with validation
- Import bills with parent bag linkages
- Duplicate detection and handling
- Error reporting with line numbers
- Batch processing for performance
- Admin-only access enforced in routes

SAFETY:
- Input validation for all fields
- Duplicate prevention
- Transaction-based imports (rollback on error)
- Memory-efficient batch processing
"""
import csv
import io
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from flask import flash
from sqlalchemy import text
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)

# Try to import openpyxl for Excel support
try:
    from openpyxl import load_workbook
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    logger.warning("openpyxl not available - Excel imports disabled")


class ImportValidator:
    """Validates import data before database insertion"""
    
    @staticmethod
    def validate_bag_data(row: Dict, row_num: int) -> Tuple[bool, Optional[str]]:
        """
        Validate a single bag row.
        
        Args:
            row: Dictionary with bag data
            row_num: Row number for error reporting
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Required fields
        required_fields = ['qr_id', 'type']
        for field in required_fields:
            if not row.get(field):
                return False, f"Row {row_num}: Missing required field '{field}'"
        
        # Validate QR ID format
        qr_id = str(row['qr_id']).strip()
        if len(qr_id) < 3 or len(qr_id) > 50:
            return False, f"Row {row_num}: QR ID must be between 3 and 50 characters"
        
        # Validate bag type
        bag_type = str(row['type']).strip().lower()
        if bag_type not in ('parent', 'child'):
            return False, f"Row {row_num}: Type must be 'parent' or 'child', got '{row['type']}'"
        
        # Validate parent QR ID for child bags
        if bag_type == 'child':
            if not row.get('parent_qr_id'):
                return False, f"Row {row_num}: Child bags must have a parent_qr_id"
        
        return True, None
    
    @staticmethod
    def validate_bill_data(row: Dict, row_num: int) -> Tuple[bool, Optional[str]]:
        """
        Validate a single bill row.
        
        Args:
            row: Dictionary with bill data
            row_num: Row number for error reporting
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Required fields
        if not row.get('bill_id'):
            return False, f"Row {row_num}: Missing required field 'bill_id'"
        
        # Validate bill ID format
        bill_id = str(row['bill_id']).strip()
        if len(bill_id) < 3 or len(bill_id) > 50:
            return False, f"Row {row_num}: Bill ID must be between 3 and 50 characters"
        
        # Validate parent bag count if provided and not empty
        if 'parent_bag_count' in row and str(row['parent_bag_count']).strip():
            try:
                count = int(row['parent_bag_count'])
                if count < 1 or count > 50:
                    return False, f"Row {row_num}: Parent bag count must be between 1 and 50"
            except (ValueError, TypeError):
                return False, f"Row {row_num}: Parent bag count must be a valid number"
        
        return True, None


class BagImporter:
    """Handles bulk import of bags from CSV/Excel"""
    
    @staticmethod
    def parse_csv(file_storage: FileStorage) -> Tuple[List[Dict], List[str]]:
        """
        Parse CSV file and return bag data with any errors.
        
        Args:
            file_storage: Uploaded file object
            
        Returns:
            Tuple of (bag_data_list, error_list)
        """
        try:
            # Read file content
            content = file_storage.read().decode('utf-8')
            file_storage.seek(0)  # Reset for potential re-use
            
            # Parse CSV
            csv_reader = csv.DictReader(io.StringIO(content))
            
            bags = []
            errors = []
            
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
                # Validate row
                is_valid, error_msg = ImportValidator.validate_bag_data(row, row_num)
                if not is_valid:
                    errors.append(error_msg)
                    continue
                
                # Normalize data
                bags.append({
                    'qr_id': str(row['qr_id']).strip(),
                    'type': str(row['type']).strip().lower(),
                    'parent_qr_id': str(row.get('parent_qr_id', '')).strip() if row.get('parent_qr_id') else None
                })
            
            return bags, errors
        
        except Exception as e:
            logger.error(f"CSV parsing error: {str(e)}")
            return [], [f"Error parsing CSV file: {str(e)}"]
    
    @staticmethod
    def parse_excel(file_storage: FileStorage) -> Tuple[List[Dict], List[str]]:
        """
        Parse Excel file and return bag data with any errors.
        
        Args:
            file_storage: Uploaded file object
            
        Returns:
            Tuple of (bag_data_list, error_list)
        """
        if not EXCEL_AVAILABLE:
            return [], ["Excel support not available - openpyxl not installed"]
        
        try:
            # Load workbook
            wb = load_workbook(file_storage)
            ws = wb.active
            
            # Get header row
            headers = [cell.value for cell in ws[1]]
            
            bags = []
            errors = []
            
            # Process data rows
            for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                # Skip empty rows
                if not any(row):
                    continue
                
                # Create row dict
                row_dict = dict(zip(headers, row))
                
                # Validate row
                is_valid, error_msg = ImportValidator.validate_bag_data(row_dict, row_num)
                if not is_valid:
                    errors.append(error_msg)
                    continue
                
                # Normalize data
                bags.append({
                    'qr_id': str(row_dict['qr_id']).strip(),
                    'type': str(row_dict['type']).strip().lower(),
                    'parent_qr_id': str(row_dict.get('parent_qr_id', '')).strip() if row_dict.get('parent_qr_id') else None
                })
            
            return bags, errors
        
        except Exception as e:
            logger.error(f"Excel parsing error: {str(e)}")
            return [], [f"Error parsing Excel file: {str(e)}"]
    
    @staticmethod
    def import_bags(db, bags: List[Dict], user_id: int) -> Tuple[int, int, List[str]]:
        """
        Import bags into database with transaction safety.
        
        Args:
            db: Database session
            bags: List of bag dictionaries
            user_id: ID of user performing import
            
        Returns:
            Tuple of (imported_count, skipped_count, error_list)
        """
        from models import Bag, Link
        
        imported = 0
        skipped = 0
        errors = []
        
        try:
            # Check for duplicates in batch (much faster than individual queries)
            qr_ids = [bag['qr_id'] for bag in bags]
            
            existing_query = text("""
                SELECT qr_id FROM bag WHERE qr_id = ANY(:qr_ids)
            """)
            
            existing_qr_ids = set(
                row[0] for row in db.session.execute(existing_query, {'qr_ids': qr_ids}).fetchall()
            )
            
            # Process bags in batches with savepoint-based rollback for resilience
            batch_size = 100
            for i in range(0, len(bags), batch_size):
                batch = bags[i:i + batch_size]
                batch_start = imported
                batch_qr_ids = []  # Track IDs added in this batch
                
                # Use nested transaction (savepoint) for batch-level rollback
                savepoint = db.session.begin_nested()
                
                try:
                    for bag_data in batch:
                        qr_id = bag_data['qr_id']
                        
                        # Skip duplicates
                        if qr_id in existing_qr_ids:
                            skipped += 1
                            errors.append(f"Skipped duplicate QR ID: {qr_id}")
                            continue
                        
                        # Create bag
                        new_bag = Bag(
                            qr_id=qr_id,
                            type=bag_data['type']
                        )
                        db.session.add(new_bag)
                        existing_qr_ids.add(qr_id)  # Track newly added
                        batch_qr_ids.append(qr_id)  # Track for potential rollback cleanup
                        imported += 1
                    
                    # Commit batch savepoint
                    savepoint.commit()
                    db.session.flush()
                    # Batch succeeded - IDs are now permanent in existing_qr_ids
                    
                except Exception as batch_error:
                    # Rollback only this batch, not entire import
                    savepoint.rollback()
                    
                    # CRITICAL FIX: Remove batch IDs from tracking set since they were rolled back
                    for qr_id in batch_qr_ids:
                        existing_qr_ids.discard(qr_id)  # Remove rolled-back IDs
                    
                    batch_imported = imported - batch_start
                    imported = batch_start  # Reset counter
                    errors.append(f"Batch {i//batch_size + 1} failed: {str(batch_error)} ({batch_imported} bags lost)")
                    logger.warning(f"Batch rollback at index {i}: {str(batch_error)}")
            
            # Handle child bag linkages after all bags are created
            for bag_data in bags:
                if bag_data['type'] == 'child' and bag_data.get('parent_qr_id'):
                    parent_qr = bag_data['parent_qr_id']
                    child_qr = bag_data['qr_id']
                    
                    # Find parent and child bags
                    parent = Bag.query.filter_by(qr_id=parent_qr).first()
                    child = Bag.query.filter_by(qr_id=child_qr).first()
                    
                    if parent and child:
                        # Check if link already exists
                        existing_link = Link.query.filter_by(
                            parent_bag_id=parent.id,
                            child_bag_id=child.id
                        ).first()
                        
                        if not existing_link:
                            link = Link(
                                parent_bag_id=parent.id,
                                child_bag_id=child.id
                            )
                            db.session.add(link)
                    elif not parent:
                        errors.append(f"Warning: Parent bag '{parent_qr}' not found for child '{child_qr}'")
            
            # Final commit
            db.session.commit()
            
            # Log import activity
            from audit_utils import log_audit
            log_audit(
                action='BULK_IMPORT',
                entity_type='bag',
                entity_id=None,
                details=f"Imported {imported} bags, skipped {skipped} duplicates"
            )
            
            return imported, skipped, errors
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Bag import error: {str(e)}")
            errors.append(f"Database error: {str(e)}")
            return imported, skipped, errors


class BillImporter:
    """Handles bulk import of bills from CSV/Excel"""
    
    @staticmethod
    def parse_csv(file_storage: FileStorage) -> Tuple[List[Dict], List[str]]:
        """Parse CSV file and return bill data with any errors"""
        try:
            content = file_storage.read().decode('utf-8')
            file_storage.seek(0)
            
            csv_reader = csv.DictReader(io.StringIO(content))
            
            bills = []
            errors = []
            
            for row_num, row in enumerate(csv_reader, start=2):
                is_valid, error_msg = ImportValidator.validate_bill_data(row, row_num)
                if not is_valid:
                    errors.append(error_msg)
                    continue
                
                # Safely parse numeric fields with empty value handling
                try:
                    parent_bag_count_str = str(row.get('parent_bag_count', '')).strip()
                    parent_bag_count = int(parent_bag_count_str) if parent_bag_count_str else 1
                except (ValueError, TypeError):
                    parent_bag_count = 1
                
                try:
                    expected_weight_str = str(row.get('expected_weight_kg', '')).strip()
                    expected_weight_kg = float(expected_weight_str) if expected_weight_str else 0.0
                except (ValueError, TypeError):
                    expected_weight_kg = 0.0
                
                bills.append({
                    'bill_id': str(row['bill_id']).strip(),
                    'description': str(row.get('description', '')).strip(),
                    'parent_bag_count': parent_bag_count,
                    'expected_weight_kg': expected_weight_kg
                })
            
            return bills, errors
        
        except Exception as e:
            logger.error(f"CSV parsing error: {str(e)}")
            return [], [f"Error parsing CSV file: {str(e)}"]
    
    @staticmethod
    def import_bills(db, bills: List[Dict], user_id: int) -> Tuple[int, int, List[str]]:
        """Import bills into database with transaction safety"""
        from models import Bill
        
        imported = 0
        skipped = 0
        errors = []
        
        try:
            # Check for duplicates in batch
            bill_ids = [bill['bill_id'] for bill in bills]
            
            existing_query = text("""
                SELECT bill_id FROM bill WHERE bill_id = ANY(:bill_ids)
            """)
            
            existing_bill_ids = set(
                row[0] for row in db.session.execute(existing_query, {'bill_ids': bill_ids}).fetchall()
            )
            
            # Process bills in batches with savepoint-based rollback
            batch_size = 100
            for i in range(0, len(bills), batch_size):
                batch = bills[i:i + batch_size]
                batch_start = imported
                batch_bill_ids = []  # Track IDs added in this batch
                
                # Use nested transaction (savepoint) for batch-level rollback
                savepoint = db.session.begin_nested()
                
                try:
                    for bill_data in batch:
                        bill_id = bill_data['bill_id']
                        
                        # Skip duplicates
                        if bill_id in existing_bill_ids:
                            skipped += 1
                            errors.append(f"Skipped duplicate Bill ID: {bill_id}")
                            continue
                        
                        # Create bill
                        new_bill = Bill(
                            bill_id=bill_id,
                            description=bill_data.get('description'),
                            parent_bag_count=bill_data.get('parent_bag_count', 1),
                            expected_weight_kg=bill_data.get('expected_weight_kg', 0),
                            created_by_id=user_id
                        )
                        db.session.add(new_bill)
                        existing_bill_ids.add(bill_id)
                        batch_bill_ids.append(bill_id)  # Track for potential rollback cleanup
                        imported += 1
                    
                    # Commit batch savepoint
                    savepoint.commit()
                    db.session.flush()
                    # Batch succeeded - IDs are now permanent in existing_bill_ids
                    
                except Exception as batch_error:
                    # Rollback only this batch, not entire import
                    savepoint.rollback()
                    
                    # CRITICAL FIX: Remove batch IDs from tracking set since they were rolled back
                    for bill_id in batch_bill_ids:
                        existing_bill_ids.discard(bill_id)  # Remove rolled-back IDs
                    
                    batch_imported = imported - batch_start
                    imported = batch_start  # Reset counter
                    errors.append(f"Batch {i//batch_size + 1} failed: {str(batch_error)} ({batch_imported} bills lost)")
                    logger.warning(f"Bill batch rollback at index {i}: {str(batch_error)}")
            
            db.session.commit()
            
            # Log import activity
            from audit_utils import log_audit
            log_audit(
                action='BULK_IMPORT',
                entity_type='bill',
                entity_id=None,
                details=f"Imported {imported} bills, skipped {skipped} duplicates"
            )
            
            return imported, skipped, errors
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Bill import error: {str(e)}")
            errors.append(f"Database error: {str(e)}")
            return imported, skipped, errors
