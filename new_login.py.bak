"""
Brand new login system for Traitor Track
"""
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-key")

# Import the database from existing app
from app_clean import db
from models import User

@app.route('/')
def index():
    if not session.get('logged_in'):
        return render_template('landing.html')
    
    return render_template('dashboard.html', 
                         username=session.get('username'),
                         user_role=session.get('user_role'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        # Find user in database
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Set session data
            session.permanent = True
            session['logged_in'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.init_app(app)
        app.run(host='0.0.0.0', port=5000, debug=True)