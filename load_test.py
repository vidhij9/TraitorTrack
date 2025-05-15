#!/usr/bin/env python3
"""
Load testing script for TraceTrack application.
Simulates high concurrency to validate the improvements for 100+ concurrent users.
"""
import argparse
import asyncio
import aiohttp
import time
import random
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
DEFAULT_CONCURRENCY = 100
DEFAULT_REQUESTS = 1000
DEFAULT_TIMEOUT = 30  # seconds

# Global statistics
stats = {
    'total_requests': 0,
    'successful_requests': 0,
    'failed_requests': 0,
    'timeouts': 0,
    'start_time': 0,
    'end_time': 0,
    'response_times': [],
    'status_codes': defaultdict(int),
    'endpoint_stats': defaultdict(lambda: {
        'count': 0,
        'success': 0,
        'fail': 0,
        'avg_time': 0,
        'total_time': 0
    })
}

# Test endpoints
ENDPOINTS = [
    # Public endpoints
    '/login',
    '/register',
    '/',  # Home page
    # Admin endpoints that require authentication (will likely fail with 302 redirect)
    '/parent_bags',
    '/child_bags',
    '/locations',
    # Health check endpoint
    '/api/db/health',
]

async def make_request(session, url, endpoint):
    """Make a single request to the specified endpoint"""
    stats['total_requests'] += 1
    
    start_time = time.time()
    try:
        async with session.get(url + endpoint, timeout=DEFAULT_TIMEOUT) as response:
            await response.text()  # Ensure we read the full response
            
            # Record response time
            response_time = time.time() - start_time
            stats['response_times'].append(response_time)
            
            # Update endpoint stats
            stats['endpoint_stats'][endpoint]['count'] += 1
            stats['endpoint_stats'][endpoint]['total_time'] += response_time
            
            # Record status code
            status = response.status
            stats['status_codes'][status] += 1
            
            if 200 <= status < 400:
                stats['successful_requests'] += 1
                stats['endpoint_stats'][endpoint]['success'] += 1
            else:
                stats['failed_requests'] += 1
                stats['endpoint_stats'][endpoint]['fail'] += 1
                
            return response.status
            
    except asyncio.TimeoutError:
        stats['timeouts'] += 1
        stats['endpoint_stats'][endpoint]['fail'] += 1
        stats['failed_requests'] += 1
        return 'timeout'
    except Exception as e:
        logger.error(f"Error while making request to {endpoint}: {str(e)}")
        stats['failed_requests'] += 1
        stats['endpoint_stats'][endpoint]['fail'] += 1
        return f'error: {str(e)}'

async def load_test(url, concurrency, total_requests):
    """Run the load test with the specified parameters"""
    logger.info(f"Starting load test with {concurrency} concurrent users, {total_requests} total requests")
    logger.info(f"Target URL: {url}")
    
    # Initialize statistics
    stats['start_time'] = time.time()
    
    # Create session
    async with aiohttp.ClientSession() as session:
        # Create tasks for all requests
        tasks = []
        for _ in range(total_requests):
            # Select a random endpoint
            endpoint = random.choice(ENDPOINTS)
            
            # Create task
            task = asyncio.create_task(make_request(session, url, endpoint))
            tasks.append(task)
            
            # Wait if we've reached concurrency limit
            if len(tasks) >= concurrency:
                # Wait for one task to complete
                await asyncio.gather(tasks.pop(0))
        
        # Wait for remaining tasks
        if tasks:
            await asyncio.gather(*tasks)
    
    # Record end time
    stats['end_time'] = time.time()
    
    # Calculate endpoint averages
    for endpoint, data in stats['endpoint_stats'].items():
        if data['count'] > 0:
            data['avg_time'] = data['total_time'] / data['count']

def display_results():
    """Display the results of the load test"""
    duration = stats['end_time'] - stats['start_time']
    requests_per_second = stats['total_requests'] / duration if duration > 0 else 0
    
    # Calculate average response time
    avg_response_time = sum(stats['response_times']) / len(stats['response_times']) if stats['response_times'] else 0
    
    # Calculate percentiles
    if stats['response_times']:
        sorted_times = sorted(stats['response_times'])
        p50 = sorted_times[int(len(sorted_times) * 0.5)]
        p90 = sorted_times[int(len(sorted_times) * 0.9)]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]
    else:
        p50 = p90 = p95 = p99 = 0
    
    print("\n===== LOAD TEST RESULTS =====")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Total Requests: {stats['total_requests']}")
    print(f"Successful Requests: {stats['successful_requests']} ({stats['successful_requests']/stats['total_requests']*100:.2f}%)")
    print(f"Failed Requests: {stats['failed_requests']} ({stats['failed_requests']/stats['total_requests']*100:.2f}%)")
    print(f"Timeouts: {stats['timeouts']}")
    print(f"Requests Per Second: {requests_per_second:.2f}")
    
    print("\n----- Response Times -----")
    print(f"Average: {avg_response_time*1000:.2f} ms")
    print(f"P50: {p50*1000:.2f} ms")
    print(f"P90: {p90*1000:.2f} ms")
    print(f"P95: {p95*1000:.2f} ms")
    print(f"P99: {p99*1000:.2f} ms")
    
    print("\n----- Status Codes -----")
    for status, count in sorted(stats['status_codes'].items()):
        print(f"{status}: {count} ({count/stats['total_requests']*100:.2f}%)")
    
    print("\n----- Endpoint Performance -----")
    for endpoint, data in sorted(stats['endpoint_stats'].items(), key=lambda x: x[1]['avg_time'], reverse=True):
        success_rate = data['success'] / data['count'] * 100 if data['count'] > 0 else 0
        print(f"{endpoint}:")
        print(f"  Requests: {data['count']}")
        print(f"  Success Rate: {success_rate:.2f}%")
        print(f"  Avg Response Time: {data['avg_time']*1000:.2f} ms")
        print("  ---")

async def main():
    """Main entry point for the load testing script"""
    parser = argparse.ArgumentParser(description='Load test the TraceTrack application.')
    parser.add_argument('--url', type=str, default='http://localhost:5000',
                      help='Target URL (default: http://localhost:5000)')
    parser.add_argument('--concurrency', type=int, default=DEFAULT_CONCURRENCY,
                      help=f'Number of concurrent users (default: {DEFAULT_CONCURRENCY})')
    parser.add_argument('--requests', type=int, default=DEFAULT_REQUESTS,
                      help=f'Total number of requests (default: {DEFAULT_REQUESTS})')
    
    args = parser.parse_args()
    
    try:
        await load_test(args.url, args.concurrency, args.requests)
        display_results()
    except KeyboardInterrupt:
        logger.info("Load test interrupted by user")
        display_results()
    except Exception as e:
        logger.error(f"Error during load test: {str(e)}")

if __name__ == '__main__':
    asyncio.run(main())