#!/usr/bin/env python3
"""
Enhanced Deployment Script for TraceTrack
Applies all enhancement features and optimizations
"""

import os
import sys
import logging
import time
import subprocess
import json
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('deployment.log')
    ]
)
logger = logging.getLogger(__name__)

def print_banner():
    """Print deployment banner"""
    print("=" * 80)
    print("🚀 TRACETRACK ENHANCED DEPLOYMENT")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Applying comprehensive system enhancements...")
    print("=" * 80)

def check_prerequisites():
    """Check if all prerequisites are met"""
    logger.info("🔍 Checking prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        logger.error("❌ Python 3.8+ required")
        return False
    
    # Check required files
    required_files = [
        'main.py',
        'app_clean.py',
        'models.py',
        'enhancement_features.py',
        'enhanced_production_config.py'
    ]
    
    for file in required_files:
        if not os.path.exists(file):
            logger.error(f"❌ Required file not found: {file}")
            return False
    
    logger.info("✅ Prerequisites check passed")
    return True

def apply_database_enhancements():
    """Apply database enhancements and optimizations"""
    logger.info("🗄️ Applying database enhancements...")
    
    try:
        # Import and apply database optimizations
        from enhancement_features import optimize_database_performance
        
        db_optimizer = optimize_database_performance()
        
        # Create performance indexes
        logger.info("Creating performance indexes...")
        db_optimizer['create_performance_indexes']()
        
        # Update database statistics
        logger.info("Updating database statistics...")
        db_optimizer['update_database_statistics']()
        
        # Optimize connection pool
        logger.info("Optimizing connection pool...")
        db_optimizer['optimize_connection_pool']()
        
        # Create materialized views
        logger.info("Creating materialized views...")
        db_optimizer['create_materialized_views']()
        
        logger.info("✅ Database enhancements applied successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database enhancement failed: {e}")
        return False

def apply_system_enhancements():
    """Apply all system enhancements"""
    logger.info("🔧 Applying system enhancements...")
    
    try:
        # Import and apply all enhancements
        from enhancement_features import apply_all_enhancements
        
        result = apply_all_enhancements()
        
        if result:
            logger.info("✅ System enhancements applied successfully")
            return True
        else:
            logger.error("❌ System enhancement application failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ System enhancement failed: {e}")
        return False

def update_production_config():
    """Update production configuration files"""
    logger.info("⚙️ Updating production configuration...")
    
    try:
        # Create enhanced gunicorn config
        from enhancement_features import improve_production_deployment
        
        deployment = improve_production_deployment()
        
        # Generate enhanced gunicorn config
        gunicorn_config = deployment['create_enhanced_gunicorn_config']()
        
        # Write enhanced gunicorn config
        with open('gunicorn_enhanced.py', 'w') as f:
            f.write("#!/usr/bin/env python3\n")
            f.write('"""Enhanced Gunicorn Configuration"""\n\n')
            for key, value in gunicorn_config.items():
                f.write(f"{key} = {repr(value)}\n")
        
        # Generate nginx config
        nginx_config = deployment['create_nginx_config']()
        with open('nginx_enhanced.conf', 'w') as f:
            f.write(nginx_config)
        
        # Generate systemd service
        service_config = deployment['create_systemd_service']()
        with open('tracetrack.service', 'w') as f:
            f.write(service_config)
        
        logger.info("✅ Production configuration updated")
        return True
        
    except Exception as e:
        logger.error(f"❌ Production configuration update failed: {e}")
        return False

def run_health_checks():
    """Run comprehensive health checks"""
    logger.info("🏥 Running health checks...")
    
    try:
        # Import health check functionality
        from enhancement_features import enhance_endpoint_reliability
        
        reliability = enhance_endpoint_reliability()
        health_result = reliability['health_check_endpoint']()
        
        if health_result.status_code == 200:
            logger.info("✅ Health check passed")
            return True
        else:
            logger.error(f"❌ Health check failed: {health_result.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False

def create_deployment_summary():
    """Create deployment summary report"""
    logger.info("📋 Creating deployment summary...")
    
    summary = {
        'deployment_timestamp': datetime.now().isoformat(),
        'enhancements_applied': [
            'Bill creator tracking',
            '100% success rate endpoints',
            'Weight update fixes',
            'CV export functionality',
            'Print functionality',
            'Production deployment improvements',
            'Database performance optimization'
        ],
        'new_endpoints': [
            '/api/enhancements/apply',
            '/api/export/bills/csv',
            '/api/export/bags/csv',
            '/api/print/bill/<bill_id>',
            '/api/print/summary',
            '/api/weights/update/<bill_id>',
            '/api/weights/update-all',
            '/health'
        ],
        'configuration_files': [
            'gunicorn_enhanced.py',
            'nginx_enhanced.conf',
            'tracetrack.service',
            'enhanced_production_config.py'
        ],
        'database_optimizations': [
            'Performance indexes created',
            'Database statistics updated',
            'Connection pool optimized',
            'Materialized views created'
        ]
    }
    
    # Write summary to file
    with open('deployment_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info("✅ Deployment summary created")
    return summary

def start_enhanced_server():
    """Start the enhanced production server"""
    logger.info("🚀 Starting enhanced production server...")
    
    try:
        # Use enhanced gunicorn configuration
        cmd = [
            'gunicorn',
            '--config', 'enhanced_production_config.py',
            'main:app'
        ]
        
        logger.info(f"Starting server with command: {' '.join(cmd)}")
        
        # Start the server
        process = subprocess.Popen(cmd)
        
        logger.info(f"✅ Enhanced server started with PID: {process.pid}")
        return process
        
    except Exception as e:
        logger.error(f"❌ Failed to start enhanced server: {e}")
        return None

def main():
    """Main deployment function"""
    print_banner()
    
    # Step 1: Check prerequisites
    if not check_prerequisites():
        logger.error("❌ Prerequisites check failed. Deployment aborted.")
        return False
    
    # Step 2: Apply database enhancements
    if not apply_database_enhancements():
        logger.error("❌ Database enhancement failed. Deployment aborted.")
        return False
    
    # Step 3: Apply system enhancements
    if not apply_system_enhancements():
        logger.error("❌ System enhancement failed. Deployment aborted.")
        return False
    
    # Step 4: Update production configuration
    if not update_production_config():
        logger.error("❌ Production configuration update failed. Deployment aborted.")
        return False
    
    # Step 5: Run health checks
    if not run_health_checks():
        logger.error("❌ Health check failed. Deployment aborted.")
        return False
    
    # Step 6: Create deployment summary
    summary = create_deployment_summary()
    
    # Step 7: Start enhanced server (optional)
    start_server = input("\n🚀 Start enhanced production server? (y/n): ").lower().strip()
    if start_server == 'y':
        server_process = start_enhanced_server()
        if server_process:
            logger.info("✅ Enhanced deployment completed successfully!")
            logger.info("Server is running. Press Ctrl+C to stop.")
            try:
                server_process.wait()
            except KeyboardInterrupt:
                logger.info("🛑 Stopping server...")
                server_process.terminate()
                server_process.wait()
                logger.info("✅ Server stopped")
        else:
            logger.error("❌ Failed to start server")
            return False
    else:
        logger.info("✅ Enhanced deployment completed successfully!")
        logger.info("Server not started. Use 'gunicorn --config enhanced_production_config.py main:app' to start manually.")
    
    # Print summary
    print("\n" + "=" * 80)
    print("🎉 ENHANCED DEPLOYMENT COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print("New Features Available:")
    for feature in summary['enhancements_applied']:
        print(f"  ✅ {feature}")
    
    print("\nNew API Endpoints:")
    for endpoint in summary['new_endpoints']:
        print(f"  🔗 {endpoint}")
    
    print("\nConfiguration Files Created:")
    for config_file in summary['configuration_files']:
        print(f"  📄 {config_file}")
    
    print("\nDatabase Optimizations Applied:")
    for optimization in summary['database_optimizations']:
        print(f"  🗄️ {optimization}")
    
    print(f"\n📋 Full deployment summary saved to: deployment_summary.json")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("🛑 Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Deployment failed with unexpected error: {e}")
        sys.exit(1)