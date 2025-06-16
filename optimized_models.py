"""
Optimized database models with improved indexing and query performance
"""
import datetime
import enum
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app_clean import db
from sqlalchemy import Index, text
from sqlalchemy.orm import joinedload, selectinload

class UserRole(enum.Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"

class BagType(enum.Enum):
    PARENT = "parent"
    CHILD = "child"

class PromotionRequestStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class User(UserMixin, db.Model):
    """Optimized User model with better indexing"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default=UserRole.EMPLOYEE.value, index=True)
    verification_token = db.Column(db.String(100), nullable=True)
    verified = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    last_login = db.Column(db.DateTime, nullable=True)
    login_count = db.Column(db.Integer, default=0)
    
    # Relationships with lazy loading optimization
    scans = db.relationship('Scan', backref='scanned_by', lazy='dynamic')
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_user_username_role', 'username', 'role'),
        Index('idx_user_email_verified', 'email', 'verified'),
        Index('idx_user_created_role', 'created_at', 'role'),
    )
    
    def set_password(self, password):
        """Set user password hash"""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check password against stored hash"""
        if not self.password_hash:
            return False
            
        try:
            return check_password_hash(self.password_hash, password)
        except Exception as e:
            import logging
            logging.error(f"Password check error: {str(e)}")
            return False
    
    def is_admin(self):
        """Check if user is an admin"""
        return self.role == UserRole.ADMIN.value
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'verified': self.verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'login_count': self.login_count
        }
        if include_sensitive:
            data['email'] = self.email
        return data
    
    def __repr__(self):
        return f"<User {self.username}>"

class Bag(db.Model):
    """Optimized Bag model with performance improvements"""
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(255), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=True)
    child_count = db.Column(db.Integer, nullable=True)
    parent_id = db.Column(db.Integer, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    status = db.Column(db.String(20), default='active', index=True)  # active, inactive, archived
    
    # Enhanced indexes for high-performance scanning operations
    __table_args__ = (
        Index('idx_bag_qr_id_type', 'qr_id', 'type'),  # Composite for QR lookups
        Index('idx_bag_type_status', 'type', 'status'),  # For filtered lists
        Index('idx_bag_parent_type', 'parent_id', 'type'),  # For parent-child queries
        Index('idx_bag_created_type', 'created_at', 'type'),  # For time-based queries
        Index('idx_bag_qr_id_hash', text('md5(qr_id)')),  # Hash index for faster QR lookups
    )
    
    @property
    def last_scan(self):
        """Get the most recent scan with optimized query"""
        if self.type == BagType.PARENT.value:
            return db.session.query(Scan)\
                .filter_by(parent_bag_id=self.id)\
                .order_by(Scan.timestamp.desc())\
                .options(joinedload(Scan.user))\
                .first()
        else:
            return db.session.query(Scan)\
                .filter_by(child_bag_id=self.id)\
                .order_by(Scan.timestamp.desc())\
                .options(joinedload(Scan.user))\
                .first()
    
    @property
    def child_bags(self):
        """Get all child bags with optimized query"""
        if self.type != BagType.PARENT.value:
            return []
        return db.session.query(Bag)\
            .filter_by(parent_id=self.id, type=BagType.CHILD.value, status='active')\
            .order_by(Bag.created_at)\
            .all()
    
    @property
    def parent_bag(self):
        """Get parent bag with optimized query"""
        if self.type != BagType.CHILD.value or not self.parent_id:
            return None
        return db.session.query(Bag)\
            .filter_by(id=self.parent_id, type=BagType.PARENT.value)\
            .first()
    
    @property
    def bill(self):
        """Get associated bill with optimized query"""
        if self.type != BagType.PARENT.value:
            return None
        bill_link = db.session.query(BillBag)\
            .filter_by(bag_id=self.id)\
            .options(joinedload(BillBag.bill))\
            .first()
        return bill_link.bill if bill_link else None
    
    def get_scan_count(self):
        """Get total scan count efficiently"""
        if self.type == BagType.PARENT.value:
            return db.session.query(db.func.count(Scan.id)).filter_by(parent_bag_id=self.id).scalar()
        else:
            return db.session.query(db.func.count(Scan.id)).filter_by(child_bag_id=self.id).scalar()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'qr_id': self.qr_id,
            'type': self.type,
            'name': self.name,
            'child_count': self.child_count,
            'parent_id': self.parent_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'scan_count': self.get_scan_count()
        }
    
    def __repr__(self):
        return f"<Bag {self.qr_id} ({self.type})>"

class Link(db.Model):
    """Optimized Link model for parent-child relationships"""
    id = db.Column(db.Integer, primary_key=True)
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id', ondelete='CASCADE'), nullable=False)
    child_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    status = db.Column(db.String(20), default='active', index=True)
    
    # Relationships with optimized loading
    parent_bag = db.relationship('Bag', foreign_keys=[parent_bag_id], 
                               backref=db.backref('child_links', lazy='dynamic', cascade='all, delete-orphan'))
    child_bag = db.relationship('Bag', foreign_keys=[child_bag_id], 
                              backref=db.backref('parent_links', lazy='dynamic', cascade='all, delete-orphan'))
    
    # Enhanced composite indexes
    __table_args__ = (
        Index('idx_link_parent_child_status', 'parent_bag_id', 'child_bag_id', 'status'),
        Index('idx_link_child_parent', 'child_bag_id', 'parent_bag_id'),
        Index('idx_link_created_status', 'created_at', 'status'),
        db.UniqueConstraint('parent_bag_id', 'child_bag_id', name='uq_parent_child'),
    )
    
    def __repr__(self):
        return f"<Link Parent:{self.parent_bag_id} -> Child:{self.child_bag_id}>"

