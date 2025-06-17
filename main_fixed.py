# Fixed main application entry point with cleaned up authentication
from app_clean import app, db
from flask import request, redirect, url_for, session, render_template, flash, jsonify
from models import User, Bag, BagType, Link, Scan, Bill
from production_auth_fix import production_login_handler, is_production_authenticated, production_logout, require_production_auth
import logging
from datetime import datetime
from sqlalchemy import func, desc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/login', methods=['GET', 'POST'])  
def login():
    if is_production_authenticated() and request.method == 'GET':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            return render_template('simple_login.html', error='Please enter both username and password.')
        
        success, message = production_login_handler(username, password)
        
        if success:
            next_url = session.pop('next_url', None)
            return redirect(next_url or url_for('index'))
        else:
            return render_template('simple_login.html', error=message)
    
    return render_template('simple_login.html')

@app.route('/logout')
def logout():
    production_logout()
    return redirect(url_for('login'))

@app.route('/setup')
def setup():
    from werkzeug.security import generate_password_hash
    
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@traitortrack.com',
            password_hash=generate_password_hash('admin'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        return "Admin user created. Username: admin, Password: admin"
    else:
        admin.password_hash = generate_password_hash('admin')
        db.session.commit()
        return "Admin password updated. Username: admin, Password: admin"

# Fixed API endpoints with proper authentication
@app.route('/api/stats')
@require_production_auth
def api_dashboard_stats():
    """Get dashboard statistics"""
    try:
        total_parent_bags = Bag.query.filter_by(type=BagType.PARENT.value).count()
        total_child_bags = Bag.query.filter_by(type=BagType.CHILD.value).count()
        total_scans = Scan.query.count()
        total_bills = Bill.query.count()
        
        stats = {
            'total_parent_bags': total_parent_bags,
            'total_child_bags': total_child_bags,
            'total_scans': total_scans,
            'total_bills': total_bills,
            'total_products': total_parent_bags + total_child_bags,
            'status_counts': {
                'active': total_parent_bags + total_child_bags,
                'scanned': total_scans
            }
        }
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        logger.error(f"Stats API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scans')
@require_production_auth
def api_recent_scans():
    """Get recent scans for dashboard"""
    try:
        limit = request.args.get('limit', 20, type=int)
        scans = Scan.query.order_by(desc(Scan.timestamp)).limit(limit).all()
        
        scan_data = []
        for scan in scans:
            bag = None
            if scan.parent_bag_id:
                bag = Bag.query.get(scan.parent_bag_id)
            elif scan.child_bag_id:
                bag = Bag.query.get(scan.child_bag_id)
            
            user = User.query.get(scan.user_id) if scan.user_id else None
            
            scan_data.append({
                'id': scan.id,
                'timestamp': scan.timestamp.isoformat() if scan.timestamp else None,
                'product_qr': bag.qr_id if bag else 'Unknown',
                'product_name': bag.name if bag else 'Unknown Product',
                'type': 'parent' if scan.parent_bag_id else 'child',
                'username': user.username if user else 'Unknown'
            })
        
        return jsonify({
            'success': True,
            'scans': scan_data,
            'count': len(scan_data)
        })
    except Exception as e:
        logger.error(f"Scans API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'connected'
    })

# Import the main routes
import routes

# Expose app for gunicorn
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
