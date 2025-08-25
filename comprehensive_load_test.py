#!/usr/bin/env python3
"""
Comprehensive Load Testing Script for TraceTrack
Tests all endpoints and measures performance
"""

import requests
import time
import json
import concurrent.futures
from datetime import datetime
import random
import string
import statistics

# Base configuration
BASE_URL = "http://localhost:5000"
SESSION_COOKIE = "tracetrack_session=.eJxlT0tuhDAMvYvXo1E-DAFW1VyhB4hM4kA0EGgSuql695rpdNWV5ff8Pv4CGzKVGYaAS6EL2J3yiolShaHmgxFXcrB1e1CCAXRrgmrJ6L41XWiaMI6tFK3UWprGkNRK9mpsNLDuyJlt7I7PET0MWvbdP-Ijs-_7XYjuJlnmY9mxutkyizCkY1kuQCvGhc8yTjN-vtWMsW6Zh3tc3baybNmmibyN6a82AzHZGleCQZobt5RCdVfRdK1R6gKFSolbsjOe30MI1CvldOexJ2dM770bg9JCBOeFOZsdhfLzDSVvry1vC9sD-pWDf7GEZ-KrKXz_AKOlcVo.aKv_cQ.HoFSFPXoRwGcbJeO5_Y2hKIM5L4"

# Test configuration
CONCURRENT_USERS = 10
REQUESTS_PER_USER = 5

class EndpointTest:
    def __init__(self, name, method, path, data=None, params=None):
        self.name = name
        self.method = method
        self.path = path
        self.data = data
        self.params = params
        self.response_times = []
        self.errors = []
        self.success_count = 0
        self.total_count = 0
        
    def execute(self):
        """Execute single request and measure response time"""
        url = f"{BASE_URL}{self.path}"
        headers = {"Cookie": SESSION_COOKIE}
        
        try:
            start_time = time.time()
            
            if self.method == "GET":
                response = requests.get(url, headers=headers, params=self.params, timeout=30)
            elif self.method == "POST":
                response = requests.post(url, headers=headers, data=self.data, timeout=30)
            else:
                response = requests.request(self.method, url, headers=headers, timeout=30)
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            self.response_times.append(response_time)
            
            if response.status_code in [200, 201, 302]:
                self.success_count += 1
            else:
                self.errors.append(f"Status {response.status_code}")
                
            self.total_count += 1
            return response_time, response.status_code
            
        except Exception as e:
            self.errors.append(str(e))
            self.total_count += 1
            return None, None
    
    def get_stats(self):
        """Calculate statistics for this endpoint"""
        if not self.response_times:
            return {
                "name": self.name,
                "total_requests": self.total_count,
                "successful": self.success_count,
                "errors": len(self.errors),
                "avg_ms": 0,
                "median_ms": 0,
                "p95_ms": 0,
                "p99_ms": 0,
                "min_ms": 0,
                "max_ms": 0
            }
        
        sorted_times = sorted(self.response_times)
        return {
            "name": self.name,
            "total_requests": self.total_count,
            "successful": self.success_count,
            "errors": len(self.errors),
            "avg_ms": round(statistics.mean(self.response_times), 2),
            "median_ms": round(statistics.median(self.response_times), 2),
            "p95_ms": round(sorted_times[int(len(sorted_times) * 0.95)] if len(sorted_times) > 0 else 0, 2),
            "p99_ms": round(sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) > 0 else 0, 2),
            "min_ms": round(min(self.response_times), 2),
            "max_ms": round(max(self.response_times), 2)
        }

