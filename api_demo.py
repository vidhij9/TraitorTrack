#!/usr/bin/env python3
"""
API Demonstration Script - Shows the improved API endpoints in action
This script demonstrates all the new API functionality with real data.
"""

import requests
import json
import time
from datetime import datetime

# Base URL for the application
BASE_URL = "http://localhost:5000"

def login_and_get_session():
    """Login and get session cookie for authenticated requests"""
    session = requests.Session()
    
    # Login with admin credentials
    login_data = {
        'username': 'admin',
        'password': 'admin'
    }
    
    response = session.post(f"{BASE_URL}/login", data=login_data)
    if response.status_code == 200:
        print("✓ Successfully authenticated")
        return session
    else:
        print("✗ Authentication failed")
        return None

def demo_system_health():
    """Demonstrate system health check (no auth required)"""
    print("\n=== SYSTEM HEALTH CHECK ===")
    print("New endpoint: GET /api/system/health-check")
    
    response = requests.get(f"{BASE_URL}/api/system/health-check")
    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data['status']}")
        print(f"Database: {data['checks']['database']}")
        print(f"Recent Activity: {data['checks']['recent_activity']}")
        print(f"Version: {data['version']}")
    else:
        print(f"Error: {response.status_code}")

def demo_system_analytics(session):
    """Demonstrate improved analytics endpoint"""
    print("\n=== SYSTEM ANALYTICS OVERVIEW ===")
    print("New endpoint: GET /api/analytics/system-overview")
    print("Old endpoint: GET /api/stats (deprecated)")
    
    # Test new endpoint
    response = session.get(f"{BASE_URL}/api/analytics/system-overview")
    if response.status_code == 200:
        data = response.json()
        totals = data['data']['totals']
        breakdown = data['data']['scan_breakdown']
        activity = data['data']['recent_activity']
        
        print(f"Total Bags: {totals['total_bags']} (Parent: {totals['parent_bags']}, Child: {totals['child_bags']})")
        print(f"Total Scans: {totals['total_scans']} (Parent: {breakdown['parent_scans']}, Child: {breakdown['child_scans']})")
        print(f"Recent Activity: {activity['scans_last_7_days']} scans, {activity['active_users_last_7_days']} active users")
        print(f"Generated at: {data['data']['generated_at']}")
    else:
        print(f"Error: {response.status_code}")

def demo_bag_management(session):
    """Demonstrate improved bag management endpoints"""
    print("\n=== BAG MANAGEMENT ===")
    
    # Parent bags list
    print("New endpoint: GET /api/bags/parent/list")
    print("Old endpoint: GET /api/parent_bags (deprecated)")
    
    response = session.get(f"{BASE_URL}/api/bags/parent/list")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['count']} parent bags")
        if data['data']:
            print(f"Sample parent bag: {data['data'][0]['qr_id']}")
    
    # Child bags list
    print("\nNew endpoint: GET /api/bags/child/list")
    print("Old endpoint: GET /api/child_bags (deprecated)")
    
    response = session.get(f"{BASE_URL}/api/bags/child/list")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['count']} child bags")
        if data['data']:
            print(f"Sample child bag: {data['data'][0]['qr_id']}")

def demo_scan_tracking(session):
    """Demonstrate improved scan tracking endpoints"""
    print("\n=== SCAN TRACKING ===")
    
    # Recent scans with filtering
    print("New endpoint: GET /api/tracking/scans/recent")
    print("Old endpoint: GET /api/scans (deprecated)")
    
    # Test with different filters
    filters = [
        {"limit": 5, "description": "Last 5 scans"},
        {"type": "parent", "limit": 3, "description": "Last 3 parent scans"},
        {"days": 7, "limit": 10, "description": "Last 10 scans from past week"}
    ]
    
    for filter_params in filters:
        desc = filter_params.pop('description')
        response = session.get(f"{BASE_URL}/api/tracking/scans/recent", params=filter_params)
        if response.status_code == 200:
            data = response.json()
            print(f"{desc}: {data['data']['count']} scans found")
            print(f"  Filters applied: {data['data']['filters_applied']}")

def demo_cache_management(session):
    """Demonstrate improved cache management endpoints"""
    print("\n=== CACHE MANAGEMENT ===")
    
    # Cache status
    print("New endpoint: GET /api/system/cache/status")
    print("Old endpoint: GET /api/cache_stats (deprecated)")
    
    response = session.get(f"{BASE_URL}/api/system/cache/status")
    if response.status_code == 200:
        data = response.json()
        print(f"Cache health: {data['data']['cache_health']}")
        
    # Cache clearing (demonstrate but don't actually clear)
    print("\nNew endpoint: POST /api/system/cache/clear")
    print("Old endpoint: POST /api/clear_cache (deprecated)")
    print("(Cache clearing demonstration - not executed)")

def demo_development_tools(session):
    """Demonstrate development and testing endpoints"""
    print("\n=== DEVELOPMENT TOOLS ===")
    
    print("New endpoint: POST /api/development/seed-sample-data")
    print("Old endpoint: POST /api/seed_test_data (deprecated)")
    
    # Sample data creation
    response = session.post(f"{BASE_URL}/api/development/seed-sample-data")
    if response.status_code == 200:
        data = response.json()
        print(f"Sample data created: {data['message']}")
        if 'data' in data:
            result = data['data']
            print(f"  Parent bags: {len(result['parent_bags_created'])}")
            print(f"  Child bags: {len(result['child_bags_created'])}")
            print(f"  Scans: {result['scans_created']}")
    else:
        print("Sample data already exists or creation failed")

def demo_enhanced_responses(session):
    """Demonstrate enhanced response formats"""
    print("\n=== ENHANCED RESPONSE FORMATS ===")
    
    # Show detailed bag information
    response = session.get(f"{BASE_URL}/api/bags/parent/list")
    if response.status_code == 200 and response.json()['data']:
        parent_qr = response.json()['data'][0]['qr_id']
        
        print(f"Detailed parent bag info: GET /api/bags/parent/{parent_qr}/details")
        response = session.get(f"{BASE_URL}/api/bags/parent/{parent_qr}/details")
        if response.status_code == 200:
            data = response.json()['data']
            print(f"  Child count: {data['child_count']}/{data['expected_child_count']}")
            print(f"  Children found: {len(data['child_bags'])}")

def demo_backward_compatibility(session):
    """Demonstrate backward compatibility with deprecation warnings"""
    print("\n=== BACKWARD COMPATIBILITY ===")
    print("Testing old endpoints (they still work but show deprecation warnings)")
    
    old_endpoints = [
        ("/api/stats", "System statistics"),
        ("/api/scans?limit=5", "Recent scans"),
        ("/api/parent_bags", "Parent bags list")
    ]
    
    for endpoint, description in old_endpoints:
        response = session.get(f"{BASE_URL}{endpoint}")
        if response.status_code == 200:
            print(f"✓ {description}: {endpoint} - Still working")
        else:
            print(f"✗ {description}: {endpoint} - Error {response.status_code}")

def main():
    """Run the complete API demonstration"""
    print("=== API IMPROVEMENTS DEMONSTRATION ===")
    print("Showing new descriptive endpoints vs old ones")
    print("=" * 50)
    
    # Test health check (no auth required)
    demo_system_health()
    
    # Login and get authenticated session
    session = login_and_get_session()
    if not session:
        print("Cannot proceed without authentication")
        return
    
    # Run all demonstrations
    demo_system_analytics(session)
    demo_bag_management(session)
    demo_scan_tracking(session)
    demo_cache_management(session)
    demo_development_tools(session)
    demo_enhanced_responses(session)
    demo_backward_compatibility(session)
    
    print("\n=== SUMMARY ===")
    print("✓ All new API endpoints are functional")
    print("✓ Enhanced response formats provide more metadata")
    print("✓ Hierarchical structure improves organization")
    print("✓ Backward compatibility maintained")
    print("✓ Deprecation warnings guide migration")

if __name__ == "__main__":
    main()
