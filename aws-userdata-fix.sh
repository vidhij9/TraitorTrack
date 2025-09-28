#!/bin/bash

# Fix AWS deployment using EC2 User Data update
echo "Fixing AWS deployment using alternative method..."

# Stop the instance
echo "Stopping instance for user data update..."
aws ec2 stop-instances --instance-ids i-0057a68f7062dd425 --region ap-south-1

# Wait for instance to stop
echo "Waiting for instance to stop..."
aws ec2 wait instance-stopped --instance-ids i-0057a68f7062dd425 --region ap-south-1

# Update user data with deployment script
echo "Updating user data..."
cat > /tmp/userdata.sh <<'USERDATA'
#!/bin/bash

# Update system
apt-get update -y
apt-get install -y python3-pip nginx supervisor awscli

# Create app directory
mkdir -p /opt/tracetrack
cd /opt/tracetrack

# Install Python packages
pip3 install Flask==2.3.2 Flask-SQLAlchemy==3.0.5 Flask-Login==0.6.3 Flask-WTF==1.1.1 gunicorn==21.2.0 psycopg2-binary==2.9.7 werkzeug==2.3.6 bcrypt==4.0.1 WTForms==3.0.1

# Get database URL from Parameter Store
DB_URL=$(aws ssm get-parameter --name "/tracetrack/production/DATABASE_URL" --with-decryption --query 'Parameter.Value' --output text --region ap-south-1)

# Create the application file
cat > /opt/tracetrack/app.py <<'APP'
import os
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import func

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.environ.get("SESSION_SECRET", "tracetrack-aws-secret-2025")

database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='dispatcher')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>TraceTrack Login</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center;">
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-6">
                    <div class="card" style="border-radius: 15px;">
                        <div class="card-body p-5">
                            <h2 class="text-center mb-4">TraceTrack Login</h2>
                            <form method="POST">
                                <div class="mb-3">
                                    <label>Username</label>
                                    <input type="text" class="form-control" name="username" required>
                                </div>
                                <div class="mb-3">
                                    <label>Password</label>
                                    <input type="password" class="form-control" name="password" required>
                                </div>
                                <button type="submit" class="btn btn-primary w-100">Login</button>
                            </form>
                            <div class="mt-3 text-center text-muted">
                                <small>Demo: admin/admin</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    ''')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>TraceTrack Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh;">
        <nav class="navbar navbar-expand-lg navbar-dark">
            <div class="container">
                <a class="navbar-brand" href="/dashboard">TraceTrack</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/logout">Logout</a>
                </div>
            </div>
        </nav>
        <div class="container mt-4">
            <div class="card">
                <div class="card-body">
                    <h1>TraceTrack Dashboard</h1>
                    <p>Welcome, {{ current_user.username }}!</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    ''')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'TraceTrack'}, 200

with app.app_context():
    try:
        db.create_all()
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@tracetrack.com', role='admin')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
    except Exception as e:
        print(f"Database init: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
APP

# Configure nginx
cat > /etc/nginx/sites-available/default <<'NGINX'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:5000/health;
    }
}
NGINX

nginx -t && systemctl restart nginx

# Configure supervisor
cat > /etc/supervisor/conf.d/tracetrack.conf <<SUPERVISOR
[program:tracetrack]
command=/usr/local/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 120 app:app
directory=/opt/tracetrack
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/tracetrack.log
stderr_logfile=/var/log/tracetrack.error.log
environment=DATABASE_URL="$DB_URL",SESSION_SECRET="tracetrack-aws-2025",FLASK_ENV="production"
SUPERVISOR

supervisorctl reread
supervisorctl update
supervisorctl restart tracetrack

echo "TraceTrack deployment complete!" > /var/log/tracetrack-deploy.log
USERDATA

# Encode user data
base64 /tmp/userdata.sh > /tmp/userdata.b64

# Update instance user data
aws ec2 modify-instance-attribute \
    --instance-id i-0057a68f7062dd425 \
    --user-data file:///tmp/userdata.b64 \
    --region ap-south-1

# Start the instance
echo "Starting instance..."
aws ec2 start-instances --instance-ids i-0057a68f7062dd425 --region ap-south-1

# Wait for instance to be running
echo "Waiting for instance to start..."
aws ec2 wait instance-running --instance-ids i-0057a68f7062dd425 --region ap-south-1

echo "AWS deployment fix initiated. The instance will run the deployment script on startup."
echo "Please wait 2-3 minutes for the deployment to complete."
echo "Check http://13.201.135.42 in a few minutes."