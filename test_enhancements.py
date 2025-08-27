#!/usr/bin/env python3
"""
Enhancement Test Script
Test the enhancement features
"""

import json
import requests
from datetime import datetime

def test_enhancement_features():
    """Test enhancement features"""
    print("🧪 Testing enhancement features...")
    
    base_url = "http://localhost:5000"
    
    # Test health check
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            health_data = response.json()
            print(f"   Status: {health_data.get('status')}")
            print(f"   Database: {health_data.get('services', {}).get('database')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test export endpoints
    export_endpoints = [
        "/api/export/bills/csv",
        "/api/export/bags/csv",
        "/api/export/scans/csv"
    ]
    
    for endpoint in export_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                print(f"✅ Export endpoint {endpoint} working")
            else:
                print(f"⚠️ Export endpoint {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ Export endpoint {endpoint} error: {e}")
    
    # Test print endpoints
    print_endpoints = [
        "/api/print/summary"
    ]
    
    for endpoint in print_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ Print endpoint {endpoint} working")
            else:
                print(f"⚠️ Print endpoint {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ Print endpoint {endpoint} error: {e}")
    
    print("✅ Enhancement testing completed")

if __name__ == "__main__":
    test_enhancement_features()
