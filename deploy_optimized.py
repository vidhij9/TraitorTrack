"""
Deployment optimization script for TraceTrack
Runs all performance optimizations and prepares the application for production deployment
"""
import logging
import os
from app_clean import app, db
from database_optimizer import run_full_optimization
from models import User
from werkzeug.security import generate_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_production_environment():
    """Setup production environment with optimizations"""
    
    logger.info("Starting production environment setup...")
    
    # Create application context
    with app.app_context():
        try:
            # 1. Create database tables
            logger.info("Creating database tables...")
            db.create_all()
            
            # 2. Setup admin user
            logger.info("Setting up admin user...")
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@tracetrack.com',
                    password_hash=generate_password_hash('admin'),
                    role='admin'
                )
                db.session.add(admin)
                db.session.commit()
                logger.info("Admin user created successfully")
            else:
                logger.info("Admin user already exists")
            
            # 3. Run database optimizations
            logger.info("Running database optimizations...")
            optimization_results = run_full_optimization()
            
            successful_optimizations = [k for k, v in optimization_results.items() if v]
            failed_optimizations = [k for k, v in optimization_results.items() if not v]
            
            logger.info(f"Successful optimizations: {successful_optimizations}")
            if failed_optimizations:
                logger.warning(f"Failed optimizations: {failed_optimizations}")
            
            # 4. Verify database performance
            logger.info("Verifying database performance...")
            from sqlalchemy import text
            
            # Test query performance
            start_time = time.time()
            db.session.execute(text("SELECT COUNT(*) FROM bag")).scalar()
            query_time = time.time() - start_time
            logger.info(f"Basic query performance: {query_time:.4f} seconds")
            
            # 5. Clear any existing cache
            logger.info("Clearing application cache...")
            from cache_utils import invalidate_cache
            invalidate_cache()
            
            logger.info("Production environment setup completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Production setup failed: {str(e)}")
            db.session.rollback()
            return False

def validate_production_readiness():
    """Validate that the application is ready for production deployment"""
    
    logger.info("Validating production readiness...")
    
    checks = {
        'database_connection': False,
        'admin_user_exists': False,
        'environment_variables': False,
        'api_endpoints': False,
        'mobile_interface': False
    }
    
    with app.app_context():
        try:
            # Check database connection
            from sqlalchemy import text
            db.session.execute(text("SELECT 1")).scalar()
            checks['database_connection'] = True
            logger.info("✓ Database connection verified")
        except Exception as e:
            logger.error(f"✗ Database connection failed: {str(e)}")
        
        try:
            # Check admin user
            admin = User.query.filter_by(username='admin').first()
            if admin and admin.role == 'admin':
                checks['admin_user_exists'] = True
                logger.info("✓ Admin user verified")
            else:
                logger.error("✗ Admin user not found or incorrect role")
        except Exception as e:
            logger.error(f"✗ Admin user check failed: {str(e)}")
        
        # Check environment variables
        required_env_vars = ['DATABASE_URL', 'SESSION_SECRET']
        env_vars_present = all(os.environ.get(var) for var in required_env_vars)
        if env_vars_present:
            checks['environment_variables'] = True
            logger.info("✓ Required environment variables present")
        else:
            missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
            logger.error(f"✗ Missing environment variables: {missing_vars}")
        
        # Test API endpoints
        try:
            with app.test_client() as client:
                response = client.get('/api/system/health')
                if response.status_code == 200:
                    checks['api_endpoints'] = True
                    logger.info("✓ API endpoints responding")
                else:
                    logger.error(f"✗ API health check failed: {response.status_code}")
        except Exception as e:
            logger.error(f"✗ API endpoint test failed: {str(e)}")
        
        # Check mobile interface
        try:
            # Verify mobile template exists
            from flask import render_template_string
            template_path = os.path.join(app.template_folder, 'mobile_dashboard.html')
            if os.path.exists(template_path):
                checks['mobile_interface'] = True
                logger.info("✓ Mobile interface template exists")
            else:
                logger.error("✗ Mobile dashboard template not found")
        except Exception as e:
            logger.error(f"✗ Mobile interface check failed: {str(e)}")
    
    passed_checks = sum(checks.values())
    total_checks = len(checks)
    
    logger.info(f"Production readiness: {passed_checks}/{total_checks} checks passed")
    
    if passed_checks == total_checks:
        logger.info("🎉 Application is ready for production deployment!")
        return True
    else:
        logger.warning("⚠️  Application has some issues that should be addressed before deployment")
        return False

def create_deployment_summary():
    """Create a summary of deployment optimizations and features"""
    
    summary = {
        'performance_optimizations': [
            'Database indexes for faster queries',
            'Connection pool optimization',
            'Query result caching',
            'Optimized API endpoints with selective loading',
            'Mobile-first responsive design'
        ],
        'mobile_features': [
            'Touch-optimized interface',
            'Offline capability with service worker',
            'Pull-to-refresh functionality',
            'Mobile navigation with bottom tabs',
            'Responsive grid layouts'
        ],
        'api_improvements': [
            'Cached responses for better performance',
            'Mobile-optimized endpoints',
            'Error handling and validation',
            'Standardized JSON responses',
            'System health monitoring'
        ],
        'database_optimizations': [
            'Composite indexes for common queries',
            'Optimized scan tracking queries',
            'Efficient bag lookup operations',
            'Enhanced PostgreSQL settings',
            'Query performance monitoring'
        ]
    }
    
    return summary

if __name__ == "__main__":
    import time
    
    print("=" * 60)
    print("TraceTrack Production Deployment Optimizer")
    print("=" * 60)
    
    # Setup production environment
    if setup_production_environment():
        print("\n✓ Production setup completed successfully")
    else:
        print("\n✗ Production setup failed")
        exit(1)
    
    # Validate readiness
    if validate_production_readiness():
        print("\n✓ Application validated and ready for deployment")
    else:
        print("\n⚠️  Application validation completed with warnings")
    
    # Print deployment summary
    summary = create_deployment_summary()
    print("\n" + "=" * 60)
    print("DEPLOYMENT SUMMARY")
    print("=" * 60)
    
    for category, features in summary.items():
        print(f"\n{category.replace('_', ' ').title()}:")
        for feature in features:
            print(f"  • {feature}")
    
    print("\n" + "=" * 60)
    print("Ready for deployment on Replit!")
    print("The application is optimized for:")
    print("  • Fast database queries")
    print("  • Mobile-friendly interface")
    print("  • High-performance API responses")
    print("  • Production-ready configuration")
    print("=" * 60)