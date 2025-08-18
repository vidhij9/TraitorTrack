import datetime
import enum
import os
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app_clean import db

# Schema-based isolation - no table prefixes needed
# Tables will be isolated by PostgreSQL schemas (production/development)

class UserRole(enum.Enum):
    ADMIN = "admin"
    BILLER = "biller"
    DISPATCHER = "dispatcher"

class BagType(enum.Enum):
    PARENT = "parent"
    CHILD = "child"

class DispatchArea(enum.Enum):
    LUCKNOW = "lucknow"
    INDORE = "indore"
    JAIPUR = "jaipur"
    HISAR = "hisar"
    SRI_GANGANAGAR = "sri_ganganagar"
    SANGARIA = "sangaria"
    BATHINDA = "bathinda"
    RAIPUR = "raipur"
    RANCHI = "ranchi"
    AKOLA = "akola"

class PromotionRequestStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class User(UserMixin, db.Model):
    """User model for authentication and tracking"""
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default=UserRole.DISPATCHER.value)
    dispatch_area = db.Column(db.String(30), nullable=True)  # Only for dispatchers
    verification_token = db.Column(db.String(100), nullable=True)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    scans = db.relationship('Scan', backref='scanned_by', lazy='dynamic')
    
    def set_password(self, password):
        """Set user password hash"""
        # Use default method for consistent hashing
        self.password_hash = generate_password_hash(password)
        # Log for debugging
        import logging
        logging.info(f"Password hash set for user {self.username}: {self.password_hash[:20]}...")
        
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
    
    def is_biller(self):
        """Check if user is a biller"""
        return self.role == UserRole.BILLER.value
    
    def is_dispatcher(self):
        """Check if user is a dispatcher"""
        return self.role == UserRole.DISPATCHER.value
    
    def can_access_area(self, area):
        """Check if user can access a specific dispatch area"""
        if self.is_admin() or self.is_biller():
            return True
        if self.is_dispatcher():
            return self.dispatch_area == area
        return False
    
    def can_edit_bills(self):
        """Check if user can edit bills"""
        return self.is_admin() or self.is_biller()
    
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.is_admin()
    
    def __repr__(self):
        return f"<User {self.username}>"

# Location model removed - no longer needed

class Bag(db.Model):
    """Base bag model with common properties"""
    __tablename__ = 'bag'
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(255), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    child_count = db.Column(db.Integer, nullable=True)  # For parent bags
    parent_id = db.Column(db.Integer, nullable=True)  # For child bags
    dispatch_area = db.Column(db.String(30), nullable=True)  # Area for area-based access control
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    # Ultra-optimized indexes for lightning-fast filtering
    __table_args__ = (
        db.Index('idx_bag_qr_id', 'qr_id'),
        db.Index('idx_bag_type', 'type'),
        db.Index('idx_bag_created_at', 'created_at'),
        db.Index('idx_bag_type_created', 'type', 'created_at'),
        db.Index('idx_bag_name_search', 'name'),
        db.Index('idx_bag_parent_id', 'parent_id'),
        # Ultra-fast filtering indexes for bag management page
        db.Index('idx_bag_dispatch_area', 'dispatch_area'),
        db.Index('idx_bag_type_dispatch', 'type', 'dispatch_area'),
        # Composite indexes for common filter combinations
        db.Index('idx_bag_type_area_created', 'type', 'dispatch_area', 'created_at'),
    )
    
    @property
    def last_scan(self):
        """Get the most recent scan for this bag"""
        # Check if this is a parent or child bag
        if self.type == BagType.PARENT.value:
            return Scan.query.filter_by(parent_bag_id=self.id).order_by(Scan.timestamp.desc()).first()
        else:
            return Scan.query.filter_by(child_bag_id=self.id).order_by(Scan.timestamp.desc()).first()
    
    @property
    def child_bags(self):
        """Get all child bags linked to this parent bag"""
        if self.type != BagType.PARENT.value:
            return []
        links = Link.query.filter_by(parent_bag_id=self.id).all()
        return [link.child_bag for link in links if link.child_bag]
    
    @property
    def parent_bag(self):
        """Get the parent bag this child bag is linked to"""
        if self.type != BagType.CHILD.value:
            return None
        link = Link.query.filter_by(child_bag_id=self.id).first()
        return link.parent_bag if link else None
    
    @property
    def bill(self):
        """Get the bill this bag is associated with (for parent bags)"""
        if self.type != BagType.PARENT.value:
            return None
        bill_link = BillBag.query.filter_by(bag_id=self.id).first()
        return bill_link.bill if bill_link else None
    
    def __repr__(self):
        return f"<Bag {self.qr_id} ({self.type})>"

