#!/usr/bin/env python3
"""
Comprehensive Performance Testing for TraceTrack Application
Tests application performance under various load conditions
"""

import time
import json
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import psutil
import os
import sys
from datetime import datetime

class PerformanceTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.results = {}
        self.start_time = None
        self.end_time = None
        
    def test_single_request(self, endpoint="/"):
        """Test a single request to an endpoint"""
        try:
            start = time.time()
            response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
            end = time.time()
            
            return {
                'status_code': response.status_code,
                'response_time': end - start,
                'success': response.status_code < 400,
                'size': len(response.content)
            }
        except Exception as e:
            return {
                'status_code': 0,
                'response_time': 10.0,  # Default timeout
                'success': False,
                'error': str(e)
            }
    
    def test_concurrent_requests(self, endpoint="/", num_requests=10, max_workers=5):
        """Test concurrent requests"""
        print(f"Testing {num_requests} concurrent requests to {endpoint} with {max_workers} workers...")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.test_single_request, endpoint) for _ in range(num_requests)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        
        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]
        
        if successful_requests:
            response_times = [r['response_time'] for r in successful_requests]
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            median_response_time = statistics.median(response_times)
        else:
            avg_response_time = min_response_time = max_response_time = median_response_time = 0
        
        return {
            'total_requests': num_requests,
            'successful_requests': len(successful_requests),
            'failed_requests': len(failed_requests),
            'success_rate': len(successful_requests) / num_requests,
            'total_time': end_time - start_time,
            'requests_per_second': num_requests / (end_time - start_time),
            'avg_response_time': avg_response_time,
            'min_response_time': min_response_time,
            'max_response_time': max_response_time,
            'median_response_time': median_response_time,
            'failed_details': failed_requests
        }
    
    def test_load_scenarios(self):
        """Test various load scenarios"""
        scenarios = [
            {'name': 'Light Load', 'requests': 10, 'workers': 2},
            {'name': 'Medium Load', 'requests': 50, 'workers': 5},
            {'name': 'Heavy Load', 'requests': 100, 'workers': 10},
            {'name': 'Stress Test', 'requests': 200, 'workers': 20},
        ]
        
        endpoints = ['/', '/login', '/register']
        
        for scenario in scenarios:
            print(f"\n{'='*60}")
            print(f"🧪 Testing {scenario['name']}")
            print(f"{'='*60}")
            
            scenario_results = {}
            
            for endpoint in endpoints:
                print(f"\n📊 Testing endpoint: {endpoint}")
                result = self.test_concurrent_requests(
                    endpoint=endpoint,
                    num_requests=scenario['requests'],
                    max_workers=scenario['workers']
                )
                scenario_results[endpoint] = result
                
                print(f"✅ {endpoint}:")
                print(f"   Success Rate: {result['success_rate']:.1%}")
                print(f"   Avg Response Time: {result['avg_response_time']:.3f}s")
                print(f"   Requests/Second: {result['requests_per_second']:.1f}")
                print(f"   Failed Requests: {result['failed_requests']}")
            
            self.results[scenario['name']] = scenario_results
    
    def test_memory_usage(self):
        """Test memory usage under load"""
        print(f"\n{'='*60}")
        print("🧠 Testing Memory Usage")
        print(f"{'='*60}")
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"Initial memory usage: {initial_memory:.2f} MB")
        
        # Make many requests to test memory usage
        memory_samples = []
        
        for i in range(10):
            # Make 10 requests
            for _ in range(10):
                self.test_single_request('/')
            
            # Check memory
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            print(f"After {i+1}0 requests: {current_memory:.2f} MB")
        
        final_memory = memory_samples[-1]
        memory_increase = final_memory - initial_memory
        
        self.results['Memory Usage'] = {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_increase_mb': memory_increase,
            'memory_samples': memory_samples,
            'avg_memory_usage': statistics.mean(memory_samples)
        }
        
        print(f"Final memory usage: {final_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")
    
    def test_response_time_distribution(self):
        """Test response time distribution"""
        print(f"\n{'='*60}")
        print("⏱️ Testing Response Time Distribution")
        print(f"{'='*60}")
        
        # Make 100 requests and collect response times
        response_times = []
        
        for i in range(100):
            result = self.test_single_request('/')
            if result['success']:
                response_times.append(result['response_time'])
            
            if (i + 1) % 20 == 0:
                print(f"Completed {i + 1}/100 requests...")
        
        if response_times:
            self.results['Response Time Distribution'] = {
                'count': len(response_times),
                'mean': statistics.mean(response_times),
                'median': statistics.median(response_times),
                'min': min(response_times),
                'max': max(response_times),
                'std_dev': statistics.stdev(response_times) if len(response_times) > 1 else 0,
                'percentile_95': sorted(response_times)[int(len(response_times) * 0.95)],
                'percentile_99': sorted(response_times)[int(len(response_times) * 0.99)],
                'all_times': response_times
            }
            
            print(f"Response Time Statistics:")
            print(f"  Count: {len(response_times)}")
            print(f"  Mean: {statistics.mean(response_times):.3f}s")
            print(f"  Median: {statistics.median(response_times):.3f}s")
            print(f"  Min: {min(response_times):.3f}s")
            print(f"  Max: {max(response_times):.3f}s")
            print(f"  95th Percentile: {self.results['Response Time Distribution']['percentile_95']:.3f}s")
            print(f"  99th Percentile: {self.results['Response Time Distribution']['percentile_99']:.3f}s")
    
    def test_endurance(self):
        """Test application endurance over time"""
        print(f"\n{'='*60}")
        print("🏃 Testing Endurance (5 minutes)")
        print(f"{'='*60}")
        
        start_time = time.time()
        end_time = start_time + 300  # 5 minutes
        
        requests_made = 0
        successful_requests = 0
        failed_requests = 0
        response_times = []
        
        print("Starting endurance test...")
        
        while time.time() < end_time:
            result = self.test_single_request('/')
            requests_made += 1
            
            if result['success']:
                successful_requests += 1
                response_times.append(result['response_time'])
            else:
                failed_requests += 1
            
            # Print progress every 30 seconds
            elapsed = time.time() - start_time
            if int(elapsed) % 30 == 0 and int(elapsed) > 0:
                print(f"Progress: {elapsed:.0f}s elapsed, {requests_made} requests made")
        
        total_time = time.time() - start_time
        
        self.results['Endurance Test'] = {
            'duration_seconds': total_time,
            'total_requests': requests_made,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': successful_requests / requests_made if requests_made > 0 else 0,
            'requests_per_second': requests_made / total_time,
            'avg_response_time': statistics.mean(response_times) if response_times else 0,
            'min_response_time': min(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0
        }
        
        print(f"Endurance Test Complete:")
        print(f"  Duration: {total_time:.1f} seconds")
        print(f"  Total Requests: {requests_made}")
        print(f"  Success Rate: {self.results['Endurance Test']['success_rate']:.1%}")
        print(f"  Requests/Second: {self.results['Endurance Test']['requests_per_second']:.1f}")
        print(f"  Avg Response Time: {self.results['Endurance Test']['avg_response_time']:.3f}s")
    
    def run_all_tests(self):
        """Run all performance tests"""
        print("🚀 Starting Comprehensive Performance Testing")
        print("="*60)
        
        self.start_time = time.time()
        
        # Test load scenarios
        self.test_load_scenarios()
        
        # Test memory usage
        self.test_memory_usage()
        
        # Test response time distribution
        self.test_response_time_distribution()
        
        # Test endurance
        self.test_endurance()
        
        self.end_time = time.time()
        
        # Generate summary
        self.generate_summary()
        
        # Save results
        self.save_results()
    
    def generate_summary(self):
        """Generate a summary of all test results"""
        print(f"\n{'='*60}")
        print("📊 PERFORMANCE TEST SUMMARY")
        print(f"{'='*60}")
        
        total_time = self.end_time - self.start_time
        print(f"Total test time: {total_time:.1f} seconds")
        
        # Overall success rates
        success_rates = []
        for scenario_name, scenario_results in self.results.items():
            if isinstance(scenario_results, dict) and 'Response Time Distribution' not in scenario_name:
                for endpoint, result in scenario_results.items():
                    if isinstance(result, dict) and 'success_rate' in result:
                        success_rates.append(result['success_rate'])
        
        if success_rates:
            avg_success_rate = statistics.mean(success_rates)
            print(f"Average success rate: {avg_success_rate:.1%}")
        
        # Memory usage summary
        if 'Memory Usage' in self.results:
            memory_data = self.results['Memory Usage']
            print(f"Memory increase: {memory_data['memory_increase_mb']:.2f} MB")
        
        # Response time summary
        if 'Response Time Distribution' in self.results:
            rt_data = self.results['Response Time Distribution']
            print(f"Average response time: {rt_data['mean']:.3f}s")
            print(f"95th percentile: {rt_data['percentile_95']:.3f}s")
        
        # Endurance summary
        if 'Endurance Test' in self.results:
            endurance_data = self.results['Endurance Test']
            print(f"Endurance requests/second: {endurance_data['requests_per_second']:.1f}")
    
    def save_results(self):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_test_results_{timestamp}.json"
        
        # Add metadata
        self.results['metadata'] = {
            'timestamp': timestamp,
            'total_test_time': self.end_time - self.start_time,
            'base_url': self.base_url
        }
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📈 Results saved to: {filename}")

def main():
    """Main function to run performance tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run comprehensive performance tests')
    parser.add_argument('--url', default='http://localhost:5000', 
                       help='Base URL of the application to test')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick tests only (skip endurance test)')
    
    args = parser.parse_args()
    
    print("🧪 TraceTrack Performance Testing Suite")
    print("="*60)
    print(f"Testing URL: {args.url}")
    print(f"Quick mode: {args.quick}")
    
    tester = PerformanceTester(args.url)
    
    if args.quick:
        # Quick tests only
        tester.test_load_scenarios()
        tester.test_memory_usage()
        tester.test_response_time_distribution()
    else:
        # Full test suite
        tester.run_all_tests()
    
    print("\n🎉 Performance testing completed!")

if __name__ == '__main__':
    main()