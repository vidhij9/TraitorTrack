"""
Standalone dashboard API endpoints without authentication requirements
"""
from flask import Flask, jsonify, request
from app_clean import app, db
from models import Bag, Scan, Bill
from datetime import datetime, timedelta

@app.route('/dashboard/stats')
def dashboard_stats():
    """Get system statistics for dashboard"""
    try:
        total_parent_bags = Bag.query.filter_by(type='parent').count()
        total_child_bags = Bag.query.filter_by(type='child').count()
        total_scans = Scan.query.count()
        total_bills = Bill.query.count() if 'Bill' in globals() else 0
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_parent_bags': total_parent_bags,
                'total_child_bags': total_child_bags,
                'total_scans': total_scans,
                'total_bills': total_bills
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/dashboard/scans')
def dashboard_scans():
    """Get recent scans for dashboard"""
    try:
        limit = request.args.get('limit', 50, type=int)
        scans = Scan.query.order_by(Scan.timestamp.desc()).limit(limit).all()
        
        scan_list = []
        for scan in scans:
            try:
                scan_dict = {
                    'id': scan.id,
                    'product_qr': getattr(scan, 'qr_id', getattr(scan, 'product_qr', 'Unknown')),
                    'type': getattr(scan, 'scan_type', 'unknown'),
                    'timestamp': scan.timestamp.isoformat() if scan.timestamp else None,
                    'username': getattr(scan, 'username', 'Unknown')
                }
                scan_list.append(scan_dict)
            except Exception as e:
                continue
        
        return jsonify({
            'success': True,
            'scans': scan_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/dashboard/activity/<int:days>')
def dashboard_activity(days):
    """Get scan activity for the past X days"""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        activity_data = []
        current_date = start_date
        
        while current_date <= end_date:
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())
            
            scan_count = Scan.query.filter(
                Scan.timestamp >= day_start,
                Scan.timestamp <= day_end
            ).count()
            
            activity_data.append({
                'date': current_date.isoformat(),
                'scan_count': scan_count
            })
            
            current_date += timedelta(days=1)
        
        return jsonify({
            'success': True,
            'activity': activity_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500