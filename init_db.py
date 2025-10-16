"""Initialize database with default users"""
import os
import secrets
from app_clean import app, db
from models import User
from werkzeug.security import generate_password_hash

def init_users():
    with app.app_context():
        # Create admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # SECURITY: Admin password must be provided via environment variable
            admin_password = os.environ.get('ADMIN_PASSWORD')
            
            if not admin_password:
                # Generate a secure random password if none provided
                admin_password = secrets.token_urlsafe(16)
                print('=' * 80)
                print('WARNING: No ADMIN_PASSWORD environment variable set!')
                print('Generated secure random password for admin user:')
                print(f'USERNAME: admin')
                print(f'PASSWORD: {admin_password}')
                print('IMPORTANT: Save this password NOW! It will not be displayed again.')
                print('=' * 80)
            
            admin = User()
            admin.username = 'admin'
            admin.email = 'admin@tracetrack.com'
            admin.password_hash = generate_password_hash(admin_password)
            admin.role = 'admin'
            admin.dispatch_area = None
            admin.verified = True
            db.session.add(admin)
            print('Created admin user')
        
        # Create biller user if not exists (TEST/DEV ONLY)
        biller = User.query.filter_by(username='biller1').first()
        if not biller:
            biller_password = os.environ.get('BILLER_PASSWORD', 'biller123')
            biller = User()
            biller.username = 'biller1'
            biller.email = 'biller@tracetrack.com'
            biller.password_hash = generate_password_hash(biller_password)
            biller.role = 'biller'
            biller.dispatch_area = None
            biller.verified = True
            db.session.add(biller)
            print('Created biller1 user (TEST/DEV ONLY)')
        
        # Create dispatcher user if not exists (TEST/DEV ONLY)
        dispatcher = User.query.filter_by(username='dispatcher1').first()
        if not dispatcher:
            dispatcher_password = os.environ.get('DISPATCHER_PASSWORD', 'dispatcher123')
            dispatcher = User()
            dispatcher.username = 'dispatcher1'
            dispatcher.email = 'dispatcher@tracetrack.com'
            dispatcher.password_hash = generate_password_hash(dispatcher_password)
            dispatcher.role = 'dispatcher'
            dispatcher.dispatch_area = 'lucknow'
            dispatcher.verified = True
            db.session.add(dispatcher)
            print('Created dispatcher1 user (TEST/DEV ONLY)')
        
        try:
            db.session.commit()
            print('Database initialized successfully!')
        except Exception as e:
            db.session.rollback()
            print(f'Error: {e}')

if __name__ == '__main__':
    init_users()