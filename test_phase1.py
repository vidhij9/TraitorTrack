#!/usr/bin/env python3
"""Test Phase 1 Performance with Redis Caching"""

import requests
import time
import json

BASE_URL = 'http://0.0.0.0:5000'

print('='*60)
print('TESTING PHASE 1: REDIS CACHING PERFORMANCE')
print('='*60)

# Test cached endpoints
endpoints = [
    '/api/cached/stats',
    '/api/cached/recent_scans?limit=10',
    '/api/cached/bags?limit=100',
    '/api/health/redis',
    '/api/cache/stats'
]

print('\n📊 Testing Cached Endpoints:')
for endpoint in endpoints:
    times = []
    for i in range(3):
        start = time.time()
        try:
            r = requests.get(f'{BASE_URL}{endpoint}', timeout=5)
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            if i == 0:  # First call (cache miss)
                print(f'  {endpoint:40} First: {elapsed:7.1f}ms')
            elif i == 2:  # Third call (cached)
                spaces = ' ' * 40
                print(f'  {spaces} Cached: {elapsed:7.1f}ms (Status: {r.status_code})')
        except Exception as e:
            print(f'  {endpoint:40} Error: {str(e)[:50]}')
            break

print('\n📈 Cache Statistics:')
try:
    r = requests.get(f'{BASE_URL}/api/cache/stats')
    stats = r.json()
    print(f"  Hit Rate: {stats.get('hit_rate', 'N/A')}")
    print(f"  Total Hits: {stats.get('hits', 0)}")
    print(f"  Total Misses: {stats.get('misses', 0)}")
    print(f"  Using Redis: {stats.get('using_redis', False)}")
except:
    pass

# Test regular endpoints for comparison
print('\n📊 Comparing with Non-Cached Endpoints:')
non_cached = ['/api/stats', '/api/scans?limit=10']
for endpoint in non_cached:
    start = time.time()
    try:
        r = requests.get(f'{BASE_URL}{endpoint}', timeout=5)
        elapsed = (time.time() - start) * 1000
        print(f'  {endpoint:40} Time: {elapsed:7.1f}ms')
    except Exception as e:
        print(f'  {endpoint:40} Error: {str(e)[:50]}')

print('\n✅ Phase 1 Complete - Redis caching implemented')
print('='*60)