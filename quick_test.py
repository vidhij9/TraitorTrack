"""Quick test to verify authentication and scanning workflow"""
import requests
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = 'http://localhost:5000'

def test_user_workflow(user_num):
    """Test complete workflow for a single user"""
    session = requests.Session()
    results = {'login': False, 'parent': False, 'child': False, 'errors': []}
    
    try:
        # Login
        login_resp = session.post(
            f'{BASE_URL}/login',
            data={'username': 'admin', 'password': 'admin123'},
            timeout=10
        )
        if login_resp.status_code in [200, 302] and login_resp.url != f'{BASE_URL}/login':
            results['login'] = True
            
            # Parent scan
            parent_qr = f'SB{random.randint(10000, 99999)}'
            parent_resp = session.post(
                f'{BASE_URL}/process_parent_scan',
                data={'qr_code': parent_qr},
                timeout=10
            )
            if parent_resp.status_code == 200 and 'scan_child' in parent_resp.url:
                results['parent'] = True
                
                # Child scan
                child_qr = f'CB{random.randint(10000, 99999)}'
                child_resp = session.post(
                    f'{BASE_URL}/process_child_scan',
                    data={'qr_code': child_qr},
                    timeout=10
                )
                if child_resp.status_code == 200:
                    try:
                        data = child_resp.json()
                        results['child'] = data.get('success', False)
                    except:
                        pass
    except Exception as e:
        results['errors'].append(str(e))
    
    return results

def run_concurrent_test(num_users=10):
    """Run concurrent user test"""
    print(f"🚀 Testing with {num_users} concurrent users...")
    print("=" * 60)
    
    start_time = time.time()
    success_count = {'login': 0, 'parent': 0, 'child': 0}
    errors = []
    
    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [executor.submit(test_user_workflow, i) for i in range(num_users)]
        
        for future in as_completed(futures):
            result = future.result()
            if result['login']:
                success_count['login'] += 1
            if result['parent']:
                success_count['parent'] += 1
            if result['child']:
                success_count['child'] += 1
            if result['errors']:
                errors.extend(result['errors'])
    
    elapsed = time.time() - start_time
    
    print(f"\n📊 Results after {elapsed:.2f} seconds:")
    print(f"   Login Success: {success_count['login']}/{num_users} ({success_count['login']*100/num_users:.1f}%)")
    print(f"   Parent Scan Success: {success_count['parent']}/{num_users} ({success_count['parent']*100/num_users:.1f}%)")
    print(f"   Child Scan Success: {success_count['child']}/{num_users} ({success_count['child']*100/num_users:.1f}%)")
    
    if errors:
        print(f"\n⚠️  Errors encountered: {len(errors)}")
        for err in errors[:3]:
            print(f"   - {err}")
    
    if success_count['child'] == num_users:
        print("\n✅ PERFECT! All users completed full workflow successfully!")
    elif success_count['child'] >= num_users * 0.9:
        print("\n✅ EXCELLENT! 90%+ success rate achieved!")
    elif success_count['child'] >= num_users * 0.8:
        print("\n✅ GOOD! 80%+ success rate achieved!")
    else:
        print("\n⚠️  Success rate below 80% - needs optimization")
    
    return success_count

if __name__ == '__main__':
    # Test with increasing loads
    for num_users in [5, 10, 20, 50]:
        print(f"\n{'='*60}")
        print(f"TESTING WITH {num_users} USERS")
        print('='*60)
        
        results = run_concurrent_test(num_users)
        
        # Stop if success rate drops below 80%
        if results['child'] < num_users * 0.8:
            print(f"\n⚠️  Stopping tests - success rate dropped below 80% at {num_users} users")
            break
        
        # Brief pause between tests
        time.sleep(2)
    
    print("\n" + "="*60)
    print("✅ TESTING COMPLETE!")
    print("="*60)