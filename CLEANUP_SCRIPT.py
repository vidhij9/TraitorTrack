#!/usr/bin/env python3
"""
TraceTrack Codebase Cleanup Script
Removes duplicate, stale, and unused files to streamline the codebase.
"""

import os
import shutil
from pathlib import Path

# Files to DELETE (confirmed duplicates/unused)
FILES_TO_DELETE = [
    # Duplicate Authentication Files
    'basic_auth.py',
    'deployment_auth.py', 
    'final_auth.py',
    'production_auth_fix.py',
    'simple_auth_fix.py',
    'stateless_auth.py',
    'ultimate_auth.py',
    'working_auth.py',
    
    # Duplicate Application Files
    'main_clean.py',
    'main_fixed.py', 
    'main_restructured.py',
    'app_restructured.py',
    'app_environment_isolated.py',
    'production_main.py',
    
    # Duplicate API Files
    'api_improved.py',
    'api_endpoints.py',
    'optimized_api.py', 
    'high_performance_api.py',
    'optimized_bag_api.py',
    'mobile_api.py',
    
    # Duplicate Config Files
    'config_restructured.py',
    'deployment_config.py',
    'gunicorn_config.py',
    
    # Test & Development Files
    'test_account.py',
    'test_application.py',
    'test_database_isolation.py', 
    'test_routes.py',
    'demo_environment_isolation.py',
    'environment_demo.py',
    'api_demo.py',
    'performance_benchmark.py',
    'load_test.py',
    'quick_performance_test.py',
    
    # Seed & Setup Files (one-time use)
    'seed_db.py',
    'seed_test_data.py',
    'create_dev_test_data.py',
    'create_simple_admin.py',
    'quick_test_data.py',
    'setup_database_isolation.py',
    'setup_dev_database.py',
    'initialize_dev_database.py',
    'recreate_tables.py',
    
    # Database Management Duplicates
    'database_environment_switcher.py',
    'database_integrity_monitor.py', 
    'database_manager.py',
    'database_utils.py',
    'db_monitoring.py',
    'fix_database_isolation.py',
    'verify_current_isolation.py',
    'verify_database_integrity.py',
    
    # Deployment Duplicates
    'deploy_optimized.py',
    'deployment_test.py',
    'one-click-deploy.sh',
    'deploy.sh',
    'run_server.sh',
    'start.sh',
    'switch-to-dev.sh',
    'switch-to-prod.sh',
    
    # Temporary & Log Files
    'cookies.txt',
    'production_cookies.txt',
    'stateless_cookies.txt',
    'test_cookies.txt',
    'final_prod_test.txt',
    'final_test.txt',
    'prod_test.txt',
    'production_final.txt',
    'production_test.txt',
    'test_session.txt',
    'ultimate_test.txt',
    'working_test.txt',
    'fresh_session.txt',
    
    # Utility Duplicates
    'security_middleware.py',
    'security_test.py',
    'password_utils.py',
    'template_utils.py',
    'login_routes.py',
    'secure_login.py',
    'user_management.py',
    
    # Cleanup & Migration Scripts (one-time use)
    'cleanup_unlinked_children.py',
    'switch_environment.py',
    'environment_setup.md',
    'deployment_guide.md',
    
    # Backup Files
    'main_fixed.py.bak',
    'new_login.py.bak',
]

# Directories to clean
DIRS_TO_CLEAN = [
    'cache/',
    '__pycache__/',
    'logs/',
]

# Documentation files to consolidate
DOC_FILES_TO_MERGE = [
    'README_RESTRUCTURED.md',
    'RESTRUCTURE_SUMMARY.md', 
    'API_IMPROVEMENTS_SUMMARY.md',
    'PERFORMANCE_OPTIMIZATION_SUMMARY.md',
    'DATABASE_ISOLATION_GUIDE.md',
    'AWS_DEPLOYMENT_GUIDE.md',
    'AWS_DEPLOYMENT_COMPLETE_GUIDE.md',
]

def cleanup_files():
    """Remove duplicate and unused files"""
    deleted_count = 0
    
    print("🧹 Starting TraceTrack codebase cleanup...")
    
    # Delete individual files
    for file_path in FILES_TO_DELETE:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✅ Deleted: {file_path}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ Failed to delete {file_path}: {e}")
        else:
            print(f"⚠️  File not found: {file_path}")
    
    # Clean directories
    for dir_path in DIRS_TO_CLEAN:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"✅ Cleaned directory: {dir_path}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ Failed to clean {dir_path}: {e}")
    
    return deleted_count

def consolidate_documentation():
    """Consolidate multiple documentation files"""
    print("\n📚 Consolidating documentation...")
    
    consolidated_content = """# TraceTrack - Supply Chain Traceability Platform

## Overview
A cutting-edge supply chain traceability platform leveraging digital technologies to streamline agricultural bag tracking and management.

## Key Features
- Flask web framework with Python backend
- JWT-based stateless authentication  
- Mobile-first responsive design
- JavaScript-powered QR code scanning
- Role-based access control
- Real-time data tracking and analytics
- Comprehensive error logging and debugging

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python main.py

# Access at http://localhost:5000
# Default login: admin/admin
```

## File Structure
```
├── main.py              # Application entry point
├── app_clean.py         # Flask application configuration
├── routes.py            # URL routes and handlers
├── models.py            # Database models
├── forms.py             # Form definitions
├── templates/           # HTML templates
├── static/              # CSS, JS, images
└── mobile/              # Mobile app components
```

## API Endpoints
- `/api/stats` - System statistics
- `/api/scans` - Recent scan data
- `/api/bags/parent/list` - Parent bag listing
- `/api/bags/child/list` - Child bag listing

## Deployment
Use Replit deployment or configure with:
```bash
gunicorn --bind 0.0.0.0:5000 main:app
```

## Database
PostgreSQL with automatic table creation and optimization.

## Security
- CSRF protection on all forms
- Account lockout protection
- Session-based authentication
- Input validation and sanitization
"""
    
    try:
        with open('README.md', 'w') as f:
            f.write(consolidated_content)
        print("✅ Created consolidated README.md")
        
        # Remove old documentation files
        for doc_file in DOC_FILES_TO_MERGE:
            if os.path.exists(doc_file):
                os.remove(doc_file)
                print(f"✅ Removed old doc: {doc_file}")
                
    except Exception as e:
        print(f"❌ Failed to consolidate docs: {e}")

if __name__ == "__main__":
    deleted_count = cleanup_files()
    consolidate_documentation()
    
    print(f"\n🎉 Cleanup complete!")
    print(f"📊 Removed {deleted_count} duplicate/unused files")
    print(f"📚 Consolidated documentation into README.md")
    print(f"🚀 Codebase is now streamlined and production-ready")