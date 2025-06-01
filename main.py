# Import the working application but with fixed authentication
from app_clean import app, db

# Override the problematic login route with working authentication
from flask import request, redirect, url_for, session, render_template
from models import User

@app.route('/login', methods=['GET', 'POST'])
def login():
    import logging
    logging.info(f"Login request: method={request.method}, logged_in={session.get('logged_in')}")
    
    if session.get('logged_in') and request.method == 'GET':
        logging.info("User already logged in, redirecting to index")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        logging.info(f"Login attempt for username: {username}")
        
        if not username or not password:
            logging.info("Missing username or password")
            return render_template('simple_login.html', error='Please enter both username and password.')
        
        user = User.query.filter_by(username=username).first()
        logging.info(f"User found: {user is not None}")
        
        if user and user.check_password(password):
            logging.info("Password correct, setting session")
            # Use simplified authentication
            session.clear()
            session.permanent = True
            session['authenticated'] = True
            session['logged_in'] = True  # Keep for backward compatibility
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            
            logging.info(f"Session set: {dict(session)}")
            return redirect(url_for('index'))
        else:
            logging.info("Invalid credentials")
            return render_template('simple_login.html', error='Invalid username or password.')
    
    return render_template('simple_login.html')

@app.route('/setup')
def setup():
    """Setup admin user"""
    from werkzeug.security import generate_password_hash
    
    # Check if admin exists
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
        # Update password
        admin.password_hash = generate_password_hash('admin')
        db.session.commit()
        return "Admin password updated. Username: admin, Password: admin"

# Add diagnostic endpoint for deployment debugging
@app.route('/debug-deployment')
def debug_deployment():
    """Debug endpoint for deployment issues"""
    import os
    from models import User
    
    info = {
        'database_url_set': bool(os.environ.get('DATABASE_URL')),
        'session_secret_set': bool(os.environ.get('SESSION_SECRET')),
        'admin_user_exists': User.query.filter_by(username='admin').first() is not None,
        'environment': os.environ.get('ENVIRONMENT', 'development'),
        'app_running': True,
        'current_session': dict(session),
        'logged_in': session.get('logged_in', False),
        'authenticated': session.get('authenticated', False)
    }
    
    return f"""
    <h2>Deployment Debug Info</h2>
    <ul>
        <li>Database URL Set: {info['database_url_set']}</li>
        <li>Session Secret Set: {info['session_secret_set']}</li>
        <li>Admin User Exists: {info['admin_user_exists']}</li>
        <li>Environment: {info['environment']}</li>
        <li>App Running: {info['app_running']}</li>
        <li>Current Session: {info['current_session']}</li>
        <li>Logged In: {info['logged_in']}</li>
        <li>Authenticated: {info['authenticated']}</li>
    </ul>
    <p><a href="/setup">Run Setup</a> | <a href="/login">Login Page</a> | <a href="/test-login">Test Login</a></p>
    """

@app.route('/test-login', methods=['GET', 'POST'])
def test_login():
    """Test login endpoint for debugging"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        from models import User
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session.clear()
            session.permanent = True
            session['authenticated'] = True
            session['logged_in'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            
            return f"""
            <h2>Login Test Results</h2>
            <p>✓ Authentication successful</p>
            <p>Session data: {dict(session)}</p>
            <p><a href="/">Go to Dashboard</a></p>
            <p><a href="/debug-deployment">Check Debug Info</a></p>
            """
        else:
            return f"""
            <h2>Login Test Results</h2>
            <p>✗ Authentication failed</p>
            <p>User found: {user is not None}</p>
            <p><a href="/test-login">Try Again</a></p>
            """
    
    return '''
    <h2>Test Login</h2>
    <form method="POST">
        <p>Username: <input type="text" name="username" value="admin"></p>
        <p>Password: <input type="password" name="password" value="admin"></p>
        <p><input type="submit" value="Test Login"></p>
    </form>
    <p><a href="/debug-deployment">Back to Debug</a></p>
    '''

# Import all the routes to restore full functionality
import routes

# Expose app for gunicorn
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)