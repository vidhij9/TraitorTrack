# Import the working application but with fixed authentication
from app_clean import app, db

# Override the problematic login route with working authentication
from flask import request, redirect, url_for, session, render_template
from models import User

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in') and request.method == 'GET':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            return render_template('simple_login.html', error='Please enter both username and password.')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session.permanent = True
            session['logged_in'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            
            return redirect(url_for('index'))
        else:
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

# Import all the routes to restore full functionality
import routes

# Expose app for gunicorn
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)