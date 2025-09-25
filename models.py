from app_clean import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def can_edit_bills(self):
        return self.role in ['admin', 'biller']

class Bag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    type = db.Column(db.String(50))
    name = db.Column(db.String(200))
    child_count = db.Column(db.Integer, default=0)
    parent_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    dispatch_area = db.Column(db.String(100))
    status = db.Column(db.String(50), default='received')
    weight_kg = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    children = db.relationship('Bag', backref=db.backref('parent', remote_side=[id]))
    
    @property
    def total_weight(self):
        try:
            children_weight = sum(child.weight_kg for child in self.children.all())
            return children_weight + (self.weight_kg or 0.0)
        except:
            return self.weight_kg or 0.0
    
    # Add properties for compatibility
    @property
    def qr_code(self):
        return self.qr_id
    
    @qr_code.setter
    def qr_code(self, value):
        self.qr_id = value
    
    @property
    def customer_name(self):
        return self.name
    
    @customer_name.setter
    def customer_name(self, value):
        self.name = value
    
    @property
    def weight(self):
        return self.weight_kg
    
    @weight.setter
    def weight(self, value):
        self.weight_kg = value

class ScanLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    response_time_ms = db.Column(db.Integer, default=0)
    
    bag = db.relationship('Bag', backref='scan_logs')
    user = db.relationship('User', backref='scan_logs')
