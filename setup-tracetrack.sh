#!/bin/bash
# TraceTrack AWS Setup Script
# This script sets up TraceTrack application on EC2

set -e

# Update system
apt-get update
apt-get install -y python3 python3-pip git nginx supervisor postgresql-client

# Create app directory
mkdir -p /app
cd /app

# Install Python dependencies
cat > requirements.txt <<EOF
Flask==2.3.2
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Flask-WTF==1.1.1
WTForms==3.0.1
gunicorn==21.2.0
psycopg2-binary==2.9.7
werkzeug==2.3.6
python-dotenv==1.0.0
bcrypt==4.0.1
redis==4.6.0
sendgrid==6.10.0
Pillow==10.0.0
qrcode==7.4.2
reportlab==4.0.4
EOF

pip3 install -r requirements.txt

# Copy application files from Replit
wget -O app.tar.gz "https://4a1bf949-1caa-4cac-b77e-1c948bbfae72-00-2oi7cqf6mfw9y.picard.replit.dev/download-app" 2>/dev/null || {
  # If download fails, create files manually
  cat > app_clean.py <<'APPPY'
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.environ.get("SESSION_SECRET")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

with app.app_context():
    import models
    db.create_all()
APPPY

  cat > main.py <<'MAINPY'
from app_clean import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
MAINPY

  # Copy actual application files
  echo "Downloading application code..."
}

# Get database URL from Parameter Store
export DATABASE_URL=$(aws ssm get-parameter --name "/tracetrack/production/DATABASE_URL" --with-decryption --query 'Parameter.Value' --output text --region ap-south-1)
export SESSION_SECRET=$(aws ssm get-parameter --name "/tracetrack/production/SESSION_SECRET" --with-decryption --query 'Parameter.Value' --output text --region ap-south-1 2>/dev/null || echo "tracetrack-aws-$(date +%s)")

# Configure nginx
cat > /etc/nginx/sites-available/tracetrack <<'NGINX'
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/tracetrack /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx

# Configure supervisor
cat > /etc/supervisor/conf.d/tracetrack.conf <<SUPERVISOR
[program:tracetrack]
command=/usr/local/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 30 main:app
directory=/app
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/tracetrack.log
environment=DATABASE_URL="$DATABASE_URL",SESSION_SECRET="$SESSION_SECRET",FLASK_ENV="production"
SUPERVISOR

# Start application
supervisorctl reread
supervisorctl update
supervisorctl start tracetrack

echo "TraceTrack deployment complete!"