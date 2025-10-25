"""
Enhanced Audit Logging Utilities
Provides comprehensive before/after snapshots for entity changes
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Union
from flask import request, g
from flask_login import current_user
from app import db

logger = logging.getLogger(__name__)


def serialize_entity(entity: Any, exclude_fields: list = None) -> Dict[str, Any]:
    """
    Serialize a SQLAlchemy model instance to a dictionary.
    
    Args:
        entity: SQLAlchemy model instance
        exclude_fields: List of field names to exclude from serialization
        
    Returns:
        Dictionary representation of the entity
    """
    if entity is None:
        return None
    
    # Default exclusions: passwords, tokens, internal state, lockout data
    default_exclusions = [
        '_sa_instance_state',
        'password_hash',
        'verification_token',      # Email verification tokens
        'reset_token',             # Password reset tokens
        'api_key',                 # API authentication keys
        'secret_key',              # Any secret keys
        'failed_login_attempts',   # Security-related internal state
        'locked_until',            # Account lockout timestamps
        'last_failed_login'        # Failed login tracking
    ]
    
    # Merge default exclusions with custom ones
    exclude_fields = exclude_fields or []
    all_exclusions = list(set(default_exclusions + exclude_fields))
    
    result = {}
    
    # Get all columns
    try:
        from sqlalchemy.inspection import inspect
        mapper = inspect(entity.__class__)
        
        for column in mapper.columns:
            key = column.key
            if key not in all_exclusions:
                value = getattr(entity, key, None)
                
                # Handle datetime serialization
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                # Handle enum serialization
                elif hasattr(value, 'value'):
                    result[key] = value.value
                # Handle other types
                else:
                    result[key] = value
    except Exception as e:
        logger.error(f"Error serializing entity: {str(e)}")
        result = {'error': 'Serialization failed', 'entity_type': type(entity).__name__}
    
    # Add metadata about what was excluded
    if len(all_exclusions) > len(default_exclusions):
        result['_excluded_fields'] = [f for f in all_exclusions if f not in default_exclusions]
    
    return result


def log_audit_with_snapshot(
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    before_state: Optional[Union[Dict, Any]] = None,
    after_state: Optional[Union[Dict, Any]] = None,
    details: Optional[Dict] = None,
    auto_serialize: bool = True
):
    """
    Log an audit trail entry with before/after snapshots.
    
    Args:
        action: The action being performed (e.g., 'update_user', 'delete_bag')
        entity_type: Type of entity (e.g., 'user', 'bag', 'bill')
        entity_id: ID of the affected entity
        before_state: Entity state before change (dict or model instance)
        after_state: Entity state after change (dict or model instance)
        details: Additional context about the change
        auto_serialize: Whether to auto-serialize SQLAlchemy models
        
    Example:
        # Manual snapshots
        log_audit_with_snapshot(
            'update_user',
            'user',
            user.id,
            before_state={'role': 'biller', 'area': 'lucknow'},
            after_state={'role': 'dispatcher', 'area': 'indore'}
        )
        
        # Auto-serialization
        log_audit_with_snapshot(
            'update_bag',
            'bag',
            bag.id,
            before_state=old_bag_instance,  # Will be auto-serialized
            after_state=bag,  # Will be auto-serialized
            auto_serialize=True
        )
    """
    try:
        from models import AuditLog
        from request_tracking import get_request_id
        
        # Serialize if needed
        if auto_serialize:
            if before_state and not isinstance(before_state, dict):
                before_state = serialize_entity(before_state)
            if after_state and not isinstance(after_state, dict):
                after_state = serialize_entity(after_state)
        
        audit = AuditLog()
        # Handle current_user safely (may be None outside request context)
        try:
            audit.user_id = current_user.id if current_user and current_user.is_authenticated else None
        except (AttributeError, RuntimeError):
            audit.user_id = None
        audit.action = action
        audit.entity_type = entity_type
        audit.entity_id = entity_id
        audit.details = json.dumps(details) if details else None
        audit.before_state = json.dumps(before_state) if before_state else None
        audit.after_state = json.dumps(after_state) if after_state else None
        audit.ip_address = request.remote_addr if request else None
        audit.request_id = get_request_id() if hasattr(g, 'request_id') else None
        
        db.session.add(audit)
        # Note: commit should be done by the calling function
        
        logger.info(
            f"Audit logged: {action} on {entity_type} {entity_id} by user {audit.user_id}",
            extra={
                'request_id': audit.request_id,
                'action': action,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'has_before_state': bool(before_state),
                'has_after_state': bool(after_state)
            }
        )
        
    except Exception as e:
        logger.error(f'Enhanced audit logging failed: {str(e)}', exc_info=True)


def capture_entity_snapshot(entity: Any) -> Dict[str, Any]:
    """
    Capture a snapshot of an entity's current state.
    Useful for capturing "before" state before making changes.
    
    Args:
        entity: SQLAlchemy model instance
        
    Returns:
        Dictionary snapshot of the entity
        
    Example:
        user = User.query.get(user_id)
        before = capture_entity_snapshot(user)
        
        # Make changes
        user.role = 'admin'
        user.dispatch_area = 'lucknow'
        
        log_audit_with_snapshot(
            'update_user',
            'user',
            user.id,
            before_state=before,
            after_state=user
        )
        db.session.commit()
    """
    return serialize_entity(entity)


def audit_changes_decorator(action: str, entity_type: str):
    """
    Decorator to automatically log entity changes with before/after snapshots.
    
    Args:
        action: The action being performed
        entity_type: Type of entity being modified
        
    Example:
        @audit_changes_decorator('update_user', 'user')
        def update_user_role(user_id, new_role):
            user = User.query.get(user_id)
            user.role = new_role
            db.session.commit()
            return user
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to find the entity before the function runs
            # This is a best-effort approach
            before_state = None
            entity_id = None
            
            # Look for entity_id in args/kwargs
            if 'entity_id' in kwargs:
                entity_id = kwargs['entity_id']
            elif args and isinstance(args[0], int):
                entity_id = args[0]
            
            # If we have an entity_id, try to capture before state
            if entity_id:
                try:
                    from models import User, Bag, Bill, Link
                    entity_map = {
                        'user': User,
                        'bag': Bag,
                        'bill': Bill,
                        'link': Link
                    }
                    if entity_type in entity_map:
                        entity = entity_map[entity_type].query.get(entity_id)
                        if entity:
                            before_state = capture_entity_snapshot(entity)
                except Exception as e:
                    logger.debug(f"Could not capture before state: {str(e)}")
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Try to capture after state from result
            after_state = None
            if result and hasattr(result, '__tablename__'):
                after_state = capture_entity_snapshot(result)
                entity_id = entity_id or getattr(result, 'id', None)
            
            # Log the audit
            log_audit_with_snapshot(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_state=before_state,
                after_state=after_state
            )
            
            return result
        
        return wrapper
    return decorator


