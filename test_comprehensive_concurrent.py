#!/usr/bin/env python3
"""
Comprehensive concurrent testing for TraceTrack
Tests all endpoints with 20+ users accessing features simultaneously
"""
import requests
import threading
import time
import random
import json
from datetime import datetime
from collections import defaultdict
import statistics

BASE_URL = "http://localhost:5000"
NUM_USERS = 25  # Testing with 25 concurrent users
DURATION_SECONDS = 30  # Run test for 30 seconds

class EndpointStats:
    def __init__(self):
        self.response_times = []
        self.status_codes = defaultdict(int)
        self.errors = []
        self.success_count = 0
        self.total_count = 0
    
    def add_result(self, response_time, status_code, error=None):
        self.total_count += 1
        if error:
            self.errors.append(error)
        else:
            self.response_times.append(response_time)
            self.status_codes[status_code] += 1
            if status_code < 400:
                self.success_count += 1
    
    def get_stats(self):
        if not self.response_times:
            return {
                'total_requests': self.total_count,
                'success_rate': 0,
                'avg_response_time': 0,
                'p50': 0,
                'p95': 0,
                'p99': 0,
                'min': 0,
                'max': 0,
                'errors': len(self.errors)
            }
        
        sorted_times = sorted(self.response_times)
        return {
            'total_requests': self.total_count,
            'success_rate': round(self.success_count / self.total_count * 100, 1) if self.total_count > 0 else 0,
            'avg_response_time': round(statistics.mean(self.response_times), 2),
            'p50': round(sorted_times[len(sorted_times)//2], 2),
            'p95': round(sorted_times[int(len(sorted_times)*0.95)], 2) if len(sorted_times) > 20 else sorted_times[-1],
            'p99': round(sorted_times[int(len(sorted_times)*0.99)], 2) if len(sorted_times) > 100 else sorted_times[-1],
            'min': round(min(self.response_times), 2),
            'max': round(max(self.response_times), 2),
            'errors': len(self.errors),
            'status_codes': dict(self.status_codes)
        }

# Endpoint configurations with realistic user behavior
ENDPOINTS = {
    # Public endpoints
    'home': {'path': '/', 'method': 'GET', 'auth': False, 'weight': 10},
    'login_page': {'path': '/login', 'method': 'GET', 'auth': False, 'weight': 5},
    'health': {'path': '/health', 'method': 'GET', 'auth': False, 'weight': 3},
    'production_health': {'path': '/production-health', 'method': 'GET', 'auth': False, 'weight': 2},
    
    # Authentication
    'login': {'path': '/login', 'method': 'POST', 'auth': False, 'weight': 5, 
              'data': {'username': 'admin', 'password': 'admin'}},
    
    # Dashboard & Analytics
    'dashboard': {'path': '/dashboard', 'method': 'GET', 'auth': True, 'weight': 15},
    'api_stats': {'path': '/api/stats', 'method': 'GET', 'auth': True, 'weight': 10},
    'api_scans': {'path': '/api/scans?limit=10', 'method': 'GET', 'auth': True, 'weight': 8},
    'dashboard_analytics': {'path': '/api/dashboard/analytics', 'method': 'GET', 'auth': True, 'weight': 5},
    
    # Scanning Operations (most critical)
    'parent_scan': {'path': '/parent-scan', 'method': 'GET', 'auth': True, 'weight': 20},
    'child_scan': {'path': '/child-scan', 'method': 'GET', 'auth': True, 'weight': 15},
    'scan_parent': {'path': '/scan/parent/SB12345', 'method': 'GET', 'auth': True, 'weight': 10},
    'scan_child': {'path': '/scan/child/CB67890', 'method': 'GET', 'auth': True, 'weight': 10},
    
    # Bag Management
    'parent_bags_list': {'path': '/api/bags/parent/list', 'method': 'GET', 'auth': True, 'weight': 8},
    'bag_lookup': {'path': '/bag-lookup', 'method': 'GET', 'auth': True, 'weight': 5},
    'parent_bag_detail': {'path': '/parent-bag-detail/1', 'method': 'GET', 'auth': True, 'weight': 5},
    
    # Billing Operations
    'billing': {'path': '/billing', 'method': 'GET', 'auth': True, 'weight': 8},
    'create_bill': {'path': '/create-bill', 'method': 'GET', 'auth': True, 'weight': 5},
    'view_bills': {'path': '/view-bills', 'method': 'GET', 'auth': True, 'weight': 5},
    
    # User Management (Admin)
    'user_management': {'path': '/user_management', 'method': 'GET', 'auth': True, 'weight': 3},
    'admin_dashboard': {'path': '/admin-dashboard', 'method': 'GET', 'auth': True, 'weight': 3},
    
    # Reports
    'reports': {'path': '/reports', 'method': 'GET', 'auth': True, 'weight': 5},
    'scan_report': {'path': '/scan-report', 'method': 'GET', 'auth': True, 'weight': 3},
}

class ConcurrentUser:
    def __init__(self, user_id):
        self.user_id = user_id
        self.session = requests.Session()
        self.authenticated = False
        self.running = True
        self.stats = defaultdict(EndpointStats)
        
    def authenticate(self):
        """Login and get session cookie"""
        try:
            response = self.session.post(
                f"{BASE_URL}/login",
                data={'username': 'admin', 'password': 'admin'},
                timeout=10,
                allow_redirects=False
            )
            if response.status_code in [200, 302, 303]:
                self.authenticated = True
                return True
        except Exception as e:
            print(f"User {self.user_id} auth failed: {e}")
        return False
    
    def make_request(self, endpoint_name, endpoint_config):
        """Make a single request to an endpoint"""
        start_time = time.time()
        try:
            if endpoint_config['method'] == 'GET':
                response = self.session.get(
                    f"{BASE_URL}{endpoint_config['path']}",
                    timeout=10
                )
            else:  # POST
                response = self.session.post(
                    f"{BASE_URL}{endpoint_config['path']}",
                    data=endpoint_config.get('data', {}),
                    timeout=10,
                    allow_redirects=False
                )
            
            response_time = (time.time() - start_time) * 1000  # ms
            self.stats[endpoint_name].add_result(response_time, response.status_code)
            
        except requests.Timeout:
            response_time = (time.time() - start_time) * 1000
            self.stats[endpoint_name].add_result(response_time, 0, "Timeout")
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.stats[endpoint_name].add_result(response_time, 0, str(e))
    
    def run(self):
        """Simulate user behavior"""
        # Authenticate first if needed
        if not self.authenticate():
            print(f"User {self.user_id} failed to authenticate")
            return
        
        # Create weighted list of endpoints
        weighted_endpoints = []
        for name, config in ENDPOINTS.items():
            if config['auth'] and not self.authenticated:
                continue
            weighted_endpoints.extend([name] * config.get('weight', 1))
        
        # Simulate user activity
        while self.running:
            endpoint_name = random.choice(weighted_endpoints)
            endpoint_config = ENDPOINTS[endpoint_name]
            
            self.make_request(endpoint_name, endpoint_config)
            
            # Random delay between requests (50-500ms)
            time.sleep(random.uniform(0.05, 0.5))

def run_comprehensive_test():
    """Run comprehensive concurrent test"""
    print("\n" + "="*80)
    print("TraceTrack Comprehensive Concurrent Load Test")
    print("="*80)
    print(f"Testing with {NUM_USERS} concurrent users for {DURATION_SECONDS} seconds")
    print(f"Testing {len(ENDPOINTS)} different endpoints")
    print("="*80 + "\n")
    
    # Create and start user threads
    users = []
    threads = []
    
    for i in range(NUM_USERS):
        user = ConcurrentUser(i + 1)
        users.append(user)
        thread = threading.Thread(target=user.run)
        threads.append(thread)
        thread.start()
        time.sleep(0.1)  # Stagger user starts
    
    print(f"All {NUM_USERS} users started. Running for {DURATION_SECONDS} seconds...")
    
    # Run for specified duration
    time.sleep(DURATION_SECONDS)
    
    # Stop all users
    print("\nStopping users...")
    for user in users:
        user.running = False
    
    # Wait for threads to complete
    for thread in threads:
        thread.join(timeout=5)
    
    # Aggregate results
    print("\n" + "="*80)
    print("Test Results - Response Times by Endpoint")
    print("="*80)
    
    all_stats = defaultdict(EndpointStats)
    for user in users:
        for endpoint_name, stats in user.stats.items():
            for rt in stats.response_times:
                all_stats[endpoint_name].response_times.append(rt)
            all_stats[endpoint_name].total_count += stats.total_count
            all_stats[endpoint_name].success_count += stats.success_count
            for code, count in stats.status_codes.items():
                all_stats[endpoint_name].status_codes[code] += count
            all_stats[endpoint_name].errors.extend(stats.errors)
    
    # Sort endpoints by request count
    sorted_endpoints = sorted(all_stats.items(), key=lambda x: x[1].total_count, reverse=True)
    
    print(f"\n{'Endpoint':<30} {'Requests':<10} {'Success%':<10} {'Avg(ms)':<10} {'P50(ms)':<10} {'P95(ms)':<10} {'P99(ms)':<10}")
    print("-" * 100)
    
    total_requests = 0
    total_success = 0
    all_response_times = []
    
    for endpoint_name, stats in sorted_endpoints:
        endpoint_stats = stats.get_stats()
        if endpoint_stats['total_requests'] > 0:
            total_requests += endpoint_stats['total_requests']
            total_success += stats.success_count
            all_response_times.extend(stats.response_times)
            
            print(f"{endpoint_name:<30} {endpoint_stats['total_requests']:<10} "
                  f"{endpoint_stats['success_rate']:<10.1f} "
                  f"{endpoint_stats['avg_response_time']:<10.0f} "
                  f"{endpoint_stats['p50']:<10.0f} "
                  f"{endpoint_stats['p95']:<10.0f} "
                  f"{endpoint_stats['p99']:<10.0f}")
    
    # Overall statistics
    print("\n" + "="*80)
    print("Overall Performance Summary")
    print("="*80)
    
    if all_response_times:
        sorted_all = sorted(all_response_times)
        overall_stats = {
            'total_requests': total_requests,
            'requests_per_second': round(total_requests / DURATION_SECONDS, 2),
            'success_rate': round(total_success / total_requests * 100, 1) if total_requests > 0 else 0,
            'avg_response_time': round(statistics.mean(all_response_times), 2),
            'median_response_time': round(sorted_all[len(sorted_all)//2], 2),
            'p95_response_time': round(sorted_all[int(len(sorted_all)*0.95)], 2),
            'p99_response_time': round(sorted_all[int(len(sorted_all)*0.99)], 2),
            'min_response_time': round(min(all_response_times), 2),
            'max_response_time': round(max(all_response_times), 2)
        }
        
        print(f"Total Requests: {overall_stats['total_requests']}")
        print(f"Requests/Second: {overall_stats['requests_per_second']}")
        print(f"Success Rate: {overall_stats['success_rate']}%")
        print(f"Average Response Time: {overall_stats['avg_response_time']} ms")
        print(f"Median Response Time: {overall_stats['median_response_time']} ms")
        print(f"95th Percentile: {overall_stats['p95_response_time']} ms")
        print(f"99th Percentile: {overall_stats['p99_response_time']} ms")
        print(f"Min Response Time: {overall_stats['min_response_time']} ms")
        print(f"Max Response Time: {overall_stats['max_response_time']} ms")
        
        # Performance evaluation
        print("\n" + "="*80)
        print("Performance Evaluation")
        print("="*80)
        
        if overall_stats['success_rate'] >= 99 and overall_stats['avg_response_time'] < 200:
            print("✅ EXCELLENT PERFORMANCE!")
            print("The application handles 25 concurrent users with excellent response times.")
        elif overall_stats['success_rate'] >= 95 and overall_stats['avg_response_time'] < 500:
            print("✅ GOOD PERFORMANCE!")
            print("The application handles concurrent load well with acceptable response times.")
        elif overall_stats['success_rate'] >= 90:
            print("⚠️ ADEQUATE PERFORMANCE")
            print("The application handles load but may benefit from further optimization.")
        else:
            print("❌ PERFORMANCE ISSUES DETECTED")
            print("The application struggles with concurrent load. Optimization needed.")
        
        # Specific recommendations
        print("\nKey Findings:")
        slow_endpoints = [(name, stats.get_stats()) for name, stats in sorted_endpoints 
                         if stats.get_stats()['avg_response_time'] > 500 and stats.get_stats()['total_requests'] > 10]
        if slow_endpoints:
            print(f"- {len(slow_endpoints)} endpoints have response times >500ms")
            for name, stats in slow_endpoints[:3]:
                print(f"  • {name}: {stats['avg_response_time']:.0f}ms avg")
        else:
            print("- All frequently accessed endpoints respond quickly (<500ms)")
        
        error_endpoints = [(name, stats) for name, stats in sorted_endpoints 
                          if stats.errors and len(stats.errors) > 5]
        if error_endpoints:
            print(f"- {len(error_endpoints)} endpoints have frequent errors")
            for name, stats in error_endpoints[:3]:
                print(f"  • {name}: {len(stats.errors)} errors")
        else:
            print("- No significant error patterns detected")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    # Wait for server to be ready
    time.sleep(2)
    
    # Check server health
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ Server is running (health check: {response.status_code})")
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        exit(1)
    
    # Run comprehensive test
    run_comprehensive_test()