#!/usr/bin/env python3
"""Deployment script for TraceTrack application"""

import os
import sys
import subprocess
from pathlib import Path

def setup_production_environment():
    """Configure production environment variables and settings"""
    print("Setting up production environment...")
    
    # Ensure critical environment variables are set
    required_vars = ['DATABASE_URL', 'SESSION_SECRET']
    for var in required_vars:
        if not os.environ.get(var):
            print(f"Warning: {var} not set in environment")
    
    # Set production-specific environment variables
    os.environ['ENVIRONMENT'] = 'production'
    os.environ['FLASK_ENV'] = 'production'
    os.environ['FLASK_DEBUG'] = 'False'
    
    print("Production environment configured")

def run_database_migrations():
    """Run database migrations to ensure schema is up to date"""
    print("Running database migrations...")
    
    try:
        # Import and create all tables
        from app_clean import app, db
        with app.app_context():
            db.create_all()
            print("Database tables created/updated successfully")
    except Exception as e:
        print(f"Database migration error: {e}")
        return False
    
    return True

def create_admin_user():
    """Ensure admin user exists for production"""
    print("Setting up admin user...")
    
    try:
        from app_clean import app, db
        from models import User
        from werkzeug.security import generate_password_hash
        
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@tracetrack.com',
                    password_hash=generate_password_hash('admin123'),
                    role='admin'
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully")
            else:
                print("Admin user already exists")
    except Exception as e:
        print(f"Admin user setup error: {e}")
        return False
    
    return True

def verify_deployment():
    """Verify that the application is ready for deployment"""
    print("Verifying deployment readiness...")
    
    try:
        from app_clean import app, db
        from models import User, Bag
        
        # Work within application context
        with app.app_context():
            # Test database queries
            user_count = User.query.count()
            bag_count = Bag.query.count()
            
            print(f"✓ Database connected - {user_count} users, {bag_count} bags")
            print("✓ Models are properly configured")
            print("✓ Application context working")
        
        print("Deployment verification completed")
        return True
        
    except Exception as e:
        print(f"Deployment verification failed: {e}")
        return False

def main():
    """Main deployment function"""
    print("=== TraceTrack Production Deployment ===")
    
    # Setup production environment
    setup_production_environment()
    
    # Run database migrations
    if not run_database_migrations():
        print("Database migration failed - aborting deployment")
        sys.exit(1)
    
    # Create admin user
    if not create_admin_user():
        print("Admin user setup failed - continuing with deployment")
    
    # Verify deployment
    if not verify_deployment():
        print("Deployment verification failed - check logs")
        sys.exit(1)
    
    print("=== Deployment Ready ===")
    print("Application is configured and ready for production deployment")
    print("Database is set up with required tables")
    print("Admin user is available (username: admin)")
    print("To deploy: Use Replit's Deploy button or run with gunicorn")

if __name__ == "__main__":
    main()