"""
Role and permission models.
"""

import datetime
import enum
from ..core.app import db

class PromotionRequestStatus(enum.Enum):
    """Status enumeration for promotion requests"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class PromotionRequest(db.Model):
    """Model for user promotion requests"""
    __tablename__ = 'promotion_request'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requested_role = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default=PromotionRequestStatus.PENDING.value)
    reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    processed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='promotion_requests')
    processor = db.relationship('User', foreign_keys=[processed_by], backref='processed_promotions')
    
    @property
    def is_pending(self):
        """Check if request is still pending"""
        return self.status == PromotionRequestStatus.PENDING.value
    
    def approve(self, processor_id):
        """Approve the promotion request"""
        self.status = PromotionRequestStatus.APPROVED.value
        self.processed_at = datetime.datetime.utcnow()
        self.processed_by = processor_id
    
    def reject(self, processor_id):
        """Reject the promotion request"""
        self.status = PromotionRequestStatus.REJECTED.value
        self.processed_at = datetime.datetime.utcnow()
        self.processed_by = processor_id
    
    def __repr__(self):
        return f"<PromotionRequest {self.user_id} -> {self.requested_role}>"