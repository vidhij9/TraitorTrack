import datetime
import enum
import json
import os
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

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
    
    # Account lockout fields
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_failed_login = db.Column(db.DateTime, nullable=True)
    
    # Password reset fields
    password_reset_token = db.Column(db.String(100), nullable=True)
    password_reset_token_expires = db.Column(db.DateTime, nullable=True)
    
    # Two-Factor Authentication (TOTP) fields
    totp_secret = db.Column(db.String(32), nullable=True)  # Base32-encoded TOTP secret
    two_fa_enabled = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        """Set user password hash"""
        # Use fast bcrypt hashing if available
        try:
            from fast_auth import FastAuth
            self.password_hash = FastAuth.hash_password(password)
        except ImportError:
            # Fallback to werkzeug
            self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check password against stored hash"""
        if not self.password_hash:
            return False
            
        try:
            # Use fast authentication if available
            try:
                from fast_auth import FastAuth
                return FastAuth.verify_password(password, self.password_hash)
            except ImportError:
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)  # Owner/scanner of the bag
    dispatch_area = db.Column(db.String(30), nullable=True)  # Area for area-based access control
    status = db.Column(db.String(20), default='pending')  # pending, completed (for parent bags)
    weight_kg = db.Column(db.Float, default=0.0)  # Weight in kg (1kg per child, 30kg for full parent)
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
        db.Index('idx_bag_user_id', 'user_id'),  # Index for user ownership queries
        # Ultra-fast filtering indexes for bag management page
        db.Index('idx_bag_dispatch_area', 'dispatch_area'),
        db.Index('idx_bag_type_dispatch', 'type', 'dispatch_area'),
        # Composite indexes for common filter combinations
        db.Index('idx_bag_type_area_created', 'type', 'dispatch_area', 'created_at'),
        db.Index('idx_bag_user_type', 'user_id', 'type'),  # For user's bags by type
    )
    
    # Relationship to User model
    owner = db.relationship('User', backref=db.backref('owned_bags', lazy='dynamic'))
    
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


# SQLAlchemy event listeners for automatic QR code normalization
from sqlalchemy import event

@event.listens_for(Bag, 'before_insert')
@event.listens_for(Bag, 'before_update')
def normalize_qr_code(mapper, connection, target):
    """
    Automatically normalize QR codes to uppercase before saving to database.
    
    This ensures case-insensitive uniqueness and consistent data storage.
    Works in conjunction with the database-level unique constraint on UPPER(qr_id).
    """
    if target.qr_id:
        target.qr_id = target.qr_id.upper()


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
    total_weight_kg = db.Column(db.Float, default=0.0)  # Actual weight based on real child count
    expected_weight_kg = db.Column(db.Float, default=0.0)  # Expected weight (30kg per parent bag)
    total_child_bags = db.Column(db.Integer, default=0)  # Total number of child bags
    status = db.Column(db.String(20), default='new')  # Possible values: new, processing, completed
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    created_by = db.relationship('User', backref=db.backref('created_bills', lazy='dynamic'))
    # Ultra-fast indexes for bill management
    __table_args__ = (
        db.Index('idx_bill_id', 'bill_id'),
        db.Index('idx_bill_status', 'status'),
        db.Index('idx_bill_created', 'created_at'),
        db.Index('idx_bill_status_created', 'status', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Bill {self.bill_id}>"
    
    def recalculate_weights(self):
        """
        Recalculate bill weights from scratch based on current linked bags.
        Fixes edge cases like deleted parent bags or modified child weights.
        
        Returns:
            tuple: (actual_weight, expected_weight, parent_count, child_count)
        """
        from sqlalchemy import text
        
        # Calculate actual weight from all child bags
        actual_weight_result = db.session.execute(
            text("""
                SELECT COALESCE(SUM(child.weight_kg), 0)
                FROM bill_bag bb
                JOIN bag parent ON bb.bag_id = parent.id
                LEFT JOIN link l ON parent.id = l.parent_bag_id
                LEFT JOIN bag child ON l.child_bag_id = child.id
                WHERE bb.bill_id = :bill_id AND parent.type = 'parent'
            """),
            {'bill_id': self.id}
        ).scalar()
        
        actual_weight = float(actual_weight_result or 0)
        
        # Count linked parent bags
        parent_count = BillBag.query.filter_by(bill_id=self.id).count()
        
        # Count total child bags
        child_count_result = db.session.execute(
            text("""
                SELECT COUNT(DISTINCT child.id)
                FROM bill_bag bb
                JOIN bag parent ON bb.bag_id = parent.id
                LEFT JOIN link l ON parent.id = l.parent_bag_id
                LEFT JOIN bag child ON l.child_bag_id = child.id
                WHERE bb.bill_id = :bill_id AND parent.type = 'parent' AND child.id IS NOT NULL
            """),
            {'bill_id': self.id}
        ).scalar()
        
        child_count = int(child_count_result or 0)
        
        # Expected weight is 30kg per parent bag
        expected_weight = parent_count * 30.0
        
        # Update ALL bill fields to fix stale data
        self.parent_bag_count = parent_count  # FIX: Update parent count
        self.total_weight_kg = actual_weight
        self.expected_weight_kg = expected_weight
        self.total_child_bags = child_count
        
        return (actual_weight, expected_weight, parent_count, child_count)

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
        # OPTIMIZED FOR 1.8M+ BAGS: Composite indexes for common queries
        db.Index('idx_scan_user_timestamp', 'user_id', 'timestamp'),  # User's scan history
        db.Index('idx_scan_timestamp_user', 'timestamp', 'user_id'),  # Recent scans by user
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
    """Model for tracking all system changes and actions with before/after snapshots"""
    __tablename__ = 'audit_log'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # e.g., 'create_bill', 'link_bag', 'delete_bill'
    entity_type = db.Column(db.String(20), nullable=False)  # e.g., 'bill', 'bag', 'link'
    entity_id = db.Column(db.Integer, nullable=True)  # ID of the affected entity
    details = db.Column(db.Text, nullable=True)  # JSON string with additional details
    before_state = db.Column(db.Text, nullable=True)  # JSON snapshot of entity state before change
    after_state = db.Column(db.Text, nullable=True)  # JSON snapshot of entity state after change
    ip_address = db.Column(db.String(45), nullable=True)  # Support IPv6
    request_id = db.Column(db.String(36), nullable=True)  # UUID from request tracking
    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))
    
    # Indexes for fast audit trail queries
    __table_args__ = (
        db.Index('idx_audit_timestamp', 'timestamp'),
        db.Index('idx_audit_user', 'user_id'),
        db.Index('idx_audit_action', 'action'),
        db.Index('idx_audit_entity', 'entity_type', 'entity_id'),
        # OPTIMIZED FOR 1.8M+ BAGS: Composite indexes for audit queries
        db.Index('idx_audit_user_timestamp', 'user_id', 'timestamp'),  # User audit history
        db.Index('idx_audit_action_timestamp', 'action', 'timestamp'),  # Action timeline
        db.Index('idx_audit_request_id', 'request_id'),  # Request correlation
    )
    
    def __repr__(self):
        return f"<AuditLog {self.id}: {self.action} by user {self.user_id} at {self.timestamp}>"
    
    def get_changes(self):
        """
        Compare before and after states to identify what changed.
        Returns a dict of field: (old_value, new_value) for changed fields.
        """
        if not self.before_state or not self.after_state:
            return None
        
        try:
            before = json.loads(self.before_state)
            after = json.loads(self.after_state)
            changes = {}
            
            all_keys = set(before.keys()) | set(after.keys())
            for key in all_keys:
                old_val = before.get(key)
                new_val = after.get(key)
                if old_val != new_val:
                    changes[key] = (old_val, new_val)
            
            return changes
        except (json.JSONDecodeError, AttributeError):
            return None