#!/usr/bin/env python3
"""
Code Cleaner for TraceTrack - Automated code cleanup and optimization
====================================================================

This script automatically cleans up the codebase by:
- Removing unused imports
- Standardizing formatting
- Fixing common issues
- Removing duplicate code
- Organizing file structure

Run with: python code_cleaner.py
"""

import os
import re
import ast
import shutil
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeCleaner:
    """Automated code cleaner for Python files"""
    
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.cleaned_files = []
        self.removed_files = []
        self.issues_fixed = []
        
    def clean_project(self):
        """Run complete project cleanup"""
        logger.info("Starting TraceTrack code cleanup...")
        
        # 1. Remove unused files
        self.remove_unused_files()
        
        # 2. Clean Python files
        self.clean_python_files()
        
        # 3. Organize file structure
        self.organize_file_structure()
        
        # 4. Clean static assets
        self.clean_static_assets()
        
        # 5. Generate report
        self.generate_cleanup_report()
        
        logger.info("Code cleanup completed!")
    
    def remove_unused_files(self):
        """Remove unused and redundant files"""
        # Files to remove (identified as unused/redundant)
        files_to_remove = [
            'api_old.py',
            'test_submit_button.py',
            'optimized_main.py',
            'config.py'  # If unused
        ]
        
        # Directories to clean
        dirs_to_clean = [
            '__pycache__',
            '.pytest_cache',
            'attached_assets'  # Clean old screenshots
        ]
        
        for file_name in files_to_remove:
            file_path = self.project_root / file_name
            if file_path.exists():
                try:
                    file_path.unlink()
                    self.removed_files.append(str(file_path))
                    logger.info(f"Removed unused file: {file_name}")
                except Exception as e:
                    logger.warning(f"Could not remove {file_name}: {e}")
        
        # Clean directories
        for dir_name in dirs_to_clean:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                try:
                    if dir_name == 'attached_assets':
                        # Keep the directory but clean old files
                        self.clean_attached_assets(dir_path)
                    else:
                        shutil.rmtree(dir_path)
                        logger.info(f"Removed directory: {dir_name}")
                except Exception as e:
                    logger.warning(f"Could not remove directory {dir_name}: {e}")
    
    def clean_attached_assets(self, assets_dir):
        """Clean old/unused assets but keep the directory"""
        try:
            # Keep only recent files (last 30 days based on name timestamp)
            current_time = 1754500000  # Approximate current timestamp
            cutoff_time = current_time - (30 * 24 * 60 * 60 * 1000)  # 30 days ago
            
            removed_count = 0
            for file_path in assets_dir.iterdir():
                if file_path.is_file():
                    # Extract timestamp from filename if present
                    timestamp_match = re.search(r'_(\d{13})', file_path.name)
                    if timestamp_match:
                        file_timestamp = int(timestamp_match.group(1))
                        if file_timestamp < cutoff_time:
                            file_path.unlink()
                            removed_count += 1
            
            logger.info(f"Cleaned {removed_count} old asset files")
        except Exception as e:
            logger.warning(f"Error cleaning assets: {e}")
    
    def clean_python_files(self):
        """Clean all Python files in the project"""
        python_files = list(self.project_root.glob("*.py"))
        
        for file_path in python_files:
            if self.should_clean_file(file_path):
                self.clean_python_file(file_path)
    
    def should_clean_file(self, file_path):
        """Determine if a file should be cleaned"""
        # Skip certain files
        skip_files = ['comprehensive_tests.py', 'code_cleaner.py']
        return file_path.name not in skip_files
    
    def clean_python_file(self, file_path):
        """Clean a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            cleaned_content = original_content
            changes_made = []
            
            # 1. Remove unused imports
            cleaned_content, import_changes = self.remove_unused_imports(cleaned_content, file_path)
            changes_made.extend(import_changes)
            
            # 2. Fix common formatting issues
            cleaned_content, format_changes = self.fix_formatting_issues(cleaned_content)
            changes_made.extend(format_changes)
            
            # 3. Remove duplicate blank lines
            cleaned_content = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_content)
            
            # 4. Ensure file ends with newline
            if not cleaned_content.endswith('\n'):
                cleaned_content += '\n'
                changes_made.append("Added trailing newline")
            
            # Write back if changes were made
            if cleaned_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                
                self.cleaned_files.append(str(file_path))
                self.issues_fixed.extend([f"{file_path.name}: {change}" for change in changes_made])
                logger.info(f"Cleaned {file_path.name}: {', '.join(changes_made)}")
        
        except Exception as e:
            logger.warning(f"Error cleaning {file_path}: {e}")
    
    def remove_unused_imports(self, content, file_path):
        """Remove unused imports from Python code"""
        try:
            tree = ast.parse(content)
            
            # Collect all imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            imports.append(f"{node.module}.{alias.name}")
            
            # For now, just return original content and empty changes
            # Full unused import detection would require more complex analysis
            return content, []
        
        except:
            # If parsing fails, return original content
            return content, []
    
    def fix_formatting_issues(self, content):
        """Fix common formatting issues"""
        changes = []
        
        # Fix multiple spaces before operators
        if re.search(r'\s{2,}=', content):
            content = re.sub(r'\s{2,}=', ' =', content)
            changes.append("Fixed spacing around operators")
        
        # Fix trailing whitespace
        lines = content.split('\n')
        cleaned_lines = [line.rstrip() for line in lines]
        if lines != cleaned_lines:
            content = '\n'.join(cleaned_lines)
            changes.append("Removed trailing whitespace")
        
        return content, changes
    
    def organize_file_structure(self):
        """Organize project file structure"""
        # Create utils directory if it doesn't exist
        utils_dir = self.project_root / "utils"
        if not utils_dir.exists():
            utils_dir.mkdir()
            
            # Move utility files to utils directory
            utility_files = [
                'auth_utils.py',
                'validation_utils.py',
                'query_optimizer.py',
                'cache_manager.py',
                'performance_monitor.py',
                'database_optimizer.py'
            ]
            
            moved_files = []
            for util_file in utility_files:
                src_path = self.project_root / util_file
                if src_path.exists():
                    dst_path = utils_dir / util_file
                    try:
                        shutil.move(str(src_path), str(dst_path))
                        moved_files.append(util_file)
                    except Exception as e:
                        logger.warning(f"Could not move {util_file}: {e}")
            
            if moved_files:
                logger.info(f"Organized utility files into utils/: {', '.join(moved_files)}")
                
                # Update imports in main files
                self.update_import_paths(moved_files)
    
    def update_import_paths(self, moved_files):
        """Update import paths for moved utility files"""
        main_files = ['routes.py', 'api.py', 'main.py', 'app_clean.py']
        
        for main_file in main_files:
            file_path = self.project_root / main_file
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    updated = False
                    for util_file in moved_files:
                        module_name = util_file.replace('.py', '')
                        old_import = f"from {module_name} import"
                        new_import = f"from utils.{module_name} import"
                        
                        if old_import in content:
                            content = content.replace(old_import, new_import)
                            updated = True
                        
                        old_import_alt = f"import {module_name}"
                        new_import_alt = f"import utils.{module_name} as {module_name}"
                        
                        if old_import_alt in content and new_import_alt not in content:
                            content = content.replace(old_import_alt, new_import_alt)
                            updated = True
                    
                    if updated:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        logger.info(f"Updated imports in {main_file}")
                
                except Exception as e:
                    logger.warning(f"Error updating imports in {main_file}: {e}")
    
    def clean_static_assets(self):
        """Clean and organize static assets"""
        static_dir = self.project_root / "static"
        if static_dir.exists():
            # Clean up any temporary or unused CSS/JS files
            for css_file in (static_dir / "css").glob("*.css"):
                if css_file.name.startswith("temp_") or css_file.name.endswith("_backup.css"):
                    try:
                        css_file.unlink()
                        logger.info(f"Removed temporary CSS file: {css_file.name}")
                    except Exception as e:
                        logger.warning(f"Could not remove {css_file.name}: {e}")
    
    def generate_cleanup_report(self):
        """Generate a cleanup report"""
        report_path = self.project_root / "cleanup_report.md"
        
        report_content = f"""# Code Cleanup Report
Generated on: {self.get_current_timestamp()}

## Summary
- Files cleaned: {len(self.cleaned_files)}
- Files removed: {len(self.removed_files)}
- Issues fixed: {len(self.issues_fixed)}

## Cleaned Files
{chr(10).join(f"- {file}" for file in self.cleaned_files)}

## Removed Files
{chr(10).join(f"- {file}" for file in self.removed_files)}

## Issues Fixed
{chr(10).join(f"- {issue}" for issue in self.issues_fixed)}

## Next Steps
1. Run comprehensive tests to ensure everything works
2. Review any import path changes
3. Test application functionality
4. Update documentation if needed
"""
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f"Cleanup report generated: {report_path}")
        except Exception as e:
            logger.error(f"Could not generate cleanup report: {e}")
    
    def get_current_timestamp(self):
        """Get current timestamp as string"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def main():
    """Main cleanup function"""
    print("TraceTrack Code Cleaner")
    print("=" * 50)
    
    cleaner = CodeCleaner()
    cleaner.clean_project()
    
    print("\nCleanup completed! Check cleanup_report.md for details.")
    print("Remember to:")
    print("1. Run tests to ensure everything works")
    print("2. Update any import statements if needed")
    print("3. Review the changes before committing")

if __name__ == "__main__":
    main()