#!/usr/bin/env python3
"""
Migration Creator - Helper script to create new migration files
Usage: python create_migration.py "description of migration"
"""

import sys
import os
from datetime import datetime

def create_migration(description):
    """Create a new migration file with timestamp and description"""
    
    # Get current timestamp for ordering
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Clean description for filename
    clean_desc = description.lower().replace(' ', '_').replace('-', '_')
    clean_desc = ''.join(c for c in clean_desc if c.isalnum() or c == '_')
    
    # Get next migration number
    migrations_dir = os.path.dirname(__file__)
    existing_files = [f for f in os.listdir(migrations_dir) if f.endswith('.sql')]
    existing_numbers = []
    
    for filename in existing_files:
        if filename[:3].isdigit():
            existing_numbers.append(int(filename[:3]))
    
    next_number = max(existing_numbers, default=0) + 1
    
    # Create filename
    filename = f"{next_number:03d}_{clean_desc}.sql"
    filepath = os.path.join(migrations_dir, filename)
    
    # Create migration template
    template = f"""-- Migration: {description}
-- Date: {datetime.now().strftime('%Y-%m-%d')}
-- Description: {description}

-- Add your SQL statements here
-- Example:
-- ALTER TABLE table_name ADD COLUMN new_column VARCHAR(255);
-- UPDATE table_name SET new_column = 'default_value';

-- Remember:
-- - Use IF NOT EXISTS for CREATE statements when possible
-- - Handle data migration carefully
-- - Test migrations on development environment first
"""
    
    # Write migration file
    with open(filepath, 'w') as f:
        f.write(template)
    
    print(f"✅ Created migration: {filename}")
    print(f"📝 Edit the file to add your SQL statements")
    return filepath

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_migration.py \"description of migration\"")
        sys.exit(1)
    
    description = ' '.join(sys.argv[1:])
    create_migration(description)