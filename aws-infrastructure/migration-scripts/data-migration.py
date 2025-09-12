#!/usr/bin/env python3
"""
Data Migration Script for TraceTrack
Migrates data from Replit database to AWS RDS
"""

import os
import psycopg2
import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataMigration:
    def __init__(self):
        # Source database (Replit)
        self.source_url = os.environ.get('PRODUCTION_DATABASE_URL') or os.environ.get('DATABASE_URL')
        
        # Target database (AWS RDS)
        self.target_url = os.environ.get('AWS_DATABASE_URL') or os.environ.get('TARGET_DATABASE_URL')
        
        if not self.source_url or not self.target_url:
            raise ValueError("Both source and target database URLs must be provided")
        
        # Migration settings
        self.batch_size = 1000
        self.max_workers = 4
        self.dry_run = os.environ.get('DRY_RUN', 'false').lower() == 'true'
        
        # Migration tracking
        self.migration_stats = {
            'start_time': None,
            'end_time': None,
            'tables_migrated': {},
            'total_records': 0,
            'errors': []
        }
    
    def get_connection(self, database_url: str):
        """Get database connection"""
        return psycopg2.connect(database_url)
    
    def test_connections(self) -> Dict[str, bool]:
        """Test both database connections"""
        results = {}
        
        # Test source connection
        try:
            with self.get_connection(self.source_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            results['source'] = True
            logger.info("✅ Source database connection successful")
        except Exception as e:
            results['source'] = False
            logger.error(f"❌ Source database connection failed: {e}")
        
        # Test target connection
        try:
            with self.get_connection(self.target_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            results['target'] = True
            logger.info("✅ Target database connection successful")
        except Exception as e:
            results['target'] = False
            logger.error(f"❌ Target database connection failed: {e}")
        
        return results
    
    def get_table_schema(self, database_url: str) -> Dict[str, List[Dict]]:
        """Get schema information for all tables"""
        schema = {}
        
        try:
            with self.get_connection(database_url) as conn:
                with conn.cursor() as cursor:
                    # Get all user tables
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                        ORDER BY table_name
                    """)
                    
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    for table in tables:
                        # Get column information
                        cursor.execute("""
                            SELECT column_name, data_type, is_nullable, column_default
                            FROM information_schema.columns 
                            WHERE table_schema = 'public' 
                            AND table_name = %s
                            ORDER BY ordinal_position
                        """, (table,))
                        
                        columns = []
                        for col_row in cursor.fetchall():
                            columns.append({
                                'name': col_row[0],
                                'type': col_row[1],
                                'nullable': col_row[2] == 'YES',
                                'default': col_row[3]
                            })
                        
                        schema[table] = columns
            
            return schema
            
        except Exception as e:
            logger.error(f"Failed to get table schema: {e}")
            return {}
    
    def compare_schemas(self) -> Dict[str, Any]:
        """Compare schemas between source and target databases"""
        logger.info("🔍 Comparing database schemas...")
        
        source_schema = self.get_table_schema(self.source_url)
        target_schema = self.get_table_schema(self.target_url)
        
        comparison = {
            'source_tables': set(source_schema.keys()),
            'target_tables': set(target_schema.keys()),
            'missing_in_target': [],
            'missing_in_source': [],
            'schema_differences': {}
        }
        
        # Find missing tables
        comparison['missing_in_target'] = list(comparison['source_tables'] - comparison['target_tables'])
        comparison['missing_in_source'] = list(comparison['target_tables'] - comparison['source_tables'])
        
        # Compare column schemas for common tables
        common_tables = comparison['source_tables'] & comparison['target_tables']
        
        for table in common_tables:
            source_cols = {col['name']: col for col in source_schema[table]}
            target_cols = {col['name']: col for col in target_schema[table]}
            
            if source_cols != target_cols:
                comparison['schema_differences'][table] = {
                    'source_columns': list(source_cols.keys()),
                    'target_columns': list(target_cols.keys()),
                    'missing_in_target': list(set(source_cols.keys()) - set(target_cols.keys())),
                    'missing_in_source': list(set(target_cols.keys()) - set(source_cols.keys()))
                }
        
        return comparison
    
    def get_table_count(self, database_url: str, table: str) -> int:
        """Get record count for a table"""
        try:
            with self.get_connection(database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get count for table {table}: {e}")
            return 0
    
    def get_data_checksum(self, database_url: str, table: str, columns: List[str]) -> str:
        """Generate checksum for table data"""
        try:
            with self.get_connection(database_url) as conn:
                with conn.cursor() as cursor:
                    # Create a deterministic hash of the data
                    column_list = ', '.join(columns)
                    cursor.execute(f"""
                        SELECT MD5(string_agg(MD5(CONCAT({column_list})), '' ORDER BY {columns[0]}))
                        FROM {table}
                    """)
                    result = cursor.fetchone()[0]
                    return result or ''
        except Exception as e:
            logger.warning(f"Could not generate checksum for table {table}: {e}")
            return ''
    
    def migrate_table_data(self, table: str, columns: List[Dict]) -> Dict[str, Any]:
        """Migrate data for a single table"""
        logger.info(f"📦 Migrating table: {table}")
        
        start_time = time.time()
        
        try:
            # Get source data count
            source_count = self.get_table_count(self.source_url, table)
            logger.info(f"   Source records: {source_count:,}")
            
            if source_count == 0:
                return {
                    'table': table,
                    'success': True,
                    'source_count': 0,
                    'migrated_count': 0,
                    'duration': time.time() - start_time
                }
            
            # Clear target table (if not dry run)
            if not self.dry_run:
                with self.get_connection(self.target_url) as target_conn:
                    with target_conn.cursor() as target_cursor:
                        target_cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
                        target_conn.commit()
                        logger.info(f"   Cleared target table {table}")
            
            # Migrate data in batches
            migrated_count = 0
            column_names = [col['name'] for col in columns]
            column_list = ', '.join(column_names)
            placeholders = ', '.join(['%s'] * len(column_names))
            
            with self.get_connection(self.source_url) as source_conn:
                with source_conn.cursor() as source_cursor:
                    # Use server-side cursor for large datasets
                    source_cursor.execute(f"SELECT {column_list} FROM {table}")
                    
                    batch = []
                    while True:
                        rows = source_cursor.fetchmany(self.batch_size)
                        if not rows:
                            break
                        
                        batch.extend(rows)
                        
                        # Insert batch to target
                        if not self.dry_run:
                            with self.get_connection(self.target_url) as target_conn:
                                with target_conn.cursor() as target_cursor:
                                    insert_sql = f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})"
                                    target_cursor.executemany(insert_sql, batch)
                                    target_conn.commit()
                        
                        migrated_count += len(batch)
                        batch = []
                        
                        logger.info(f"   Migrated: {migrated_count:,}/{source_count:,} records ({migrated_count/source_count*100:.1f}%)")
            
            # Verify migration
            if not self.dry_run:
                target_count = self.get_table_count(self.target_url, table)
                if target_count != source_count:
                    raise Exception(f"Count mismatch: source={source_count}, target={target_count}")
            
            duration = time.time() - start_time
            logger.info(f"✅ Table {table} migrated successfully in {duration:.2f}s")
            
            return {
                'table': table,
                'success': True,
                'source_count': source_count,
                'migrated_count': migrated_count,
                'duration': duration
            }
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Failed to migrate table {table}: {e}")
            
            return {
                'table': table,
                'success': False,
                'error': str(e),
                'duration': duration
            }
    
    def migrate_table_sequences(self) -> bool:
        """Update sequence values after migration"""
        logger.info("🔢 Updating sequence values...")
        
        if self.dry_run:
            logger.info("   Skipping sequence updates (dry run)")
            return True
        
        try:
            with self.get_connection(self.target_url) as conn:
                with conn.cursor() as cursor:
                    # Get all sequences
                    cursor.execute("""
                        SELECT schemaname, sequencename 
                        FROM pg_sequences 
                        WHERE schemaname = 'public'
                    """)
                    
                    sequences = cursor.fetchall()
                    
                    for schema, seq_name in sequences:
                        # Find the table and column that uses this sequence
                        cursor.execute("""
                            SELECT t.table_name, c.column_name
                            FROM information_schema.tables t
                            JOIN information_schema.columns c ON t.table_name = c.table_name
                            WHERE c.column_default LIKE %s
                            AND t.table_schema = 'public'
                        """, (f"%{seq_name}%",))
                        
                        result = cursor.fetchone()
                        if result:
                            table_name, column_name = result
                            
                            # Get max value from table
                            cursor.execute(f"SELECT MAX({column_name}) FROM {table_name}")
                            max_value = cursor.fetchone()[0]
                            
                            if max_value:
                                # Update sequence to max value + 1
                                cursor.execute(f"SELECT setval('{seq_name}', {max_value})")
                                logger.info(f"   Updated sequence {seq_name} to {max_value}")
                    
                    conn.commit()
            
            logger.info("✅ Sequence values updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update sequences: {e}")
            return False
    
    def run_migration(self) -> bool:
        """Run complete data migration"""
        logger.info("🚀 Starting TraceTrack Data Migration")
        logger.info("=" * 50)
        
        if self.dry_run:
            logger.info("🔍 DRY RUN MODE - No data will be modified")
            logger.info("=" * 50)
        
        self.migration_stats['start_time'] = datetime.now()
        
        # Step 1: Test connections
        connections = self.test_connections()
        if not all(connections.values()):
            logger.error("❌ Database connection test failed")
            return False
        
        # Step 2: Compare schemas
        schema_comparison = self.compare_schemas()
        
        if schema_comparison['missing_in_target']:
            logger.error(f"❌ Missing tables in target: {schema_comparison['missing_in_target']}")
            return False
        
        if schema_comparison['schema_differences']:
            logger.warning(f"⚠️ Schema differences found: {list(schema_comparison['schema_differences'].keys())}")
            for table, diff in schema_comparison['schema_differences'].items():
                logger.warning(f"   {table}: missing columns in target: {diff['missing_in_target']}")
        
        # Step 3: Get migration order (respecting foreign keys)
        migration_order = self.get_migration_order(schema_comparison['source_tables'])
        logger.info(f"📋 Migration order: {' → '.join(migration_order)}")
        
        # Step 4: Migrate table data
        source_schema = self.get_table_schema(self.source_url)
        total_tables = len(migration_order)
        
        for i, table in enumerate(migration_order, 1):
            logger.info(f"\n📦 Migrating table {i}/{total_tables}: {table}")
            
            result = self.migrate_table_data(table, source_schema[table])
            self.migration_stats['tables_migrated'][table] = result
            
            if result['success']:
                self.migration_stats['total_records'] += result.get('migrated_count', 0)
            else:
                self.migration_stats['errors'].append({
                    'table': table,
                    'error': result.get('error', 'Unknown error')
                })
        
        # Step 5: Update sequences
        if not self.migrate_table_sequences():
            logger.warning("⚠️ Sequence update failed, but continuing...")
        
        # Step 6: Final validation
        if not self.dry_run:
            logger.info("\n🔍 Running final validation...")
            validation_results = self.validate_migration(schema_comparison['source_tables'])
            
            if not validation_results['valid']:
                logger.error("❌ Migration validation failed")
                return False
        
        # Migration complete
        self.migration_stats['end_time'] = datetime.now()
        self.print_migration_summary()
        
        return True
    
    def get_migration_order(self, tables: set) -> List[str]:
        """Get optimal migration order respecting foreign key constraints"""
        # For now, use a simple predefined order based on TraceTrack schema
        # In a more complex scenario, we would analyze foreign key constraints
        
        preferred_order = [
            'user',           # Base table, no dependencies
            'bag',            # References user
            'link',           # References bag (parent_bag_id, child_bag_id)
            'scan',           # References user and bag
            'bill',           # References user and bag
            'audit_log'       # References user (if exists)
        ]
        
        # Add any tables not in preferred order
        ordered_tables = []
        for table in preferred_order:
            if table in tables:
                ordered_tables.append(table)
        
        # Add remaining tables
        for table in sorted(tables):
            if table not in ordered_tables:
                ordered_tables.append(table)
        
        return ordered_tables
    
    def validate_migration(self, tables: set) -> Dict[str, Any]:
        """Validate migration by comparing record counts and checksums"""
        logger.info("🔍 Validating migration...")
        
        validation = {
            'valid': True,
            'table_validations': {}
        }
        
        source_schema = self.get_table_schema(self.source_url)
        
        for table in tables:
            try:
                source_count = self.get_table_count(self.source_url, table)
                target_count = self.get_table_count(self.target_url, table)
                
                counts_match = source_count == target_count
                
                # Generate checksums for small tables
                checksum_match = True
                if source_count <= 10000:  # Only checksum small tables
                    columns = [col['name'] for col in source_schema.get(table, [])]
                    if columns:
                        source_checksum = self.get_data_checksum(self.source_url, table, columns)
                        target_checksum = self.get_data_checksum(self.target_url, table, columns)
                        checksum_match = source_checksum == target_checksum
                
                table_valid = counts_match and checksum_match
                
                validation['table_validations'][table] = {
                    'source_count': source_count,
                    'target_count': target_count,
                    'counts_match': counts_match,
                    'checksum_match': checksum_match,
                    'valid': table_valid
                }
                
                if table_valid:
                    logger.info(f"   ✅ {table}: {source_count:,} records")
                else:
                    logger.error(f"   ❌ {table}: validation failed")
                    validation['valid'] = False
                    
            except Exception as e:
                logger.error(f"   ❌ {table}: validation error - {e}")
                validation['valid'] = False
        
        return validation
    
    def print_migration_summary(self):
        """Print migration completion summary"""
        duration = (self.migration_stats['end_time'] - self.migration_stats['start_time']).total_seconds()
        
        logger.info("\n" + "=" * 50)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total Duration: {duration:.2f} seconds")
        logger.info(f"Total Records Migrated: {self.migration_stats['total_records']:,}")
        logger.info(f"Tables Processed: {len(self.migration_stats['tables_migrated'])}")
        
        successful_tables = sum(1 for result in self.migration_stats['tables_migrated'].values() if result['success'])
        logger.info(f"Successful Tables: {successful_tables}")
        
        if self.migration_stats['errors']:
            logger.info(f"Failed Tables: {len(self.migration_stats['errors'])}")
            for error in self.migration_stats['errors']:
                logger.info(f"  ❌ {error['table']}: {error['error']}")
        
        logger.info("\nTable Details:")
        for table, result in self.migration_stats['tables_migrated'].items():
            if result['success']:
                count = result.get('migrated_count', 0)
                duration = result.get('duration', 0)
                logger.info(f"  ✅ {table}: {count:,} records in {duration:.2f}s")
            else:
                logger.info(f"  ❌ {table}: {result.get('error', 'Unknown error')}")
        
        logger.info("=" * 50)
        
        if self.dry_run:
            logger.info("🔍 DRY RUN COMPLETED - No data was actually migrated")
        else:
            success_rate = successful_tables / len(self.migration_stats['tables_migrated']) * 100
            if success_rate == 100:
                logger.info("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
            else:
                logger.info(f"⚠️ MIGRATION COMPLETED WITH ISSUES ({success_rate:.1f}% success rate)")

def main():
    """Main migration function"""
    migration = DataMigration()
    success = migration.run_migration()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()