class Bill(db.Model):
    """Optimized Bill model with enhanced indexing"""
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    parent_bag_count = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='new', index=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationship with user
    creator = db.relationship('User', backref='created_bills')
    
    # Enhanced indexes for common queries
    __table_args__ = (
        Index('idx_bill_id_status', 'bill_id', 'status'),
        Index('idx_bill_status_created', 'status', 'created_at'),
        Index('idx_bill_created_by', 'created_by', 'created_at'),
        Index('idx_bill_updated_status', 'updated_at', 'status'),
    )
    
    def get_associated_bags(self):
        """Get all bags associated with this bill efficiently"""
        return db.session.query(Bag)\
            .join(BillBag, Bag.id == BillBag.bag_id)\
            .filter(BillBag.bill_id == self.id)\
            .options(selectinload(Bag.child_links))\
            .all()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'description': self.description,
            'parent_bag_count': self.parent_bag_count,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }
    
    def __repr__(self):
        return f"<Bill {self.bill_id}>"

class BillBag(db.Model):
    """Optimized association model for bills and bags"""
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id', ondelete='CASCADE'), nullable=False)
    bag_id = db.Column(db.Integer, db.ForeignKey('bag.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    
    # Relationships with optimized loading
    bill = db.relationship('Bill', backref=db.backref('bag_links', lazy='dynamic', cascade='all, delete-orphan'))
    bag = db.relationship('Bag', backref=db.backref('bill_links', lazy='dynamic', cascade='all, delete-orphan'))
    
    # Enhanced indexes
    __table_args__ = (
        Index('idx_billbag_bill_created', 'bill_id', 'created_at'),
        Index('idx_billbag_bag_created', 'bag_id', 'created_at'),
        Index('idx_billbag_bill_bag', 'bill_id', 'bag_id'),
        db.UniqueConstraint('bill_id', 'bag_id', name='uq_bill_bag'),
    )
    
    def __repr__(self):
        return f"<BillBag Bill:{self.bill_id} -> Bag:{self.bag_id}>"

class Scan(db.Model):
    """Optimized Scan model for high-performance tracking"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=True)
    child_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    scan_type = db.Column(db.String(20), default='manual', index=True)  # manual, auto, bulk
    location_data = db.Column(db.Text, nullable=True)  # JSON for GPS coordinates if needed
    
    # Relationships with optimized eager loading
    parent_bag = db.relationship('Bag', foreign_keys=[parent_bag_id], 
                               backref=db.backref('parent_scans', lazy='dynamic'))
    child_bag = db.relationship('Bag', foreign_keys=[child_bag_id], 
                              backref=db.backref('child_scans', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('user_scans', lazy='dynamic', overlaps="scanned_by,scans"), 
                         overlaps="scanned_by,scans")
    
    # Comprehensive indexes for all query patterns
    __table_args__ = (
        Index('idx_scan_timestamp_desc', text('timestamp DESC')),  # For recent scans
        Index('idx_scan_user_timestamp', 'user_id', 'timestamp'),  # User activity
        Index('idx_scan_parent_timestamp', 'parent_bag_id', 'timestamp'),  # Parent bag history
        Index('idx_scan_child_timestamp', 'child_bag_id', 'timestamp'),  # Child bag history
        Index('idx_scan_type_timestamp', 'scan_type', 'timestamp'),  # Scan type filtering
        Index('idx_scan_date_user', text('DATE(timestamp)'), 'user_id'),  # Daily statistics
        Index('idx_scan_bags_timestamp', 'parent_bag_id', 'child_bag_id', 'timestamp'),  # Combined queries
    )
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'parent_bag_id': self.parent_bag_id,
            'child_bag_id': self.child_bag_id,
            'user_id': self.user_id,
            'scan_type': self.scan_type,
            'parent_bag_qr': self.parent_bag.qr_id if self.parent_bag else None,
            'child_bag_qr': self.child_bag.qr_id if self.child_bag else None,
            'user_username': self.user.username if self.user else None
        }
    
    def __repr__(self):
        return f"<Scan ID:{self.id} at {self.timestamp}>"

class PromotionRequest(db.Model):
    """Optimized model for admin promotion requests"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default=PromotionRequestStatus.PENDING.value, index=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    requested_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    processed_at = db.Column(db.DateTime, nullable=True, index=True)
    
    # Relationships
    requested_by = db.relationship('User', foreign_keys=[user_id], backref='promotion_requests')
    processed_by = db.relationship('User', foreign_keys=[admin_id])
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_promotion_status_requested', 'status', 'requested_at'),
        Index('idx_promotion_user_status', 'user_id', 'status'),
        Index('idx_promotion_admin_processed', 'admin_id', 'processed_at'),
    )
    
    def __repr__(self):
        return f"<PromotionRequest {self.id}: {self.requested_by.username} - {self.status}>"