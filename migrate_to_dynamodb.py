#!/usr/bin/env python3
"""
PostgreSQL to DynamoDB Migration Script
Migrates all data from PostgreSQL to high-performance DynamoDB
"""

import os
import boto3
from sqlalchemy import create_engine, text
import json
import time
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataMigrator:
    def __init__(self):
        # Database connection
        self.pg_url = os.environ.get('DATABASE_URL', '')
        if self.pg_url.startswith('postgres://'):
            self.pg_url = self.pg_url.replace('postgres://', 'postgresql://', 1)
        
        # DynamoDB setup
        self.dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
        
    def migrate_all(self):
        """Migrate all data from PostgreSQL to DynamoDB"""
        
        engine = create_engine(self.pg_url)
        
        with engine.connect() as conn:
            # Get statistics
            stats = {
                'bags': conn.execute(text("SELECT COUNT(*) FROM bag")).scalar(),
                'scans': conn.execute(text("SELECT COUNT(*) FROM scan")).scalar(),
                'bills': conn.execute(text("SELECT COUNT(*) FROM bill")).scalar(),
                'users': conn.execute(text("SELECT COUNT(*) FROM \"user\"")).scalar()
            }
            
            logger.info("📊 Current PostgreSQL Data:")
            for table, count in stats.items():
                logger.info(f"  {table}: {count:,} records")
            
            logger.info("\n🚀 Starting migration to DynamoDB...")
            
            # Migrate users
            logger.info("\n👥 Migrating users...")
            users_table = self.dynamodb.Table('tracetrack_users')
            users = conn.execute(text("SELECT * FROM \"user\"")).fetchall()
            
            with users_table.batch_writer() as batch:
                for user in users:
                    batch.put_item(Item={
                        'username': user['username'],
                        'user_id': str(user['id']),
                        'email': user['email'],
                        'role': user['role'],
                        'password_hash': user['password_hash'],
                        'created_at': str(user['created_at'])
                    })
            logger.info(f"  ✅ Migrated {len(users)} users")
            
            # Migrate bags
            logger.info("\n📦 Migrating bags...")
            bags_table = self.dynamodb.Table('tracetrack_bags')
            bags = conn.execute(text("SELECT * FROM bag")).fetchall()
            
            with bags_table.batch_writer() as batch:
                for bag in bags:
                    timestamp = int(bag['created_at'].timestamp() * 1000) if bag['created_at'] else int(time.time() * 1000)
                    
                    # Get parent QR if this is a child bag
                    parent_qr = ''
                    if bag['type'] == 'child':
                        parent_result = conn.execute(
                            text("""
                                SELECT pb.qr_id 
                                FROM link l 
                                JOIN bag pb ON l.parent_bag_id = pb.id 
                                WHERE l.child_bag_id = :child_id
                                LIMIT 1
                            """),
                            {'child_id': bag['id']}
                        ).first()
                        if parent_result:
                            parent_qr = parent_result[0]
                    
                    batch.put_item(Item={
                        'qr_id': bag['qr_id'],
                        'timestamp': timestamp,
                        'type': bag['type'],
                        'parent_qr': parent_qr,
                        'created_at': str(bag['created_at'])
                    })
            logger.info(f"  ✅ Migrated {len(bags)} bags")
            
            # Migrate scans (last 100k for performance)
            logger.info("\n📋 Migrating scans...")
            scans_table = self.dynamodb.Table('tracetrack_scans')
            scans = conn.execute(text("""
                SELECT s.*, pb.qr_id as parent_qr, cb.qr_id as child_qr
                FROM scan s
                LEFT JOIN bag pb ON s.parent_bag_id = pb.id
                LEFT JOIN bag cb ON s.child_bag_id = cb.id
                ORDER BY s.timestamp DESC
                LIMIT 100000
            """)).fetchall()
            
            with scans_table.batch_writer() as batch:
                for scan in scans:
                    timestamp = int(scan['timestamp'].timestamp() * 1000) if scan['timestamp'] else int(time.time() * 1000)
                    
                    batch.put_item(Item={
                        'scan_id': str(scan['id']),
                        'timestamp': timestamp,
                        'user_id': str(scan['user_id']) if scan['user_id'] else 'unknown',
                        'parent_qr': scan['parent_qr'] or '',
                        'child_qr': scan['child_qr'] or '',
                        'date': scan['timestamp'].strftime('%Y-%m-%d') if scan['timestamp'] else datetime.now().strftime('%Y-%m-%d')
                    })
            logger.info(f"  ✅ Migrated {len(scans)} scans")
            
            # Migrate bills
            logger.info("\n💰 Migrating bills...")
            bills_table = self.dynamodb.Table('tracetrack_bills')
            bills = conn.execute(text("SELECT * FROM bill LIMIT 50000")).fetchall()
            
            with bills_table.batch_writer() as batch:
                for bill in bills:
                    timestamp = int(bill['created_at'].timestamp() * 1000) if bill['created_at'] else int(time.time() * 1000)
                    
                    batch.put_item(Item={
                        'bill_id': str(bill['id']),
                        'timestamp': timestamp,
                        'user_id': str(bill['user_id']) if bill['user_id'] else 'unknown',
                        'total_bags': bill.get('total_bags', 0),
                        'created_at': str(bill['created_at'])
                    })
            logger.info(f"  ✅ Migrated {len(bills)} bills")
            
            logger.info("\n✅ Migration complete!")
            
            # Verify migration
            logger.info("\n🔍 Verifying migration...")
            
            dynamodb_stats = {
                'bags': bags_table.scan(Select='COUNT')['Count'],
                'scans': scans_table.scan(Select='COUNT')['Count'],
                'bills': bills_table.scan(Select='COUNT')['Count'],
                'users': users_table.scan(Select='COUNT')['Count']
            }
            
            logger.info("📊 DynamoDB Data:")
            for table, count in dynamodb_stats.items():
                logger.info(f"  {table}: {count:,} records")

if __name__ == "__main__":
    migrator = DataMigrator()
    migrator.migrate_all()