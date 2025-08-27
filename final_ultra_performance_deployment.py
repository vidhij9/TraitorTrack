#!/usr/bin/env python3
"""
Final Ultra-Performance Deployment and Testing Script
Complete setup for 100+ concurrent users and 600,000+ bags with <300ms response times
"""

import os
import sys
import time
import json
import subprocess
import requests
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

def check_prerequisites():
    """Check if all prerequisites are met"""
    print("🔍 Checking prerequisites...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Check required files
    required_files = [
        'main.py',
        'app_clean.py',
        'models.py',
        'routes.py',
        'gunicorn_ultra_performance.py',
        'optimize_database_ultra_scale.py',
        'ultra_load_test.py',
        'comprehensive_performance_test.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✅ All prerequisites met")
    return True

def apply_database_optimizations():
    """Apply database optimizations for ultra-scale"""
    print("🗄️ Applying database optimizations...")
    
    try:
        result = subprocess.run([
            'python3', 'optimize_database_ultra_scale.py'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Database optimizations applied successfully")
            return True
        else:
            print(f"❌ Database optimization failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Database optimization timed out")
        return False
    except Exception as e:
        print(f"❌ Database optimization error: {e}")
        return False

def start_ultra_performance_server():
    """Start the ultra-performance server"""
    print("🚀 Starting ultra-performance server...")
    
    try:
        # Start server in background
        process = subprocess.Popen([
            'gunicorn', '--config', 'gunicorn_ultra_performance.py', 'main:app'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        print("⏳ Waiting for server to start...")
        time.sleep(10)
        
        # Check if server is running
        try:
            response = requests.get('http://localhost:5000/health', timeout=10)
            if response.status_code == 200:
                print("✅ Ultra-performance server started successfully")
                return process
            else:
                print(f"❌ Server not responding properly: {response.status_code}")
                process.terminate()
                return None
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def run_performance_tests():
    """Run comprehensive performance tests"""
    print("🧪 Running performance tests...")
    
    try:
        result = subprocess.run([
            'python3', 'comprehensive_performance_test.py'
        ], capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("✅ Performance tests completed successfully")
            print(result.stdout)
            return True
        else:
            print(f"❌ Performance tests failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Performance tests timed out")
        return False
    except Exception as e:
        print(f"❌ Performance test error: {e}")
        return False

def run_load_tests():
    """Run load tests for 100+ concurrent users"""
    print("📊 Running load tests...")
    
    try:
        result = subprocess.run([
            'python3', 'ultra_load_test.py'
        ], capture_output=True, text=True, timeout=900)
        
        if result.returncode == 0:
            print("✅ Load tests completed successfully")
            print(result.stdout)
            return True
        else:
            print(f"❌ Load tests failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Load tests timed out")
        return False
    except Exception as e:
        print(f"❌ Load test error: {e}")
        return False

def test_concurrent_users_simulation():
    """Test concurrent user simulation"""
    print("👥 Testing concurrent user simulation...")
    
    def simulate_user(user_id):
        """Simulate a single user"""
        try:
            # Test multiple endpoints
            endpoints = [
                '/health',
                '/api/dashboard/analytics',
                '/api/bills',
                '/api/bags'
            ]
            
            results = []
            for endpoint in endpoints:
                try:
                    start_time = time.time()
                    response = requests.get(f'http://localhost:5000{endpoint}', timeout=30)
                    response_time = (time.time() - start_time) * 1000
                    
                    results.append({
                        'user_id': user_id,
                        'endpoint': endpoint,
                        'status_code': response.status_code,
                        'response_time_ms': response_time,
                        'success': response.status_code < 400
                    })
                    
                except Exception as e:
                    results.append({
                        'user_id': user_id,
                        'endpoint': endpoint,
                        'error': str(e),
                        'success': False
                    })
            
            return results
            
        except Exception as e:
            return [{'user_id': user_id, 'error': str(e), 'success': False}]
    
    # Test with 100 concurrent users
    all_results = []
    successful_requests = 0
    total_requests = 0
    
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(simulate_user, i) for i in range(100)]
        
        for future in as_completed(futures):
            try:
                user_results = future.result()
                all_results.extend(user_results)
                
                for result in user_results:
                    total_requests += 1
                    if result.get('success', False):
                        successful_requests += 1
                        
            except Exception as e:
                print(f"User simulation error: {e}")
    
    # Calculate metrics
    success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
    response_times = [r['response_time_ms'] for r in all_results if r.get('success') and 'response_time_ms' in r]
    
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    max_response_time = max(response_times) if response_times else 0
    min_response_time = min(response_times) if response_times else 0
    
    metrics = {
        'concurrent_users': 100,
        'total_requests': total_requests,
        'successful_requests': successful_requests,
        'success_rate': success_rate,
        'avg_response_time_ms': avg_response_time,
        'max_response_time_ms': max_response_time,
        'min_response_time_ms': min_response_time,
        'target_met': success_rate >= 99 and avg_response_time <= 300
    }
    
    print(f"✅ Concurrent user simulation completed:")
    print(f"   Success Rate: {success_rate:.1f}%")
    print(f"   Avg Response Time: {avg_response_time:.1f}ms")
    print(f"   Max Response Time: {max_response_time:.1f}ms")
    print(f"   Target Met: {'✅ Yes' if metrics['target_met'] else '❌ No'}")
    
    return metrics

def generate_final_report(test_results):
    """Generate final deployment report"""
    print("📊 Generating final deployment report...")
    
    report = {
        'deployment_timestamp': datetime.now().isoformat(),
        'target_specifications': {
            'concurrent_users': 100,
            'bags_data': 600000,
            'response_time_ms': 300,
            'success_rate_percent': 99
        },
        'test_results': test_results,
        'overall_status': 'PASS' if all(test_results.values()) else 'FAIL',
        'recommendations': []
    }
    
    # Add recommendations based on results
    if not test_results.get('database_optimization', False):
        report['recommendations'].append("Database optimization failed - check database connection and permissions")
    
    if not test_results.get('server_startup', False):
        report['recommendations'].append("Server startup failed - check Gunicorn configuration and dependencies")
    
    if not test_results.get('performance_tests', False):
        report['recommendations'].append("Performance tests failed - optimize database queries and add caching")
    
    if not test_results.get('load_tests', False):
        report['recommendations'].append("Load tests failed - increase server resources or optimize application")
    
    if not test_results.get('concurrent_simulation', False):
        report['recommendations'].append("Concurrent user simulation failed - optimize for high concurrency")
    
    if all(test_results.values()):
        report['recommendations'].append("🎉 All targets achieved! System ready for production deployment")
    
    # Save report
    filename = f"ultra_performance_deployment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Final report saved to: {filename}")
    return report

def main():
    """Main deployment and testing function"""
    print("=" * 80)
    print("🚀 ULTRA-PERFORMANCE DEPLOYMENT AND TESTING")
    print("=" * 80)
    print("Target: 100+ concurrent users, 600,000+ bags, <300ms response times")
    print("=" * 80)
    
    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites not met. Exiting.")
        return False
    
    test_results = {}
    server_process = None
    
    try:
        # Step 1: Apply database optimizations
        print("\n" + "="*60)
        print("STEP 1: Database Optimization")
        print("="*60)
        test_results['database_optimization'] = apply_database_optimizations()
        
        # Step 2: Start ultra-performance server
        print("\n" + "="*60)
        print("STEP 2: Server Startup")
        print("="*60)
        server_process = start_ultra_performance_server()
        test_results['server_startup'] = server_process is not None
        
        if not server_process:
            print("❌ Cannot proceed without server. Exiting.")
            return False
        
        # Step 3: Run performance tests
        print("\n" + "="*60)
        print("STEP 3: Performance Testing")
        print("="*60)
        test_results['performance_tests'] = run_performance_tests()
        
        # Step 4: Run load tests
        print("\n" + "="*60)
        print("STEP 4: Load Testing")
        print("="*60)
        test_results['load_tests'] = run_load_tests()
        
        # Step 5: Test concurrent users
        print("\n" + "="*60)
        print("STEP 5: Concurrent User Testing")
        print("="*60)
        concurrent_metrics = test_concurrent_users_simulation()
        test_results['concurrent_simulation'] = concurrent_metrics['target_met']
        
        # Generate final report
        print("\n" + "="*60)
        print("STEP 6: Final Report")
        print("="*60)
        final_report = generate_final_report(test_results)
        
        # Print summary
        print("\n" + "=" * 80)
        print("🎉 ULTRA-PERFORMANCE DEPLOYMENT COMPLETED")
        print("=" * 80)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name.replace('_', ' ').title()}")
        
        overall_status = "PASS" if all(test_results.values()) else "FAIL"
        print(f"\nOverall Status: {overall_status}")
        
        if all(test_results.values()):
            print("\n🎯 ALL TARGETS ACHIEVED!")
            print("✅ System ready for 100+ concurrent users")
            print("✅ System ready for 600,000+ bags")
            print("✅ All endpoints responding within 300ms")
            print("✅ Success rate above 99%")
            print("\n🚀 Ready for production deployment!")
        else:
            print("\n⚠️ SOME TARGETS NOT MET")
            print("📋 Check recommendations in the detailed report")
        
        print("=" * 80)
        
        return all(test_results.values())
        
    except KeyboardInterrupt:
        print("\n🛑 Deployment interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Deployment failed with error: {e}")
        return False
    finally:
        # Cleanup
        if server_process:
            print("\n🧹 Cleaning up...")
            server_process.terminate()
            server_process.wait()
            print("✅ Server stopped")

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)