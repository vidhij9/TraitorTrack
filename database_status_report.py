"""
Database Status Report
Comprehensive analysis of database isolation and configuration
"""
import os
import logging
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_database_report():
    """Generate comprehensive database status report"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found")
    
    engine = create_engine(database_url)
    
    report = {
        'environment_detection': {},
        'schema_analysis': {},
        'table_analysis': {},
        'data_isolation': {},
        'recommendations': []
    }
    
    with engine.connect() as conn:
        # Environment Detection Analysis
        from app_clean import get_current_environment
        current_env = get_current_environment()
        report['environment_detection'] = {
            'detected_environment': current_env,
            'environment_var': os.environ.get('ENVIRONMENT', 'not_set'),
            'flask_env': os.environ.get('FLASK_ENV', 'not_set'),
            'replit_env': os.environ.get('REPLIT_ENVIRONMENT', 'not_set'),
            'repl_slug': os.environ.get('REPL_SLUG', 'not_set')
        }
        
        # Schema Analysis
        schemas = conn.execute(text("""
            SELECT schema_name, 
                   COUNT(*) as table_count
            FROM information_schema.tables 
            WHERE schema_name IN ('development', 'production', 'public')
            GROUP BY schema_name
            ORDER BY schema_name
        """)).fetchall()
        
        for schema, table_count in schemas:
            report['schema_analysis'][schema] = {'table_count': table_count}
        
        # Detailed Table Analysis
        required_tables = ['user', 'bag', 'link', 'bill', 'billbag', 'scan', 'promotionrequest']
        
        for schema in ['development', 'production']:
            tables = conn.execute(text(f"""
                SELECT table_name, 
                       pg_size_pretty(pg_total_relation_size('{schema}.'||table_name)) as size
                FROM information_schema.tables 
                WHERE table_schema = '{schema}'
                ORDER BY table_name
            """)).fetchall()
            
            table_names = [t[0] for t in tables]
            missing_tables = [t for t in required_tables if t not in table_names]
            extra_tables = [t for t in table_names if t not in required_tables]
            
            report['table_analysis'][schema] = {
                'existing_tables': table_names,
                'missing_tables': missing_tables,
                'extra_tables': extra_tables,
                'table_sizes': dict(tables),
                'is_complete': len(missing_tables) == 0
            }
        
        # Data Isolation Test
        for schema in ['development', 'production']:
            conn.execute(text(f"SET search_path TO {schema}"))
            user_count = conn.execute(text('SELECT COUNT(*) FROM "user"')).scalar()
            bag_count = conn.execute(text('SELECT COUNT(*) FROM bag')).scalar() if 'bag' in report['table_analysis'][schema]['existing_tables'] else 0
            scan_count = conn.execute(text('SELECT COUNT(*) FROM scan')).scalar() if 'scan' in report['table_analysis'][schema]['existing_tables'] else 0
            
            report['data_isolation'][schema] = {
                'user_count': user_count,
                'bag_count': bag_count,
                'scan_count': scan_count
            }
        
        # Generate Recommendations
        recommendations = []
        
        # Check for missing tables
        for schema in ['development', 'production']:
            missing = report['table_analysis'][schema]['missing_tables']
            if missing:
                recommendations.append(f"❌ {schema.title()} schema missing tables: {', '.join(missing)}")
            else:
                recommendations.append(f"✅ {schema.title()} schema has all required tables")
        
        # Check data isolation
        dev_users = report['data_isolation']['development']['user_count']
        prod_users = report['data_isolation']['production']['user_count']
        
        if dev_users > 0 and prod_users > 0:
            recommendations.append("✅ Both environments have user data - isolation working")
        elif dev_users > 0 and prod_users == 0:
            recommendations.append("⚠️  Development has data, production empty - normal for new deployment")
        else:
            recommendations.append("❌ Database isolation may not be working properly")
        
        # Environment detection
        if current_env in ['development', 'production']:
            recommendations.append(f"✅ Environment correctly detected as: {current_env}")
        else:
            recommendations.append(f"❌ Environment detection unclear: {current_env}")
        
        report['recommendations'] = recommendations
    
    return report

def print_report(report):
    """Print formatted database report"""
    print("\n" + "="*60)
    print("DATABASE ISOLATION STATUS REPORT")
    print("="*60)
    
    print(f"\n📍 ENVIRONMENT DETECTION:")
    env_data = report['environment_detection']
    print(f"   Detected Environment: {env_data['detected_environment']}")
    print(f"   ENVIRONMENT variable: {env_data['environment_var']}")
    print(f"   FLASK_ENV variable: {env_data['flask_env']}")
    print(f"   REPLIT_ENVIRONMENT: {env_data['replit_env']}")
    print(f"   REPL_SLUG: {env_data['repl_slug']}")
    
    print(f"\n📊 SCHEMA ANALYSIS:")
    for schema, data in report['schema_analysis'].items():
        print(f"   {schema}: {data['table_count']} tables")
    
    print(f"\n📋 TABLE ANALYSIS:")
    for schema, data in report['table_analysis'].items():
        print(f"   {schema.upper()} Schema:")
        print(f"     ✓ Tables: {', '.join(data['existing_tables'])}")
        if data['missing_tables']:
            print(f"     ❌ Missing: {', '.join(data['missing_tables'])}")
        if data['extra_tables']:
            print(f"     ⚠️  Extra: {', '.join(data['extra_tables'])}")
        print(f"     Complete: {'✅ Yes' if data['is_complete'] else '❌ No'}")
    
    print(f"\n🔒 DATA ISOLATION:")
    for schema, data in report['data_isolation'].items():
        print(f"   {schema.upper()}: {data['user_count']} users, {data['bag_count']} bags, {data['scan_count']} scans")
    
    print(f"\n💡 RECOMMENDATIONS:")
    for rec in report['recommendations']:
        print(f"   {rec}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        logger.info("Generating database status report...")
        report = generate_database_report()
        print_report(report)
        
        # Summary
        dev_complete = report['table_analysis']['development']['is_complete']
        prod_complete = report['table_analysis']['production']['is_complete']
        
        if dev_complete and prod_complete:
            print("\n🎉 DATABASE ISOLATION: FULLY CONFIGURED")
        else:
            print("\n⚠️  DATABASE ISOLATION: NEEDS ATTENTION")
            
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise