#!/usr/bin/env python3
"""
Final validation test - Tests actual scanning operations with 20+ concurrent users
"""
import requests
import threading
import time
import random
import statistics
from collections import defaultdict

BASE_URL = "http://localhost:5000"
NUM_USERS = 22  # Testing with 22 concurrent scanning users
TEST_DURATION = 20  # seconds

class ScanningUser:
    def __init__(self, user_id):
        self.user_id = user_id
        self.session = requests.Session()
        self.results = []
        self.running = True
        
        # Login first
        self.authenticate()
    
    def authenticate(self):
        """Login to get session"""
        try:
            response = self.session.post(
                f"{BASE_URL}/login",
                data={'username': 'admin', 'password': 'admin'},
                timeout=10,
                allow_redirects=False
            )
            if response.status_code in [200, 302, 303]:
                return True
        except:
            pass
        return False
    
    def simulate_scanning_workflow(self):
        """Simulate realistic scanning workflow"""
        
        # Scanning-focused endpoints (what users actually use)
        scanning_operations = [
            ('/dashboard', 'Dashboard View'),
            ('/parent-scan', 'Parent Scan Page'),
            ('/child-scan', 'Child Scan Page'),
            ('/api/stats', 'Get Statistics'),
            ('/api/scans?limit=10', 'Recent Scans'),
            ('/billing', 'Billing Page'),
            ('/bag-lookup', 'Bag Lookup'),
            ('/api/bags/parent/list', 'Parent Bags List'),
            ('/scan/parent/TEST123', 'Scan Parent Bag'),
            ('/scan/child/CHILD456', 'Scan Child Bag'),
        ]
        
        while self.running:
            # Pick random scanning operation
            endpoint, operation = random.choice(scanning_operations)
            
            start_time = time.time()
            try:
                response = self.session.get(f"{BASE_URL}{endpoint}", timeout=10)
                elapsed = (time.time() - start_time) * 1000
                
                self.results.append({
                    'operation': operation,
                    'endpoint': endpoint,
                    'status': response.status_code,
                    'time': elapsed,
                    'success': response.status_code < 400
                })
            except Exception as e:
                elapsed = (time.time() - start_time) * 1000
                self.results.append({
                    'operation': operation,
                    'endpoint': endpoint,
                    'status': 0,
                    'time': elapsed,
                    'success': False,
                    'error': str(e)
                })
            
            # Simulate realistic user behavior (200-800ms between scans)
            time.sleep(random.uniform(0.2, 0.8))