def get_audit_trail(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    limit: int = 100
) -> list:
    """
    Retrieve audit trail with optional filtering.
    
    Args:
        entity_type: Filter by entity type
        entity_id: Filter by entity ID
        user_id: Filter by user who performed the action
        action: Filter by action type
        limit: Maximum number of records to return
        
    Returns:
        List of AuditLog instances
        
    Example:
        # Get all changes to a specific bag
        trail = get_audit_trail(entity_type='bag', entity_id=123)
        
        # Get all actions by a user
        trail = get_audit_trail(user_id=5)
        
        # Get all delete operations
        trail = get_audit_trail(action='delete_bag')
    """
    from models import AuditLog
    
    query = AuditLog.query
    
    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    if entity_id:
        query = query.filter_by(entity_id=entity_id)
    if user_id:
        query = query.filter_by(user_id=user_id)
    if action:
        query = query.filter_by(action=action)
    
    return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()


def get_entity_history(entity_type: str, entity_id: int) -> list:
    """
    Get complete change history for a specific entity.
    Returns a chronological list of all changes with before/after diffs.
    
    Args:
        entity_type: Type of entity (e.g., 'user', 'bag')
        entity_id: ID of the entity
        
    Returns:
        List of dicts with timestamp, action, user, and changes
        
    Example:
        history = get_entity_history('user', 5)
        for entry in history:
            print(f"{entry['timestamp']}: {entry['action']} by {entry['user']}")
            if entry['changes']:
                for field, (old, new) in entry['changes'].items():
                    print(f"  {field}: {old} -> {new}")
    """
    from models import AuditLog, User
    
    audit_logs = AuditLog.query.filter_by(
        entity_type=entity_type,
        entity_id=entity_id
    ).order_by(AuditLog.timestamp.asc()).all()
    
    history = []
    for log in audit_logs:
        entry = {
            'id': log.id,
            'timestamp': log.timestamp,
            'action': log.action,
            'user': log.user.username if log.user else 'System',
            'user_id': log.user_id,
            'ip_address': log.ip_address,
            'request_id': log.request_id,
            'changes': log.get_changes(),
            'details': json.loads(log.details) if log.details else None
        }
        history.append(entry)
    
    return history


# Backward compatibility function with auto-snapshot
def log_audit(action, entity_type, entity_id=None, details=None):
    """
    Legacy audit logging function with automatic snapshot capture.
    
    This function maintains backward compatibility while automatically
    capturing before/after snapshots when possible:
    - For delete operations: captures before_state automatically
    - For update operations: attempts to capture after_state
    - For create operations: captures after_state
    
    New code should use log_audit_with_snapshot for explicit control.
    
    Args:
        action: The action being performed
        entity_type: Type of entity
        entity_id: ID of the entity
        details: Additional context
    """
    before_state = None
    after_state = None
    
    # Try to auto-capture snapshots if entity_id is provided
    if entity_id:
        try:
            from models import User, Bag, Bill, Link, Scan
            entity_map = {
                'user': User,
                'bag': Bag,
                'bill': Bill,
                'link': Link,
                'scan': Scan
            }
            
            if entity_type in entity_map:
                model_class = entity_map[entity_type]
                entity = model_class.query.get(entity_id)
                
                if entity:
                    # For delete operations, capture before state
                    if 'delete' in action.lower():
                        before_state = serialize_entity(entity)
                    # For create/update, capture after state
                    else:
                        after_state = serialize_entity(entity)
                        
        except Exception as e:
            # Don't fail audit logging if auto-snapshot fails
            logger.debug(f"Auto-snapshot failed for {entity_type} {entity_id}: {str(e)}")
    
    log_audit_with_snapshot(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        before_state=before_state,
        after_state=after_state
    )
