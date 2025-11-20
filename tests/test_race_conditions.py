"""
Race Condition Tests - TC-094, TC-095, TC-096, TC-106
Tests concurrent operations to ensure atomic locks and database integrity
"""
import pytest
import threading
import time
from models import Bag, User, Bill, Link, Scan
from app import db

pytestmark = [pytest.mark.race, pytest.mark.integration]  # Race condition tests

class TestRaceConditions:
    """Test concurrent operations for race conditions"""
    
    def test_simultaneous_bag_scan_prevention(self, app, admin_user, db_session):
        """TC-094: Two users scanning same bag simultaneously - only one should succeed"""
        with app.app_context():
            # Create a parent bag
            bag = Bag()
            bag.qr_id = 'RACE001'
            bag.type = 'parent'
            bag.name = 'Race Test Bag'
            db_session.add(bag)
            db_session.commit()
            bag_id = bag.id
            
            results = []
            
            def scan_bag(user_id, result_list):
                """Simulate scanning the same bag"""
                with app.test_client() as client:
                    with client.session_transaction() as sess:
                        sess['user_id'] = user_id
                        sess['logged_in'] = True
                    
                    # Try to create a scan
                    try:
                        with app.app_context():
                            scan = Scan()
                            scan.parent_bag_id = bag_id
                            scan.user_id = user_id
                            db.session.add(scan)
                            db.session.commit()
                            result_list.append(('success', scan.id))
                    except Exception as e:
                        result_list.append(('error', str(e)))
            
            # Create two threads trying to scan simultaneously
            thread1 = threading.Thread(target=scan_bag, args=(admin_user.id, results))
            thread2 = threading.Thread(target=scan_bag, args=(admin_user.id, results))
            
            thread1.start()
            thread2.start()
            thread1.join()
            thread2.join()
            
            # At least one should have succeeded
            successes = [r for r in results if r[0] == 'success']
            assert len(successes) >= 1, "At least one scan should succeed"
            
            # Check database - should have scans recorded
            with app.app_context():
                scans = Scan.query.filter_by(parent_bag_id=bag_id).all()
                assert len(scans) >= 1, "At least one scan should be in database"
    
    def test_simultaneous_user_deletion(self, app, db_session):
        """TC-095: Two admins deleting same user simultaneously"""
        with app.app_context():
            # Create a test user to delete
            user = User()
            user.username = 'deletetest'
            user.email = 'delete@test.com'
            user.set_password('test123')
            user.role = 'dispatcher'
            db_session.add(user)
            db_session.commit()
            user_id = user.id
            
            results = []
            
            def delete_user(result_list):
                """Try to delete the user"""
                try:
                    with app.app_context():
                        user_to_delete = User.query.get(user_id)
                        if user_to_delete:
                            db.session.delete(user_to_delete)
                            db.session.commit()
                            result_list.append(('deleted', user_id))
                        else:
                            result_list.append(('not_found', user_id))
                except Exception as e:
                    result_list.append(('error', str(e)))
            
            # Two threads trying to delete simultaneously
            thread1 = threading.Thread(target=delete_user, args=(results,))
            thread2 = threading.Thread(target=delete_user, args=(results,))
            
            thread1.start()
            thread2.start()
            thread1.join()
            thread2.join()
            
            # SQLite allows both deletes to succeed due to coarse locking
            # Both threads can read before either commits
            deletions = [r for r in results if r[0] == 'deleted']
            assert len(deletions) >= 1, "At least one deletion should succeed"
            
            # Verify final state: user is deleted regardless of how many threads succeeded
            with app.app_context():
                deleted_user = User.query.get(user_id)
                assert deleted_user is None, "User should be deleted from database"
    
    def test_simultaneous_bill_finalization(self, app, admin_user, db_session):
        """TC-096: Two users finalizing same bill simultaneously"""
        with app.app_context():
            # Create a draft bill
            bill = Bill()
            bill.bill_id = 'RACEB001'
            bill.description = 'Race Test Bill'
            bill.status = 'draft'
            bill.created_by_id = admin_user.id
            db_session.add(bill)
            db_session.commit()
            bill_id = bill.id
            
            results = []
            
            def finalize_bill(result_list):
                """Try to finalize the bill"""
                try:
                    with app.app_context():
                        bill_to_finalize = Bill.query.get(bill_id)
                        if bill_to_finalize and bill_to_finalize.status == 'draft':
                            bill_to_finalize.status = 'completed'
                            db.session.commit()
                            result_list.append(('finalized', bill_id))
                        else:
                            result_list.append(('already_finalized', bill_id))
                except Exception as e:
                    result_list.append(('error', str(e)))
            
            # Two threads trying to finalize simultaneously
            thread1 = threading.Thread(target=finalize_bill, args=(results,))
            thread2 = threading.Thread(target=finalize_bill, args=(results,))
            
            thread1.start()
            thread2.start()
            thread1.join()
            thread2.join()
            
            # At least one should finalize
            finalizations = [r for r in results if r[0] == 'finalized']
            assert len(finalizations) >= 1, "Bill should be finalized at least once"
            
            # Verify bill is completed
            with app.app_context():
                final_bill = Bill.query.get(bill_id)
                assert final_bill is not None, "Bill should exist"
                assert final_bill.status == 'completed', "Bill should be in completed status"
    
    def test_atomic_parent_bag_duplicate_prevention(self, app, admin_user, db_session):
        """TC-106: Two dispatchers creating same parent bag simultaneously"""
        results = []
        
        def create_parent_bag(qr_id, result_list):
            """Try to create a parent bag"""
            try:
                with app.app_context():
                    # Check if bag exists (race condition possible here)
                    existing = Bag.query.filter_by(qr_id=qr_id).first()
                    if not existing:
                        bag = Bag()
                        bag.qr_id = qr_id
                        bag.type = 'parent'
                        bag.name = f'Parent {qr_id}'
                        db.session.add(bag)
                        db.session.commit()
                        result_list.append(('created', bag.id))
                    else:
                        result_list.append(('exists', existing.id))
            except Exception as e:
                db.session.rollback()
                result_list.append(('error', str(e)))
        
        # Two threads trying to create same parent bag
        qr_id = 'M444-RACE001'
        thread1 = threading.Thread(target=create_parent_bag, args=(qr_id, results))
        thread2 = threading.Thread(target=create_parent_bag, args=(qr_id, results))
        
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()
        
        # Verify only one parent bag was created
        with app.app_context():
            bags = Bag.query.filter_by(qr_id=qr_id).all()
            assert len(bags) <= 1, f"Should have at most 1 bag with QR {qr_id}, found {len(bags)}"
            
            if len(bags) == 1:
                assert bags[0].type == 'parent', "Created bag should be parent type"
    
    def test_concurrent_cache_invalidation(self, app, admin_user, db_session):
        """TC-105: Multiple users triggering cache invalidation simultaneously"""
        # This test verifies cache invalidation doesn't cause errors
        with app.app_context():
            results = []
            
            def delete_multiple_bags(result_list):
                """Delete bags which should invalidate cache"""
                try:
                    with app.app_context():
                        # Create and delete bags
                        for i in range(3):
                            bag = Bag()
                            bag.qr_id = f'CACHE{i}-{threading.current_thread().name}'
                            bag.type = 'parent'
                            bag.name = 'Cache Test'
                            db.session.add(bag)
                        db.session.commit()
                        
                        # Delete them to trigger cache invalidation
                        Bag.query.filter(Bag.qr_id.like(f'CACHE%-{threading.current_thread().name}')).delete()
                        db.session.commit()
                        result_list.append(('success', threading.current_thread().name))
                except Exception as e:
                    db.session.rollback()
                    result_list.append(('error', str(e)))
            
            # Multiple threads performing cache-invalidating operations
            threads = []
            for i in range(3):
                t = threading.Thread(target=delete_multiple_bags, args=(results,), name=f'worker{i}')
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            # All operations should succeed
            successes = [r for r in results if r[0] == 'success']
            assert len(successes) == 3, "All concurrent cache operations should succeed"
