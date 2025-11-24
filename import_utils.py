"""
Bulk Import Utilities for TraitorTrack
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
from app import db
from models import Bag, Bill, Link, BillBag, User

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
            file_storage.stream.seek(0)
            wb = load_workbook(file_storage.stream)
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


class ChildParentBatchImporter:
    """
    Handles batch import of child bags linked to parent bags from Excel files.
    
    Expected format:
    - Multiple rows with child bag QR codes (Sr. No. is numeric, QR Code starts with 'LABEL NO.')
    - Followed by one parent bag row (Sr. No. contains 'Parent Code', QR Code contains parent bag ID)
    - Pattern repeats for each batch
    
    Example:
    Row 1: Sr. No.=1, QR Code='LABEL NO.0016586 LOT NO.:...'  <- Child bag
    Row 2: Sr. No.=2, QR Code='LABEL NO.0016587 LOT NO.:...'  <- Child bag
    Row 3: Sr. No.='Parent Code', QR Code='SB12260'           <- Parent bag (marks end of batch)
    """
    
    @staticmethod
    def extract_label_number(qr_text: str) -> Optional[str]:
        """
        Extract only the label number from QR code text.
        
        Example input: 'LABEL NO.0016586 LOT NO.:STAR44GG24611, D.O.T.:30/09/2025...'
        Expected output: '0016586'
        
        Args:
            qr_text: Full QR code text
            
        Returns:
            Label number string or None if not found
        """
        if not qr_text or not isinstance(qr_text, str):
            return None
        
        # Look for 'LABEL NO.' followed by digits
        import re
        match = re.search(r'LABEL\s*NO\.(\d+)', qr_text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    @staticmethod
    def is_child_row(sr_no, qr_code) -> bool:
        """
        Determine if a row represents a child bag.
        
        Child bag criteria:
        - Sr. No. is numeric (1, 2, 3, etc.)
        - QR Code starts with 'LABEL NO.'
        
        Args:
            sr_no: Value from Sr. No. column
            qr_code: Value from QR Code column
            
        Returns:
            True if this is a child bag row
        """
        # Check if Sr. No. is numeric
        try:
            if sr_no is not None:
                float(sr_no)  # Can be 1.0 or 1
                
                # Check if QR code contains 'LABEL NO.'
                if qr_code and isinstance(qr_code, str) and 'LABEL NO.' in qr_code.upper():
                    return True
        except (ValueError, TypeError):
            pass
        
        return False
    
    @staticmethod
    def is_parent_row(sr_no, qr_code) -> Tuple[bool, Optional[str]]:
        """
        Determine if a row represents a parent bag and extract parent code.
        
        Parent bag criteria:
        - Sr. No. contains 'Parent Code' text
        - QR Code contains the parent bag code (e.g., 'SB12260')
        
        Args:
            sr_no: Value from Sr. No. column
            qr_code: Value from QR Code column
            
        Returns:
            Tuple of (is_parent_row, parent_code)
        """
        if sr_no and isinstance(sr_no, str) and 'parent code' in sr_no.lower():
            # Extract parent code from QR Code column
            parent_code = str(qr_code).strip() if qr_code else None
            return True, parent_code
        
        return False, None
    
    @staticmethod
    def parse_excel_batch(file_storage: FileStorage) -> Tuple[List[Dict], List[str], Dict]:
        """
        Parse Excel file with batch pattern (children followed by parent).
        
        Args:
            file_storage: Uploaded Excel file
            
        Returns:
            Tuple of (batches_list, error_list, stats_dict)
            
            batches_list format:
            [
                {
                    'parent_code': 'SB12260',
                    'children': ['0016586', '0016587', '0016585', ...],
                    'row_range': '2-17'
                },
                ...
            ]
        """
        if not EXCEL_AVAILABLE:
            return [], ["Excel support not available - openpyxl not installed"], {}
        
        try:
            file_storage.stream.seek(0)
            wb = load_workbook(file_storage.stream)
            ws = wb.active
            
            batches = []
            errors = []
            current_children = []
            batch_start_row = None
            
            total_children = 0
            total_parents = 0
            skipped_rows = 0
            
            # Process rows (skip header row 1)
            for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                # Skip completely blank rows
                if not any(row):
                    skipped_rows += 1
                    continue
                
                sr_no = row[0] if len(row) > 0 else None
                qr_code = row[1] if len(row) > 1 else None
                
                # Check if this is a child bag row
                if ChildParentBatchImporter.is_child_row(sr_no, qr_code):
                    label_number = ChildParentBatchImporter.extract_label_number(qr_code)
                    
                    if label_number:
                        if batch_start_row is None:
                            batch_start_row = row_num
                        current_children.append(label_number)
                        total_children += 1
                    else:
                        errors.append(f"Row {row_num}: Could not extract label number from QR code")
                
                # Check if this is a parent bag row
                is_parent, parent_code = ChildParentBatchImporter.is_parent_row(sr_no, qr_code)
                if is_parent:
                    if not parent_code:
                        errors.append(f"Row {row_num}: Parent row found but parent code is blank/missing")
                        # Clear children and start fresh
                        current_children = []
                        batch_start_row = None
                        continue
                    
                    if not current_children:
                        errors.append(f"Row {row_num}: Parent code '{parent_code}' found but no child bags above it")
                        continue
                    
                    # Create batch
                    batches.append({
                        'parent_code': parent_code,
                        'children': current_children.copy(),
                        'row_range': f"{batch_start_row}-{row_num}"
                    })
                    total_parents += 1
                    
                    # Reset for next batch
                    current_children = []
                    batch_start_row = None
            
            # Handle orphaned children at end of sheet
            if current_children:
                errors.append(f"Warning: {len(current_children)} child bags found at end of sheet without a parent code")
                batches.append({
                    'parent_code': None,
                    'children': current_children,
                    'row_range': f"{batch_start_row}-END",
                    'orphaned': True
                })
            
            stats = {
                'total_batches': len(batches),
                'total_children': total_children,
                'total_parents': total_parents,
                'skipped_rows': skipped_rows
            }
            
            return batches, errors, stats
        
        except Exception as e:
            logger.error(f"Excel batch parsing error: {str(e)}")
            return [], [f"Error parsing Excel file: {str(e)}"], {}
    
    @staticmethod
    def import_batches(db, batches: List[Dict], user_id: int, dispatch_area: Optional[str] = None) -> Tuple[int, int, int, int, List[str]]:
        """
        Import batches of child-parent bag relationships.
        
        Args:
            db: Database session
            batches: List of batch dictionaries from parse_excel_batch
            user_id: ID of user performing import
            dispatch_area: Optional dispatch area for the bags
            
        Returns:
            Tuple of (parents_created, children_created, links_created, parents_not_found, error_list)
        """
        from models import Bag, Link, BagType
        
        parents_created = 0
        children_created = 0
        links_created = 0
        parents_not_found = 0
        errors = []
        
        try:
            for batch_num, batch in enumerate(batches, 1):
                parent_code = batch['parent_code']
                child_labels = batch['children']
                row_range = batch['row_range']
                is_orphaned = batch.get('orphaned', False)
                
                # Skip orphaned batches unless user explicitly wants them
                if is_orphaned:
                    errors.append(f"Batch {batch_num} (rows {row_range}): Skipped {len(child_labels)} orphaned children without parent")
                    continue
                
                # Start a savepoint for this batch
                savepoint = db.session.begin_nested()
                
                try:
                    # Check if parent already exists (case-insensitive search)
                    from sqlalchemy import func
                    parent_bag = Bag.query.filter(func.upper(Bag.qr_id) == parent_code.upper()).first()
                    
                    if not parent_bag:
                        # REJECT batch - parent bag does NOT exist in database
                        # Do not create parent bags automatically - user must create them first
                        parents_not_found += 1
                        error_msg = f"Batch {batch_num} (rows {row_range}): Parent bag '{parent_code}' not found in database - {len(child_labels)} child bags rejected"
                        errors.append(error_msg)
                        logger.warning(error_msg)
                        savepoint.rollback()
                        continue
                    
                    # Parent exists - process children
                    logger.info(f"Parent bag {parent_code} found, processing {len(child_labels)} children")
                    
                    # Create child bags and links
                    batch_children_created = 0
                    batch_links_created = 0
                    
                    for label_number in child_labels:
                        # Check if child already exists (case-insensitive search)
                        from sqlalchemy import func
                        child_bag = Bag.query.filter(func.upper(Bag.qr_id) == label_number.upper()).first()
                        
                        if not child_bag:
                            # Create child bag with exact label number (no case conversion)
                            child_bag = Bag(
                                qr_id=label_number,
                                type=BagType.CHILD.value,
                                user_id=user_id,
                                dispatch_area=dispatch_area,
                                weight_kg=1.0  # Each child is 1kg
                            )
                            db.session.add(child_bag)
                            db.session.flush()  # Get child bag ID
                            batch_children_created += 1
                        
                        # Verify child_bag has ID before creating link
                        if not child_bag or not child_bag.id:
                            errors.append(f"Batch {batch_num}: Child bag '{label_number}' could not be created or found")
                            logger.error(f"Child bag '{label_number}' has no ID - skipping link creation")
                            continue
                        
                        # CRITICAL: Check if child already has ANY parent link (one child = one parent rule)
                        existing_parent_link = Link.query.filter_by(child_bag_id=child_bag.id).first()
                        
                        if existing_parent_link:
                            # Child already has a parent link
                            if existing_parent_link.parent_bag_id == parent_bag.id:
                                # Already linked to this same parent - skip silently
                                logger.debug(f"Child '{label_number}' already linked to parent '{parent_code}' - skipping")
                                continue
                            else:
                                # Child linked to a DIFFERENT parent - this violates the one-child-one-parent rule
                                existing_parent_bag = Bag.query.get(existing_parent_link.parent_bag_id)
                                existing_parent_qr = existing_parent_bag.qr_id if existing_parent_bag else "Unknown"
                                error_msg = f"Row {row_range}: Child '{label_number}' already linked to parent '{existing_parent_qr}', cannot link to '{parent_code}'"
                                errors.append(error_msg)
                                logger.warning(error_msg)
                                continue
                        
                        # No existing parent link - safe to create new link
                        link = Link(
                            parent_bag_id=parent_bag.id,
                            child_bag_id=child_bag.id
                        )
                        db.session.add(link)
                        batch_links_created += 1
                    
                    # Update parent's child count
                    actual_child_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
                    parent_bag.child_count = actual_child_count
                    parent_bag.weight_kg = actual_child_count * 1.0
                    
                    # Commit this batch
                    savepoint.commit()
                    db.session.flush()
                    
                    children_created += batch_children_created
                    links_created += batch_links_created
                    
                    # Clearer logging to distinguish new vs reused children
                    children_reused = len(child_labels) - batch_children_created
                    if children_reused > 0:
                        logger.info(f"Batch {batch_num} ({row_range}): Parent '{parent_code}', {batch_children_created} new children + {children_reused} existing children, {batch_links_created} new links")
                    else:
                        logger.info(f"Batch {batch_num} ({row_range}): Created parent '{parent_code}', {batch_children_created} children, {batch_links_created} links")
                
                except Exception as batch_error:
                    savepoint.rollback()
                    error_msg = f"Batch {batch_num} (rows {row_range}, parent '{parent_code}'): {str(batch_error)}"
                    errors.append(error_msg)
                    logger.error(f"Batch import error: {error_msg}")
            
            # Final commit
            db.session.commit()
            
            # Log audit
            from audit_utils import log_audit
            log_audit(
                action='BATCH_IMPORT_CHILD_PARENT',
                entity_type='bag',
                entity_id=None,
                details=f"Imported {len(batches)} batches: {parents_created} parents, {children_created} children, {links_created} links ({parents_not_found} parents not found)"
            )
            
            return parents_created, children_created, links_created, parents_not_found, errors
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Batch import error: {str(e)}")
            errors.append(f"Database error: {str(e)}")
            return parents_created, children_created, links_created, parents_not_found, errors


class ParentBillBatchImporter:
    """
    Handles batch import of parent bags linked to bills from Excel files.
    
    Expected format (similar to child→parent pattern):
    - Multiple rows with parent bag QR codes (Sr. No. is numeric)
    - Followed by one bill number row (Sr. No. contains 'Bill No' or similar marker)
    - Pattern repeats for each batch
    
    Example:
    Row 1: Sr. No.=1, Parent Bag='SB12260'     <- Parent bag
    Row 2: Sr. No.=2, Parent Bag='SB12248'     <- Parent bag
    Row 3: Sr. No.='Bill No', Bill='BILL001'   <- Bill number (marks end of batch)
    """
    
    @staticmethod
    def is_parent_bag_row(sr_no, parent_code) -> bool:
        """
        Determine if a row represents a parent bag.
        
        Parent bag criteria:
        - Sr. No. is numeric (1, 2, 3, etc.)
        - Parent code/QR is not empty
        
        Args:
            sr_no: Value from Sr. No. column
            parent_code: Value from parent bag column
            
        Returns:
            True if this is a parent bag row
        """
        try:
            if sr_no is not None:
                float(sr_no)  # Can be 1.0 or 1
                
                # Check if parent code exists
                if parent_code and isinstance(parent_code, str) and parent_code.strip():
                    return True
        except (ValueError, TypeError):
            pass
        
        return False
    
    @staticmethod
    def is_bill_row(sr_no, bill_code) -> Tuple[bool, Optional[str]]:
        """
        Determine if a row represents a bill and extract bill number.
        
        Bill row criteria:
        - Sr. No. contains 'Bill' text (case-insensitive)
        - Bill code column contains the bill number
        
        Args:
            sr_no: Value from Sr. No. column
            bill_code: Value from bill code column
            
        Returns:
            Tuple of (is_bill_row, bill_number)
        """
        if sr_no and isinstance(sr_no, str) and 'bill' in sr_no.lower():
            # Extract bill number
            bill_number = str(bill_code).strip() if bill_code else None
            return True, bill_number
        
        return False, None
    
    @staticmethod
    def parse_excel_batch(file_storage: FileStorage) -> Tuple[List[Dict], List[str], Dict]:
        """
        Parse Excel file with batch pattern (parent bags followed by bill).
        
        Args:
            file_storage: Uploaded Excel file
            
        Returns:
            Tuple of (batches_list, error_list, stats_dict)
            
            batches_list format:
            [
                {
                    'bill_number': 'BILL001',
                    'parent_bags': ['SB12260', 'SB12248', ...],
                    'row_range': '2-10'
                },
                ...
            ]
        """
        if not EXCEL_AVAILABLE:
            return [], ["Excel support not available - openpyxl not installed"], {}
        
        try:
            file_storage.stream.seek(0)
            wb = load_workbook(file_storage.stream)
            ws = wb.active
            
            batches = []
            errors = []
            current_parents = []
            batch_start_row = None
            
            total_parents = 0
            total_bills = 0
            skipped_rows = 0
            
            # Process rows (skip header row 1)
            for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                # Skip completely blank rows
                if not any(row):
                    skipped_rows += 1
                    continue
                
                sr_no = row[0] if len(row) > 0 else None
                parent_or_bill = row[1] if len(row) > 1 else None
                
                # Check if this is a parent bag row
                if ParentBillBatchImporter.is_parent_bag_row(sr_no, parent_or_bill):
                    if batch_start_row is None:
                        batch_start_row = row_num
                    
                    parent_code = str(parent_or_bill).strip()
                    current_parents.append(parent_code)
                    total_parents += 1
                
                # Check if this is a bill row
                is_bill, bill_number = ParentBillBatchImporter.is_bill_row(sr_no, parent_or_bill)
                if is_bill:
                    if not bill_number:
                        errors.append(f"Row {row_num}: Bill row found but bill number is blank/missing")
                        # Clear parents and start fresh
                        current_parents = []
                        batch_start_row = None
                        continue
                    
                    if not current_parents:
                        errors.append(f"Row {row_num}: Bill number '{bill_number}' found but no parent bags above it")
                        continue
                    
                    # Create batch
                    batches.append({
                        'bill_number': bill_number,
                        'parent_bags': current_parents.copy(),
                        'row_range': f"{batch_start_row}-{row_num}"
                    })
                    total_bills += 1
                    
                    # Reset for next batch
                    current_parents = []
                    batch_start_row = None
            
            # Handle orphaned parents at end of sheet
            if current_parents:
                errors.append(f"Warning: {len(current_parents)} parent bags found at end of sheet without a bill number")
                batches.append({
                    'bill_number': None,
                    'parent_bags': current_parents,
                    'row_range': f"{batch_start_row}-END",
                    'orphaned': True
                })
            
            stats = {
                'total_batches': len(batches),
                'total_parents': total_parents,
                'total_bills': total_bills,
                'skipped_rows': skipped_rows
            }
            
            return batches, errors, stats
        
        except Exception as e:
            logger.error(f"Excel batch parsing error: {str(e)}")
            return [], [f"Error parsing Excel file: {str(e)}"], {}
    
    @staticmethod
    def import_batches(db, batches: List[Dict], user_id: int) -> Tuple[int, int, int, List[str]]:
        """
        Import batches of parent bag → bill relationships.
        
        Args:
            db: Database session
            batches: List of batch dictionaries from parse_excel_batch
            user_id: ID of user performing import
            
        Returns:
            Tuple of (bills_created, links_created, parents_not_found, error_list)
        """
        from models import Bag, Bill, BillBag, BagType
        
        bills_created = 0
        links_created = 0
        parents_not_found = 0
        errors = []
        
        try:
            for batch_num, batch in enumerate(batches, 1):
                bill_number = batch['bill_number']
                parent_codes = batch['parent_bags']
                row_range = batch['row_range']
                is_orphaned = batch.get('orphaned', False)
                
                # Skip orphaned batches
                if is_orphaned:
                    errors.append(f"Batch {batch_num} (rows {row_range}): Skipped {len(parent_codes)} orphaned parents without bill")
                    continue
                
                # Start a savepoint for this batch
                savepoint = db.session.begin_nested()
                
                try:
                    # Check if bill already exists
                    bill = Bill.query.filter_by(bill_id=bill_number.upper()).first()
                    
                    if not bill:
                        # Create bill
                        bill = Bill(
                            bill_id=bill_number,
                            parent_bag_count=len(parent_codes),
                            created_by_id=user_id
                        )
                        db.session.add(bill)
                        db.session.flush()  # Get bill ID
                        bills_created += 1
                    else:
                        # Bill exists - we'll add parent bags to it
                        logger.info(f"Bill {bill_number} already exists, adding parent bags to it")
                    
                    # Link parent bags to bill
                    batch_links_created = 0
                    batch_parents_not_found = 0
                    
                    for parent_code in parent_codes:
                        # Find parent bag
                        parent_bag = Bag.query.filter_by(
                            qr_id=parent_code.upper(),
                            type=BagType.PARENT.value
                        ).first()
                        
                        if not parent_bag:
                            batch_parents_not_found += 1
                            errors.append(f"Batch {batch_num}: Parent bag '{parent_code}' not found in database")
                            continue
                        
                        # Check if link already exists
                        existing_link = BillBag.query.filter_by(
                            bill_id=bill.id,
                            bag_id=parent_bag.id
                        ).first()
                        
                        if not existing_link:
                            # Create link
                            bill_bag = BillBag(
                                bill_id=bill.id,
                                bag_id=parent_bag.id
                            )
                            db.session.add(bill_bag)
                            batch_links_created += 1
                    
                    # Update bill's parent bag count
                    actual_parent_count = BillBag.query.filter_by(bill_id=bill.id).count()
                    bill.parent_bag_count = actual_parent_count
                    
                    # Commit this batch
                    savepoint.commit()
                    db.session.flush()
                    
                    links_created += batch_links_created
                    parents_not_found += batch_parents_not_found
                    
                    logger.info(f"Batch {batch_num} ({row_range}): Linked bill '{bill_number}' to {batch_links_created} parent bags ({batch_parents_not_found} not found)")
                
                except Exception as batch_error:
                    savepoint.rollback()
                    error_msg = f"Batch {batch_num} (rows {row_range}, bill '{bill_number}'): {str(batch_error)}"
                    errors.append(error_msg)
                    logger.error(f"Batch import error: {error_msg}")
            
            # Final commit
            db.session.commit()
            
            # Log audit
            from audit_utils import log_audit
            log_audit(
                action='BATCH_IMPORT_PARENT_BILL',
                entity_type='bill',
                entity_id=None,
                details=f"Imported {len(batches)} batches: {bills_created} bills, {links_created} parent-bill links ({parents_not_found} parents not found)"
            )
            
            return bills_created, links_created, parents_not_found, errors
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Batch import error: {str(e)}")
            errors.append(f"Database error: {str(e)}")
            return bills_created, links_created, parents_not_found, errors


class MultiFileBatchProcessor:
    """
    Handles processing multiple Excel files in a single upload session.
    Generates detailed error reports for any issues encountered.
    """
    
    @staticmethod
    def generate_error_report(results: List[Dict]) -> bytes:
        """
        Generate an Excel error report from processing results.
        
        Args:
            results: List of file processing results
            
        Returns:
            Excel file as bytes
        """
        if not EXCEL_AVAILABLE:
            return b""
        
        from openpyxl import Workbook
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Import Errors"
        
        # Add headers
        headers = ['File Name', 'Import Type', 'Status', 'Row/Batch', 'Error Details', 'Timestamp']
        for col, header in enumerate(headers, 1):
            ws.cell(1, col, header)
            ws.cell(1, col).font = ws.cell(1, col).font.copy(bold=True)
        
        # Add error data
        row = 2
        for result in results:
            filename = result.get('filename', 'Unknown')
            import_type = result.get('import_type', 'Unknown')
            status = result.get('status', 'Unknown')
            timestamp = result.get('timestamp', '')
            
            # Add main file status
            ws.cell(row, 1, filename)
            ws.cell(row, 2, import_type)
            ws.cell(row, 3, status)
            ws.cell(row, 4, '')
            ws.cell(row, 5, result.get('summary', ''))
            ws.cell(row, 6, timestamp)
            row += 1
            
            # Add detailed errors if any
            errors = result.get('errors', [])
            for error in errors:
                ws.cell(row, 1, filename)
                ws.cell(row, 2, import_type)
                ws.cell(row, 3, 'Error')
                ws.cell(row, 4, '')
                ws.cell(row, 5, error)
                ws.cell(row, 6, timestamp)
                row += 1
        
        # Auto-adjust column widths
        for col in range(1, 7):
            max_length = 0
            column_letter = ws.cell(1, col).column_letter
            for cell in ws[column_letter]:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Save to bytes
        import io
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.read()
    
    @staticmethod
    def process_child_parent_files(files: List[FileStorage], user_id: int, dispatch_area: Optional[str] = None) -> Tuple[List[Dict], bool]:
        """
        Process multiple child-parent batch import files.
        
        Args:
            files: List of uploaded Excel files
            user_id: ID of user performing import
            dispatch_area: Optional dispatch area filter
            
        Returns:
            Tuple of (results_list, has_errors)
        """
        from datetime import datetime
        
        results = []
        has_errors = False
        
        for file in files:
            filename = file.filename or 'unknown.xlsx'
            result = {
                'filename': filename,
                'import_type': 'Child → Parent',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'errors': [],
                'summary': ''
            }
            
            try:
                # Reset stream position
                file.stream.seek(0)
                
                # Parse batches
                batches, parse_errors, stats = ChildParentBatchImporter.parse_excel_batch(file)
                
                # Add parse errors
                if parse_errors:
                    result['errors'].extend(parse_errors[:20])  # Limit to first 20 errors
                    has_errors = True
                
                if not batches:
                    result['status'] = 'Failed'
                    result['summary'] = 'No valid batches found'
                    has_errors = True
                    results.append(result)
                    continue
                
                # Import batches
                parents_created, children_created, links_created, parents_not_found, import_errors = ChildParentBatchImporter.import_batches(
                    db, batches, user_id, dispatch_area
                )
                
                # Add import errors
                if import_errors:
                    result['errors'].extend(import_errors[:20])  # Limit to first 20 errors
                    has_errors = True
                
                # Set status
                if import_errors or parse_errors:
                    result['status'] = 'Partial Success'
                else:
                    result['status'] = 'Success'
                
                result['summary'] = f'{len(batches)} batches, {parents_created} parents, {children_created} children, {links_created} links'
                if parents_not_found > 0:
                    result['summary'] += f', {parents_not_found} parents not found'
                
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
                result['status'] = 'Failed'
                result['summary'] = f'Fatal error: {str(e)}'
                result['errors'].append(str(e))
                has_errors = True
            
            results.append(result)
        
        return results, has_errors
    
    @staticmethod
    def process_parent_bill_files(files: List[FileStorage], user_id: int) -> Tuple[List[Dict], bool]:
        """
        Process multiple parent-bill batch import files.
        
        Args:
            files: List of uploaded Excel files
            user_id: ID of user performing import
            
        Returns:
            Tuple of (results_list, has_errors)
        """
        from datetime import datetime
        
        results = []
        has_errors = False
        
        for file in files:
            filename = file.filename or 'unknown.xlsx'
            result = {
                'filename': filename,
                'import_type': 'Parent → Bill',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'errors': [],
                'summary': ''
            }
            
            try:
                # Reset stream position
                file.stream.seek(0)
                
                # Parse batches
                batches, parse_errors, stats = ParentBillBatchImporter.parse_excel_batch(file)
                
                # Add parse errors
                if parse_errors:
                    result['errors'].extend(parse_errors[:20])  # Limit to first 20 errors
                    has_errors = True
                
                if not batches:
                    result['status'] = 'Failed'
                    result['summary'] = 'No valid batches found'
                    has_errors = True
                    results.append(result)
                    continue
                
                # Import batches
                bills_created, links_created, parents_not_found, import_errors = ParentBillBatchImporter.import_batches(
                    db, batches, user_id
                )
                
                # Add import errors
                if import_errors:
                    result['errors'].extend(import_errors[:20])  # Limit to first 20 errors
                    has_errors = True
                
                # Set status
                if import_errors or parse_errors:
                    result['status'] = 'Partial Success'
                else:
                    result['status'] = 'Success'
                
                result['summary'] = f'{len(batches)} batches, {bills_created} bills, {links_created} links'
                if parents_not_found > 0:
                    result['summary'] += f', {parents_not_found} parents not found'
                
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
                result['status'] = 'Failed'
                result['summary'] = f'Fatal error: {str(e)}'
                result['errors'].append(str(e))
                has_errors = True
            
            results.append(result)
        
        return results, has_errors