def get_all_endpoints():
    """Define all endpoints to test"""
    endpoints = [
        # Authentication & User Management
        EndpointTest("Login Page", "GET", "/login"),
        EndpointTest("Dashboard", "GET", "/dashboard"),
        EndpointTest("User Management", "GET", "/user_management"),
        EndpointTest("User Profile", "GET", "/user/raghav"),
        
        # Bag Management
        EndpointTest("Bag Management - All", "GET", "/bag_management"),
        EndpointTest("Bag Management - Parent Only", "GET", "/bag_management", params={"type": "parent"}),
        EndpointTest("Bag Management - Child Only", "GET", "/bag_management", params={"type": "child"}),
        EndpointTest("Bag Management - Linked", "GET", "/bag_management", params={"linked_status": "linked"}),
        EndpointTest("Bag Management - Unlinked", "GET", "/bag_management", params={"linked_status": "unlinked"}),
        EndpointTest("Bag Management - Billed", "GET", "/bag_management", params={"bill_status": "billed"}),
        EndpointTest("Bag Management - Unbilled", "GET", "/bag_management", params={"bill_status": "unbilled"}),
        EndpointTest("Bag Management - Search", "GET", "/bag_management", params={"search": "SB"}),
        EndpointTest("Bag Management - Date Filter", "GET", "/bag_management", 
                    params={"date_from": "2025-08-01", "date_to": "2025-08-31"}),
        
        # Bill Management
        EndpointTest("Bill Management - All", "GET", "/bill_management"),
        EndpointTest("Bill Management - Completed", "GET", "/bill_management", params={"status": "completed"}),
        EndpointTest("Bill Management - In Progress", "GET", "/bill_management", params={"status": "in_progress"}),
        EndpointTest("Bill Management - Empty", "GET", "/bill_management", params={"status": "empty"}),
        EndpointTest("Bill Summary", "GET", "/bill_summary"),
        EndpointTest("EOD Summary Preview", "GET", "/eod_summary_preview"),
        
        # Scanning Pages
        EndpointTest("Parent Scan Page", "GET", "/scan_parent"),
        EndpointTest("Child Scan Page", "GET", "/scan_child"),
        
        # API Endpoints - Statistics
        EndpointTest("API Stats V2", "GET", "/api/v2/stats"),
        EndpointTest("API Dashboard Stats", "GET", "/api/dashboard_stats"),
        EndpointTest("API Dashboard Data", "GET", "/api/dashboard_data"),
        EndpointTest("API Interactive Dashboard", "GET", "/api/dashboard/interactive"),
        
        # API Endpoints - Scanning
        EndpointTest("API Fast Parent Scan", "POST", "/api/fast_parent_scan", 
                    data={"qr_code": "SB99999"}),
        EndpointTest("Fast Bill Parent Scan", "POST", "/fast/bill_parent_scan", 
                    data={"bill_id": "1", "qr_code": "SB99999"}),
        EndpointTest("Process Child Scan Fast", "POST", "/process_child_scan_fast", 
                    data={"parent_bag_id": "SB00001", "child_bag_id": "CB00001"}),
        
        # API Endpoints - Bill Summary
        EndpointTest("API Bill Summary", "GET", "/api/bill_summary"),
        EndpointTest("API Bill Summary EOD", "GET", "/api/bill_summary/eod"),
        
        # Reports
        EndpointTest("Reports Page", "GET", "/reports"),
        
        # Dispatcher Routes
        EndpointTest("Dispatcher Dashboard", "GET", "/dispatcher_dashboard"),
        
        # Bag Details (sample)
        EndpointTest("Bag Details", "GET", "/bag/1"),
        
        # Health Check
        EndpointTest("Health Check", "GET", "/health"),
        
        # Static Resources
        EndpointTest("Static JS - jsQR", "GET", "/static/js/jsQR.js"),
        EndpointTest("Static CSS - Bootstrap", "GET", "/static/css/bootstrap.min.css"),
    ]
    
    return endpoints

