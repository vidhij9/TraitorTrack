#!/usr/bin/env python3
"""
Emergency script to fix admin password issues in production.
This script properly resets admin passwords without affecting any bag data.

SAFETY: This script only updates password hashes for admin accounts.
        It does NOT delete or modify any bag data.

Usage:
    python fix_admin_passwords.py

This will:
1. Connect to the appropriate database (dev or production based on environment)
2. Reset admin and superadmin passwords to 'vidhi2029'
3. Clear any lockout status
4. Verify the fix worked
"""

import os
import sys
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_admin_passwords():
    """Fix admin password issues by properly resetting them"""
    
    try:
        # Import Flask app and dependencies
        from app import app, db
        from models import User
        from werkzeug.security import generate_password_hash
        
        with app.app_context():
            logger.info("=" * 80)
            logger.info("🔧 ADMIN PASSWORD FIX SCRIPT")
            logger.info("=" * 80)
            
            # Check which database we're connected to
            is_production = (
                os.environ.get('REPLIT_DEPLOYMENT') == '1' and 
                os.environ.get('FORCE_DEV_DB', '').lower() not in ('1', 'true', 'yes')
            )
            
            db_type = "PRODUCTION (AWS RDS)" if is_production else "DEVELOPMENT (Replit PostgreSQL)"
            logger.info(f"📊 Connected to: {db_type}")
            
            # Safety check - count bags to ensure we're not affecting bag data
            from models import Bag
            bag_count = Bag.query.count()
            logger.info(f"✅ Database has {bag_count} bags (will NOT be modified)")
            
            # Fix admin account
            logger.info("\n🔐 Fixing admin account...")
            admin = User.query.filter_by(username='admin').first()
            
            if admin:
                # Set password using the same method as regular users
                new_password = 'vidhi2029'
                admin.password_hash = generate_password_hash(new_password)
                admin.role = 'admin'
                admin.verified = True
                admin.failed_login_attempts = 0
                admin.locked_until = None
                admin.last_failed_login = None
                
                db.session.commit()
                logger.info(f"✅ Admin account reset successfully")
                logger.info(f"   - Username: admin")
                logger.info(f"   - Password: vidhi2029")
                logger.info(f"   - Lockout cleared: Yes")
                logger.info(f"   - Hash prefix: {admin.password_hash[:20]}...")
            else:
                logger.warning("⚠️  Admin account not found - creating new one")
                admin = User()
                admin.username = 'admin'
                admin.email = 'admin@traitortrack.com'
                admin.password_hash = generate_password_hash('vidhi2029')
                admin.role = 'admin'
                admin.verified = True
                admin.failed_login_attempts = 0
                admin.locked_until = None
                
                db.session.add(admin)
                db.session.commit()
                logger.info("✅ Admin account created successfully")
            
            # Fix superadmin account
            logger.info("\n🔐 Fixing superadmin account...")
            superadmin = User.query.filter_by(username='superadmin').first()
            
            if superadmin:
                superadmin.password_hash = generate_password_hash('vidhi2029')
                superadmin.role = 'admin'
                superadmin.verified = True
                superadmin.failed_login_attempts = 0
                superadmin.locked_until = None
                superadmin.last_failed_login = None
                
                db.session.commit()
                logger.info(f"✅ Superadmin account reset successfully")
                logger.info(f"   - Username: superadmin")
                logger.info(f"   - Password: vidhi2029")
                logger.info(f"   - Lockout cleared: Yes")
                logger.info(f"   - Hash prefix: {superadmin.password_hash[:20]}...")
            else:
                logger.warning("⚠️  Superadmin account not found - creating new one")
                superadmin = User()
                superadmin.username = 'superadmin'
                superadmin.email = 'superadmin@traitortrack.com'
                superadmin.password_hash = generate_password_hash('vidhi2029')
                superadmin.role = 'admin'
                superadmin.verified = True
                superadmin.failed_login_attempts = 0
                superadmin.locked_until = None
                
                db.session.add(superadmin)
                db.session.commit()
                logger.info("✅ Superadmin account created successfully")
            
            # Verify the fix by testing password verification
            logger.info("\n🔍 Verifying password fix...")
            from werkzeug.security import check_password_hash
            
            # Re-query to get fresh data
            admin = User.query.filter_by(username='admin').first()
            superadmin = User.query.filter_by(username='superadmin').first()
            
            admin_check = check_password_hash(admin.password_hash, 'vidhi2029')
            superadmin_check = check_password_hash(superadmin.password_hash, 'vidhi2029')
            
            if admin_check:
                logger.info("✅ Admin password verification: PASSED")
            else:
                logger.error("❌ Admin password verification: FAILED")
            
            if superadmin_check:
                logger.info("✅ Superadmin password verification: PASSED")
            else:
                logger.error("❌ Superadmin password verification: FAILED")
            
            # Final safety check - ensure bags are untouched
            final_bag_count = Bag.query.count()
            if final_bag_count == bag_count:
                logger.info(f"\n✅ SAFETY CHECK: All {bag_count} bags remain untouched")
            else:
                logger.error(f"❌ UNEXPECTED: Bag count changed from {bag_count} to {final_bag_count}")
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ PASSWORD FIX COMPLETE")
            logger.info("=" * 80)
            logger.info("\n📝 Next steps:")
            logger.info("1. Try logging in with: admin / vidhi2029")
            logger.info("2. Also try: superadmin / vidhi2029")
            logger.info("3. Both should work now in production")
            logger.info("\n⚠️  IMPORTANT: The app.py file has been modified to prevent")
            logger.info("   automatic password resets on startup. Passwords will only")
            logger.info("   be reset if FORCE_ADMIN_PASSWORD_RESET=1 is set.")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error fixing passwords: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = fix_admin_passwords()
    sys.exit(0 if success else 1)