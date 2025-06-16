# Import the main application
from app_clean import app, db
from flask import request, redirect, url_for, session, render_template, flash
from models import User
from production_auth_fix import production_login_handler, is_production_authenticated, production_logout, require_production_auth
import logging

# Import all the main routes to ensure they're registered
import routes

@app.route('/login', methods=['GET', 'POST'])  
def login():
    logging.info(f"Production login request: method={request.method}")
    
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

@app.route('/dashboard')
def dashboard():
    """Dashboard route - redirects to main index"""
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Production logout handler"""
    logging.info("Production user logout")
    production_logout()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)