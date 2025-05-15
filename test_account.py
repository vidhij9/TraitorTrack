from models import User, UserRole
from app import db, app

def test_admin_account():
    with app.app_context():
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print(f"Admin exists: {admin.username}, password hash: {admin.password_hash[:10]}...")
        else:
            print("Admin user does not exist")
            # Create admin user if doesn't exist
            admin = User()
            admin.username = "admin"
            admin.email = "admin@example.com"
            admin.role = UserRole.ADMIN.value
            admin.verified = True
            admin.set_password("adminpass")
            db.session.add(admin)
            db.session.commit()
            print(f"Created admin: {admin.username}, password hash: {admin.password_hash[:10]}...")

if __name__ == '__main__':
    test_admin_account()