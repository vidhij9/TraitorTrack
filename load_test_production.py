"""
Load Testing Script for TraceTrack Production
Tests system capacity for 50+ concurrent users
"""

import requests
import concurrent.futures
import time
import statistics
import json
from datetime import datetime

class LoadTester:
    """Load test the production system"""
    
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url
        self.results = []
        
    def simulate_user_workflow(self, user_id):
        """Simulate a complete user workflow"""
        session = requests.Session()
        workflow_times = {}
        
        try:
            # 1. Login
            start = time.time()
            response = session.post(
                f'{self.base_url}/login',
                data={'username': 'admin', 'password': 'admin123'},
                timeout=15
            )
            workflow_times['login'] = time.time() - start
            
            if response.status_code not in [200, 302]:
                return {'user_id': user_id, 'success': False, 'error': 'Login failed'}
            
            # 2. Parent bag scan
            start = time.time()
            response = session.post(
                f'{self.base_url}/process_parent_scan',
                data={'qr_code': f'PARENT-{user_id:05d}', 'location': 'LoadTest'},
                headers={'X-Requested-With': 'XMLHttpRequest'},
                timeout=15
            )
            workflow_times['parent_scan'] = time.time() - start
            
            # 3. Child bag scan
            start = time.time()
            response = session.post(
                f'{self.base_url}/process_child_scan',
                data={'qr_code': f'CHILD-{user_id:05d}'},
                headers={'X-Requested-With': 'XMLHttpRequest'},
                timeout=15
            )
            workflow_times['child_scan'] = time.time() - start
            
            # 4. Bill creation
            start = time.time()
            response = session.post(
                f'{self.base_url}/bill/create',
                data={
                    'bill_id': f'LOAD-TEST-{user_id}-{int(time.time())}',
                    'parent_bag_count': '10'
                },
                headers={'X-Requested-With': 'XMLHttpRequest'},
                timeout=15
            )
            workflow_times['bill_create'] = time.time() - start
            
            # Calculate total time
            workflow_times['total'] = sum(workflow_times.values())
            
            return {
                'user_id': user_id,
                'success': True,
                'times': workflow_times
            }
            
        except Exception as e:
            return {
                'user_id': user_id,
                'success': False,
                'error': str(e)[:100]
            }
    
    def run_load_test(self, num_users, max_workers=50):
        """Run load test with specified number of concurrent users"""
        print(f"\n🚀 Starting load test with {num_users} concurrent users")
        print("="*60)
        
        start_time = time.time()
        
        # Execute concurrent user simulations
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(num_users, max_workers)) as executor:
            # Stagger user starts slightly to avoid thundering herd
            futures = []
            for i in range(num_users):
                if i > 0 and i % 10 == 0:
                    time.sleep(0.5)  # Small delay every 10 users
                futures.append(executor.submit(self.simulate_user_workflow, i))
            
            # Collect results
            results = []
            for future in concurrent.futures.as_completed(futures, timeout=120):
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append({'success': False, 'error': str(e)})
        
        elapsed = time.time() - start_time
        
        # Analyze results
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]
        
        analysis = {
            'total_users': num_users,
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': (len(successful) / num_users * 100) if num_users > 0 else 0,
            'total_time': round(elapsed, 2),
            'throughput': round(len(successful) / elapsed, 2) if elapsed > 0 else 0
        }
        
        if successful:
            all_times = [r['times']['total'] for r in successful]
            analysis['response_times'] = {
                'min': round(min(all_times), 2),
                'max': round(max(all_times), 2),
                'avg': round(statistics.mean(all_times), 2),
                'median': round(statistics.median(all_times), 2)
            }
            
            # Operation breakdown
            operations = ['login', 'parent_scan', 'child_scan', 'bill_create']
            analysis['operation_times'] = {}
            for op in operations:
                op_times = [r['times'][op] for r in successful if op in r['times']]
                if op_times:
                    analysis['operation_times'][op] = round(statistics.mean(op_times), 2)
        
        return analysis
    
    def progressive_load_test(self):
        """Run progressive load test to find system limits"""
        test_scenarios = [
            (1, "Baseline"),
            (5, "Light Load"),
            (10, "Moderate Load"),
            (25, "Heavy Load"),
            (50, "Target Load"),
            (75, "Stress Test"),
            (100, "Maximum Load")
        ]
        
        all_results = []
        
        print("\n📊 PROGRESSIVE LOAD TEST")
        print("="*60)
        
        for num_users, scenario in test_scenarios:
            print(f"\n🔬 Testing: {scenario} ({num_users} users)")
            print("-"*40)
            
            results = self.run_load_test(num_users)
            results['scenario'] = scenario
            all_results.append(results)
            
            # Display results
            print(f"✅ Success Rate: {results['success_rate']:.1f}%")
            print(f"⏱️  Total Time: {results['total_time']}s")
            print(f"📈 Throughput: {results['throughput']} users/sec")
            
            if 'response_times' in results:
                rt = results['response_times']
                print(f"⚡ Response Times: Min={rt['min']}s, Avg={rt['avg']}s, Max={rt['max']}s")
                
                # Check if meeting targets
                if rt['avg'] < 2.0:
                    print("🎯 PASS: Meeting <2s response time target")
                else:
                    print(f"⚠️  FAIL: Response time {rt['avg']}s exceeds 2s target")
            
            # Stop if success rate drops below 50%
            if results['success_rate'] < 50:
                print("\n❌ Stopping test - success rate below 50%")
                break
            
            # Brief pause between scenarios
            if num_users < 100:
                time.sleep(2)
        
        # Save results
        with open('load_test_results.json', 'w') as f:
            json.dump(all_results, f, indent=2)
        
        # Final assessment
        print("\n" + "="*60)
        print("📊 LOAD TEST SUMMARY")
        print("="*60)
        
        max_successful = max([r['successful'] for r in all_results])
        best_scenario = [r for r in all_results if r['successful'] == max_successful][0]
        
        print(f"🏆 Best Performance: {best_scenario['scenario']}")
        print(f"   - {best_scenario['successful']} concurrent users")
        print(f"   - {best_scenario['success_rate']:.1f}% success rate")
        print(f"   - {best_scenario['throughput']:.2f} users/sec throughput")
        
        if max_successful >= 50:
            print("\n✅ SUCCESS: System can handle 50+ concurrent users!")
        elif max_successful >= 25:
            print("\n⚠️  PARTIAL: System handles 25+ users, needs optimization for 50+")
        else:
            print("\n❌ NEEDS IMPROVEMENT: System capacity below 25 concurrent users")
        
        return all_results

if __name__ == "__main__":
    import sys
    
    # Parse arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--progressive':
            tester = LoadTester()
            tester.progressive_load_test()
        else:
            num_users = int(sys.argv[1])
            tester = LoadTester()
            results = tester.run_load_test(num_users)
            print("\n📊 Load Test Results:")
            print(json.dumps(results, indent=2))
    else:
        print("Usage:")
        print("  python load_test_production.py <num_users>  # Test with specific number")
        print("  python load_test_production.py --progressive  # Progressive load test")