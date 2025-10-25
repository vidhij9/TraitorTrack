#!/usr/bin/env python3
"""
Database Migration Management Script
 
This script provides CLI commands for managing database migrations using Flask-Migrate/Alembic.
"""

from app import app, db
from flask_migrate import Migrate, init, migrate, upgrade, downgrade, current, history

# Note: Migrate is already initialized in app.py, just importing it here for CLI commands

if __name__ == '__main__':
    import sys
    
    with app.app_context():
        if len(sys.argv) < 2:
            print("Usage: python manage.py [command]")
            print("\nAvailable commands:")
            print("  init       - Initialize migrations directory (first time only)")
            print("  migrate    - Generate a new migration from model changes")
            print("  upgrade    - Apply pending migrations to database")
            print("  downgrade  - Rollback the last migration")
            print("  current    - Show current migration version")
            print("  history    - Show migration history")
            print("\nExamples:")
            print("  python manage.py init")
            print("  python manage.py migrate -m 'Add user lockout columns'")
            print("  python manage.py upgrade")
            sys.exit(1)
        
        command = sys.argv[1]
        
        if command == 'init':
            print("Initializing migrations directory...")
            init()
            print("Migrations directory created successfully!")
            
        elif command == 'migrate':
            message = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == '-m' else 'Auto-generated migration'
            print(f"Generating migration: {message}")
            migrate(message=message)
            print("Migration generated successfully!")
            
        elif command == 'upgrade':
            print("Applying migrations...")
            upgrade()
            print("Database upgraded successfully!")
            
        elif command == 'downgrade':
            print("Rolling back last migration...")
            downgrade()
            print("Migration rolled back successfully!")
            
        elif command == 'current':
            print("Current migration version:")
            current()
            
        elif command == 'history':
            print("Migration history:")
            history()
            
        else:
            print(f"Unknown command: {command}")
            print("Run 'python manage.py' to see available commands")
            sys.exit(1)
