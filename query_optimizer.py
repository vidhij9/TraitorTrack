"""
Database query optimization utilities
Consolidates and optimizes all database queries for maximum performance
"""
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import joinedload, selectinload
from app_clean import db
from models import User, Bag, BagType, Link, Scan, Bill, BillBag
import logging

logger = logging.getLogger(__name__)

class QueryOptimizer:
    """Centralized query optimization for high-performance database operations"""
    
    @staticmethod
    def get_bag_by_qr(qr_id, bag_type=None):
        """Optimized single bag lookup with optional type filter"""
        query = Bag.query.filter_by(qr_id=qr_id)
        if bag_type:
            query = query.filter_by(type=bag_type)
        return query.first()
    
    @staticmethod
    def get_parent_bags_paginated(page=1, per_page=50, search=None):
        """Optimized paginated parent bags with search"""
        query = Bag.query.filter_by(type=BagType.PARENT.value)
        
        if search:
            query = query.filter(
                or_(
                    Bag.qr_id.ilike(f'%{search}%'),
                    Bag.name.ilike(f'%{search}%')
                )
            )
        
        return query.order_by(desc(Bag.created_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
    
    @staticmethod
    def get_child_bags_for_parent(parent_id):
        """Optimized query to get all child bags for a parent"""
        return db.session.query(Bag).join(
            Link, Link.child_bag_id == Bag.id
        ).filter(Link.parent_bag_id == parent_id).all()
    
    @staticmethod
    def get_recent_scans(limit=10, user_id=None):
        """Optimized recent scans query with optional user filter"""
        query = Scan.query.options(
            joinedload(Scan.user),
            joinedload(Scan.parent_bag),
            joinedload(Scan.child_bag)
        )
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        return query.order_by(desc(Scan.timestamp)).limit(limit).all()
    
    @staticmethod
    def get_dashboard_stats():
        """Single optimized query for dashboard statistics"""
        stats = db.session.query(
            func.count().filter(Bag.type == BagType.PARENT.value).label('parent_count'),
            func.count().filter(Bag.type == BagType.CHILD.value).label('child_count'),
            func.count(Bag.id).label('total_bags'),
            func.count(Scan.id).label('total_scans')
        ).outerjoin(Scan).first()
        
        return {
            'parent_count': stats.parent_count or 0,
            'child_count': stats.child_count or 0,
            'total_bags': stats.total_bags or 0,
            'total_scans': stats.total_scans or 0
        }
    
    @staticmethod
    def create_bag_optimized(qr_id, bag_type, name=None, dispatch_area=None):
        """Optimized bag creation with validation to prevent role conflicts"""
        # CRITICAL: Check if bag with this QR already exists with a different type
        existing_bag = Bag.query.filter_by(qr_id=qr_id).first()
        if existing_bag:
            if existing_bag.type != bag_type:
                raise ValueError(f"QR code {qr_id} is already registered as a {existing_bag.type} bag. One bag can only have one role - either parent OR child, never both.")
            # If same type, return existing bag
            return existing_bag
        
        bag = Bag()
        bag.qr_id = qr_id
        bag.type = bag_type
        bag.name = name or f"{bag_type.title()} {qr_id}"
        bag.dispatch_area = dispatch_area
        
        db.session.add(bag)
        db.session.flush()  # Get ID without full commit
        return bag
    
    @staticmethod
    def create_scan_optimized(user_id, parent_bag_id=None, child_bag_id=None):
        """Optimized scan creation"""
        from datetime import datetime
        
        scan = Scan()
        scan.user_id = user_id
        scan.parent_bag_id = parent_bag_id
        scan.child_bag_id = child_bag_id
        scan.timestamp = datetime.utcnow()
        
        db.session.add(scan)
        return scan
    
    @staticmethod
    def create_link_optimized(parent_id, child_id):
        """Optimized link creation with duplicate handling"""
        # Check if link already exists
        existing = Link.query.filter_by(
            parent_bag_id=parent_id, 
            child_bag_id=child_id
        ).first()
        
        if existing:
            return existing, False  # Return existing link, not created
        
        # Create new link
        link = Link()
        link.parent_bag_id = parent_id
        link.child_bag_id = child_id
        
        db.session.add(link)
        return link, True  # Return new link, created
    
    @staticmethod
    def bulk_commit():
        """Optimized bulk commit with error handling"""
        try:
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Bulk commit failed: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def bulk_create_child_bags(parent_bag, child_qr_codes, user_id):
        """Optimized bulk creation of child bags and links"""
        try:
            created_children = []
            created_links = []
            created_scans = []
            
            # Prepare all objects in memory first
            for child_qr in child_qr_codes:
                # Check if child bag already exists
                existing_child = Bag.query.filter_by(qr_id=child_qr).first()
                
                if existing_child:
                    # Check if it's already linked
                    existing_link = Link.query.filter_by(
                        parent_bag_id=parent_bag.id,
                        child_bag_id=existing_child.id
                    ).first()
                    
                    if not existing_link:
                        link = Link(parent_bag_id=parent_bag.id, child_bag_id=existing_child.id)
                        created_links.append(link)
                        
                        # Create scan record
                        scan = QueryOptimizer.create_scan_optimized(user_id, parent_bag.id, existing_child.id)
                        created_scans.append(scan)
                else:
                    # Create new child bag
                    child_bag = Bag(
                        qr_id=child_qr,
                        type=BagType.CHILD.value,
                        name=f"Child of {parent_bag.qr_id}",
                        parent_id=parent_bag.id
                    )
                    created_children.append(child_bag)
            
            # Bulk insert all child bags first
            if created_children:
                db.session.add_all(created_children)
                db.session.flush()  # Get IDs for linking
            
            # Create links for new child bags
            for child_bag in created_children:
                link = Link(parent_bag_id=parent_bag.id, child_bag_id=child_bag.id)
                created_links.append(link)
                
                # Create scan record
                scan = QueryOptimizer.create_scan_optimized(user_id, parent_bag.id, child_bag.id)
                created_scans.append(scan)
            
            # Bulk insert all links and scans
            if created_links:
                db.session.add_all(created_links)
            if created_scans:
                db.session.add_all(created_scans)
            
            # Update parent bag child count
            total_links = Link.query.filter_by(parent_bag_id=parent_bag.id).count() + len(created_links)
            parent_bag.child_count = total_links
            
            # Single commit for everything
            db.session.commit()
            
            return {
                'success': True,
                'children_created': len(created_children),
                'links_created': len(created_links),
                'total_children': total_links
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Bulk child creation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'children_created': 0,
                'links_created': 0
            }

# Global instance for easy access
query_optimizer = QueryOptimizer()