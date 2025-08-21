#!/usr/bin/env python3
"""
Analyze and identify potentially unrequired or duplicate files in the TraceTrack system
"""

import os
import hashlib
from pathlib import Path
from collections import defaultdict
import json

def get_file_hash(filepath):
    """Calculate MD5 hash of a file"""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

def analyze_files():
    """Analyze all files and identify duplicates and potentially unrequired files"""
    
    # Categories of files
    file_categories = {
        'test_files': [],
        'config_duplicates': [],
        'route_duplicates': [],
        'api_duplicates': [],
        'cache_duplicates': [],
        'performance_duplicates': [],
        'documentation': [],
        'deployment_scripts': [],
        'monitoring_files': [],
        'old_versions': [],
        'temporary_files': [],
        'debug_files': []
    }
    
    # File patterns that might be duplicates or unrequired
    patterns = {
        'test_files': ['test_', '_test.py', 'debug_', 'simple_', 'quick_', 'stress_test', 'load_test', 'comprehensive_test', 'workflow_test', 'critical_test', 'final_', 'full_'],
        'config_duplicates': ['_config.py', 'config_', 'highperf', 'high_performance', 'optimized', 'production'],
        'route_duplicates': ['routes_', '_routes.py'],
        'api_duplicates': ['api_', '_api.py'],
        'cache_duplicates': ['cache', 'redis_', 'ultra_cache'],
        'performance_duplicates': ['performance_', 'optimizer', 'ultra_optimizer'],
        'documentation': ['.md', 'CHECKLIST', 'SUMMARY'],
        'deployment_scripts': ['deploy_', '.sh'],
        'monitoring_files': ['monitor_', 'monitoring_'],
        'old_versions': ['_old', '_backup', '_orig'],
        'temporary_files': ['.json', '.txt', '.html', '.lock'],
        'debug_files': ['debug_', 'fix_']
    }
    
    # Get all Python and other files
    all_files = []
    for root, dirs, files in os.walk('.'):
        # Skip hidden directories and common non-source directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', 'env']]
        
        for file in files:
            if not file.startswith('.'):
                filepath = os.path.join(root, file)
                all_files.append(filepath)
    
    # Analyze files
    file_hashes = {}
    duplicate_groups = defaultdict(list)
    
    for filepath in all_files:
        # Skip directories we don't want to analyze
        if any(skip in filepath for skip in ['./static/', './templates/', './attached_assets/', './__pycache__']):
            continue
            
        filename = os.path.basename(filepath)
        
        # Categorize files
        for category, category_patterns in patterns.items():
            for pattern in category_patterns:
                if pattern in filename.lower():
                    file_categories[category].append(filepath)
                    break
        
        # Check for duplicates by hash
        file_hash = get_file_hash(filepath)
        if file_hash:
            if file_hash in file_hashes:
                duplicate_groups[file_hash].append(filepath)
                duplicate_groups[file_hash].append(file_hashes[file_hash])
            else:
                file_hashes[file_hash] = filepath
    
    # Identify core required files
    required_files = {
        './main.py',  # Entry point
        './app_clean.py',  # Main app configuration
        './models.py',  # Database models
        './routes.py',  # Main routes
        './forms.py',  # Form definitions
        './auth_utils.py',  # Authentication utilities
        './validation_utils.py',  # Validation utilities
        './error_handlers.py',  # Error handling
        './gunicorn_config.py',  # Server configuration
        './pyproject.toml',  # Project dependencies
        './replit.md',  # Project documentation
        './high_performance_config.py',  # Performance configuration
        './query_optimizer.py',  # Query optimization
        './optimized_cache.py',  # Cache implementation
        './connection_manager.py',  # Database connection management
    }
    
    # Analyze results
    results = {
        'summary': {
            'total_files': len(all_files),
            'python_files': len([f for f in all_files if f.endswith('.py')]),
            'required_files': len(required_files),
            'test_files': len(file_categories['test_files']),
            'config_duplicates': len(file_categories['config_duplicates']),
            'potential_duplicates': sum(len(files) for files in duplicate_groups.values())
        },
        'potentially_unrequired': {
            'test_files': sorted(set(file_categories['test_files'])),
            'config_duplicates': sorted(set(file_categories['config_duplicates'])),
            'route_duplicates': sorted(set(file_categories['route_duplicates'])),
            'api_duplicates': sorted(set(file_categories['api_duplicates'])),
            'cache_duplicates': sorted(set(file_categories['cache_duplicates'])),
            'performance_duplicates': sorted(set(file_categories['performance_duplicates'])),
            'documentation': sorted(set(file_categories['documentation'])),
            'deployment_scripts': sorted(set(file_categories['deployment_scripts'])),
            'monitoring_files': sorted(set(file_categories['monitoring_files'])),
            'debug_files': sorted(set(file_categories['debug_files'])),
            'temporary_files': sorted(set(file_categories['temporary_files']))
        },
        'exact_duplicates': {
            hash_val: list(set(files)) for hash_val, files in duplicate_groups.items()
        },
        'required_files': sorted(required_files)
    }
    
    return results

def print_results(results):
    """Print analysis results"""
    print("=" * 80)
    print("FILE ANALYSIS REPORT - POTENTIALLY UNREQUIRED FILES")
    print("=" * 80)
    
    print("\n📊 SUMMARY:")
    for key, value in results['summary'].items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    
    print("\n⚠️  POTENTIALLY UNREQUIRED FILES BY CATEGORY:")
    print("(These files may be redundant or no longer needed)")
    print("-" * 80)
    
    for category, files in results['potentially_unrequired'].items():
        if files:
            print(f"\n📁 {category.replace('_', ' ').upper()}:")
            for file in files[:20]:  # Limit to first 20 for readability
                size = os.path.getsize(file) if os.path.exists(file) else 0
                print(f"  - {file} ({size:,} bytes)")
            if len(files) > 20:
                print(f"  ... and {len(files) - 20} more files")
    
    if results['exact_duplicates']:
        print("\n🔄 EXACT DUPLICATE FILES:")
        print("(These files have identical content)")
        print("-" * 80)
        for i, (hash_val, files) in enumerate(results['exact_duplicates'].items(), 1):
            if len(set(files)) > 1:
                print(f"\nDuplicate Group {i}:")
                for file in set(files):
                    print(f"  - {file}")
    
    print("\n✅ CORE REQUIRED FILES:")
    print("(These files are essential for the system)")
    print("-" * 80)
    for file in results['required_files']:
        if os.path.exists(file):
            print(f"  ✓ {file}")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS:")
    print("=" * 80)
    print("""
1. TEST FILES: Consider removing old test files that are no longer used:
   - Keep only the latest comprehensive test suite
   - Remove debug and temporary test files
   
2. CONFIG DUPLICATES: Consolidate configuration files:
   - Keep high_performance_config.py as the main config
   - Remove redundant config variations
   
3. ROUTE/API DUPLICATES: Merge duplicate route implementations:
   - Keep routes.py as the main routes file
   - Remove experimental route files (routes_fast.py, routes_ultra_fast.py)
   
4. CACHE IMPLEMENTATIONS: Use a single caching strategy:
   - Keep optimized_cache.py
   - Remove redundant cache implementations
   
5. TEMPORARY FILES: Clean up:
   - Remove .json report files from old tests
   - Remove .txt debug files
   - Remove .lock files if not needed

NOTE: DO NOT DELETE these files yet. Review each carefully before deletion.
""")
    
    # Save detailed report
    report_file = 'file_analysis_report.json'
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n📄 Detailed report saved to: {report_file}")

if __name__ == "__main__":
    results = analyze_files()
    print_results(results)