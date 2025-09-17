#!/bin/bash
yum update -y
yum install -y python3 python3-pip
pip3 install Flask Flask-SQLAlchemy Flask-Login gunicorn bcrypt

mkdir -p /app && cd /app

# Minimal TraceTrack app
cat > app.py << 'EOF'
from flask import Flask, render_template_string, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "aws-tracetrack-2025"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tracetrack.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Bag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_code = db.Column(db.String(100), unique=True, nullable=False)
    scanned_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'TraceTrack'}, 200

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template_string('''
    <div style="font-family:Arial;max-width:400px;margin:100px auto;padding:30px;background:white;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,0.3);">
        <h2 style="text-align:center;color:#667eea;">🏷️ TraceTrack</h2>
        <div style="background:#FF6600;color:white;padding:15px;border-radius:8px;margin:15px 0;text-align:center;font-weight:bold;">
            🚀 AWS MIGRATION SUCCESS!
        </div>
        <form method="POST" action="/login">
            <div style="margin:15px 0;">
                <label>Username:</label>
                <input type="text" name="username" required style="width:100%;padding:12px;border:1px solid #ddd;border-radius:5px;">
            </div>
            <div style="margin:15px 0;">
                <label>Password:</label>
                <input type="password" name="password" required style="width:100%;padding:12px;border:1px solid #ddd;border-radius:5px;">
            </div>
            <button type="submit" style="width:100%;padding:15px;background:#667eea;color:white;border:none;border-radius:5px;font-size:16px;">Login</button>
        </form>
        <p style="text-align:center;color:#666;">Demo: admin / admin123</p>
    </div>
    ''')

@app.route('/login', methods=['POST'])
def login():
    user = User.query.filter_by(username=request.form['username']).first()
    if user and user.check_password(request.form['password']):
        login_user(user)
        return redirect(url_for('dashboard'))
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_bags = Bag.query.count()
    total_scans = db.session.query(db.func.sum(Bag.scanned_count)).scalar() or 0
    return render_template_string('''
    <div style="font-family:Arial;margin:20px;max-width:1000px;margin:20px auto;">
        <div style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:30px;border-radius:15px;text-align:center;">
            <h1>🏷️ TraceTrack Dashboard</h1>
            <div style="background:#FF6600;padding:15px;border-radius:10px;margin:15px 0;">
                🎉 AWS MIGRATION COMPLETE!
            </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin:30px 0;">
            <div style="background:white;padding:25px;border-radius:12px;text-align:center;box-shadow:0 5px 15px rgba(0,0,0,0.1);">
                <div style="font-size:2.5em;font-weight:bold;color:#667eea;">{{ total_bags }}</div>
                <div>Total Bags</div>
            </div>
            <div style="background:white;padding:25px;border-radius:12px;text-align:center;box-shadow:0 5px 15px rgba(0,0,0,0.1);">
                <div style="font-size:2.5em;font-weight:bold;color:#28a745;">{{ total_scans }}</div>
                <div>Total Scans</div>
            </div>
        </div>
        <div style="text-align:center;">
            <a href="/scanner" style="background:#28a745;color:white;padding:15px 25px;border-radius:8px;text-decoration:none;margin:10px;font-weight:bold;">🔍 QR Scanner</a>
            <a href="/bags" style="background:#667eea;color:white;padding:15px 25px;border-radius:8px;text-decoration:none;margin:10px;font-weight:bold;">📦 Bags</a>
        </div>
    </div>
    ''', total_bags=total_bags, total_scans=total_scans)

@app.route('/scanner')
@login_required
def scanner():
    return render_template_string('''
    <div style="font-family:Arial;max-width:600px;margin:50px auto;background:white;padding:40px;border-radius:15px;box-shadow:0 10px 30px rgba(0,0,0,0.1);">
        <h2 style="text-align:center;">🔍 QR Scanner</h2>
        <div style="background:#FF6600;color:white;padding:12px;border-radius:8px;margin:15px 0;text-align:center;font-weight:bold;">
            ⚡ AWS-Powered
        </div>
        <form method="POST" action="/scan" style="text-align:center;">
            <input type="text" name="qr_code" placeholder="Enter QR Code" required style="width:100%;padding:18px;border:2px solid #ddd;border-radius:10px;margin:15px 0;font-size:18px;text-align:center;">
            <button type="submit" style="background:#28a745;color:white;padding:18px 35px;border:none;border-radius:10px;font-size:18px;font-weight:bold;">Process Scan</button>
        </form>
        <div style="text-align:center;margin-top:20px;">
            <a href="/dashboard" style="background:#6c757d;color:white;padding:12px 25px;border-radius:8px;text-decoration:none;">← Dashboard</a>
        </div>
    </div>
    ''')

