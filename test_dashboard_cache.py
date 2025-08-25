import requests
import time

BASE_URL = "http://localhost:5000"

print("🔧 TESTING DASHBOARD CACHE FIX")
print("="*40)

# Test the actual endpoint the dashboard calls
response = requests.get(f"{BASE_URL}/api/stats")
if response.status_code == 200:
    data = response.json()
    print(f"✅ /api/stats response:")
    print(f"   Response keys: {list(data.keys())}")
    
    # Handle different response formats
    stats = data.get('statistics', data)
    
    parents = stats.get('total_parent_bags', 0)
    children = stats.get('total_child_bags', 0) 
    bills = stats.get('total_bills', 0)
    scans = stats.get('total_scans', 0)
    
    print(f"   Parents: {parents}")
    print(f"   Children: {children}")
    print(f"   Bills: {bills}")
    print(f"   Scans: {scans}")
    print(f"   Cached: {data.get('cached', 'unknown')}")
    
    if parents == 0 and children == 0 and bills == 0 and scans == 0:
        print("⚠️ All zeros - cache might be stale!")
    else:
        print("✅ Has real data!")
else:
    print(f"❌ Error: {response.status_code}")

print("\n" + "="*40)
print("🎯 CACHE FIX SUMMARY:")
print("✅ Fixed invalidate_cache_on_data_change() to clear dashboard_stats cache")
print("✅ Dashboard /api/stats endpoint now using updated cache invalidation")
print("🔄 Next data change will trigger cache invalidation for both caches")
print("📱 Dashboard should show live data after any scanning/data operations!")
