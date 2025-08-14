import sys
sys.path.insert(0, '.')

from app_clean import app, db
from models import User, Bag, Link, BagType
from werkzeug.security import generate_password_hash

with app.app_context():
    # Clean up test data first
    Link.query.filter(Link.parent_bag_id.in_(
        db.session.query(Bag.id).filter(Bag.qr_id.like('TEST%'))
    )).delete(synchronize_session=False)
    
    Bag.query.filter(Bag.qr_id.like('TEST%')).delete()
    db.session.commit()
    
    # Create test parent bags with different numbers of children
    parent1 = Bag(qr_id='TEST_P001', type=BagType.PARENT.value, name='Test Parent 1')
    parent2 = Bag(qr_id='TEST_P002', type=BagType.PARENT.value, name='Test Parent 2')
    parent3 = Bag(qr_id='TEST_P003', type=BagType.PARENT.value, name='Test Parent 3')
    
    db.session.add_all([parent1, parent2, parent3])
    db.session.flush()
    
    # Create child bags and link them
    # Parent 1: 3 children
    for i in range(1, 4):
        child = Bag(qr_id=f'TEST_C1_{i:03d}', type=BagType.CHILD.value)
        db.session.add(child)
        db.session.flush()
        link = Link(parent_bag_id=parent1.id, child_bag_id=child.id)
        db.session.add(link)
    
    # Parent 2: 5 children  
    for i in range(1, 6):
        child = Bag(qr_id=f'TEST_C2_{i:03d}', type=BagType.CHILD.value)
        db.session.add(child)
        db.session.flush()
        link = Link(parent_bag_id=parent2.id, child_bag_id=child.id)
        db.session.add(link)
    
    # Parent 3: 0 children (unlinked)
    
    db.session.commit()
    
    # Verify the links
    print("Test data created:")
    print(f"Parent TEST_P001 has {Link.query.filter_by(parent_bag_id=parent1.id).count()} children")
    print(f"Parent TEST_P002 has {Link.query.filter_by(parent_bag_id=parent2.id).count()} children")
    print(f"Parent TEST_P003 has {Link.query.filter_by(parent_bag_id=parent3.id).count()} children")
    
    # Test the optimized query
    from optimized_bag_queries import OptimizedBagQueries
    
    bags_data, stats, total = OptimizedBagQueries.get_filtered_bags_with_stats(
        search_query='TEST_P'
    )
    
    print("\nOptimized query results:")
    for bag in bags_data:
        print(f"  {bag['qr_id']}: {bag.get('linked_children_count', 0)} children")
