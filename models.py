import datetime
import enum
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

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
    """User model for authentication and tracking"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default=UserRole.EMPLOYEE.value)
    verified = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    scans = db.relationship('Scan', backref='scanned_by', lazy='dynamic')
    
    def set_password(self, password):
        """Set user password hash"""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check password against stored hash"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user is an admin"""
        return self.role == UserRole.ADMIN.value
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'verified': self.verified,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<User {self.username}>"

class Bag(db.Model):
    """Base bag model with common properties"""
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    type = db.Column(db.String(10), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=True)
    child_count = db.Column(db.Integer, nullable=True)
    parent_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    @property
    def last_scan(self):
        """Get the most recent scan for this bag"""
        if self.type == BagType.PARENT.value:
            return Scan.query.filter_by(parent_bag_id=self.id).order_by(Scan.timestamp.desc()).first()
        else:
            return Scan.query.filter_by(child_bag_id=self.id).order_by(Scan.timestamp.desc()).first()
    
    def to_dict(self):
        return {
            'id': self.id,
            'qr_id': self.qr_id,
            'type': self.type,
            'name': self.name,
            'child_count': self.child_count,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"<Bag {self.qr_id} ({self.type})>"

class Link(db.Model):
    """Link model to connect parent and child bags"""
    id = db.Column(db.Integer, primary_key=True)
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=False)
    child_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=False)
    linked_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    linked_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    parent_bag = db.relationship('Bag', foreign_keys=[parent_bag_id])
    child_bag = db.relationship('Bag', foreign_keys=[child_bag_id])
    user = db.relationship('User')
    
    __table_args__ = (
        db.UniqueConstraint('parent_bag_id', 'child_bag_id', name='unique_parent_child_link'),
        db.Index('idx_link_parent', 'parent_bag_id'),
        db.Index('idx_link_child', 'child_bag_id'),
    )
    
    def __repr__(self):
        return f"<Link Parent:{self.parent_bag_id} Child:{self.child_bag_id}>"

class Scan(db.Model):
    """Scan model to track bag scanning activities"""
    id = db.Column(db.Integer, primary_key=True)
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=True)
    child_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    notes = db.Column(db.Text, nullable=True)
    
    parent_bag = db.relationship('Bag', foreign_keys=[parent_bag_id])
    child_bag = db.relationship('Bag', foreign_keys=[child_bag_id])
    user = db.relationship('User')
    
    __table_args__ = (
        db.Index('idx_scan_timestamp', 'timestamp'),
        db.Index('idx_scan_user', 'user_id'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'parent_bag_id': self.parent_bag_id,
            'child_bag_id': self.child_bag_id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f"<Scan {self.id} by User:{self.user_id}>"

class Bill(db.Model):
    """Bill model for tracking billing information"""
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    user = db.relationship('User')
    bags = db.relationship('BillBag', backref='bill', lazy='dynamic')
    
    def __repr__(self):
        return f"<Bill {self.bill_id}>"

class BillBag(db.Model):
    """Association table for bills and bags"""
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    bag = db.relationship('Bag')
    
    __table_args__ = (
        db.UniqueConstraint('bill_id', 'bag_id', name='unique_bill_bag'),
    )

class PromotionRequest(db.Model):
    """Model for tracking employee promotion requests"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    current_role = db.Column(db.String(20), nullable=False)
    requested_role = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default=PromotionRequestStatus.PENDING.value)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    
    user = db.relationship('User', foreign_keys=[user_id])
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    def __repr__(self):
        return f"<PromotionRequest {self.id} by User:{self.user_id}>"