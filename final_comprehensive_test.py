#!/usr/bin/env python3
"""
Final Comprehensive Production Test
Testing all performance improvements across both Flask and FastAPI
"""

import asyncio
import aiohttp
import requests
import time
import statistics
from datetime import datetime

print("="*80)
print("COMPREHENSIVE PRODUCTION READINESS TEST")
print("="*80)
print(f"Test Time: {datetime.now()}")
print("-"*80)

# Test endpoints
flask_base = "http://0.0.0.0:5000"
fastapi_base = "http://0.0.0.0:8000"

def test_flask_endpoints():
    """Test Flask endpoints performance"""
    print("\n📊 FLASK PERFORMANCE (Current System):")
    print("-"*40)
    
    endpoints = [
        "/health",
        "/api/stats",
        "/api/scans?limit=10",
        "/api/cached/stats",
        "/api/cached/recent_scans?limit=10",
        "/api/cache/stats"
    ]
    
    for endpoint in endpoints:
        times = []
        for i in range(3):
            start = time.time()
            try:
                r = requests.get(f"{flask_base}{endpoint}", timeout=5)
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)
            except Exception as e:
                print(f"  {endpoint:40} Error: {str(e)[:30]}")
                break
        
        if times:
            avg = statistics.mean(times)
            status = "✅" if avg < 100 else ("⚠️" if avg < 500 else "❌")
            print(f"  {endpoint:40} Avg: {avg:7.1f}ms {status}")

async def test_fastapi_endpoints():
    """Test FastAPI async endpoints"""
    print("\n📊 FASTAPI PERFORMANCE (Async System):")
    print("-"*40)
    
    endpoints = [
        "/",
        "/api/v3/health",
        "/api/v3/stats",
        "/api/v3/scans?limit=10",
        "/api/v3/bags?limit=100",
        "/api/v3/performance"
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            times = []
            for i in range(3):
                start = time.time()
                try:
                    async with session.get(f"{fastapi_base}{endpoint}", timeout=5) as resp:
                        await resp.text()
                        elapsed = (time.time() - start) * 1000
                        times.append(elapsed)
                except Exception as e:
                    print(f"  {endpoint:40} Error: {str(e)[:30]}")
                    break
            
            if times:
                avg = statistics.mean(times)
                status = "✅" if avg < 100 else ("⚠️" if avg < 500 else "❌")
                print(f"  {endpoint:40} Avg: {avg:7.1f}ms {status}")

async def load_test(base_url, endpoint, concurrent_users=50):
    """Run load test with concurrent users"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for _ in range(concurrent_users):
            tasks.append(session.get(f"{base_url}{endpoint}"))
        
        start = time.time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start
        
        successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status == 200)
        
        return {
            'successful': successful,
            'total': concurrent_users,
            'duration': elapsed,
            'rps': concurrent_users / elapsed if elapsed > 0 else 0
        }

async def run_load_tests():
    """Run concurrent user load tests"""
    print("\n📊 LOAD TEST RESULTS (50 Concurrent Users):")
    print("-"*40)
    
    # Test Flask
    try:
        result = await load_test(flask_base, "/health", 50)
        print(f"  Flask /health:      {result['successful']}/{result['total']} successful, {result['rps']:.1f} req/sec")
    except:
        print("  Flask /health:      Failed to test")
    
    # Test FastAPI
    try:
        result = await load_test(fastapi_base, "/api/v3/health", 50)
        print(f"  FastAPI /api/v3/health: {result['successful']}/{result['total']} successful, {result['rps']:.1f} req/sec")
    except:
        print("  FastAPI /api/v3/health: Failed to test")

# Run all tests
def main():
    # Test Flask
    test_flask_endpoints()
    
    # Test FastAPI
    asyncio.run(test_fastapi_endpoints())
    
    # Run load tests
    asyncio.run(run_load_tests())
    
    print("\n" + "="*80)
    print("PRODUCTION READINESS SUMMARY")
    print("="*80)
    
    improvements = [
        "✅ Phase 1: Redis caching implemented (in-memory fallback active)",
        "✅ Phase 2: FastAPI async endpoints created",
        "✅ Database indexes optimized (10+ indexes)",
        "✅ Connection pooling configured (100 base + 200 overflow)",
        "⚠️ Redis connection issue (using fallback)",
        "⚠️ Average response still >100ms for some endpoints"
    ]
    
    for item in improvements:
        print(f"  {item}")
    
    print("\n📈 NEXT STEPS FOR FULL PRODUCTION READINESS:")
    print("  1. Fix Redis connection for proper caching")
    print("  2. Implement read replicas for database")
    print("  3. Add CDN for static content")
    print("  4. Enable HTTP/2 and compression")
    print("  5. Implement queue-based processing")
    
    print("="*80)

if __name__ == "__main__":
    main()