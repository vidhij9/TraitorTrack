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

class Product(db.Model):
    """Product model for items being tracked"""
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    manufacturer = db.Column(db.String(100))
    category = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    scans = db.relationship('Scan', backref='product', lazy='dynamic')
    
    def __repr__(self):
        return f"<Product {self.name} ({self.qr_id})>"
    
    def to_dict(self):
        """Convert product to dictionary for API response"""
        return {
            'id': self.id,
            'qr_id': self.qr_id,
            'name': self.name,
            'description': self.description,
            'manufacturer': self.manufacturer,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Location(db.Model):
    """Location model for tracking product movements"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    location_type = db.Column(db.String(50))  # warehouse, distribution center, retail, etc.
    scans = db.relationship('Scan', backref='location', lazy='dynamic')
    
    def __repr__(self):
        return f"<Location {self.name}>"
    
    def to_dict(self):
        """Convert location to dictionary for API response"""
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'location_type': self.location_type
        }

class Scan(db.Model):
    """Scan model for recording product movement events"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(50))  # received, in-transit, delivered, etc.
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f"<Scan {self.id} - Product {self.product_id}>"
    
    def to_dict(self):
        """Convert scan to dictionary for API response"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_qr': self.product.qr_id if self.product else None,
            'product_name': self.product.name if self.product else None,
            'user_id': self.user_id,
            'username': self.scanned_by.username if self.scanned_by else None,
            'location_id': self.location_id,
            'location_name': self.location.name if self.location else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'status': self.status,
            'notes': self.notes
        }
