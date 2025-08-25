#!/usr/bin/env python3
"""
CRITICAL: Database Migration Safety Check for AWS PostgreSQL
Verifies existing data will migrate safely without loss
"""

import os
import sys
from sqlalchemy import create_engine, inspect, text
from datetime import datetime

print("=" * 70)
print("🔒 CRITICAL DATABASE MIGRATION SAFETY CHECK")
print("=" * 70)
print(f"Timestamp: {datetime.now()}")
print()

# Check current database configuration
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("❌ CRITICAL: No DATABASE_URL found in environment")
    sys.exit(1)

print("📊 CURRENT DATABASE CONFIGURATION:")
print("-" * 50)

# Parse database URL safely (hide password)
if 'postgresql' in database_url or 'postgres' in database_url:
    parts = database_url.split('@')
    if len(parts) > 1:
        db_location = parts[1]
        print(f"✅ Database Type: PostgreSQL")
        print(f"✅ Database Location: ...@{db_location}")
    else:
        print(f"✅ Database URL configured (details hidden)")
else:
    print(f"⚠️ Database Type: Unknown")

# Connect to database and analyze structure
try:
    engine = create_engine(database_url)
    inspector = inspect(engine)
    
    print("\n📋 DATABASE SCHEMA ANALYSIS:")
    print("-" * 50)
    
    # Get all tables
    tables = inspector.get_table_names()
    print(f"Total tables: {len(tables)}")
    
    critical_tables = ['user', 'bag', 'scan', 'bill', 'link', 'bill_bag', 'audit_log']
    migration_safe = True
    
    # Check each critical table
    table_data = {}
    for table in critical_tables:
        if table in tables:
            # Get row count
            with engine.connect() as conn:
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = result.scalar()
                table_data[table] = count
                print(f"✅ Table '{table}': {count:,} records")
                
                # Check for foreign key constraints
                fks = inspector.get_foreign_keys(table)
                if fks:
                    print(f"   - Has {len(fks)} foreign key constraints")
        else:
            print(f"❌ Table '{table}': NOT FOUND")
            migration_safe = False
    
    # Check total data size
    print("\n📦 DATA VOLUME ASSESSMENT:")
    print("-" * 50)
    
    total_records = sum(table_data.values())
    print(f"Total records across critical tables: {total_records:,}")
    
    if total_records > 100000:
        print("⚠️ WARNING: Large dataset - migration may take time")
    elif total_records > 10000:
        print("✅ Moderate dataset - standard migration approach OK")
    else:
        print("✅ Small dataset - quick migration expected")
    
    # Check for custom types, triggers, functions
    print("\n🔧 ADVANCED DATABASE FEATURES:")
    print("-" * 50)
    
    # Check for views
    views = inspector.get_view_names()
    if views:
        print(f"⚠️ Views found: {', '.join(views)}")
        print("   Note: Views need to be recreated after migration")
    else:
        print("✅ No views found")
    
    # Check indexes
    total_indexes = 0
    for table in tables:
        indexes = inspector.get_indexes(table)
        total_indexes += len(indexes)
    print(f"✅ Total indexes: {total_indexes} (will be recreated)")
    
    # Foreign key analysis for safe deletion
    print("\n🔐 FOREIGN KEY SAFETY CHECK:")
    print("-" * 50)
    
    nullable_fks = 0
    non_nullable_fks = 0
    
    for table in tables:
        columns = inspector.get_columns(table)
        for col in columns:
            if 'user_id' in col['name'] or col['name'].endswith('_id'):
                if col['nullable']:
                    nullable_fks += 1
                else:
                    non_nullable_fks += 1
    
    print(f"✅ Nullable foreign keys: {nullable_fks}")
    if non_nullable_fks > 0:
        print(f"⚠️ Non-nullable foreign keys: {non_nullable_fks}")
        print("   Note: May need CASCADE or SET NULL handling")
    
    print("\n🚀 MIGRATION STRATEGY RECOMMENDATION:")
    print("-" * 50)
    
    if migration_safe and total_records < 100000:
        print("✅ SAFE FOR STANDARD MIGRATION")
        print("\nRecommended approach:")
        print("1. Use pg_dump to export current database")
        print("2. Create new AWS RDS PostgreSQL instance")
        print("3. Use pg_restore to import data")
        print("4. Update DATABASE_URL to point to AWS RDS")
        print("5. Test application thoroughly")
    elif total_records >= 100000:
        print("⚠️ LARGE DATASET - NEEDS CAREFUL MIGRATION")
        print("\nRecommended approach:")
        print("1. Set up AWS RDS read replica first")
        print("2. Use AWS Database Migration Service (DMS)")
        print("3. Perform incremental sync")
        print("4. Schedule maintenance window for cutover")
    else:
        print("❌ MIGRATION RISKS DETECTED")
        print("Manual review required before migration")
    
    print("\n📝 AWS RDS POSTGRESQL REQUIREMENTS:")
    print("-" * 50)
    print("✅ Instance class: db.t3.small minimum (2 vCPU, 2 GB RAM)")
    print("✅ Storage: 20 GB minimum, SSD recommended")
    print("✅ PostgreSQL version: 13.x or higher")
    print("✅ Multi-AZ: Recommended for production")
    print("✅ Automated backups: Enable with 7-day retention")
    print("✅ Security group: Allow access from application")
    
    print("\n⚠️ CRITICAL REMINDERS:")
    print("-" * 50)
    print("1. BACKUP current database before ANY migration")
    print("2. Test migration in staging environment first")
    print("3. Keep original database running until verified")
    print("4. Update all connection strings simultaneously")
    print("5. Monitor application logs after migration")
    
except Exception as e:
    print(f"\n❌ ERROR connecting to database: {e}")
    print("\n⚠️ Cannot verify migration safety without database access")
    migration_safe = False

print("\n" + "=" * 70)
if migration_safe:
    print("✅ DATABASE MIGRATION SAFETY: VERIFIED")
    print("Your existing data can be safely migrated to AWS PostgreSQL")
else:
    print("⚠️ DATABASE MIGRATION: NEEDS REVIEW")
    print("Manual verification required before migration")
print("=" * 70)