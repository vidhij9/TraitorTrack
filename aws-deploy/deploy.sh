#!/bin/bash

# Deploy to AWS EC2 instance
echo "Deploying TraceTrack to AWS..."

# Install dependencies
sudo apt-get update -y
sudo apt-get install -y python3-pip nginx supervisor awscli

# Setup application directory
sudo mkdir -p /opt/tracetrack
sudo cp app.py /opt/tracetrack/
sudo cp requirements.txt /opt/tracetrack/

cd /opt/tracetrack

# Install Python packages
sudo pip3 install -r requirements.txt

# Get database URL from Parameter Store
DB_URL=$(aws ssm get-parameter --name "/tracetrack/production/DATABASE_URL" --with-decryption --query 'Parameter.Value' --output text --region ap-south-1 2>/dev/null)

# Configure nginx
sudo tee /etc/nginx/sites-available/default > /dev/null <<'NGINX'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:5000/health;
    }
}
NGINX

sudo nginx -t && sudo systemctl restart nginx

# Configure supervisor
sudo tee /etc/supervisor/conf.d/tracetrack.conf > /dev/null <<SUPERVISOR
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

# Restart services
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart tracetrack || sudo supervisorctl start tracetrack

echo "Deployment complete!"
