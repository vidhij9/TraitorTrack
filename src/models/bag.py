"""
Bag models for tracking parent and child bags.
"""

import datetime
import enum
from ..core.app import db

class BagType(enum.Enum):
    """Bag type enumeration"""
    PARENT = "parent"
    CHILD = "child"

class Bag(db.Model):
    """Base bag model with common properties"""
    __tablename__ = 'bag'
    
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(255), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    child_count = db.Column(db.Integer, nullable=True)  # For parent bags
    parent_id = db.Column(db.Integer, nullable=True)  # For child bags
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Indexes for faster bag lookups during high-volume scanning
    __table_args__ = (
        db.Index('idx_bag_qr_id', 'qr_id'),
        db.Index('idx_bag_type', 'type'),
    )
    
    # Relationships
    child_links = db.relationship('Link', foreign_keys='Link.parent_bag_id', 
                                 backref='parent_bag', lazy='dynamic')
    parent_links = db.relationship('Link', foreign_keys='Link.child_bag_id',
                                  backref='child_bag', lazy='dynamic')
    bill_links = db.relationship('BillBag', backref='bag', lazy='dynamic')
    
    @property
    def last_scan(self):
        """Get the most recent scan for this bag"""
        if self.type == BagType.PARENT.value:
            return Scan.query.filter_by(parent_bag_id=self.id).order_by(Scan.timestamp.desc()).first()
        else:
            return Scan.query.filter_by(child_bag_id=self.id).order_by(Scan.timestamp.desc()).first()
    
    @property
    def child_bags(self):
        """Get all child bags linked to this parent bag"""
        if self.type != BagType.PARENT.value:
            return []
        return [link.child_bag for link in self.child_links]
    
    @property
    def parent_bag(self):
        """Get the parent bag this child bag is linked to"""
        if self.type != BagType.CHILD.value:
            return None
        link = self.parent_links.first()
        return link.parent_bag if link else None
    
    @property
    def bill(self):
        """Get the bill this bag is associated with"""
        if self.type != BagType.PARENT.value:
            return None
        bill_link = self.bill_links.first()
        return bill_link.bill if bill_link else None
    
    @property
    def scan_count(self):
        """Get total number of scans for this bag"""
        if self.type == BagType.PARENT.value:
            return Scan.query.filter_by(parent_bag_id=self.id).count()
        else:
            return Scan.query.filter_by(child_bag_id=self.id).count()
    
    def __repr__(self):
        return f"<Bag {self.qr_id} ({self.type})>"