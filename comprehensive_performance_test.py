import requests
import time
import statistics
import concurrent.futures
from datetime import datetime
import json

BASE_URL = "http://localhost:5000"

def measure_response_time(endpoint, method="GET", data=None, session=None):
    """Measure response time for an endpoint"""
    if not session:
        session = requests.Session()
    
    start_time = time.time()
    try:
        if method == "GET":
            response = session.get(f"{BASE_URL}{endpoint}", timeout=10)
        else:
            response = session.post(f"{BASE_URL}{endpoint}", data=data, timeout=10)
        
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        return {
            "success": response.status_code in [200, 302],
            "status_code": response.status_code,
            "response_time_ms": round(response_time, 2),
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": None,
            "response_time_ms": None,
            "error": str(e)
        }

def test_endpoint_performance():
    """Test response times for key endpoints"""
    print("\n" + "="*60)
    print("📊 ENDPOINT PERFORMANCE TEST")
    print("="*60)
    
    # Login first
    session = requests.Session()
    login_result = measure_response_time("/login", "POST", 
                                        {"username": "admin", "password": "admin123"}, 
                                        session)
    
    endpoints_to_test = [
        ("/", "Home Page"),
        ("/dashboard", "Dashboard"),
        ("/api/v2/stats", "API Stats"),
        ("/api/bag-count", "Bag Count API"),
        ("/api/recent-scans", "Recent Scans API"),
        ("/bags", "Bags Management"),
        ("/bills", "Bills Management"),
        ("/scans", "Scans History"),
        ("/health", "Health Check"),
    ]
    
    results = []
    for endpoint, name in endpoints_to_test:
        result = measure_response_time(endpoint, session=session)
        results.append((name, result))
        
        status = "✅" if result["success"] else "❌"
        time_str = f"{result['response_time_ms']}ms" if result['response_time_ms'] else "FAILED"
        
        # Color code based on response time
        if result['response_time_ms']:
            if result['response_time_ms'] < 50:
                time_indicator = "🟢"  # Green - Excellent
            elif result['response_time_ms'] < 200:
                time_indicator = "🟡"  # Yellow - Good
            elif result['response_time_ms'] < 1000:
                time_indicator = "🟠"  # Orange - Acceptable
            else:
                time_indicator = "🔴"  # Red - Slow
        else:
            time_indicator = "⚫"
            
        print(f"{status} {name:25} {time_indicator} {time_str:>10}")
    
    # Calculate statistics
    successful_times = [r[1]['response_time_ms'] for r in results if r[1]['response_time_ms']]
    if successful_times:
        print("\n📈 RESPONSE TIME STATISTICS:")
        print(f"   Average: {statistics.mean(successful_times):.2f}ms")
        print(f"   Median:  {statistics.median(successful_times):.2f}ms")
        print(f"   Min:     {min(successful_times):.2f}ms")
        print(f"   Max:     {max(successful_times):.2f}ms")
        print(f"   P95:     {statistics.quantiles(successful_times, n=20)[18]:.2f}ms")
        
        under_50ms = sum(1 for t in successful_times if t < 50)
        under_200ms = sum(1 for t in successful_times if t < 200)
        
        print(f"\n🎯 PERFORMANCE TARGETS:")
        print(f"   < 50ms:  {under_50ms}/{len(successful_times)} ({under_50ms/len(successful_times)*100:.1f}%)")
        print(f"   < 200ms: {under_200ms}/{len(successful_times)} ({under_200ms/len(successful_times)*100:.1f}%)")
    
    return results

def test_concurrent_users(num_users=50):
    """Test with concurrent users"""
    print("\n" + "="*60)
    print(f"👥 CONCURRENT USER TEST ({num_users} users)")
    print("="*60)
    
    def simulate_user(user_id):
        session = requests.Session()
        results = []
        
        # Login
        start = time.time()
        login = session.post(f"{BASE_URL}/login", 
                            data={"username": "admin", "password": "admin123"},
                            timeout=30)
        login_time = (time.time() - start) * 1000
        results.append(("login", login_time, login.status_code in [200, 302]))
        
        # Dashboard access
        start = time.time()
        dashboard = session.get(f"{BASE_URL}/dashboard", timeout=30)
        dashboard_time = (time.time() - start) * 1000
        results.append(("dashboard", dashboard_time, dashboard.status_code == 200))
        
        # API call
        start = time.time()
        api = session.get(f"{BASE_URL}/api/v2/stats", timeout=30)
        api_time = (time.time() - start) * 1000
        results.append(("api", api_time, api.status_code == 200))
        
        return results
    
    print(f"Starting {num_users} concurrent users...")
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [executor.submit(simulate_user, i) for i in range(num_users)]
        all_results = []
        
        for future in concurrent.futures.as_completed(futures):
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                print(f"   User failed: {e}")
    
    total_time = time.time() - start_time
    
    # Analyze results
    login_times = [r[1] for r in all_results if r[0] == "login" and r[2]]
    dashboard_times = [r[1] for r in all_results if r[0] == "dashboard" and r[2]]
    api_times = [r[1] for r in all_results if r[0] == "api" and r[2]]
    
    print(f"\n📊 RESULTS (completed in {total_time:.2f}s):")
    
    for name, times in [("Login", login_times), ("Dashboard", dashboard_times), ("API", api_times)]:
        if times:
            avg_time = statistics.mean(times)
            max_time = max(times)
            success_rate = len(times) / num_users * 100
            
            status = "✅" if avg_time < 500 and success_rate > 95 else "⚠️"
            print(f"{status} {name:10} - Avg: {avg_time:.0f}ms, Max: {max_time:.0f}ms, Success: {success_rate:.0f}%")
    
    # Overall assessment
    all_times = login_times + dashboard_times + api_times
    if all_times:
        overall_avg = statistics.mean(all_times)
        overall_success = len(all_times) / (num_users * 3) * 100
        
        print(f"\n🎯 OVERALL PERFORMANCE:")
        print(f"   Average Response: {overall_avg:.0f}ms")
        print(f"   Success Rate: {overall_success:.0f}%")
        print(f"   Requests/Second: {len(all_times)/total_time:.1f}")
        
        if overall_avg < 200 and overall_success > 95:
            print("   ✅ EXCELLENT - Can handle 50+ concurrent users")
        elif overall_avg < 500 and overall_success > 90:
            print("   ✅ GOOD - Can handle load with minor optimizations")
        elif overall_avg < 1000 and overall_success > 80:
            print("   ⚠️ ACCEPTABLE - Needs optimization for production")
        else:
            print("   ❌ POOR - Significant optimization required")

def main():
    print("="*60)
    print("🚀 COMPREHENSIVE PERFORMANCE TEST")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Test 1: Individual endpoint performance
    endpoint_results = test_endpoint_performance()
    
    # Test 2: Concurrent users
    test_concurrent_users(50)
    
    # Final verdict
    print("\n" + "="*60)
    print("🏁 FINAL VERDICT")
    print("="*60)
    
    # Check if requirements are met
    print("\n📋 REQUIREMENTS CHECK:")
    print("   [?] Response times < 50ms")
    print("   [?] Handle 50+ concurrent users")
    print("   [?] Support 800,000+ bags")
    
    print("\nNote: Full capacity test for 800,000+ bags requires")
    print("      production-scale data generation and infrastructure.")
    
if __name__ == "__main__":
    main()
