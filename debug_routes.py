#!/usr/bin/env python3
"""
List all registered routes
"""

import sys
sys.path.append('.')

from app_clean import app

with app.app_context():
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.rule} -> {rule.endpoint} ({rule.methods})")