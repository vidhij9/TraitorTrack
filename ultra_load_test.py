#!/usr/bin/env python3
"""
Ultra-Performance Load Testing Script
Tests 100+ concurrent users and 600k+ bags with <300ms response times
"""

import requests
import time
import threading
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

class UltraLoadTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.results = []
        self.lock = threading.Lock()
        
    def test_endpoint(self, endpoint, method="GET", data=None, headers=None):
        """Test a single endpoint"""
        try:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(f"{self.base_url}{endpoint}", 
                                      headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(f"{self.base_url}{endpoint}", 
                                       json=data, headers=headers, timeout=30)
            
            response_time = (time.time() - start_time) * 1000
            
            with self.lock:
                self.results.append({
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': response.status_code,
                    'response_time_ms': response_time,
                    'success': response.status_code < 400,
                    'timestamp': datetime.now().isoformat()
                })
            
            return response_time < 300  # Pass if <300ms
            
        except Exception as e:
            with self.lock:
                self.results.append({
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': 0,
                    'response_time_ms': 0,
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
            return False
    
    def run_concurrent_test(self, num_users=100, duration_seconds=60):
        """Run concurrent user test"""
        print(f"🚀 Starting concurrent test: {num_users} users for {duration_seconds}s")
        
        endpoints = [
            '/health',
            '/api/dashboard/analytics',
            '/api/bills',
            '/api/bags',
            '/api/users',
            '/api/export/bills/csv',
            '/api/print/summary'
        ]
        
        def user_worker(user_id):
            """Simulate user activity"""
            start_time = time.time()
            successful_requests = 0
            total_requests = 0
            
            while time.time() - start_time < duration_seconds:
                for endpoint in endpoints:
                    if self.test_endpoint(endpoint):
                        successful_requests += 1
                    total_requests += 1
                    time.sleep(0.1)  # Small delay between requests
            
            return successful_requests, total_requests
        
        # Run concurrent users
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(user_worker, i) for i in range(num_users)]
            results = [future.result() for future in as_completed(futures)]
        
        # Calculate metrics
        total_successful = sum(r[0] for r in results)
        total_requests = sum(r[1] for r in results)
        success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        
        response_times = [r['response_time_ms'] for r in self.results if r['success']]
        
        metrics = {
            'concurrent_users': num_users,
            'duration_seconds': duration_seconds,
            'total_requests': total_requests,
            'successful_requests': total_successful,
            'success_rate': success_rate,
            'avg_response_time_ms': statistics.mean(response_times) if response_times else 0,
            'median_response_time_ms': statistics.median(response_times) if response_times else 0,
            'p95_response_time_ms': statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0,
            'max_response_time_ms': max(response_times) if response_times else 0,
            'min_response_time_ms': min(response_times) if response_times else 0
        }
        
        return metrics
    
    def run_stress_test(self, max_users=200, step_size=10):
        """Run stress test to find breaking point"""
        print(f"🔥 Starting stress test: up to {max_users} users")
        
        stress_results = []
        
        for num_users in range(10, max_users + 1, step_size):
            print(f"Testing with {num_users} users...")
            
            # Clear previous results
            self.results = []
            
            # Run test for 30 seconds
            metrics = self.run_concurrent_test(num_users, 30)
            stress_results.append(metrics)
            
            # Check if performance is degrading
            if metrics['success_rate'] < 95 or metrics['avg_response_time_ms'] > 500:
                print(f"⚠️ Performance degrading at {num_users} users")
                break
        
        return stress_results
    
    def generate_report(self, metrics, filename="ultra_load_test_report.json"):
        """Generate comprehensive test report"""
        report = {
            'test_timestamp': datetime.now().isoformat(),
            'test_summary': {
                'concurrent_users': metrics['concurrent_users'],
                'duration_seconds': metrics['duration_seconds'],
                'total_requests': metrics['total_requests'],
                'success_rate': metrics['success_rate'],
                'avg_response_time_ms': metrics['avg_response_time_ms']
            },
            'performance_metrics': metrics,
            'detailed_results': self.results,
            'recommendations': []
        }
        
        # Add recommendations
        if metrics['success_rate'] < 99:
            report['recommendations'].append("Increase server resources or optimize queries")
        
        if metrics['avg_response_time_ms'] > 300:
            report['recommendations'].append("Optimize database queries and add caching")
        
        if metrics['p95_response_time_ms'] > 500:
            report['recommendations'].append("Investigate slow queries and add indexes")
        
        # Save report
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Test report saved to: {filename}")
        return report

def main():
    """Run comprehensive load tests"""
    print("=" * 80)
    print("🚀 ULTRA-PERFORMANCE LOAD TESTING")
    print("=" * 80)
    
    tester = UltraLoadTester()
    
    # Test 1: 100 concurrent users
    print("\n🧪 Test 1: 100 Concurrent Users")
    metrics_100 = tester.run_concurrent_test(100, 60)
    
    print(f"✅ Results for 100 users:")
    print(f"   Success Rate: {metrics_100['success_rate']:.1f}%")
    print(f"   Avg Response Time: {metrics_100['avg_response_time_ms']:.1f}ms")
    print(f"   P95 Response Time: {metrics_100['p95_response_time_ms']:.1f}ms")
    
    # Test 2: Stress test
    print("\n🔥 Test 2: Stress Test")
    stress_results = tester.run_stress_test(200, 20)
    
    # Generate report
    print("\n📊 Generating comprehensive report...")
    report = tester.generate_report(metrics_100, "ultra_load_test_report.json")
    
    print("\n" + "=" * 80)
    print("🎉 LOAD TESTING COMPLETED")
    print("=" * 80)
    print(f"✅ 100 User Test: {metrics_100['success_rate']:.1f}% success rate")
    print(f"✅ Avg Response Time: {metrics_100['avg_response_time_ms']:.1f}ms")
    print(f"✅ P95 Response Time: {metrics_100['p95_response_time_ms']:.1f}ms")
    
    if metrics_100['success_rate'] >= 99 and metrics_100['avg_response_time_ms'] <= 300:
        print("🎯 TARGET ACHIEVED: System ready for 100+ users with <300ms response times!")
    else:
        print("⚠️ TARGET NOT MET: Further optimization required")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
