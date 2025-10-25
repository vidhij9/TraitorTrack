"""
Audit Log Retention Policy and Cleanup Utilities
Manages storage growth for audit logs with before/after snapshots
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import text
from app import db

logger = logging.getLogger(__name__)

# Retention Policy Configuration
AUDIT_RETENTION_DAYS = 90  # Keep audit logs for 90 days
AUDIT_SNAPSHOT_RETENTION_DAYS = 30  # Keep before/after snapshots for 30 days
AUDIT_CLEANUP_BATCH_SIZE = 1000  # Process deletions in batches


class AuditRetentionPolicy:
    """Manages audit log retention and cleanup"""
    
    @staticmethod
    def get_retention_cutoff_date(retention_days: int = AUDIT_RETENTION_DAYS) -> datetime:
        """Calculate the cutoff date for audit log retention"""
        return datetime.utcnow() - timedelta(days=retention_days)
    
    @staticmethod
    def cleanup_old_snapshots(
        retention_days: int = AUDIT_SNAPSHOT_RETENTION_DAYS,
        dry_run: bool = True
    ) -> dict:
        """
        Remove before/after snapshots from old audit logs to save space.
        Keeps the audit log record but removes the large JSON snapshots.
        
        Args:
            retention_days: Number of days to keep snapshots
            dry_run: If True, only count records without deleting
            
        Returns:
            Dict with operation stats
        """
        cutoff_date = AuditRetentionPolicy.get_retention_cutoff_date(retention_days)
        
        # Count records that will be affected
        count_query = text("""
            SELECT COUNT(*) as count
            FROM audit_log
            WHERE timestamp < :cutoff_date
            AND (before_state IS NOT NULL OR after_state IS NOT NULL)
        """)
        
        result = db.session.execute(count_query, {'cutoff_date': cutoff_date}).fetchone()
        affected_count = result[0] if result else 0
        
        if dry_run:
            logger.info(
                f"[DRY RUN] Would clear snapshots from {affected_count} audit logs "
                f"older than {retention_days} days"
            )
            return {
                'dry_run': True,
                'affected_records': affected_count,
                'cutoff_date': cutoff_date.isoformat()
            }
        
        # Clear snapshots but keep audit records
        update_query = text("""
            UPDATE audit_log
            SET before_state = NULL,
                after_state = NULL
            WHERE timestamp < :cutoff_date
            AND (before_state IS NOT NULL OR after_state IS NOT NULL)
        """)
        
        result = db.session.execute(update_query, {'cutoff_date': cutoff_date})
        db.session.commit()
        
        logger.info(
            f"Cleared snapshots from {result.rowcount} audit logs "
            f"older than {retention_days} days"
        )
        
        return {
            'dry_run': False,
            'cleared_snapshots': result.rowcount,
            'cutoff_date': cutoff_date.isoformat()
        }
    
    @staticmethod
    def cleanup_old_audit_logs(
        retention_days: int = AUDIT_RETENTION_DAYS,
        preserve_critical_actions: bool = True,
        dry_run: bool = True
    ) -> dict:
        """
        Delete old audit logs completely.
        
        Args:
            retention_days: Number of days to keep audit logs
            preserve_critical_actions: Keep critical actions (deletes, role changes) indefinitely
            dry_run: If True, only count records without deleting
            
        Returns:
            Dict with operation stats
        """
        cutoff_date = AuditRetentionPolicy.get_retention_cutoff_date(retention_days)
        
        # Build query with optional preservation of critical actions
        if preserve_critical_actions:
            count_query = text("""
                SELECT COUNT(*) as count
                FROM audit_log
                WHERE timestamp < :cutoff_date
                AND action NOT IN ('delete_user', 'delete_bag', 'delete_bill', 'role_change', 'promote_to_admin')
            """)
            delete_query = text("""
                DELETE FROM audit_log
                WHERE timestamp < :cutoff_date
                AND action NOT IN ('delete_user', 'delete_bag', 'delete_bill', 'role_change', 'promote_to_admin')
            """)
        else:
            count_query = text("""
                SELECT COUNT(*) as count
                FROM audit_log
                WHERE timestamp < :cutoff_date
            """)
            delete_query = text("""
                DELETE FROM audit_log
                WHERE timestamp < :cutoff_date
            """)
        
        # Count records
        result = db.session.execute(count_query, {'cutoff_date': cutoff_date}).fetchone()
        affected_count = result[0] if result else 0
        
        if dry_run:
            logger.info(
                f"[DRY RUN] Would delete {affected_count} audit logs "
                f"older than {retention_days} days"
            )
            return {
                'dry_run': True,
                'would_delete': affected_count,
                'cutoff_date': cutoff_date.isoformat(),
                'critical_preserved': preserve_critical_actions
            }
        
        # Delete in batches to avoid lock timeouts
        total_deleted = 0
        batch_size = AUDIT_CLEANUP_BATCH_SIZE
        
        while True:
            batch_query = text(f"""
                DELETE FROM audit_log
                WHERE id IN (
                    SELECT id FROM audit_log
                    WHERE timestamp < :cutoff_date
                    {"AND action NOT IN ('delete_user', 'delete_bag', 'delete_bill', 'role_change', 'promote_to_admin')" if preserve_critical_actions else ""}
                    LIMIT {batch_size}
                )
            """)
            
            result = db.session.execute(batch_query, {'cutoff_date': cutoff_date})
            db.session.commit()
            
            deleted = result.rowcount
            total_deleted += deleted
            
            if deleted < batch_size:
                break
            
            logger.info(f"Deleted batch of {deleted} audit logs (total: {total_deleted})")
        
        logger.info(
            f"Deleted {total_deleted} audit logs older than {retention_days} days "
            f"(critical actions preserved: {preserve_critical_actions})"
        )
        
        return {
            'dry_run': False,
            'deleted_records': total_deleted,
            'cutoff_date': cutoff_date.isoformat(),
            'critical_preserved': preserve_critical_actions
        }
    
    @staticmethod
    def get_storage_stats() -> dict:
        """
        Get statistics about audit log storage usage.
        
        Returns:
            Dict with storage metrics
        """
        stats_query = text("""
            SELECT 
                COUNT(*) as total_logs,
                COUNT(before_state) as logs_with_before,
                COUNT(after_state) as logs_with_after,
                pg_size_pretty(pg_total_relation_size('audit_log')) as table_size,
                MIN(timestamp) as oldest_log,
                MAX(timestamp) as newest_log,
                COUNT(CASE WHEN timestamp < NOW() - INTERVAL ':retention_days days' THEN 1 END) as logs_past_retention
            FROM audit_log
        """.replace(':retention_days', str(AUDIT_RETENTION_DAYS)))
        
        result = db.session.execute(stats_query).fetchone()
        
        if result:
            return {
                'total_logs': result[0],
                'logs_with_before_state': result[1],
                'logs_with_after_state': result[2],
                'table_size': result[3],
                'oldest_log': result[4].isoformat() if result[4] else None,
                'newest_log': result[5].isoformat() if result[5] else None,
                'logs_past_retention': result[6],
                'retention_policy_days': AUDIT_RETENTION_DAYS,
                'snapshot_retention_days': AUDIT_SNAPSHOT_RETENTION_DAYS
            }
        
        return {}
    
    @staticmethod
    def run_maintenance(dry_run: bool = True) -> dict:
        """
        Run complete audit maintenance:
        1. Clear old snapshots
        2. Delete old audit logs (preserving critical actions)
        
        Args:
            dry_run: If True, only report what would be done
            
        Returns:
            Dict with all operation results
        """
        logger.info(f"Starting audit maintenance (dry_run={dry_run})")
        
        # Get current stats
        stats_before = AuditRetentionPolicy.get_storage_stats()
        
        # Clear old snapshots
        snapshot_result = AuditRetentionPolicy.cleanup_old_snapshots(
            retention_days=AUDIT_SNAPSHOT_RETENTION_DAYS,
            dry_run=dry_run
        )
        
        # Delete old audit logs (preserve critical)
        delete_result = AuditRetentionPolicy.cleanup_old_audit_logs(
            retention_days=AUDIT_RETENTION_DAYS,
            preserve_critical_actions=True,
            dry_run=dry_run
        )
        
        # Get stats after (if not dry run)
        stats_after = AuditRetentionPolicy.get_storage_stats() if not dry_run else None
        
        logger.info(f"Audit maintenance completed (dry_run={dry_run})")
        
        return {
            'dry_run': dry_run,
            'stats_before': stats_before,
            'snapshot_cleanup': snapshot_result,
            'log_cleanup': delete_result,
            'stats_after': stats_after
        }


# CLI convenience function for manage.py
def run_audit_cleanup(dry_run: bool = True):
    """
    Run audit cleanup - can be called from manage.py or scheduled task.
    
    Usage:
        # Dry run (safe, reports only)
        python manage.py run_audit_cleanup
        
        # Actually execute cleanup
        python manage.py run_audit_cleanup --no-dry-run
    """
    from app import app
    
    with app.app_context():
        result = AuditRetentionPolicy.run_maintenance(dry_run=dry_run)
        
        print("\n" + "="*60)
        print("AUDIT LOG MAINTENANCE REPORT")
        print("="*60)
        
        if result['dry_run']:
            print("\n⚠️  DRY RUN MODE - No changes made")
        else:
            print("\n✅ CHANGES APPLIED")
        
        print(f"\n📊 Storage Stats (Before):")
        stats = result['stats_before']
        print(f"   Total audit logs: {stats.get('total_logs', 0):,}")
        print(f"   Table size: {stats.get('table_size', 'unknown')}")
        print(f"   Logs with snapshots: {stats.get('logs_with_before_state', 0):,}")
        print(f"   Logs past retention: {stats.get('logs_past_retention', 0):,}")
        
        print(f"\n🗑️  Snapshot Cleanup:")
        snap = result['snapshot_cleanup']
        if snap.get('dry_run'):
            print(f"   Would clear: {snap.get('affected_records', 0):,} snapshots")
        else:
            print(f"   Cleared: {snap.get('cleared_snapshots', 0):,} snapshots")
        
        print(f"\n🗑️  Log Deletion:")
        delete = result['log_cleanup']
        if delete.get('dry_run'):
            print(f"   Would delete: {delete.get('would_delete', 0):,} logs")
        else:
            print(f"   Deleted: {delete.get('deleted_records', 0):,} logs")
        print(f"   Critical actions preserved: {delete.get('critical_preserved', False)}")
        
        if not result['dry_run'] and result['stats_after']:
            print(f"\n📊 Storage Stats (After):")
            stats_after = result['stats_after']
            print(f"   Total audit logs: {stats_after.get('total_logs', 0):,}")
            print(f"   Table size: {stats_after.get('table_size', 'unknown')}")
        
        print("\n" + "="*60)
        print()
        
        return result