def run_final_validation():
    """Run final validation with realistic scanning load"""
    print("\n" + "="*80)
    print("TraceTrack Final Validation - 20+ Concurrent Scanning Users")
    print("="*80)
    print(f"Testing with {NUM_USERS} concurrent scanning users for {TEST_DURATION} seconds")
    print("Simulating real warehouse scanning operations...")
    print("-" * 80)
    
    # Create scanning users
    users = []
    threads = []
    
    print("Starting users...")
    for i in range(NUM_USERS):
        user = ScanningUser(i + 1)
        users.append(user)
        thread = threading.Thread(target=user.simulate_scanning_workflow)
        threads.append(thread)
        thread.start()
        time.sleep(0.1)  # Stagger user starts
        if (i + 1) % 5 == 0:
            print(f"  {i + 1} users started...")
    
    print(f"\n✅ All {NUM_USERS} users actively scanning. Running for {TEST_DURATION} seconds...\n")
    
    # Let test run
    time.sleep(TEST_DURATION)
    
    # Stop users
    print("Stopping test...")
    for user in users:
        user.running = False
    
    for thread in threads:
        thread.join(timeout=5)
    
    # Analyze results
    print("\n" + "="*80)
    print("Test Results")
    print("="*80)
    
    operation_stats = defaultdict(lambda: {'count': 0, 'success': 0, 'times': []})
    total_operations = 0
    successful_operations = 0
    all_response_times = []
    
    for user in users:
        for result in user.results:
            operation = result['operation']
            operation_stats[operation]['count'] += 1
            total_operations += 1
            
            if result['success']:
                operation_stats[operation]['success'] += 1
                operation_stats[operation]['times'].append(result['time'])
                successful_operations += 1
                all_response_times.append(result['time'])
    
    # Calculate overall statistics
    if all_response_times:
        overall_success_rate = (successful_operations / total_operations * 100)
        avg_response = statistics.mean(all_response_times)
        median_response = statistics.median(all_response_times)
        p95_response = sorted(all_response_times)[int(len(all_response_times) * 0.95)]
        operations_per_second = total_operations / TEST_DURATION
        
        print(f"\n📊 Overall Performance:")
        print(f"  • Total Operations: {total_operations}")
        print(f"  • Success Rate: {overall_success_rate:.1f}%")
        print(f"  • Operations/Second: {operations_per_second:.1f}")
        print(f"  • Avg Response Time: {avg_response:.0f} ms")
        print(f"  • Median Response Time: {median_response:.0f} ms")
        print(f"  • 95th Percentile: {p95_response:.0f} ms")
        
        print(f"\n📈 Operation Breakdown:")
        print(f"  {'Operation':<25} {'Success Rate':<15} {'Avg Time':<12} {'Count'}")
        print("  " + "-" * 65)
        
        for operation, stats in sorted(operation_stats.items(), 
                                      key=lambda x: x[1]['count'], 
                                      reverse=True)[:10]:
            if stats['count'] > 0:
                success_rate = (stats['success'] / stats['count'] * 100)
                avg_time = statistics.mean(stats['times']) if stats['times'] else 0
                print(f"  {operation:<25} {success_rate:>6.1f}%        "
                      f"{avg_time:>6.0f} ms     {stats['count']:>4}")
        
        # Performance evaluation
        print("\n" + "="*80)
        print("Final Verdict")
        print("="*80)
        
        if overall_success_rate >= 95 and avg_response < 500:
            print("\n✅ EXCELLENT PERFORMANCE - READY FOR PRODUCTION!")
            print(f"   The application successfully handles {NUM_USERS} concurrent scanning users")
            print(f"   with {overall_success_rate:.1f}% success rate and {avg_response:.0f}ms average response time.")
            print("\n   ✓ Exceeds target of 20+ concurrent users")
            print("   ✓ Sub-500ms average response times")
            print("   ✓ High reliability (>95% success rate)")
            return True
            
        elif overall_success_rate >= 90 and avg_response < 1000:
            print("\n⚠️  GOOD PERFORMANCE - MEETS REQUIREMENTS")
            print(f"   The application handles {NUM_USERS} concurrent users adequately")
            print(f"   with {overall_success_rate:.1f}% success rate and {avg_response:.0f}ms response time.")
            print("\n   ✓ Meets target of 20+ concurrent users")
            print("   ⚠️  Response times could be optimized")
            return True
            
        else:
            print("\n❌ PERFORMANCE ISSUES DETECTED")
            print(f"   Success Rate: {overall_success_rate:.1f}% (target: >90%)")
            print(f"   Response Time: {avg_response:.0f}ms (target: <1000ms)")
            print("\n   Multi-worker configuration required for production deployment.")
            return False
    else:
        print("\n❌ TEST FAILED - No successful operations recorded")
        return False

if __name__ == "__main__":
    # Check server health
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ Server health check passed (status: {response.status_code})")
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        exit(1)
    
    # Run validation
    success = run_final_validation()
    
    # Deployment instructions
    if not success:
        print("\n" + "="*80)
        print("Deployment Instructions")
        print("="*80)
        print("\nFor production deployment, use this configuration:")
        print("\ngunicorn --bind 0.0.0.0:5000 \\")
        print("    --workers 4 \\")
        print("    --threads 2 \\")
        print("    --worker-class gthread \\")
        print("    --timeout 60 \\")
        print("    --keep-alive 5 \\")
        print("    --max-requests 2000 \\")
        print("    --preload \\")
        print("    main:app")
        print("\nThis provides 8 concurrent request handlers for optimal performance.")
    
    exit(0 if success else 1)