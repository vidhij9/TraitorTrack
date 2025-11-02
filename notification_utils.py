"""
Notification Utilities for TraitorTrack
Handles creation, management, and delivery of in-app notifications
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import and_

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manager class for handling notifications"""
    
    @staticmethod
    def create_notification(
        db,
        user_id: int,
        title: str,
        message: str,
        notification_type: str = 'info',
        priority: int = 0,
        link: Optional[str] = None
    ):
        """
        Create a new notification for a user
        
        Args:
            db: Database session
            user_id: ID of the user to notify
            title: Notification title
            message: Notification message
            notification_type: Type of notification (info, success, warning, error)
            priority: Priority level (0=low, 1=medium, 2=high, 3=critical)
            link: Optional link to related page
            
        Returns:
            Notification object if successful, None otherwise
        """
        try:
            from models import Notification
            
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                link=link
            )
            
            db.session.add(notification)
            db.session.commit()
            
            logger.info(f"Notification created for user {user_id}: {title}")
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification: {e}", exc_info=True)
            db.session.rollback()
            return None
    
    @staticmethod
    def create_bulk_notification(
        db,
        user_ids: List[int],
        title: str,
        message: str,
        notification_type: str = 'info',
        priority: int = 0,
        link: Optional[str] = None
    ):
        """
        Create notifications for multiple users
        
        Args:
            db: Database session
            user_ids: List of user IDs to notify
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            link: Optional link
            
        Returns:
            Number of notifications created
        """
        try:
            from models import Notification
            
            notifications = [
                Notification(
                    user_id=user_id,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    priority=priority,
                    link=link
                )
                for user_id in user_ids
            ]
            
            db.session.bulk_save_objects(notifications)
            db.session.commit()
            
            logger.info(f"Created {len(notifications)} notifications for {len(user_ids)} users")
            return len(notifications)
            
        except Exception as e:
            logger.error(f"Error creating bulk notifications: {e}", exc_info=True)
            db.session.rollback()
            return 0
    
    @staticmethod
    def get_user_notifications(
        db,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50
    ):
        """
        Get notifications for a user
        
        Args:
            db: Database session
            user_id: User ID
            unread_only: If True, only return unread notifications
            limit: Maximum number of notifications to return
            
        Returns:
            List of Notification objects
        """
        try:
            from models import Notification
            
            query = Notification.query.filter_by(user_id=user_id)
            
            if unread_only:
                query = query.filter_by(is_read=False)
            
            notifications = query.order_by(
                Notification.priority.desc(),
                Notification.created_at.desc()
            ).limit(limit).all()
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error fetching notifications: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_unread_count(db, user_id: int):
        """
        Get count of unread notifications for a user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Count of unread notifications
        """
        try:
            from models import Notification
            
            count = Notification.query.filter_by(
                user_id=user_id,
                is_read=False
            ).count()
            
            return count
            
        except Exception as e:
            logger.error(f"Error getting unread count: {e}", exc_info=True)
            return 0
    
    @staticmethod
    def mark_as_read(db, notification_id: int, user_id: int):
        """
        Mark a notification as read
        
        Args:
            db: Database session
            notification_id: Notification ID
            user_id: User ID (for security check)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from models import Notification
            
            notification = Notification.query.filter_by(
                id=notification_id,
                user_id=user_id
            ).first()
            
            if notification:
                notification.mark_as_read()
                db.session.commit()
                logger.info(f"Notification {notification_id} marked as read for user {user_id}")
                return True
            else:
                logger.warning(f"Notification {notification_id} not found or access denied for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}", exc_info=True)
            db.session.rollback()
            return False
    
    @staticmethod
    def mark_all_as_read(db, user_id: int):
        """
        Mark all notifications as read for a user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Number of notifications marked as read
        """
        try:
            from models import Notification
            
            unread_notifications = Notification.query.filter_by(
                user_id=user_id,
                is_read=False
            ).all()
            
            count = 0
            for notification in unread_notifications:
                notification.mark_as_read()
                count += 1
            
            db.session.commit()
            logger.info(f"Marked {count} notifications as read for user {user_id}")
            return count
            
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}", exc_info=True)
            db.session.rollback()
            return 0
    
    @staticmethod
    def delete_notification(db, notification_id: int, user_id: int):
        """
        Delete a notification
        
        Args:
            db: Database session
            notification_id: Notification ID
            user_id: User ID (for security check)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from models import Notification
            
            notification = Notification.query.filter_by(
                id=notification_id,
                user_id=user_id
            ).first()
            
            if notification:
                db.session.delete(notification)
                db.session.commit()
                logger.info(f"Notification {notification_id} deleted for user {user_id}")
                return True
            else:
                logger.warning(f"Notification {notification_id} not found or access denied for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting notification: {e}", exc_info=True)
            db.session.rollback()
            return False
    
    @staticmethod
    def cleanup_old_notifications(db, days: int = 30):
        """
        Delete read notifications older than specified days
        
        Args:
            db: Database session
            days: Number of days to keep read notifications
            
        Returns:
            Number of notifications deleted
        """
        try:
            from models import Notification
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            old_notifications = Notification.query.filter(
                and_(
                    Notification.is_read == True,
                    Notification.created_at < cutoff_date
                )
            ).all()
            
            count = len(old_notifications)
            for notification in old_notifications:
                db.session.delete(notification)
            
            db.session.commit()
            logger.info(f"Cleaned up {count} old notifications (older than {days} days)")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up notifications: {e}", exc_info=True)
            db.session.rollback()
            return 0


def notify_user(
    db,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = 'info',
    priority: int = 0,
    link: Optional[str] = None
):
    """
    Helper function to create a notification
    Wrapper around NotificationManager.create_notification
    """
    return NotificationManager.create_notification(
        db, user_id, title, message,
        notification_type, priority, link
    )


def notify_admins(
    db,
    title: str,
    message: str,
    notification_type: str = 'warning',
    priority: int = 2,
    link: Optional[str] = None
):
    """
    Notify all admin users
    
    Args:
        db: Database session
        title: Notification title
        message: Notification message
        notification_type: Type of notification
        priority: Priority level
        link: Optional link
        
    Returns:
        Number of admins notified
    """
    try:
        from models import User
        
        # Get all admin users
        admin_users = User.query.filter_by(role='admin').all()
        admin_ids = [admin.id for admin in admin_users]
        
        if admin_ids:
            return NotificationManager.create_bulk_notification(
                db, admin_ids, title, message,
                notification_type, priority, link
            )
        else:
            logger.warning("No admin users found to notify")
            return 0
            
    except Exception as e:
        logger.error(f"Error notifying admins: {e}", exc_info=True)
        return 0
