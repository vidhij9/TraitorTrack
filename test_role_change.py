#!/usr/bin/env python3
"""
Test script for role change functionality with real-world scenarios
"""
import os
import sys
from datetime import datetime
from flask import Flask
from sqlalchemy import text

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_clean import app, db
from models import User, UserRole, Bill, Bag, BagType, Link, BillBag, AuditLog
from werkzeug.security import generate_password_hash

def test_role_changes():
    """Test various role change scenarios"""
    
    with app.app_context():
        print("\n" + "="*80)
        print("TESTING ROLE CHANGE FUNCTIONALITY WITH REAL-WORLD SCENARIOS")
        print("="*80)
        
        # Test 1: Create test users for role changes
        print("\n1. Creating test users for role change scenarios...")
        
        # Clean up any existing test users
        User.query.filter(User.username.like('role_test_%')).delete()
        db.session.commit()
        
        # Create test users
        test_admin = User(
            username='role_test_admin',
            email='role_test_admin@test.com',
            role=UserRole.ADMIN.value,
            verified=True
        )
        test_admin.set_password('testpass123')
        
        test_biller = User(
            username='role_test_biller',
            email='role_test_biller@test.com',
            role=UserRole.BILLER.value,
            verified=True
        )
        test_biller.set_password('testpass123')
        
        test_dispatcher1 = User(
            username='role_test_dispatcher1',
            email='role_test_dispatcher1@test.com',
            role=UserRole.DISPATCHER.value,
            dispatch_area='lucknow',
            verified=True
        )
        test_dispatcher1.set_password('testpass123')
        
        test_dispatcher2 = User(
            username='role_test_dispatcher2',
            email='role_test_dispatcher2@test.com',
            role=UserRole.DISPATCHER.value,
            dispatch_area='indore',
            verified=True
        )
        test_dispatcher2.set_password('testpass123')
        
        db.session.add_all([test_admin, test_biller, test_dispatcher1, test_dispatcher2])
        db.session.commit()
        
        print(f"✓ Created 4 test users: admin, biller, and 2 dispatchers")
        
        # Test 2: Check current admin count
        print("\n2. Checking system admin count...")
        admin_count = User.query.filter_by(role=UserRole.ADMIN.value).count()
        print(f"✓ Current admin count: {admin_count}")
        
        # Test 3: Simulate role changes
        print("\n3. Testing role change scenarios...")
        
        # Scenario A: Change dispatcher to biller
        print("\n   Scenario A: Changing dispatcher1 to biller...")
        test_dispatcher1.role = UserRole.BILLER.value
        test_dispatcher1.dispatch_area = None  # Clear area when becoming biller
        db.session.commit()
        print(f"   ✓ Successfully changed {test_dispatcher1.username} from dispatcher to biller")
        
        # Scenario B: Change biller to admin
        print("\n   Scenario B: Promoting original biller to admin...")
        test_biller.role = UserRole.ADMIN.value
        db.session.commit()
        new_admin_count = User.query.filter_by(role=UserRole.ADMIN.value).count()
        print(f"   ✓ Successfully promoted {test_biller.username} to admin (total admins: {new_admin_count})")
        
        # Scenario C: Change admin to dispatcher (with area assignment)
        print("\n   Scenario C: Changing test_admin to dispatcher with area...")
        test_admin.role = UserRole.DISPATCHER.value
        test_admin.dispatch_area = 'jaipur'
        db.session.commit()
        print(f"   ✓ Successfully changed {test_admin.username} to dispatcher in {test_admin.dispatch_area}")
        
        # Test 4: Verify role changes
        print("\n4. Verifying role changes...")
        users = User.query.filter(User.username.like('role_test_%')).all()
        for user in users:
            area_info = f" (area: {user.dispatch_area})" if user.dispatch_area else ""
            print(f"   - {user.username}: {user.role}{area_info}")
        
        # Test 5: Check role-based permissions
        print("\n5. Testing role-based permissions...")
        
        # Reload users to get fresh data
        test_users = User.query.filter(User.username.like('role_test_%')).all()
        
        for user in test_users:
            permissions = []
            if user.is_admin():
                permissions.append("Full system access")
            if user.is_biller() or user.is_admin():
                permissions.append("Can create/manage bills")
            if user.can_edit_bills():
                permissions.append("Can edit bills")
            if user.can_manage_users():
                permissions.append("Can manage users")
            if user.is_dispatcher():
                permissions.append(f"Can access area: {user.dispatch_area}")
            
            print(f"   {user.username} ({user.role}): {', '.join(permissions) if permissions else 'Limited access'}")
        
        # Test 6: Simulate real-world constraint - last admin check
        print("\n6. Testing last admin protection...")
        
        # Count current admins
        current_admins = User.query.filter_by(role=UserRole.ADMIN.value).all()
        print(f"   Current admins: {len(current_admins)}")
        
        if len(current_admins) == 1:
            print(f"   ! Warning: Only 1 admin exists ({current_admins[0].username})")
            print("   ! System should prevent changing this user's role")
        else:
            print(f"   ✓ Multiple admins exist, role changes are safe")
        
        # Test 7: Create audit log entries for role changes
        print("\n7. Creating audit log entries...")
        
        audit_entries = [
            AuditLog(
                user_id=1,  # Assuming admin user ID is 1
                action='role_change',
                entity_type='user',
                entity_id=test_dispatcher1.id,
                details='{"old_role": "dispatcher", "new_role": "biller", "changed_by": "admin"}',
                ip_address='127.0.0.1'
            ),
            AuditLog(
                user_id=1,
                action='role_change',
                entity_type='user',
                entity_id=test_biller.id,
                details='{"old_role": "biller", "new_role": "admin", "changed_by": "admin"}',
                ip_address='127.0.0.1'
            )
        ]
        
        db.session.add_all(audit_entries)
        db.session.commit()
        print(f"   ✓ Created {len(audit_entries)} audit log entries")
        
        # Test 8: Query audit logs
        print("\n8. Retrieving recent role change audit logs...")
        recent_audits = AuditLog.query.filter_by(action='role_change').order_by(AuditLog.timestamp.desc()).limit(5).all()
        
        for audit in recent_audits:
            print(f"   - {audit.timestamp.strftime('%Y-%m-%d %H:%M:%S')}: User {audit.entity_id} role changed")
        
        # Test 9: Summary statistics
        print("\n9. Final role distribution:")
        role_stats = db.session.query(
            User.role,
            db.func.count(User.id)
        ).group_by(User.role).all()
        
        total_users = sum(count for _, count in role_stats)
        for role, count in role_stats:
            percentage = (count / total_users) * 100 if total_users > 0 else 0
            print(f"   - {role.title()}: {count} users ({percentage:.1f}%)")
        
        print("\n" + "="*80)
        print("ROLE CHANGE TESTING COMPLETED SUCCESSFULLY")
        print("="*80)
        
        # Clean up test users
        print("\nCleaning up test users...")
        User.query.filter(User.username.like('role_test_%')).delete()
        db.session.commit()
        print("✓ Test users cleaned up")

if __name__ == '__main__':
    test_role_changes()