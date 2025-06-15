"""
Bill models for managing billing and invoicing.
"""

import datetime
from ..core.app import db

class Bill(db.Model):
    """Model for managing bills/invoices"""
    __tablename__ = 'bill'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_contact = db.Column(db.String(100), nullable=True)
    total_amount = db.Column(db.Numeric(10, 2), nullable=True)
    status = db.Column(db.String(20), default='draft')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    bags = db.relationship('BillBag', backref='bill', lazy='dynamic')
    scans = db.relationship('Scan', backref='bill', lazy='dynamic')
    creator = db.relationship('User', backref='created_bills')
    
    @property
    def bag_count(self):
        """Get total number of bags in this bill"""
        return self.bags.count()
    
    @property
    def parent_bags(self):
        """Get all parent bags in this bill"""
        return [bb.bag for bb in self.bags if bb.bag.type == 'parent']
    
    @property
    def is_complete(self):
        """Check if bill scanning is complete"""
        return self.status == 'complete'
    
    def __repr__(self):
        return f"<Bill {self.bill_number}>"

class BillBag(db.Model):
    """Association table for bills and bags"""
    __tablename__ = 'bill_bag'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Unique constraint to prevent duplicate bag-bill associations
    __table_args__ = (
        db.UniqueConstraint('bill_id', 'bag_id', name='unique_bill_bag'),
        db.Index('idx_bill_bag_bill_id', 'bill_id'),
        db.Index('idx_bill_bag_bag_id', 'bag_id'),
    )
    
    def __repr__(self):
        return f"<BillBag Bill:{self.bill_id} Bag:{self.bag_id}>"