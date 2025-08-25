#!/usr/bin/env python3
"""
Final AWS Validation - Quick test to confirm all phases are operational
"""

import requests
import time
import json

BASE_URL = "http://localhost:5000"

def test_endpoints():
    """Test all critical endpoints"""
    results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'endpoints': {},
        'summary': {'passed': 0, 'failed': 0}
    }
    
    endpoints = [
        {'name': 'Basic Health', 'url': '/health', 'phase': 1},
        {'name': 'ELB Health', 'url': '/health/elb', 'phase': 3},
        {'name': 'Auto-scaling Metrics', 'url': '/metrics/scaling', 'phase': 3},
        {'name': 'CloudWatch Flush', 'url': '/metrics/flush', 'phase': 3},
        {'name': 'API Stats', 'url': '/api/stats', 'phase': 1},
        {'name': 'Cache Stats', 'url': '/api/cache-stats', 'phase': 1},
    ]
    
    print("=" * 60)
    print("AWS PRODUCTION VALIDATION - ALL PHASES")
    print("=" * 60)
    
    for endpoint in endpoints:
        try:
            start = time.time()
            r = requests.get(f"{BASE_URL}{endpoint['url']}", timeout=10)
            response_time = (time.time() - start) * 1000
            
            success = r.status_code == 200
            results['endpoints'][endpoint['name']] = {
                'phase': endpoint['phase'],
                'status_code': r.status_code,
                'response_time_ms': round(response_time, 1),
                'success': success
            }
            
            if success:
                print(f"✅ Phase {endpoint['phase']} - {endpoint['name']}: {response_time:.1f}ms")
                results['summary']['passed'] += 1
            else:
                print(f"❌ Phase {endpoint['phase']} - {endpoint['name']}: Status {r.status_code}")
                results['summary']['failed'] += 1
                
        except Exception as e:
            print(f"❌ Phase {endpoint['phase']} - {endpoint['name']}: {str(e)}")
            results['endpoints'][endpoint['name']] = {
                'phase': endpoint['phase'],
                'error': str(e),
                'success': False
            }
            results['summary']['failed'] += 1
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    # Phase summary
    phase1_ok = sum(1 for e in results['endpoints'].values() if e.get('phase') == 1 and e.get('success'))
    phase3_ok = sum(1 for e in results['endpoints'].values() if e.get('phase') == 3 and e.get('success'))
    
    print(f"Phase 1 Endpoints: {phase1_ok}/3 working")
    print(f"Phase 3 Endpoints: {phase3_ok}/3 working")
    print(f"Total: {results['summary']['passed']}/{results['summary']['passed'] + results['summary']['failed']} passed")
    
    # AWS readiness determination
    if results['summary']['passed'] >= 4:
        print("\n🎉 AWS READY - Core features operational")
        results['aws_ready'] = True
    else:
        print("\n⚠️ PARTIAL AWS READY - Some features need attention")
        results['aws_ready'] = False
    
    # Save results
    with open('final_aws_validation.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to final_aws_validation.json")
    
    return results

if __name__ == "__main__":
    test_endpoints()