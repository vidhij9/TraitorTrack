# Import the working application
from app_clean import app, db
from flask import request, redirect, url_for, session, render_template, flash
from models import User
from simple_auth import login_user_simple, is_authenticated, clear_auth_session
import logging

# Import all the main routes to ensure they're registered
import routes
import api  # Import improved API endpoints

@app.route('/login', methods=['GET', 'POST'])  
def login():
    logging.info(f"Production login request: method={request.method}")
    
    # Import production authentication fix
    from production_auth_fix import production_login_handler, is_production_authenticated
    
    # Check if already authenticated
    if is_production_authenticated() and request.method == 'GET':
        logging.info("User already authenticated, redirecting to dashboard")
        next_url = session.pop('next_url', None)
        return redirect(next_url or url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        logging.info(f"Production login attempt for username: {username}")
        
        if not username or not password:
            return render_template('simple_login.html', error='Please enter both username and password.')
        
        # Use production authentication handler
        success, message = production_login_handler(username, password)
        
        if success:
            logging.info(f"Production login successful for user: {username}")
            # Get the stored redirect URL or default to index
            next_url = session.pop('next_url', None)
            return redirect(next_url or url_for('index'))
        else:
            logging.info(f"Production login failed for user: {username} - {message}")
            return render_template('simple_login.html', error=message)
    
    return render_template('simple_login.html')

@app.route('/logout')
def logout():
    """Production logout handler"""
    from production_auth_fix import production_logout
    
    logging.info("Production user logout")
    production_logout()
    return redirect(url_for('login'))

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
        'authenticated': session.get('authenticated', False),
        'auth_token_present': bool(session.get('auth_token')),
        'secure_session_count': 0,
        'cookies_received': dict(request.cookies),
        'headers': dict(request.headers)
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
        <li>Cookies: {info['cookies_received']}</li>
        <li>User Agent: {info['headers'].get('User-Agent', 'Not provided')}</li>
    </ul>
    <p><a href="/setup">Run Setup</a> | <a href="/login">Login Page</a> | <a href="/test-login">Test Login</a> | <a href="/session-test">Session Test</a></p>
    """

@app.route('/session-test')
def session_test():
    """Test session persistence"""
    if 'visit_count' not in session:
        session['visit_count'] = 0
    session['visit_count'] += 1
    session.permanent = True
    
    return f"""
    <h2>Session Persistence Test</h2>
    <p>Visit count: {session['visit_count']}</p>
    <p>Session ID: {request.cookies.get('tracetrack_session', 'No session cookie')}</p>
    <p>Full session: {dict(session)}</p>
    <p><a href="/session-test">Refresh Page</a> | <a href="/debug-deployment">Debug Info</a></p>
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
            from stateless_auth import create_auth_token
            token = create_auth_token(user)
            
            # Set the auth token in cookies for testing
            from flask import make_response
            response = make_response(f"""
            <h2>Login Test Results</h2>
            <p>✓ Authentication successful</p>
            <p>Token created: {token[:20]}...</p>
            <p>User: {user.username}</p>
            <p><a href="/">Go to Dashboard</a></p>
            <p><a href="/debug-deployment">Check Debug Info</a></p>
            """)
            
            response.set_cookie('auth_token', token, max_age=86400, httponly=False, secure=False, samesite=None, path='/')
            response.set_cookie('user_session', token, max_age=86400, httponly=False, secure=False, samesite='Lax', path='/')
            
            return response
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