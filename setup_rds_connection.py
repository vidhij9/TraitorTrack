#!/usr/bin/env python3
"""
RDS Connection Setup Script
This script helps you configure the RDS database connection for migration
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def test_connection(db_url):
    """Test database connection"""
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        return True, version[0]
    except Exception as e:
        return False, str(e)

def get_database_info(db_url):
    """Get database information"""
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Get database name
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]
        
        # Get table count
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_count = cursor.fetchone()[0]
        
        # Get existing tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return {
            'database': db_name,
            'table_count': table_count,
            'tables': tables
        }
    except Exception as e:
        return {'error': str(e)}

def main():
    print("🗄️ RDS Database Connection Setup")
    print("=" * 50)
    
    # Check for existing environment variables
    db_url = os.environ.get('AWS_DATABASE_URL') or os.environ.get('DATABASE_URL')
    
    if db_url:
        print(f"✅ Found database URL: {db_url}")
        print()
        
        # Test connection
        print("🔍 Testing database connection...")
        success, result = test_connection(db_url)
        
        if success:
            print(f"✅ Connection successful!")
            print(f"📊 Database version: {result}")
            print()
            
            # Get database info
            print("📋 Analyzing database structure...")
            info = get_database_info(db_url)
            
            if 'error' not in info:
                print(f"📁 Database: {info['database']}")
                print(f"📊 Tables: {info['table_count']}")
                print(f"📋 Existing tables: {', '.join(info['tables']) if info['tables'] else 'None'}")
                print()
                
                if info['table_count'] > 0:
                    print("🎯 Ready for migration!")
                    print("Your database contains existing data that will be migrated to the new schema.")
                    print()
                    print("To proceed with deployment and migration:")
                    print("1. Run: ./deploy.sh")
                    print("2. Or run: python deploy_aws_complete.py")
                else:
                    print("📝 Empty database detected.")
                    print("The deployment will create the new schema structure.")
                    print()
                    print("To proceed with deployment:")
                    print("1. Run: ./deploy.sh")
                    print("2. Or run: python deploy_aws_complete.py")
            else:
                print(f"❌ Error analyzing database: {info['error']}")
        else:
            print(f"❌ Connection failed: {result}")
            print()
            print("Please check your database URL and credentials.")
    else:
        print("❌ No database URL found in environment variables.")
        print()
        print("Please set your RDS database URL:")
        print()
        print("Option 1: Set environment variable")
        print("export AWS_DATABASE_URL=\"postgresql://user:pass@your-rds-endpoint:5432/dbname\"")
        print()
        print("Option 2: Interactive setup")
        print("Enter your database details:")
        
        try:
            host = input("Host (RDS endpoint): ").strip()
            port = input("Port (default 5432): ").strip() or "5432"
            database = input("Database name: ").strip()
            username = input("Username: ").strip()
            password = input("Password: ").strip()
            
            if all([host, database, username, password]):
                db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
                
                print()
                print("🔍 Testing connection...")
                success, result = test_connection(db_url)
                
                if success:
                    print("✅ Connection successful!")
                    print()
                    print("To use this connection, set the environment variable:")
                    print(f"export AWS_DATABASE_URL=\"{db_url}\"")
                    print()
                    print("Then run the deployment:")
                    print("1. ./deploy.sh")
                    print("2. Or python deploy_aws_complete.py")
                else:
                    print(f"❌ Connection failed: {result}")
                    print("Please check your credentials and try again.")
            else:
                print("❌ Missing required information.")
        except KeyboardInterrupt:
            print("\n\nSetup cancelled.")
            sys.exit(1)

if __name__ == "__main__":
    main()