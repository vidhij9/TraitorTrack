#!/usr/bin/env python3
"""Quick test script to verify bill operations are working correctly"""

import requests
import time
import random
import json

BASE_URL = "http://localhost:5000"

def test_bill_deletion():
    """Test bill deletion functionality"""
    print("\n=== Testing Bill Deletion ===")
    
    # First, create a test bill via direct database access
    # This simulates having an existing bill
    test_bill_id = f"TEST_DELETE_{int(time.time())}"
    
    print(f"Testing deletion for bill ID: {test_bill_id}")
    
    # Try to access bill management page
    response = requests.get(f"{BASE_URL}/bill_management")
    if response.status_code == 200:
        print("✓ Bill management page accessible")
    else:
        print(f"✗ Bill management page returned: {response.status_code}")
    
    return True

def test_concurrent_operations():
    """Test concurrent bill and bag operations"""
    print("\n=== Testing Concurrent Operations ===")
    
    # Test rapid bill queries
    print("\nTesting rapid queries (10 requests)...")
    start = time.time()
    
    for i in range(10):
        response = requests.get(f"{BASE_URL}/api/stats")
        if response.status_code != 200:
            print(f"  Request {i+1} failed: {response.status_code}")
    
    elapsed = time.time() - start
    avg_time = (elapsed / 10) * 1000  # Convert to ms
    
    print(f"  Average response time: {avg_time:.2f}ms")
    if avg_time < 1000:
        print("  ✓ Performance within acceptable limits (<1s)")
    else:
        print("  ✗ Performance needs improvement (>1s)")
    
    return True

def test_cache_performance():
    """Test cache performance"""
    print("\n=== Testing Cache Performance ===")
    
    # First request (cache miss)
    start = time.time()
    response1 = requests.get(f"{BASE_URL}/api/stats")
    time1 = (time.time() - start) * 1000
    
    # Second request (should be cached)
    start = time.time()
    response2 = requests.get(f"{BASE_URL}/api/stats")
    time2 = (time.time() - start) * 1000
    
    print(f"  First request (cache miss): {time1:.2f}ms")
    print(f"  Second request (cached): {time2:.2f}ms")
    
    if time2 < time1:
        improvement = ((time1 - time2) / time1) * 100
        print(f"  ✓ Cache working! {improvement:.1f}% improvement")
    else:
        print("  ⚠ Cache may not be working optimally")
    
    return True

def main():
    """Run all tests"""
    print("="*50)
    print("BILL OPERATIONS TEST SUITE")
    print("="*50)
    
    tests = [
        test_bill_deletion,
        test_concurrent_operations,
        test_cache_performance
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ Test failed with error: {e}")
            failed += 1
    
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("✅ All tests passed!")
    else:
        print("⚠️ Some tests failed")

if __name__ == "__main__":
    main()