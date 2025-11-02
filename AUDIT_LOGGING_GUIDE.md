# Enhanced Audit Logging System

## Overview
TraitorTrack's enhanced audit logging system provides comprehensive change tracking with before/after snapshots, enabling complete audit trails for compliance, debugging, and forensics.

## Key Features ✅
- **Before/After Snapshots**: Automatic state capture for all entity changes
- **Request Correlation**: Links audit logs to request IDs for distributed tracing
- **Change Detection**: Automatic diff calculation showing what changed
- **Entity History**: Complete chronological timeline of all changes to any entity
- **Auto-Serialization**: Automatic conversion of SQLAlchemy models to JSON
- **Backward Compatible**: Legacy `log_audit()` function still works

## Database Schema

### AuditLog Model Fields
```python
id              # Primary key
timestamp       # When the action occurred (UTC)
user_id         # Who performed the action
action          # What action was performed (e.g., 'role_change', 'delete_bag')
entity_type     # What type of entity was affected (e.g., 'user', 'bag')
entity_id       # ID of the affected entity
details         # JSON string with additional context
before_state    # NEW: JSON snapshot before the change
after_state     # NEW: JSON snapshot after the change
ip_address      # IP address of the requester
request_id      # NEW: UUID from request tracking middleware
```

### Indexes
- `idx_audit_timestamp` - Fast chronological queries
- `idx_audit_user` - User activity tracking
- `idx_audit_action` - Action filtering
- `idx_audit_entity` - Entity lookups
- `idx_audit_user_timestamp` - User audit history
- `idx_audit_action_timestamp` - Action timeline
- `idx_audit_request_id` - Request correlation

## Usage Examples

### Basic: Capture Before/After Snapshots

#### Role Change (Automatic Serialization)
```python
from audit_utils import log_audit_with_snapshot, capture_entity_snapshot

# Capture state before making changes
before_state = capture_entity_snapshot(user)

# Make changes
user.role = 'admin'
user.dispatch_area = 'lucknow'

# Log with before/after snapshots
log_audit_with_snapshot(
    action='role_change',
    entity_type='user',
    entity_id=user.id,
    before_state=before_state,
    after_state=user,  # Auto-serialized
    details={
        'changed_by': current_user.username,
        'reason': 'Promotion approved'
    }
)

db.session.commit()
```

#### Manual Snapshots
```python
log_audit_with_snapshot(
    action='update_bag',
    entity_type='bag',
    entity_id=bag.id,
    before_state={'qr_id': '12345', 'type': 'parent'},
    after_state={'qr_id': '12345', 'type': 'child'},
    details={'converted_by': current_user.username},
    auto_serialize=False  # Already dict format
)
```

#### Deletion Tracking
```python
# Capture state before deletion
before_state = capture_entity_snapshot(bag)

log_audit_with_snapshot(
    action='delete_bag',
    entity_type='bag',
    entity_id=bag.id,
    before_state=before_state,
    after_state=None,  # No after state for deletions
    details={
        'deleted_by': current_user.username,
        'scan_count': scan_count
    }
)

db.session.delete(bag)
db.session.commit()
```

### Advanced: Retrieve Audit Trails

#### Get Entity Complete History
```python
from audit_utils import get_entity_history

# Get all changes to a specific user
history = get_entity_history('user', user_id=5)

for entry in history:
    print(f"{entry['timestamp']}: {entry['action']} by {entry['user']}")
    
    # Show what changed
    if entry['changes']:
        for field, (old_val, new_val) in entry['changes'].items():
            print(f"  {field}: {old_val} → {new_val}")

# Example output:
# 2025-10-25 15:30:00: role_change by admin_user
#   role: biller → dispatcher
#   dispatch_area: None → lucknow
# 2025-10-25 16:45:00: role_change by admin_user
#   role: dispatcher → admin
#   dispatch_area: lucknow → None
```

#### Query Audit Logs
```python
from audit_utils import get_audit_trail

# All changes to bags
bag_audits = get_audit_trail(entity_type='bag', limit=50)

# All actions by a specific user
user_actions = get_audit_trail(user_id=5, limit=100)

# All delete operations
deletions = get_audit_trail(action='delete_bag', limit=20)

# Specific entity changes
specific_bag = get_audit_trail(entity_type='bag', entity_id=123)
```

