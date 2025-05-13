import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    """User model for authentication and tracking"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="user")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    scans = db.relationship('Scan', backref='scanned_by', lazy='dynamic')
    
    def set_password(self, password):
        """Set user password hash"""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check password against stored hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f"<User {self.username}>"

class ParentBag(db.Model):
    """Parent bag model for tracking parent bags"""
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    child_bags = db.relationship('ChildBag', backref='parent', lazy='dynamic')
    scans = db.relationship('Scan', backref='parent_bag', lazy='dynamic')
    
    def __repr__(self):
        return f"<ParentBag {self.qr_id}>"
    
    def to_dict(self):
        """Convert parent bag to dictionary for API response"""
        return {
            'id': self.id,
            'qr_id': self.qr_id,
            'name': self.name,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'child_count': self.child_bags.count()
        }

class ChildBag(db.Model):
    """Child bag model for tracking child bags"""
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100))
    notes = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('parent_bag.id'))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    scans = db.relationship('Scan', backref='child_bag', lazy='dynamic')
    
    def __repr__(self):
        return f"<ChildBag {self.qr_id}>"
    
    def to_dict(self):
        """Convert child bag to dictionary for API response"""
        return {
            'id': self.id,
            'qr_id': self.qr_id,
            'name': self.name,
            'notes': self.notes,
            'parent_id': self.parent_id,
            'parent_qr_id': self.parent.qr_id if self.parent else None,
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
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('parent_bag.id'), nullable=True)
    child_bag_id = db.Column(db.Integer, db.ForeignKey('child_bag.id'), nullable=True)
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
