"""
Scan model for tracking QR code scans.
"""

import datetime
from ..core.app import db

class Scan(db.Model):
    """Model for tracking individual QR code scans"""
    __tablename__ = 'scan'
    
    id = db.Column(db.Integer, primary_key=True)
    qr_code = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=True)
    child_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=True)
    
    # Additional metadata
    ip_address = db.Column(db.String(45), nullable=True)  # Support IPv6
    user_agent = db.Column(db.Text, nullable=True)
    location_data = db.Column(db.Text, nullable=True)  # JSON string for location info
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_scan_qr_code', 'qr_code'),
        db.Index('idx_scan_timestamp', 'timestamp'),
        db.Index('idx_scan_user_id', 'user_id'),
    )
    
    @property
    def bag(self):
        """Get the associated bag (parent or child)"""
        if self.parent_bag_id:
            return Bag.query.get(self.parent_bag_id)
        elif self.child_bag_id:
            return Bag.query.get(self.child_bag_id)
        return None
    
    @property
    def formatted_timestamp(self):
        """Get formatted timestamp string"""
        return self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
    def __repr__(self):
        return f"<Scan {self.qr_code} at {self.timestamp}>"