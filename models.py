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

class User(UserMixin, db.Model):
    """User model for authentication and tracking"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default=UserRole.EMPLOYEE.value)
    verification_token = db.Column(db.String(100), nullable=True)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    scans = db.relationship('Scan', backref='scanned_by', lazy='dynamic')
    
    def set_password(self, password):
        """Set user password hash"""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check password against stored hash"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user is an admin"""
        return self.role == UserRole.ADMIN.value
    
    def __repr__(self):
        return f"<User {self.username}>"
    
    def to_dict(self):
        """Convert user to dictionary for API response"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'verified': self.verified,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Bag(db.Model):
    """Unified bag model for tracking both parent and child bags"""
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100))
    type = db.Column(db.String(20), nullable=False)  # 'parent' or 'child'
    notes = db.Column(db.Text)
    child_count = db.Column(db.Integer, default=0)
    parent_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=True)
    linked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    children = db.relationship('Bag', backref=db.backref('parent_bag', remote_side=[id]), lazy='dynamic')
    parent_scans = db.relationship('Scan', primaryjoin="Scan.parent_bag_id == Bag.id", backref="parent_bag", lazy='dynamic')
    child_scans = db.relationship('Scan', primaryjoin="Scan.child_bag_id == Bag.id", backref="child_bag", lazy='dynamic')
    
    def __repr__(self):
        return f"<Bag {self.qr_id} - Type: {self.type}>"
    
    @property
    def scans(self):
        """Get all scans for this bag, whether as parent or child"""
        from sqlalchemy import or_
        return Scan.query.filter(or_(Scan.parent_bag_id == self.id, Scan.child_bag_id == self.id))
    
    def to_dict(self, include_children=False):
        """Convert bag to dictionary for API response"""
        result = {
            'id': self.id,
            'qr_id': self.qr_id,
            'name': self.name,
            'type': self.type,
            'notes': self.notes,
            'parent_id': self.parent_id,
            'linked': self.linked,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if self.type == BagType.PARENT.value:
            result['child_count'] = self.child_count
            if include_children:
                result['children'] = [child.to_dict() for child in self.children]
        elif self.type == BagType.CHILD.value and self.parent_bag:
            result['parent_qr_id'] = self.parent_bag.qr_id
            
        return result

class Link(db.Model):
    """Link model for connecting bags to bills"""
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=False, unique=True)
    bill_id = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    parent_bag = db.relationship('Bag', backref=db.backref('link', uselist=False))
    
    def __repr__(self):
        return f"<Link {self.id} - Bill: {self.bill_id}, Parent: {self.parent_id}>"
    
    def to_dict(self):
        """Convert link to dictionary for API response"""
        return {
            'id': self.id,
            'parent_id': self.parent_id,
            'parent_qr_id': self.parent_bag.qr_id if self.parent_bag else None,
            'bill_id': self.bill_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Location(db.Model):
    """Location model for tracking bag movements"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    scans = db.relationship('Scan', backref='location', lazy='dynamic')
    
    def __repr__(self):
        return f"<Location {self.name}>"
    
    def to_dict(self):
        """Convert location to dictionary for API response"""
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Scan(db.Model):
    """Scan model for recording bag scans"""
    id = db.Column(db.Integer, primary_key=True)
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=True)
    child_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    scan_type = db.Column(db.String(20))  # 'parent' or 'child'
    notes = db.Column(db.Text)
    
    def __repr__(self):
        if self.parent_bag_id:
            return f"<Scan {self.id} - ParentBag {self.parent_bag_id}>"
        elif self.child_bag_id:
            return f"<Scan {self.id} - ChildBag {self.child_bag_id}>"
        return f"<Scan {self.id}>"
    
    def to_dict(self):
        """Convert scan to dictionary for API response"""
        bag_id = None
        bag_qr = None
        
        if self.parent_bag_id:
            bag_id = self.parent_bag_id
            bag_qr = self.parent_bag.qr_id if self.parent_bag else None
        elif self.child_bag_id:
            bag_id = self.child_bag_id
            bag_qr = self.child_bag.qr_id if self.child_bag else None
            
        return {
            'id': self.id,
            'bag_id': bag_id,
            'bag_qr': bag_qr,
            'scan_type': self.scan_type,
            'user_id': self.user_id,
            'username': self.scanned_by.username if self.scanned_by else None,
            'location_id': self.location_id,
            'location_name': self.location.name if self.location else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'notes': self.notes
        }
