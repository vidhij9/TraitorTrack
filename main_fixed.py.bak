"""
Clean implementation of Traitor Track with working authentication
"""
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

class Base(DeclarativeBase):
    pass

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-key-change-in-production")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
db = SQLAlchemy(app, model_class=Base)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='employee')
    verified = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Routes
@app.route('/')
def index():
    if not session.get('logged_in'):
        return render_template('landing.html')
    
    return f"""
    <h1>Welcome to Traitor Track Dashboard</h1>
    <p>Hello, {session.get('username')}!</p>
    <p>Role: {session.get('user_role')}</p>
    <a href="/logout">Logout</a>
    """

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('simple_login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session.permanent = True
            session['logged_in'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('simple_login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/setup')
def setup():
    """Setup admin user"""
    with app.app_context():
        db.create_all()
        
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)