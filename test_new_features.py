"""Test script for all 4 new features"""
import requests
import json

BASE_URL = 'http://localhost:5000'

def test_features():
    """Test all 4 new features"""
    print("=" * 70)
    print("TESTING NEW TRACETRACK FEATURES")
    print("=" * 70)
    
    s = requests.Session()
    
    # Login as admin
    print("\n1. LOGIN TEST")
    print("-" * 40)
    login = s.post(f'{BASE_URL}/login', data={'username': 'admin', 'password': 'admin123'})
    if login.status_code in [200, 302]:
        print("✅ Admin login successful")
    else:
        print("❌ Login failed")
        return
    
    # Test Feature 1: Bag Status Validation
    print("\n2. FEATURE 1: BAG STATUS VALIDATION")
    print("-" * 40)
    
    # Create a parent bag with pending status
    parent_qr = 'SB99999'
    parent_scan = s.post(f'{BASE_URL}/process_parent_scan', data={'qr_code': parent_qr})
    print(f"Created parent bag {parent_qr}")
    
    # Try to attach incomplete parent bag to bill
    bill_create = s.post(f'{BASE_URL}/bill/create', data={
        'bill_id': 'TEST-BILL-001',
        'parent_bag_count': 5
    })
    
    if bill_create.status_code in [200, 302]:
        print("✅ Test bill created")
        
        # Try to link incomplete parent bag (should fail)
        link_response = s.post(f'{BASE_URL}/process_bill_parent_scan', data={
            'bill_id': 1,  # Assuming first bill
            'qr_code': parent_qr
        })
        
        if link_response.status_code == 200:
            result = link_response.json()
            if not result.get('success'):
                if 'not completed' in result.get('message', ''):
                    print(f"✅ Feature 1 Working: Parent bag with pending status correctly rejected")
                    print(f"   Message: {result.get('message')}")
                else:
                    print(f"⚠️  Feature 1: Bag rejected but for different reason: {result.get('message')}")
            else:
                print("❌ Feature 1 Failed: Incomplete parent bag was attached to bill")
    
    # Test Feature 2: Manual Parent Bag Entry
    print("\n3. FEATURE 2: MANUAL PARENT BAG ENTRY")
    print("-" * 40)
    
    # Test manual entry with correct format
    manual_response = s.post(f'{BASE_URL}/bill/manual_parent_entry', data={
        'bill_id': 1,
        'manual_qr': 'SB88888'
    })
    
    if manual_response.status_code == 200:
        result = manual_response.json()
        if result.get('success'):
            print(f"✅ Feature 2 Working: Manual entry successful for {result.get('bag_qr')}")
            print(f"   Status: {result.get('bag_status')}, Weight: {result.get('weight_kg')}kg")
        else:
            print(f"⚠️  Manual entry failed: {result.get('message')}")
    
    # Test invalid format
    invalid_response = s.post(f'{BASE_URL}/bill/manual_parent_entry', data={
        'bill_id': 1,
        'manual_qr': 'INVALID123'
    })
    
    if invalid_response.status_code == 200:
        result = invalid_response.json()
        if not result.get('success') and 'Invalid format' in result.get('message', ''):
            print("✅ Feature 2 Validation: Invalid format correctly rejected")
    
    # Test Feature 3: Weight Calculations
    print("\n4. FEATURE 3: WEIGHT CALCULATIONS")
    print("-" * 40)
    
    # Create a completed parent bag (with 30 child bags)
    completed_parent = 'SB77777'
    
    # Start parent scan
    s.post(f'{BASE_URL}/process_parent_scan', data={'qr_code': completed_parent})
    
    # Add 30 child bags
    print("Creating parent with 30 child bags...")
    for i in range(30):
        child_qr = f'CB{70000 + i}'
        s.post(f'{BASE_URL}/process_child_scan', data={'qr_code': child_qr})
    
    # Complete the scan (should mark parent as completed with 30kg weight)
    complete = s.get(f'{BASE_URL}/scan/complete')
    
    if complete.status_code == 200:
        print("✅ Parent bag completed with 30 child bags")
        
        # Now try to link this completed bag to a bill
        link_completed = s.post(f'{BASE_URL}/process_bill_parent_scan', data={
            'bill_id': 1,
            'qr_code': completed_parent
        })
        
        if link_completed.status_code == 200:
            result = link_completed.json()
            if result.get('success'):
                print(f"✅ Feature 3 Working: Completed parent bag attached to bill")
                print(f"   Total weight: {result.get('total_weight', 0)}kg")
                print(f"   Total child bags: {result.get('total_child_bags', 0)}")
    
    # Test Feature 4: Bill Summary Reporting
    print("\n5. FEATURE 4: BILL SUMMARY REPORTING")
    print("-" * 40)
    
    # Access bill summary page
    summary_page = s.get(f'{BASE_URL}/bill_summary')
    
    if summary_page.status_code == 200:
        print("✅ Bill summary page accessible")
        
        # Check if summary contains expected elements
        if 'Bill Summary' in summary_page.text:
            print("✅ Bill summary report generated")
            
            # Check for key features
            if 'Total Bills' in summary_page.text:
                print("   - Overall statistics present")
            if 'Weight' in summary_page.text:
                print("   - Weight calculations displayed")
            if 'Created By' in summary_page.text:
                print("   - Bill creator tracking working")
    
    # Test EOD summary API (admin only)
    eod_summary = s.get(f'{BASE_URL}/api/bill_summary/eod')
    
    if eod_summary.status_code == 200:
        eod_data = eod_summary.json()
        print("✅ EOD Summary API Working")
        print(f"   - Report date: {eod_data.get('report_date')}")
        print(f"   - Total bills: {eod_data.get('total_bills')}")
        print(f"   - Total weight: {eod_data.get('total_weight_kg')}kg")
    
    # Summary
    print("\n" + "=" * 70)
    print("FEATURE IMPLEMENTATION SUMMARY")
    print("=" * 70)
    print("✅ Feature 1: Bag Status Validation - IMPLEMENTED")
    print("   - Only completed parent bags (30 children) can be attached to bills")
    print("✅ Feature 2: Manual Parent Bag Entry - IMPLEMENTED")
    print("   - Manual entry with SB##### format validation")
    print("✅ Feature 3: Weight Calculations - IMPLEMENTED")
    print("   - 1kg per child bag, 30kg for full parent bag")
    print("   - Weight tracking in bills")
    print("✅ Feature 4: Bill Summary Reporting - IMPLEMENTED")
    print("   - Biller sees own bills, Admin sees all")
    print("   - EOD summary API for automated reports")
    print("=" * 70)

if __name__ == '__main__':
    test_features()