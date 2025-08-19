"""
Script to diagnose template loading issues like the flask_navigation.py error
"""
import os
import re
from pathlib import Path

def check_for_template_issues():
    """Check for common template loading issues"""
    issues_found = []
    
    # Check all Python files for incorrect render_template calls
    print("Checking for template loading issues...")
    print("-" * 50)
    
    # Pattern to find render_template calls
    render_pattern = re.compile(r'render_template\s*\(\s*[\'"]([^\'",]+)[\'"]')
    
    # Check all Python files
    for py_file in Path('.').glob('**/*.py'):
        if 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue
            
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
            # Find all render_template calls
            matches = render_pattern.findall(content)
            
            for template_name in matches:
                # Check if template name ends with .py (incorrect)
                if template_name.endswith('.py'):
                    issues_found.append({
                        'file': str(py_file),
                        'template': template_name,
                        'issue': 'Template name ends with .py - should be .html'
                    })
                    print(f"❌ ERROR in {py_file}: render_template('{template_name}')")
                    print(f"   Should probably be: render_template('{template_name[:-3]}.html')")
                
                # Check if template file exists
                template_path = Path('templates') / template_name
                if not template_name.endswith('.py') and not template_path.exists():
                    # Also check with .html extension
                    template_path_html = Path('templates') / f"{template_name}.html"
                    if not template_path_html.exists():
                        issues_found.append({
                            'file': str(py_file),
                            'template': template_name,
                            'issue': 'Template file not found'
                        })
                        print(f"⚠️  WARNING in {py_file}: Template '{template_name}' not found")
                
        except Exception as e:
            print(f"Error checking {py_file}: {e}")
    
    # Check for flask_navigation specifically
    print("\n" + "-" * 50)
    print("Checking for flask_navigation references...")
    
    for py_file in Path('.').glob('**/*.py'):
        if 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue
            
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
            if 'flask_navigation' in content.lower():
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if 'flask_navigation' in line.lower():
                        issues_found.append({
                            'file': str(py_file),
                            'line': i,
                            'content': line.strip(),
                            'issue': 'Reference to flask_navigation found'
                        })
                        print(f"❌ Found flask_navigation reference in {py_file}:{i}")
                        print(f"   Line: {line.strip()}")
        except Exception as e:
            print(f"Error checking {py_file}: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    if issues_found:
        print(f"Found {len(issues_found)} potential issues:")
        for issue in issues_found:
            print(f"  - {issue}")
    else:
        print("✅ No template loading issues found in development code")
        print("\nNote: The flask_navigation.py error appears to be production-specific.")
        print("It may be caused by:")
        print("  1. Different code deployed to production")
        print("  2. A configuration file only present in production")
        print("  3. An environment variable affecting template loading")
    
    return issues_found

def suggest_fixes():
    """Suggest fixes for common issues"""
    print("\n" + "=" * 50)
    print("RECOMMENDED FIXES FOR PRODUCTION")
    print("=" * 50)
    
    print("""
1. **Template Loading Error (flask_navigation.py)**:
   - Search production code: grep -r "flask_navigation" /path/to/production/
   - Check for typos in render_template calls
   - Verify all templates have .html extension, not .py
   
2. **DNS Resolution Failure**:
   - Test DNS on production server: nslookup your-database-host.neon.tech
   - Add DNS servers to /etc/resolv.conf:
     nameserver 8.8.8.8
     nameserver 8.8.4.4
   - Or use IP address directly in DATABASE_URL (temporary fix)
   
3. **Database Connection Issues**:
   - Deploy the database_resilience.py module
   - Update app_clean.py with resilient configuration
   - Monitor connection pool usage
   
4. **Worker Stability**:
   - Increase worker timeout in gunicorn
   - Add worker health checks
   - Monitor memory usage: free -h
   
5. **Quick Production Fixes**:
   # Fix DNS (if needed)
   echo "nameserver 8.8.8.8" >> /etc/resolv.conf
   
   # Restart application
   supervisorctl restart your-app
   # or
   systemctl restart your-app
   
   # Check logs
   tail -f /var/log/your-app/error.log
    """)

if __name__ == "__main__":
    issues = check_for_template_issues()
    suggest_fixes()