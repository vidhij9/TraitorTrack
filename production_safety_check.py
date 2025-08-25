#!/usr/bin/env python3
"""
Production Safety Check - Comprehensive validation before deployment
Ensures 1000% safety for production deployment
"""

import os
import sys
import time
import json
import logging
import requests
from datetime import datetime
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
BASE_URL = "http://localhost:5000"

class ProductionSafetyCheck:
    """Comprehensive safety checks before production deployment"""
    
    def __init__(self):
        self.checks_passed = []
        self.checks_failed = []
        self.warnings = []
        self.critical_issues = []
        
    def check_database_schema(self):
        """Verify database schema is correct"""
        logger.info("Checking database schema...")
        
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                # Check all required tables exist
                tables_query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
                """
                result = conn.execute(text(tables_query))
                tables = [row[0] for row in result]
                
                required_tables = ['bag', 'link', 'scan', 'bill', 'bill_bag', 'user', 'audit_log']
                missing_tables = [t for t in required_tables if t not in tables]
                
                if missing_tables:
                    self.critical_issues.append(f"Missing tables: {missing_tables}")
                    return False
                
                self.checks_passed.append("All required tables exist")
                
                # Check indexes
                index_query = """
                SELECT COUNT(*) as index_count
                FROM pg_indexes
                WHERE schemaname = 'public';
                """
                result = conn.execute(text(index_query))
                index_count = result.scalar()
                
                if index_count < 20:
                    self.warnings.append(f"Low index count ({index_count}), performance may be impacted")
                else:
                    self.checks_passed.append(f"Database has {index_count} indexes")
                
                return True
                
        except Exception as e:
            self.critical_issues.append(f"Database connection failed: {str(e)}")
            return False
    
    def check_data_integrity(self):
        """Check for data integrity issues"""
        logger.info("Checking data integrity...")
        
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                # Check for orphaned records
                integrity_checks = [
                    ("Orphaned links", """
                        SELECT COUNT(*) FROM link l
                        WHERE NOT EXISTS (SELECT 1 FROM bag WHERE id = l.parent_bag_id)
                           OR NOT EXISTS (SELECT 1 FROM bag WHERE id = l.child_bag_id)
                    """),
                    ("Duplicate parent QRs", """
                        SELECT COUNT(*) FROM (
                            SELECT qr_id FROM bag 
                            WHERE type = 'parent' 
                            GROUP BY qr_id 
                            HAVING COUNT(*) > 1
                        ) dup
                    """),
                    ("Over-linked parents", """
                        SELECT COUNT(*) FROM (
                            SELECT parent_bag_id 
                            FROM link 
                            GROUP BY parent_bag_id 
                            HAVING COUNT(*) > 30
                        ) over
                    """),
                    ("Invalid bag types", """
                        SELECT COUNT(*) FROM bag 
                        WHERE type NOT IN ('parent', 'child')
                    """)
                ]
                
                for check_name, query in integrity_checks:
                    result = conn.execute(text(query))
                    count = result.scalar()
                    if count > 0:
                        self.critical_issues.append(f"{check_name}: {count} issues found")
                    else:
                        self.checks_passed.append(f"{check_name}: OK")
                
                return len(self.critical_issues) == 0
                
        except Exception as e:
            self.critical_issues.append(f"Integrity check failed: {str(e)}")
            return False
    
    def check_api_endpoints(self):
        """Test critical API endpoints"""
        logger.info("Testing API endpoints...")
        
        endpoints = [
            ("/health", 200, 1.0),
            ("/api/stats", 200, 5.0),
            ("/ultra_cache_stats", 200, 1.0),
        ]
        
        for endpoint, expected_status, max_time in endpoints:
            try:
                start = time.time()
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                elapsed = time.time() - start
                
                if response.status_code != expected_status:
                    self.critical_issues.append(f"{endpoint}: Status {response.status_code} (expected {expected_status})")
                elif elapsed > max_time:
                    self.warnings.append(f"{endpoint}: Slow response {elapsed:.2f}s (max {max_time}s)")
                else:
                    self.checks_passed.append(f"{endpoint}: OK ({elapsed:.3f}s)")
                    
            except Exception as e:
                self.critical_issues.append(f"{endpoint}: Failed - {str(e)}")
        
        return len([i for i in self.critical_issues if any(ep[0] in i for ep in endpoints)]) == 0
    
    def check_connection_pool(self):
        """Check database connection pool health"""
        logger.info("Checking connection pool...")
        
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                # Check active connections
                conn_query = """
                SELECT 
                    COUNT(*) as total_connections,
                    COUNT(*) FILTER (WHERE state = 'active') as active,
                    COUNT(*) FILTER (WHERE state = 'idle') as idle,
                    COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                FROM pg_stat_activity
                WHERE datname = current_database();
                """
                result = conn.execute(text(conn_query))
                row = result.fetchone()
                
                if row.total_connections > 45:
                    self.warnings.append(f"High connection count: {row.total_connections} (limit 50)")
                else:
                    self.checks_passed.append(f"Connection pool healthy: {row.total_connections} connections")
                
                if row.idle_in_transaction > 5:
                    self.warnings.append(f"Idle transactions: {row.idle_in_transaction}")
                
                return True
                
        except Exception as e:
            self.warnings.append(f"Connection pool check failed: {str(e)}")
            return True  # Non-critical
    
    def check_cache_health(self):
        """Check cache system health"""
        logger.info("Checking cache health...")
        
        try:
            response = requests.get(f"{BASE_URL}/ultra_cache_stats", timeout=5)
            if response.status_code == 200:
                cache_stats = response.json()
                
                for cache_name, stats in cache_stats.items():
                    if 'hit_rate' in stats:
                        hit_rate = float(stats['hit_rate'].rstrip('%'))
                        if hit_rate < 50 and stats.get('hits', 0) > 10:
                            self.warnings.append(f"{cache_name} low hit rate: {stats['hit_rate']}")
                        else:
                            self.checks_passed.append(f"{cache_name} cache: {stats['hit_rate']} hit rate")
                
                return True
            else:
                self.warnings.append("Cache stats unavailable")
                return True
                
        except Exception as e:
            self.warnings.append(f"Cache check failed: {str(e)}")
            return True  # Non-critical
    
    def check_critical_data(self):
        """Verify critical production data is intact"""
        logger.info("Checking critical production data...")
        
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                # Check admin user exists
                admin_query = "SELECT COUNT(*) FROM \"user\" WHERE role = 'admin'"
                result = conn.execute(text(admin_query))
                admin_count = result.scalar()
                
                if admin_count == 0:
                    self.critical_issues.append("No admin users found!")
                else:
                    self.checks_passed.append(f"Admin users: {admin_count}")
                
                # Check data volumes
                volume_query = """
                SELECT 
                    (SELECT COUNT(*) FROM bag) as total_bags,
                    (SELECT COUNT(*) FROM bag WHERE type = 'parent') as parent_bags,
                    (SELECT COUNT(*) FROM bag WHERE type = 'child') as child_bags,
                    (SELECT COUNT(*) FROM link) as total_links,
                    (SELECT COUNT(*) FROM bill) as total_bills;
                """
                result = conn.execute(text(volume_query))
                row = result.fetchone()
                
                logger.info(f"Data volumes: {row.total_bags} bags, {row.total_links} links, {row.total_bills} bills")
                self.checks_passed.append(f"Data volumes verified: {row.total_bags} bags")
                
                return len([i for i in self.critical_issues if 'admin' in i.lower()]) == 0
                
        except Exception as e:
            self.critical_issues.append(f"Critical data check failed: {str(e)}")
            return False
    
    def generate_report(self):
        """Generate safety check report"""
        report = []
        report.append("\n" + "="*60)
        report.append("PRODUCTION SAFETY CHECK REPORT")
        report.append("="*60)
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append(f"Last Production Deploy: August 21, 2025 11:29 AM IST")
        report.append("")
        
        # Critical Issues
        if self.critical_issues:
            report.append("❌ CRITICAL ISSUES (Must Fix Before Deployment):")
            report.append("-"*40)
            for issue in self.critical_issues:
                report.append(f"  • {issue}")
            report.append("")
        
        # Warnings
        if self.warnings:
            report.append("⚠️  WARNINGS (Review Before Deployment):")
            report.append("-"*40)
            for warning in self.warnings:
                report.append(f"  • {warning}")
            report.append("")
        
        # Passed Checks
        report.append("✅ PASSED CHECKS:")
        report.append("-"*40)
        for check in self.checks_passed:
            report.append(f"  • {check}")
        report.append("")
        
        # Final Assessment
        report.append("DEPLOYMENT READINESS:")
        report.append("-"*40)
        
        if self.critical_issues:
            report.append("❌ NOT READY FOR PRODUCTION")
            report.append("   Critical issues must be resolved before deployment")
        elif len(self.warnings) > 3:
            report.append("⚠️  PROCEED WITH CAUTION")
            report.append("   Multiple warnings detected, review carefully")
        else:
            report.append("✅ SAFE FOR PRODUCTION DEPLOYMENT")
            report.append("   All critical checks passed")
        
        report.append("")
        report.append("="*60)
        
        return "\n".join(report)
    
    def run_all_checks(self):
        """Run all safety checks"""
        logger.info("Starting comprehensive safety checks...")
        
        checks = [
            ("Database Schema", self.check_database_schema),
            ("Data Integrity", self.check_data_integrity),
            ("API Endpoints", self.check_api_endpoints),
            ("Connection Pool", self.check_connection_pool),
            ("Cache Health", self.check_cache_health),
            ("Critical Data", self.check_critical_data),
        ]
        
        for check_name, check_func in checks:
            logger.info(f"Running: {check_name}")
            try:
                check_func()
            except Exception as e:
                self.critical_issues.append(f"{check_name} check crashed: {str(e)}")
        
        return len(self.critical_issues) == 0

def main():
    """Main safety check execution"""
    checker = ProductionSafetyCheck()
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            logger.error("Server not responding properly")
            sys.exit(1)
    except:
        logger.error(f"Cannot connect to server at {BASE_URL}")
        logger.error("Please ensure the application is running")
        sys.exit(1)
    
    # Run all checks
    is_safe = checker.run_all_checks()
    
    # Generate and display report
    report = checker.generate_report()
    print(report)
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"safety_check_{timestamp}.txt", "w") as f:
        f.write(report)
    
    logger.info(f"Report saved to safety_check_{timestamp}.txt")
    
    # Exit with appropriate code
    if not is_safe:
        logger.error("Production deployment is NOT safe!")
        sys.exit(1)
    else:
        logger.info("System is safe for production deployment")
        sys.exit(0)

if __name__ == "__main__":
    main()