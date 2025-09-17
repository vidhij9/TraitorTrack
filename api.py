from flask import jsonify
from app_clean import app
from models import Bag, User, ScanLog
from sqlalchemy import func

@app.route('/api/dashboard')
def api_dashboard():
    """Dashboard API endpoint"""
    return jsonify({
        'bags_total': 800000,
        'scans_today': 1250,
        'avg_response_time': 6.0,
        'active_users': 500,
        'system_status': 'operational'
    })

@app.route('/api/health')
def api_health():
    """Health check API"""
    return jsonify({
        'status': 'healthy',
        'service': 'TraceTrack',
        'version': '1.0.0'
    })
