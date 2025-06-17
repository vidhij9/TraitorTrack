"""
Link model for connecting parent and child bags.
"""

import datetime
from ..core.app import db

class Link(db.Model):
    """Model for linking parent and child bags"""
    __tablename__ = 'link'
    
    id = db.Column(db.Integer, primary_key=True)
    parent_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=False)
    child_bag_id = db.Column(db.Integer, db.ForeignKey('bag.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Unique constraint to prevent duplicate links
    __table_args__ = (
        db.UniqueConstraint('parent_bag_id', 'child_bag_id', name='unique_parent_child_link'),
        db.Index('idx_link_parent_bag_id', 'parent_bag_id'),
        db.Index('idx_link_child_bag_id', 'child_bag_id'),
    )
    
    # Relationships
    creator = db.relationship('User', backref='created_links')
    
    def __repr__(self):
        return f"<Link Parent:{self.parent_bag_id} Child:{self.child_bag_id}>"