#### Get Changes from AuditLog Instance
```python
audit = AuditLog.query.get(123)

# Get dict of what changed
changes = audit.get_changes()

if changes:
    for field, (old_value, new_value) in changes.items():
        print(f"{field}: {old_value} → {new_value}")
```

### Decorator: Automatic Audit Logging
```python
from audit_utils import audit_changes_decorator

@audit_changes_decorator('update_user', 'user')
def promote_user_to_admin(user_id):
    user = User.query.get(user_id)
    user.role = 'admin'
    db.session.commit()
    return user

# Automatically logs before/after snapshots when function executes
```

## Migration to Enhanced Audit Logging

### Step 1: Apply Database Migration
```bash
# Using psql
psql $DATABASE_URL -f migrations/002_add_audit_before_after_columns.sql

# Or using execute_sql_tool
# The migration has already been applied in development
```

### Step 2: Update Existing Code (Optional)
Replace old `log_audit()` calls with enhanced version:

**Before:**
```python
log_audit('role_change', 'user', user.id, {
    'old_role': old_role,
    'new_role': new_role
})
```

**After:**
```python
before_state = capture_entity_snapshot(user)
user.role = new_role

log_audit_with_snapshot(
    'role_change', 
    'user',
    user.id,
    before_state=before_state,
    after_state=user,
    details={'changed_by': current_user.username}
)
```

**Note**: Old `log_audit()` calls still work! They just don't capture before/after snapshots.

## Request Correlation

All audit logs automatically include `request_id` from the request tracking middleware:

```python
# Find all audit logs for a specific request
from models import AuditLog

request_logs = AuditLog.query.filter_by(
    request_id='8e08826e-79ae-471e-a41f-99d3cab8a73f'
).all()

# Shows all entity changes that occurred during one request
```

## Current Implementation Status

### Enhanced Audit Logging Implemented For:
- ✅ User role changes (with before/after snapshots)
- ✅ Bag deletions (with before-state snapshot)
- ✅ Request ID correlation

### Legacy Audit Logging (Still Using Old Format):
- User deletions
- Bill operations
- Link operations
- Scan operations

### Backward Compatibility & Auto-Snapshot

All legacy `log_audit()` calls continue to work AND now automatically capture snapshots when possible!

**Auto-snapshot behavior:**
- ✅ For delete operations (action contains "delete"): Captures `before_state` automatically
- ⚠️  For update/create operations: Captures `after_state` only (no before state)
- ✅ Requires `entity_id` to be provided
- ✅ Supports: User, Bag, Bill, Link, Scan entities
- ✅ Safe: If auto-snapshot fails, audit log still recorded (snapshot NULL)

**Limitations:**
- Auto-snapshot for updates can only capture `after_state` because changes have already been made when `log_audit()` is called
- For true before/after comparison on updates, use `log_audit_with_snapshot()` explicitly

**Example:**
```python
# Delete operations - gets before_state automatically
log_audit('delete_user', 'user', user.id, {'reason': 'requested'})
# → before_state captured ✅

# Update operations - gets after_state only
log_audit('update_bill', 'bill', bill.id, {'changed': 'status'})
# → after_state captured ✅, before_state NULL ⚠️

# For complete before/after on updates - use explicit version
before = capture_entity_snapshot(bill)
bill.status = 'completed'
log_audit_with_snapshot('update_bill', 'bill', bill.id, 
                       before_state=before, after_state=bill)
# → Both before_state and after_state captured ✅
```

## Performance Considerations

### Storage Impact
- Before/after snapshots add ~1-5 KB per audit log
- For 1.8M bags with frequent changes, monitor disk usage
- Consider retention policies (e.g., keep snapshots for 90 days)

### Query Performance
- All indexes optimized for common audit queries
- `idx_audit_request_id` enables fast request correlation
- Composite indexes support user history and action timelines

### Serialization Overhead
- Auto-serialization adds ~1-2ms per audit log
- Negligible compared to database operations
- Can be disabled with `auto_serialize=False`