@app.route('/scan', methods=['POST'])
@login_required
def scan():
    qr_code = request.form['qr_code'].strip()
    bag = Bag.query.filter_by(qr_code=qr_code).first()
    if bag:
        bag.scanned_count += 1
        message = f"✅ Bag {qr_code} scanned! Total: {bag.scanned_count}"
    else:
        bag = Bag(qr_code=qr_code, scanned_count=1)
        db.session.add(bag)
        message = f"🆕 New bag {qr_code} registered!"
    db.session.commit()
    return render_template_string('''
    <div style="font-family:Arial;max-width:600px;margin:50px auto;background:white;padding:40px;border-radius:15px;text-align:center;box-shadow:0 10px 30px rgba(0,0,0,0.1);">
        <h2>Scan Result</h2>
        <div style="background:#28a745;color:white;padding:30px;border-radius:15px;margin:30px 0;font-size:18px;font-weight:bold;">{{ message }}</div>
        <a href="/scanner" style="background:#28a745;color:white;padding:15px 30px;border-radius:10px;text-decoration:none;margin:10px;font-weight:bold;">🔍 Scan Another</a>
        <a href="/dashboard" style="background:#667eea;color:white;padding:15px 30px;border-radius:10px;text-decoration:none;margin:10px;font-weight:bold;">📊 Dashboard</a>
    </div>
    ''', message=message)

@app.route('/bags')
@login_required
def bags():
    all_bags = Bag.query.order_by(Bag.created_at.desc()).all()
    return render_template_string('''
    <div style="font-family:Arial;max-width:800px;margin:20px auto;background:white;padding:30px;border-radius:15px;">
        <h2>📦 Bag Management</h2>
        <div style="background:#FF6600;color:white;padding:15px;border-radius:10px;margin:20px 0;text-align:center;font-weight:bold;">
            🚀 AWS Enterprise Database
        </div>
        {% if all_bags %}
        <table style="width:100%;border-collapse:collapse;">
            <tr style="background:#667eea;color:white;">
                <th style="padding:15px;text-align:left;">QR Code</th>
                <th style="padding:15px;text-align:left;">Scans</th>
                <th style="padding:15px;text-align:left;">Created</th>
            </tr>
            {% for bag in all_bags %}
            <tr style="border-bottom:1px solid #ddd;">
                <td style="padding:15px;font-family:monospace;font-weight:bold;">{{ bag.qr_code }}</td>
                <td style="padding:15px;">{{ bag.scanned_count }}</td>
                <td style="padding:15px;">{{ bag.created_at.strftime('%m/%d %H:%M') }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <p style="text-align:center;padding:40px;">No bags yet. <a href="/scanner">Start scanning!</a></p>
        {% endif %}
        <div style="text-align:center;margin-top:30px;">
            <a href="/scanner" style="background:#28a745;color:white;padding:12px 25px;border-radius:8px;text-decoration:none;margin:5px;">🔍 Scanner</a>
            <a href="/dashboard" style="background:#667eea;color:white;padding:12px 25px;border-radius:8px;text-decoration:none;margin:5px;">📊 Dashboard</a>
        </div>
    </div>
    ''', all_bags=all_bags)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
    app.run(host="0.0.0.0", port=5000)
EOF

# Start the app
nohup python3 -m gunicorn --bind 0.0.0.0:5000 --workers 2 app:app > /var/log/tracetrack.log 2>&1 &

# Wait and test
sleep 10
curl -f http://localhost:5000/health && echo "✅ TraceTrack running!"

echo "🚀 TraceTrack AWS deployment complete!"