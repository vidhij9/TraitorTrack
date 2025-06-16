#!/usr/bin/env python3
"""
Simple production test to identify deployment issues
"""

import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def health():
    return jsonify({
        'status': 'ok',
        'environment': os.environ.get('FLASK_ENV', 'unknown'),
        'database_url_present': bool(os.environ.get('DATABASE_URL')),
        'session_secret_present': bool(os.environ.get('SESSION_SECRET'))
    })

@app.route('/test')
def test():
    try:
        # Test database import
        from app_clean import db
        return jsonify({'db_import': 'success'})
    except Exception as e:
        return jsonify({'db_import': 'failed', 'error': str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)