## Security Considerations

### Sensitive Data
The serializer automatically excludes:
- `password_hash` - Password hashes
- `verification_token` - Email verification tokens
- `reset_token` - Password reset tokens
- `api_key` - API authentication keys
- `secret_key` - Any secret keys
- `failed_login_attempts` - Security-related internal state
- `locked_until` - Account lockout timestamps
- `last_failed_login` - Failed login tracking
- `_sa_instance_state` - SQLAlchemy internal fields

**Add more exclusions if needed:**
```python
snapshot = serialize_entity(user, exclude_fields=['custom_sensitive_field', 'another_secret'])
```

### Access Control
Audit logs are only accessible to:
- Admin users (via admin panel)
- System processes (for debugging)
- Compliance officers (via direct database access)

## Compliance & Forensics

### GDPR/Privacy Compliance
When deleting user data:
1. Audit logs preserve historical context
2. User ID set to NULL (preserving audit integrity)
3. Snapshots may contain PII - consider anonymization:

```python
# Example: Anonymize user data in audit snapshots
from models import AuditLog

user_audits = AuditLog.query.filter_by(entity_type='user', entity_id=user_id).all()
for audit in user_audits:
    if audit.before_state:
        # Replace PII in snapshots
        state = json.loads(audit.before_state)
        state['email'] = 'REDACTED'
        state['username'] = f'USER_{user_id}_DELETED'
        audit.before_state = json.dumps(state)
    # Same for after_state
```

### Forensic Investigation
```python
# Who deleted bag #12345 and when?
deletion = AuditLog.query.filter_by(
    action='delete_bag',
    entity_id=12345
).first()

if deletion:
    print(f"Deleted by user {deletion.user_id} at {deletion.timestamp}")
    print(f"Request ID: {deletion.request_id}")
    print(f"Bag state before deletion: {deletion.before_state}")
```

## Troubleshooting

### Audit Logs Not Captured
1. Check that `log_audit_with_snapshot()` is called BEFORE `db.session.commit()`
2. Verify request tracking middleware is initialized
3. Check logs for audit logging errors

### Missing Before/After State
- Verify you're calling `capture_entity_snapshot()` before making changes
- Check that entity is a SQLAlchemy model instance
- Ensure `auto_serialize=True` (default)

### Performance Issues
- Review query patterns and use appropriate indexes
- Consider pagination for large audit trail queries
- Implement retention policies for old audit logs

## Retention & Cleanup

### Automated Cleanup System
The `audit_retention.py` module provides automated cleanup:

```python
from audit_retention import AuditRetentionPolicy

# Get storage statistics
stats = AuditRetentionPolicy.get_storage_stats()
print(f"Total logs: {stats['total_logs']}")
print(f"Table size: {stats['table_size']}")

# Dry run (safe) - see what would be cleaned
result = AuditRetentionPolicy.run_maintenance(dry_run=True)

# Execute cleanup
result = AuditRetentionPolicy.run_maintenance(dry_run=False)
```

### Retention Policies
- **Audit logs**: Keep for 90 days (critical actions preserved forever)
- **Snapshots**: Keep for 30 days, then clear to save space
- **Critical actions**: Delete operations, role changes kept indefinitely

### Manual Cleanup
```bash
# From manage.py (when implemented)
python manage.py run_audit_cleanup          # Dry run
python manage.py run_audit_cleanup --no-dry-run  # Execute

# Or schedule via cron
0 2 * * 0  cd /path/to/app && python manage.py run_audit_cleanup --no-dry-run
```

## Future Enhancements

Potential improvements:
- [ ] Automated snapshot compression for old logs ✅ DONE (retention policies)
- [ ] Configurable retention policies with automated cleanup ✅ DONE
- [ ] Audit log export to external SIEM systems
- [ ] Real-time audit streaming to monitoring tools
- [ ] Machine learning anomaly detection on audit patterns
- [ ] Visual diff UI for before/after comparisons

## Related Documentation
- `REQUEST_TRACKING_README.md` - Request ID tracking system
- `MIGRATION_GUIDE.md` - Database migration system
- `models.py` - AuditLog model definition
- `audit_utils.py` - Audit utility functions
