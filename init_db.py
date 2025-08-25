"""Initialize database with default users"""
from app_clean import app, db
from models import User
from werkzeug.security import generate_password_hash

def init_users():
    with app.app_context():
        # Create admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User()
            admin.username = 'admin'
            admin.email = 'admin@tracetrack.com'
            admin.password_hash = generate_password_hash('admin123')
            admin.role = 'admin'
            admin.dispatch_area = None
            admin.verified = True
            db.session.add(admin)
            print('Created admin user')
        
        # Create biller user if not exists
        biller = User.query.filter_by(username='biller').first()
        if not biller:
            biller = User()
            biller.username = 'biller'
            biller.email = 'biller@tracetrack.com'
            biller.password_hash = generate_password_hash('biller123')
            biller.role = 'biller'
            biller.dispatch_area = None
            biller.verified = True
            db.session.add(biller)
            print('Created biller user')
        
        # Create dispatcher user if not exists
        dispatcher = User.query.filter_by(username='dispatcher').first()
        if not dispatcher:
            dispatcher = User()
            dispatcher.username = 'dispatcher'
            dispatcher.email = 'dispatcher@tracetrack.com'
            dispatcher.password_hash = generate_password_hash('dispatcher123')
            dispatcher.role = 'dispatcher'
            dispatcher.dispatch_area = 'lucknow'
            dispatcher.verified = True
            db.session.add(dispatcher)
            print('Created dispatcher user')
        
        try:
            db.session.commit()
            print('Database initialized successfully!')
        except Exception as e:
            db.session.rollback()
            print(f'Error: {e}')

if __name__ == '__main__':
    init_users()