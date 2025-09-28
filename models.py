from app_clean import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        return str(self.id)

class Bag(db.Model):
    __tablename__ = 'bags'
    id = db.Column(db.Integer, primary_key=True)
    qr_code = db.Column(db.String(100), unique=True, nullable=False)
    customer_name = db.Column(db.String(200))
    weight = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='created')
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('bags.id'))
    is_parent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Scan(db.Model):
    __tablename__ = 'scans'
    id = db.Column(db.Integer, primary_key=True)
    bag_id = db.Column(db.Integer, db.ForeignKey('bags.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    scan_type = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
