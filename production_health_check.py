#!/usr/bin/env python3
"""
Production Health Check and Readiness Assessment
"""

import time
import json
import psycopg2
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Tuple
import os
import random
import string

# Configuration
BASE_URL = "http://0.0.0.0:5000"
DATABASE_URL = os.environ.get("DATABASE_URL")
CONCURRENT_USERS = 20  # Start with lower number to test
TEST_DURATION = 30  # seconds

class ProductionHealthChecker:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "passed": [],
            "failed": [],
            "warnings": [],
            "metrics": {},
            "recommendations": []
        }
        self.session = requests.Session()
        
    def run_all_checks(self):
        """Run comprehensive health checks"""
        print("=" * 60)
        print("PRODUCTION READINESS ASSESSMENT")
        print("=" * 60)
        
        # 1. Database Health
        print("\n1. DATABASE HEALTH CHECK...")
        self.check_database_health()
        
        # 2. API Endpoints
        print("\n2. API ENDPOINTS CHECK...")
        self.check_api_endpoints()
        
        # 3. Performance Under Load
        print("\n3. PERFORMANCE UNDER LOAD...")
        self.check_performance_under_load()
        
        # 4. Data Integrity
        print("\n4. DATA INTEGRITY CHECK...")
        self.check_data_integrity()
        
        # 5. Security Checks
        print("\n5. SECURITY CHECKS...")
        self.check_security()
        
        # Generate Report
        self.generate_report()
        
    def check_database_health(self):
        """Check database connection and performance"""
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            
            # Check connection pool
            cur.execute("""
                SELECT count(*) as connections, state 
                FROM pg_stat_activity 
                WHERE datname = current_database() 
                GROUP BY state
            """)
            connections = cur.fetchall()
            
            total_connections = sum(row[0] for row in connections)
            if total_connections < 50:
                self.results["passed"].append(f"Database connections healthy: {total_connections} connections")
            else:
                self.results["warnings"].append(f"High database connections: {total_connections}")
            
            # Check table sizes
            cur.execute("""
                SELECT COUNT(*) FROM bag
                UNION ALL
                SELECT COUNT(*) FROM scan
                UNION ALL
                SELECT COUNT(*) FROM link
            """)
            counts = cur.fetchall()
            
            if all(count[0] < 1000000 for count in counts):
                self.results["passed"].append("Database size within limits")
            else:
                self.results["warnings"].append("Large dataset detected")
            
            # Check indexes
            cur.execute("""
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE schemaname = 'public'
            """)
            index_count = cur.fetchone()[0]
            
            if index_count >= 10:
                self.results["passed"].append(f"Adequate indexes: {index_count} indexes found")
            else:
                self.results["failed"].append(f"Insufficient indexes: only {index_count} found")
            
            cur.close()
            conn.close()
            
        except Exception as e:
            self.results["failed"].append(f"Database health check failed: {str(e)}")
            
    def check_api_endpoints(self):
        """Test all critical API endpoints"""
        endpoints = [
            ("/health", "GET", None),
            ("/status", "GET", None),
            ("/", "GET", None),
            ("/login", "GET", None),
        ]
        
        for endpoint, method, data in endpoints:
            try:
                start = time.time()
                
                if method == "GET":
                    response = self.session.get(f"{BASE_URL}{endpoint}", timeout=5)
                else:
                    response = self.session.post(f"{BASE_URL}{endpoint}", json=data, timeout=5)
                
                elapsed = (time.time() - start) * 1000
                
                if response.status_code in [200, 302]:
                    if elapsed < 500:
                        self.results["passed"].append(f"{endpoint}: {elapsed:.2f}ms")
                    else:
                        self.results["warnings"].append(f"{endpoint}: Slow response {elapsed:.2f}ms")
                else:
                    self.results["failed"].append(f"{endpoint}: HTTP {response.status_code}")
                    
            except Exception as e:
                self.results["failed"].append(f"{endpoint}: {str(e)}")
                
    def check_performance_under_load(self):
        """Simulate concurrent users"""
        def make_request():
            try:
                start = time.time()
                response = self.session.get(f"{BASE_URL}/health", timeout=5)
                elapsed = time.time() - start
                return response.status_code, elapsed
            except:
                return None, None
        
        # Test with concurrent requests
        with ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
            futures = []
            for _ in range(CONCURRENT_USERS * 5):
                futures.append(executor.submit(make_request))
            
            success_count = 0
            failed_count = 0
            response_times = []
            
            for future in as_completed(futures):
                status, elapsed = future.result()
                if status == 200:
                    success_count += 1
                    response_times.append(elapsed)
                else:
                    failed_count += 1
        
        # Calculate metrics
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            p95_time = sorted(response_times)[int(len(response_times) * 0.95)]
            
            self.results["metrics"]["avg_response_time"] = f"{avg_time*1000:.2f}ms"
            self.results["metrics"]["p95_response_time"] = f"{p95_time*1000:.2f}ms"
            self.results["metrics"]["success_rate"] = f"{(success_count/(success_count+failed_count))*100:.1f}%"
            
            if avg_time < 0.5 and p95_time < 1.0:
                self.results["passed"].append(f"Performance under load: avg={avg_time*1000:.2f}ms, p95={p95_time*1000:.2f}ms")
            else:
                self.results["warnings"].append(f"Performance degradation: avg={avg_time*1000:.2f}ms, p95={p95_time*1000:.2f}ms")
                
    def check_data_integrity(self):
        """Check data integrity constraints"""
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            
            # Check for orphaned records
            cur.execute("""
                SELECT COUNT(*) 
                FROM link l 
                LEFT JOIN bag p ON l.parent_bag_id = p.id 
                LEFT JOIN bag c ON l.child_bag_id = c.id 
                WHERE p.id IS NULL OR c.id IS NULL
            """)
            orphaned = cur.fetchone()[0]
            
            if orphaned == 0:
                self.results["passed"].append("No orphaned links found")
            else:
                self.results["failed"].append(f"Found {orphaned} orphaned links")
            
            # Check constraint violations
            cur.execute("""
                SELECT COUNT(*) 
                FROM bag 
                WHERE type NOT IN ('parent', 'child')
            """)
            invalid_types = cur.fetchone()[0]
            
            if invalid_types == 0:
                self.results["passed"].append("All bag types valid")
            else:
                self.results["failed"].append(f"Found {invalid_types} bags with invalid types")
            
            cur.close()
            conn.close()
            
        except Exception as e:
            self.results["failed"].append(f"Data integrity check failed: {str(e)}")
            
    def check_security(self):
        """Basic security checks"""
        # Test SQL injection protection
        try:
            response = self.session.post(
                f"{BASE_URL}/login",
                data={"username": "admin' OR '1'='1", "password": "test"},
                timeout=5
            )
            
            if "error" in response.text.lower() or response.status_code != 200:
                self.results["passed"].append("SQL injection protection working")
            else:
                self.results["failed"].append("Potential SQL injection vulnerability")
                
        except:
            self.results["warnings"].append("Could not test SQL injection protection")
        
        # Check CSRF protection
        try:
            response = self.session.get(f"{BASE_URL}/login")
            if "csrf" in response.text.lower():
                self.results["passed"].append("CSRF protection enabled")
            else:
                self.results["warnings"].append("CSRF protection may not be enabled")
        except:
            pass
            
    def generate_report(self):
        """Generate final report"""
        print("\n" + "=" * 60)
        print("PRODUCTION READINESS REPORT")
        print("=" * 60)
        
        # Calculate summary
        total_checks = len(self.results["passed"]) + len(self.results["failed"])
        pass_rate = (len(self.results["passed"]) / total_checks * 100) if total_checks > 0 else 0
        
        print(f"\n📊 SUMMARY:")
        print(f"  ✅ Passed: {len(self.results['passed'])}")
        print(f"  ❌ Failed: {len(self.results['failed'])}")
        print(f"  ⚠️  Warnings: {len(self.results['warnings'])}")
        print(f"  📈 Pass Rate: {pass_rate:.1f}%")
        
        if self.results["failed"]:
            print(f"\n❌ CRITICAL ISSUES:")
            for issue in self.results["failed"]:
                print(f"  • {issue}")
        
        if self.results["warnings"]:
            print(f"\n⚠️  WARNINGS:")
            for warning in self.results["warnings"]:
                print(f"  • {warning}")
        
        if self.results["metrics"]:
            print(f"\n📊 METRICS:")
            for key, value in self.results["metrics"].items():
                print(f"  • {key}: {value}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if pass_rate < 80:
            print("  • System NOT ready for production - critical issues need to be resolved")
            self.results["recommendations"].append("Fix critical issues before deployment")
        elif pass_rate < 95:
            print("  • System needs improvements before production deployment")
            self.results["recommendations"].append("Address warnings and optimize performance")
        else:
            print("  • System appears ready for production deployment")
            self.results["recommendations"].append("System ready for deployment")
        
        # Specific recommendations based on issues
        if any("connection" in str(f).lower() for f in self.results["failed"]):
            print("  • Optimize database connection pool settings")
            self.results["recommendations"].append("Increase connection pool size")
            
        if any("slow" in str(w).lower() for w in self.results["warnings"]):
            print("  • Implement caching for frequently accessed data")
            print("  • Add database indexes for slow queries")
            self.results["recommendations"].append("Optimize query performance")
        
        # Save report
        with open("production_readiness_final.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Full report saved to: production_readiness_final.json")
        print("=" * 60)
        
        return pass_rate >= 80

if __name__ == "__main__":
    checker = ProductionHealthChecker()
    is_ready = checker.run_all_checks()
    
    if is_ready:
        print("\n✅ SYSTEM IS READY FOR PRODUCTION DEPLOYMENT")
    else:
        print("\n❌ SYSTEM NEEDS FIXES BEFORE PRODUCTION DEPLOYMENT")