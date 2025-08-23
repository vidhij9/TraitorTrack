#!/usr/bin/env python3
"""
Test script to demonstrate EOD Bill Summary feature
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"

def test_eod_json_api():
    """Test the EOD JSON API endpoint"""
    print("\n" + "="*60)
    print("TESTING EOD BILL SUMMARY FEATURE")
    print("="*60)
    
    # First, we need to login as admin
    session = requests.Session()
    
    # Login as admin
    login_data = {
        'username': 'admin',
        'password': 'admin'
    }
    
    print("\n1. Logging in as admin...")
    response = session.post(f"{BASE_URL}/login", data=login_data)
    if response.status_code == 200:
        print("   ✅ Login successful")
    else:
        print(f"   ❌ Login failed: {response.status_code}")
        return
    
    # Get EOD JSON summary
    print("\n2. Fetching EOD JSON Summary...")
    response = session.get(f"{BASE_URL}/api/bill_summary/eod")
    
    if response.status_code == 200:
        eod_data = response.json()
        print("   ✅ EOD Summary Retrieved Successfully!")
        
        print("\n   📊 EOD SUMMARY DATA:")
        print("   " + "-"*40)
        print(f"   Report Date: {eod_data.get('report_date', 'N/A')}")
        print(f"   Total Bills: {eod_data.get('total_bills', 0)}")
        print(f"   Total Parent Bags: {eod_data.get('total_parent_bags', 0)}")
        print(f"   Total Child Bags: {eod_data.get('total_child_bags', 0)}")
        print(f"   Total Weight: {eod_data.get('total_weight_kg', 0):.2f} KG")
        
        if eod_data.get('bills_by_status'):
            print("\n   📈 Bills by Status:")
            for status, count in eod_data['bills_by_status'].items():
                print(f"      - {status}: {count}")
        
        if eod_data.get('bills_by_user'):
            print("\n   👥 Bills by User:")
            for user, count in eod_data['bills_by_user'].items():
                print(f"      - {user}: {count}")
        
        if eod_data.get('detailed_bills'):
            print(f"\n   📋 Detailed Bills: {len(eod_data['detailed_bills'])} bills")
            for i, bill in enumerate(eod_data['detailed_bills'][:3], 1):
                print(f"      {i}. {bill['bill_id']} by {bill['created_by']} - Status: {bill['status']}")
            if len(eod_data['detailed_bills']) > 3:
                print(f"      ... and {len(eod_data['detailed_bills']) - 3} more bills")
        
        # Save to file for inspection
        with open('eod_summary_sample.json', 'w') as f:
            json.dump(eod_data, f, indent=2)
        print("\n   💾 Full EOD data saved to: eod_summary_sample.json")
        
    else:
        print(f"   ❌ Failed to get EOD summary: {response.status_code}")
        if response.status_code == 403:
            print("      (Admin access required)")
    
    # Test the scheduled endpoint
    print("\n3. Testing Scheduled EOD Endpoint...")
    headers = {
        'X-EOD-Secret': 'default-eod-secret-2025',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(f"{BASE_URL}/api/bill_summary/schedule_eod", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("   ✅ Scheduled EOD endpoint works!")
        print(f"   Message: {result.get('message', 'N/A')}")
        
        if result.get('results'):
            results = result['results']
            print(f"   Billers processed: {results.get('total_processed', 0)}")
            print(f"   Note: Emails not sent (SMTP not configured)")
    else:
        print(f"   ❌ Scheduled endpoint failed: {response.status_code}")
        try:
            error_data = response.json()
            print(f"      Error: {error_data.get('error', 'Unknown error')}")
        except:
            pass

def demonstrate_eod_feature():
    """Demonstrate the complete EOD feature"""
    print("\n" + "="*60)
    print("EOD BILL SUMMARY FEATURE DEMONSTRATION")
    print("="*60)
    
    print("""
The EOD Bill Summary feature has been successfully implemented with:

✅ FEATURES IMPLEMENTED:
   1. EOD Summary Generation
      - Billers receive their own bill summaries
      - Admins receive comprehensive summaries of all users
   
   2. Multiple Access Methods:
      - Web UI: /bill_summary page with EOD buttons
      - Preview: /eod_summary_preview (admin only)
      - API: /api/bill_summary/eod (JSON data)
      - Send: /api/bill_summary/send_eod (email dispatch)
      - Schedule: /api/bill_summary/schedule_eod (cron job)
   
   3. Email Templates:
      - HTML formatted emails for billers
      - Comprehensive admin emails with all user data
      - Statistics, charts, and detailed bill lists
   
   4. Security:
      - Role-based access (admin-only for sending)
      - Secret key authentication for scheduled jobs
      - CSRF protection where appropriate

📧 EMAIL CONFIGURATION:
   To enable email sending, set these environment variables:
   - SMTP_HOST (e.g., smtp.gmail.com)
   - SMTP_PORT (e.g., 587)
   - SMTP_USER (your email)
   - SMTP_PASSWORD (app password)
   
⏰ SCHEDULING:
   Add to crontab for daily EOD at 6 PM:
   0 18 * * * curl -X POST https://your-domain/api/bill_summary/schedule_eod \\
     -H "X-EOD-Secret: your-secret-key"

🔍 TESTING THE FEATURE:
   1. Login as admin
   2. Go to /bill_summary
   3. Click "Preview EOD Email" to see the format
   4. Click "Send EOD Summaries" to send emails
   5. Or use the API endpoints programmatically
""")

if __name__ == "__main__":
    # Run the test
    test_eod_json_api()
    
    # Show feature documentation
    demonstrate_eod_feature()
    
    print("\n✅ EOD Bill Summary Feature Test Complete!")
    print("   Check 'eod_summary_sample.json' for sample data")
    print("   Documentation available in 'EOD_SCHEDULER_SETUP.md'")