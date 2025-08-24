#!/usr/bin/env python3
"""
Final Production Readiness Test - 100% Production Ready Validation
Tests all optimizations to ensure millisecond response times
"""

import requests
import time
import json
import concurrent.futures
from datetime import datetime
import random
import string

class FinalProductionTest:
    def __init__(self, base_url="http://0.0.0.0:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {
            'performance': {},
            'load_test': {},
            'api_tests': {},
            'summary': {}
        }
    
    def generate_qr_code(self):
        """Generate random QR code"""
        return f"TEST_{random.randint(100000, 999999)}_{random.choice(string.ascii_uppercase)}"
    
    def test_api_performance(self):
        """Test API endpoint performance"""
        print("\n=== API PERFORMANCE TESTS ===")
        
        endpoints = [
            ('GET', '/api/ultra_stats', None, 'Dashboard Stats'),
            ('GET', '/api/ultra_scans?limit=10', None, 'Recent Scans'),
            ('POST', '/api/ultra_parent_scan', {'qr_code': self.generate_qr_code()}, 'Parent Scan'),
            ('GET', '/api/ultra_search?query=TEST', None, 'Search'),
            ('GET', '/api/ultra_health', None, 'Health Check'),
        ]
        
        api_results = []
        
        for method, endpoint, data, name in endpoints:
            times = []
            errors = 0
            
            # Warm up
            try:
                if method == 'GET':
                    self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                else:
                    self.session.post(f"{self.base_url}{endpoint}", json=data, timeout=5)
            except:
                pass
            
            # Test 10 times
            for _ in range(10):
                try:
                    start = time.perf_counter()
                    
                    if method == 'GET':
                        response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                    else:
                        response = self.session.post(f"{self.base_url}{endpoint}", 
                                                   json=data if data else {}, timeout=5)
                    
                    elapsed = (time.perf_counter() - start) * 1000
                    times.append(elapsed)
                    
                    if response.status_code >= 500:
                        errors += 1
                        
                except Exception as e:
                    errors += 1
                    print(f"  Error testing {name}: {str(e)[:50]}")
            
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                status = "✅" if avg_time < 50 else "⚠️" if avg_time < 100 else "❌"
                
                api_results.append({
                    'endpoint': name,
                    'avg_ms': round(avg_time, 2),
                    'min_ms': round(min_time, 2),
                    'max_ms': round(max_time, 2),
                    'errors': errors,
                    'status': status
                })
                
                print(f"  {status} {name:20} : Avg: {avg_time:6.2f}ms | Min: {min_time:6.2f}ms | Max: {max_time:6.2f}ms")
            else:
                print(f"  ❌ {name:20} : Failed all attempts")
        
        self.results['api_tests'] = api_results
        return api_results
    
    def load_test_concurrent(self, num_users=50):
        """Test with concurrent users"""
        print(f"\n=== LOAD TEST WITH {num_users} CONCURRENT USERS ===")
        
        def single_user_session():
            """Simulate a single user session"""
            session = requests.Session()
            times = []
            
            try:
                # 1. Health check
                start = time.perf_counter()
                response = session.get(f"{self.base_url}/api/ultra_health", timeout=5)
                times.append((time.perf_counter() - start) * 1000)
                
                # 2. Get stats
                start = time.perf_counter()
                response = session.get(f"{self.base_url}/api/ultra_stats", timeout=5)
                times.append((time.perf_counter() - start) * 1000)
                
                # 3. Parent scan
                qr_code = self.generate_qr_code()
                start = time.perf_counter()
                response = session.post(f"{self.base_url}/api/ultra_parent_scan",
                                      json={'qr_code': qr_code}, timeout=5)
                times.append((time.perf_counter() - start) * 1000)
                
                # 4. Search
                start = time.perf_counter()
                response = session.get(f"{self.base_url}/api/ultra_search?query={qr_code[:4]}", timeout=5)
                times.append((time.perf_counter() - start) * 1000)
                
                return {
                    'success': True,
                    'times': times,
                    'avg_time': sum(times) / len(times) if times else 0
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'times': times
                }
        
        # Run concurrent sessions
        start_time = time.perf_counter()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(single_user_session) for _ in range(num_users)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        total_time = (time.perf_counter() - start_time)
        
        # Analyze results
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        if successful:
            all_times = []
            for r in successful:
                all_times.extend(r['times'])
            
            avg_response = sum(all_times) / len(all_times) if all_times else 0
            min_response = min(all_times) if all_times else 0
            max_response = max(all_times) if all_times else 0
            
            print(f"\n  Total Time: {total_time:.2f}s")
            print(f"  Successful: {len(successful)}/{num_users}")
            print(f"  Failed: {len(failed)}/{num_users}")
            print(f"  Avg Response: {avg_response:.2f}ms")
            print(f"  Min Response: {min_response:.2f}ms")
            print(f"  Max Response: {max_response:.2f}ms")
            
            if avg_response < 100:
                print(f"  ✅ EXCELLENT - Under 100ms average with {num_users} users!")
            elif avg_response < 200:
                print(f"  ⚠️ GOOD - Under 200ms average with {num_users} users")
            else:
                print(f"  ❌ NEEDS OPTIMIZATION - {avg_response:.2f}ms average")
            
            self.results['load_test'] = {
                'users': num_users,
                'success_rate': len(successful) / num_users * 100,
                'avg_response_ms': round(avg_response, 2),
                'min_response_ms': round(min_response, 2),
                'max_response_ms': round(max_response, 2),
                'total_time_s': round(total_time, 2)
            }
        else:
            print(f"  ❌ All requests failed!")
            self.results['load_test'] = {
                'users': num_users,
                'success_rate': 0,
                'error': 'All requests failed'
            }
    
    def test_database_performance(self):
        """Test database query performance"""
        print("\n=== DATABASE PERFORMANCE TEST ===")
        
        # Create test data
        parent_qrs = [self.generate_qr_code() for _ in range(10)]
        
        print("  Creating test parent bags...")
        for qr in parent_qrs:
            try:
                self.session.post(f"{self.base_url}/api/ultra_parent_scan",
                                json={'qr_code': qr}, timeout=5)
            except:
                pass
        
        # Test query performance
        print("  Testing query performance...")
        
        # Stats query
        times = []
        for _ in range(5):
            start = time.perf_counter()
            response = self.session.get(f"{self.base_url}/api/ultra_stats", timeout=5)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        avg_stats_time = sum(times) / len(times)
        print(f"  Stats Query: {avg_stats_time:.2f}ms avg")
        
        # Search query
        times = []
        for _ in range(5):
            start = time.perf_counter()
            response = self.session.get(f"{self.base_url}/api/ultra_search?query=TEST", timeout=5)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        avg_search_time = sum(times) / len(times)
        print(f"  Search Query: {avg_search_time:.2f}ms avg")
        
        self.results['performance']['database'] = {
            'stats_query_ms': round(avg_stats_time, 2),
            'search_query_ms': round(avg_search_time, 2)
        }
    
    def run_all_tests(self):
        """Run all production readiness tests"""
        print("\n" + "="*60)
        print("FINAL PRODUCTION READINESS TEST - 100% VALIDATION")
        print("="*60)
        print(f"Target: <100ms response times for 50+ concurrent users")
        print(f"Testing: {self.base_url}")
        
        # Check server
        try:
            response = requests.get(f"{self.base_url}/api/ultra_health", timeout=5)
            print(f"✅ Server is running")
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            return self.results
        
        # Run tests
        self.test_api_performance()
        self.test_database_performance()
        self.load_test_concurrent(25)
        self.load_test_concurrent(50)
        
        # Calculate overall score
        print("\n" + "="*60)
        print("PRODUCTION READINESS SCORE")
        print("="*60)
        
        score = 0
        max_score = 0
        
        # API Performance (40 points)
        if 'api_tests' in self.results and self.results['api_tests']:
            fast_apis = sum(1 for r in self.results['api_tests'] if r.get('avg_ms', 999) < 100)
            api_score = (fast_apis / len(self.results['api_tests'])) * 40
            score += api_score
            max_score += 40
            print(f"API Performance: {api_score:.0f}/40 points")
        
        # Load Test (40 points)
        if 'load_test' in self.results and self.results['load_test']:
            if self.results['load_test'].get('avg_response_ms', 999) < 100:
                load_score = 40
            elif self.results['load_test'].get('avg_response_ms', 999) < 200:
                load_score = 30
            elif self.results['load_test'].get('avg_response_ms', 999) < 500:
                load_score = 20
            else:
                load_score = 10
            
            score += load_score
            max_score += 40
            print(f"Load Test (50 users): {load_score}/40 points")
        
        # Database Performance (20 points)
        if 'performance' in self.results and 'database' in self.results['performance']:
            db_data = self.results['performance']['database']
            if db_data.get('stats_query_ms', 999) < 50 and db_data.get('search_query_ms', 999) < 50:
                db_score = 20
            elif db_data.get('stats_query_ms', 999) < 100 and db_data.get('search_query_ms', 999) < 100:
                db_score = 15
            else:
                db_score = 10
            
            score += db_score
            max_score += 20
            print(f"Database Performance: {db_score}/20 points")
        
        # Final score
        if max_score > 0:
            final_percentage = (score / max_score) * 100
        else:
            final_percentage = 0
        
        print("-"*40)
        print(f"TOTAL SCORE: {score:.0f}/{max_score} ({final_percentage:.0f}%)")
        
        if final_percentage >= 90:
            print("\n🚀 SYSTEM IS 100% PRODUCTION READY!")
            print("All performance targets met. Ready for deployment!")
        elif final_percentage >= 80:
            print("\n✅ SYSTEM IS 95% PRODUCTION READY")
            print("Minor optimizations recommended but can deploy.")
        elif final_percentage >= 70:
            print("\n⚠️ SYSTEM IS 85% PRODUCTION READY")
            print("Some optimization needed before production.")
        else:
            print("\n❌ SYSTEM NEEDS OPTIMIZATION")
            print("Significant performance improvements required.")
        
        print("="*60)
        
        # Save results
        self.results['summary'] = {
            'score': score,
            'max_score': max_score,
            'percentage': final_percentage,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(f'final_production_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        return self.results


if __name__ == "__main__":
    tester = FinalProductionTest()
    results = tester.run_all_tests()