class Link(db.Model):
    """Link model for associating parent and child bags"""
    __tablename__ = 'link'
    id = db.Column(db.Integer, primary_key=True)
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id', ondelete='CASCADE'), nullable=False)
    child_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    parent_bag = db.relationship('Bag', foreign_keys=[parent_bag_id], backref=db.backref('child_links', lazy='dynamic', cascade='all, delete-orphan'))
    child_bag = db.relationship('Bag', foreign_keys=[child_bag_id], backref=db.backref('parent_links', lazy='dynamic', cascade='all, delete-orphan'))
    # Ultra-fast relationship lookup indexes
    __table_args__ = (
        db.Index('idx_link_parent_id', 'parent_bag_id'),
        db.Index('idx_link_child_id', 'child_bag_id'),
        db.Index('idx_link_parent_child', 'parent_bag_id', 'child_bag_id'),
        db.UniqueConstraint('parent_bag_id', 'child_bag_id', name='uq_parent_child'),
    )
    
    def __repr__(self):
        return f"<Link Parent:{self.parent_bag_id} -> Child:{self.child_bag_id}>"

class Bill(db.Model):
    """Bill model for tracking bills and associated parent bags"""
    __tablename__ = 'bill'
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    parent_bag_count = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='new')  # Possible values: new, processing, completed
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    # Index for faster bill lookups
    __table_args__ = (
        db.Index('idx_bill_id', 'bill_id'),
        db.Index('idx_bill_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Bill {self.bill_id}>"

class BillBag(db.Model):
    """Association model for linking bills to parent bags"""
    __tablename__ = 'bill_bag'
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id', ondelete='CASCADE'), nullable=False)
    bag_id = db.Column(db.Integer, db.ForeignKey('bag.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    bill = db.relationship('Bill', backref=db.backref('bag_links', lazy='dynamic', cascade='all, delete-orphan'))
    bag = db.relationship('Bag', backref=db.backref('bill_links', lazy='dynamic', cascade='all, delete-orphan'))
    # Ultra-fast bill-bag relationship indexes
    __table_args__ = (
        db.Index('idx_bill_bag_bill_id', 'bill_id'),
        db.Index('idx_bill_bag_bag_id', 'bag_id'),
        db.UniqueConstraint('bill_id', 'bag_id', name='uq_bill_bag_new'),
    )
    
    def __repr__(self):
        return f"<BillBag Bill:{self.bill_id} -> Bag:{self.bag_id}>"

class Scan(db.Model):
    """Scan model for tracking all scanning activities"""
    __tablename__ = 'scan'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=True)
    child_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=True)
    # location_id removed - no longer tracking locations
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships with eager loading for performance
    parent_bag = db.relationship('Bag', foreign_keys=[parent_bag_id], backref=db.backref('parent_scans', lazy='dynamic'))
    child_bag = db.relationship('Bag', foreign_keys=[child_bag_id], backref=db.backref('child_scans', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('user_scans', lazy='dynamic', overlaps="scanned_by,scans"), overlaps="scanned_by,scans")
    
    # Indexes for optimized scan queries and reporting
    __table_args__ = (
        db.Index('idx_scan_timestamp', 'timestamp'),
        db.Index('idx_scan_parent_bag', 'parent_bag_id'),
        db.Index('idx_scan_child_bag', 'child_bag_id'),
        db.Index('idx_scan_user', 'user_id'),
    )
    
    def __repr__(self):
        return f"<Scan ID:{self.id} at {self.timestamp}>"

class PromotionRequest(db.Model):
    """Model for handling admin promotion requests"""
    __tablename__ = 'promotionrequest'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    requested_by = db.relationship('User', foreign_keys=[user_id], backref='promotion_requests')
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default=PromotionRequestStatus.PENDING.value)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    processed_by = db.relationship('User', foreign_keys=[admin_id])
    admin_notes = db.Column(db.Text, nullable=True)
    requested_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"<PromotionRequest {self.id}: {self.requested_by.username} - {self.status}>"

class AuditLog(db.Model):
    """Model for tracking all system changes and actions"""
    __tablename__ = 'audit_log'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # e.g., 'create_bill', 'link_bag', 'delete_bill'
    entity_type = db.Column(db.String(20), nullable=False)  # e.g., 'bill', 'bag', 'link'
    entity_id = db.Column(db.Integer, nullable=True)  # ID of the affected entity
    details = db.Column(db.Text, nullable=True)  # JSON string with additional details
    ip_address = db.Column(db.String(45), nullable=True)  # Support IPv6
    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))
    
    # Indexes for fast audit trail queries
    __table_args__ = (
        db.Index('idx_audit_timestamp', 'timestamp'),
        db.Index('idx_audit_user', 'user_id'),
        db.Index('idx_audit_action', 'action'),
        db.Index('idx_audit_entity', 'entity_type', 'entity_id'),
    )
    
    def __repr__(self):
        return f"<AuditLog {self.id}: {self.action} by user {self.user_id} at {self.timestamp}>"