def test_endpoint_concurrent(endpoint, num_requests):
    """Test single endpoint with concurrent requests"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        futures = []
        for _ in range(num_requests):
            futures.append(executor.submit(endpoint.execute))
        
        # Wait for all requests to complete
        concurrent.futures.wait(futures)
    
    return endpoint.get_stats()

def run_comprehensive_test():
    """Run comprehensive load test on all endpoints"""
    print("=" * 80)
    print("TraceTrack Comprehensive Load Test")
    print(f"Testing with {CONCURRENT_USERS} concurrent users")
    print(f"Each endpoint tested with {REQUESTS_PER_USER * CONCURRENT_USERS} total requests")
    print("=" * 80)
    
    endpoints = get_all_endpoints()
    all_results = []
    
    # Test each endpoint
    for i, endpoint in enumerate(endpoints, 1):
        print(f"\n[{i}/{len(endpoints)}] Testing: {endpoint.name}")
        print(f"  Method: {endpoint.method} {endpoint.path}")
        
        stats = test_endpoint_concurrent(endpoint, REQUESTS_PER_USER * CONCURRENT_USERS)
        all_results.append(stats)
        
        # Print immediate results
        print(f"  ✓ Avg: {stats['avg_ms']}ms | P95: {stats['p95_ms']}ms | Success: {stats['successful']}/{stats['total_requests']}")
        
        if stats['errors'] > 0:
            print(f"  ⚠ Errors: {stats['errors']}")
        
        # Small delay between endpoint tests
        time.sleep(0.5)
    
    # Print summary report
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY REPORT")
    print("=" * 80)
    
    # Sort by average response time
    all_results.sort(key=lambda x: x['avg_ms'], reverse=True)
    
    print("\n🔴 SLOWEST ENDPOINTS (Need Optimization):")
    print("-" * 60)
    slow_count = 0
    for result in all_results:
        if result['avg_ms'] > 100:  # Threshold for slow endpoints
            slow_count += 1
            print(f"{slow_count}. {result['name']}")
            print(f"   Avg: {result['avg_ms']}ms | P95: {result['p95_ms']}ms | P99: {result['p99_ms']}ms")
            if result['errors'] > 0:
                print(f"   ⚠ Error Rate: {(result['errors']/result['total_requests']*100):.1f}%")
    
    print("\n🟢 FASTEST ENDPOINTS (Well Optimized):")
    print("-" * 60)
    fast_endpoints = [r for r in all_results if r['avg_ms'] <= 20]
    for i, result in enumerate(fast_endpoints[:10], 1):
        print(f"{i}. {result['name']}: {result['avg_ms']}ms avg")
    
    print("\n📊 OVERALL STATISTICS:")
    print("-" * 60)
    total_requests = sum(r['total_requests'] for r in all_results)
    total_successful = sum(r['successful'] for r in all_results)
    total_errors = sum(r['errors'] for r in all_results)
    avg_response = statistics.mean(r['avg_ms'] for r in all_results)
    
    print(f"Total Requests: {total_requests}")
    print(f"Successful: {total_successful} ({(total_successful/total_requests*100):.1f}%)")
    print(f"Errors: {total_errors} ({(total_errors/total_requests*100):.1f}%)")
    print(f"Average Response Time: {avg_response:.2f}ms")
    
    # Identify critical issues
    print("\n⚠️ CRITICAL ISSUES TO ADDRESS:")
    print("-" * 60)
    critical_issues = []
    
    for result in all_results:
        if result['avg_ms'] > 500:
            critical_issues.append(f"- {result['name']}: Extremely slow ({result['avg_ms']}ms avg)")
        elif result['errors'] > result['total_requests'] * 0.1:
            critical_issues.append(f"- {result['name']}: High error rate ({(result['errors']/result['total_requests']*100):.1f}%)")
    
    if critical_issues:
        for issue in critical_issues:
            print(issue)
    else:
        print("No critical issues found! System is performing well.")
    
    # Save detailed results to file
    with open('load_test_results.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print("\n✅ Detailed results saved to load_test_results.json")
    print("=" * 80)

if __name__ == "__main__":
    print("Starting comprehensive load test...")
    print("This will take several minutes to complete.\n")
    
    try:
        run_comprehensive_test()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()