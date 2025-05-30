# Complete AWS Deployment Guide for TraceTrack

This guide will walk you through deploying your TraceTrack application to AWS using EC2, RDS, and Application Load Balancer.

## Prerequisites

1. AWS Account with billing enabled
2. AWS CLI installed and configured
3. Domain name (optional but recommended)

## Step 1: Set Up AWS Infrastructure

### 1.1 Create RDS PostgreSQL Database

```bash
# Create DB subnet group
aws rds create-db-subnet-group \
    --db-subnet-group-name tracetrack-db-subnet-group \
    --db-subnet-group-description "Subnet group for TraceTrack database" \
    --subnet-ids subnet-xxxxxxxx subnet-yyyyyyyy

# Create security group for database
aws ec2 create-security-group \
    --group-name tracetrack-db-sg \
    --description "Security group for TraceTrack database"

# Allow PostgreSQL access from application servers
aws ec2 authorize-security-group-ingress \
    --group-name tracetrack-db-sg \
    --protocol tcp \
    --port 5432 \
    --source-group tracetrack-app-sg

# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier tracetrack-prod \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username tracetrack_admin \
    --master-user-password "YourSecurePassword123!" \
    --allocated-storage 20 \
    --vpc-security-group-ids sg-xxxxxxxxx \
    --db-subnet-group-name tracetrack-db-subnet-group \
    --backup-retention-period 7 \
    --storage-encrypted
```

### 1.2 Create EC2 Security Groups

```bash
# Application server security group
aws ec2 create-security-group \
    --group-name tracetrack-app-sg \
    --description "Security group for TraceTrack application servers"

# Allow HTTP traffic
aws ec2 authorize-security-group-ingress \
    --group-name tracetrack-app-sg \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0

# Allow HTTPS traffic
aws ec2 authorize-security-group-ingress \
    --group-name tracetrack-app-sg \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0

# Allow SSH access (restrict to your IP)
aws ec2 authorize-security-group-ingress \
    --group-name tracetrack-app-sg \
    --protocol tcp \
    --port 22 \
    --cidr YOUR_IP_ADDRESS/32
```

## Step 2: Launch EC2 Instance

### 2.1 Create EC2 Instance

```bash
# Launch EC2 instance
aws ec2 run-instances \
    --image-id ami-0c7217cdde317cfec \
    --count 1 \
    --instance-type t3.small \
    --key-name your-key-pair \
    --security-group-ids sg-xxxxxxxxx \
    --subnet-id subnet-xxxxxxxx \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=TraceTrack-App}]'
```

### 2.2 Connect to EC2 Instance

```bash
# SSH into your instance
ssh -i your-key-pair.pem ubuntu@your-ec2-public-ip
```

## Step 3: Set Up Application Environment

### 3.1 Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and pip
sudo apt install python3.11 python3.11-venv python3-pip nginx git -y

# Install PostgreSQL client
sudo apt install postgresql-client -y

# Install Gunicorn and other dependencies
sudo apt install python3.11-dev libpq-dev -y
```

### 3.2 Deploy Application

```bash
# Clone your repository
cd /opt
sudo git clone https://github.com/vidhij9/baggsy.git tracetrack
sudo chown -R ubuntu:ubuntu /opt/tracetrack
cd /opt/tracetrack

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3.3 Configure Environment Variables

```bash
# Create environment file
sudo nano /opt/tracetrack/.env
```

Add the following content:

```env
DATABASE_URL=postgresql://tracetrack_admin:YourSecurePassword123!@your-rds-endpoint:5432/postgres
SESSION_SECRET=your-super-secret-session-key-here
FLASK_ENV=production
FLASK_DEBUG=False
```

## Step 4: Configure Nginx

### 4.1 Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/tracetrack
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /opt/tracetrack/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 4.2 Enable Site

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/tracetrack /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Start Nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

## Step 5: Set Up Application Service

### 5.1 Create Systemd Service

```bash
sudo nano /etc/systemd/system/tracetrack.service
```

Add this content:

```ini
[Unit]
Description=TraceTrack Flask Application
After=network.target

[Service]
Type=exec
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/tracetrack
Environment=PATH=/opt/tracetrack/venv/bin
EnvironmentFile=/opt/tracetrack/.env
ExecStart=/opt/tracetrack/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 --timeout 300 main:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

### 5.2 Start Application Service

```bash
# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable tracetrack
sudo systemctl start tracetrack

# Check status
sudo systemctl status tracetrack
```

## Step 6: Set Up SSL with Let's Encrypt

### 6.1 Install Certbot

```bash
sudo apt install snapd
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

### 6.2 Get SSL Certificate

```bash
# Get certificate (make sure your domain points to your EC2 IP)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

## Step 7: Set Up Application Load Balancer (Optional)

### 7.1 Create Target Group

```bash
aws elbv2 create-target-group \
    --name tracetrack-targets \
    --protocol HTTP \
    --port 80 \
    --vpc-id vpc-xxxxxxxx \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3
```

### 7.2 Create Application Load Balancer

```bash
aws elbv2 create-load-balancer \
    --name tracetrack-alb \
    --subnets subnet-xxxxxxxx subnet-yyyyyyyy \
    --security-groups sg-xxxxxxxxx
```

### 7.3 Register Targets

```bash
aws elbv2 register-targets \
    --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/tracetrack-targets/xxxxxxxxx \
    --targets Id=i-xxxxxxxxx
```

## Step 8: Database Migration

### 8.1 Initialize Database

```bash
cd /opt/tracetrack
source venv/bin/activate

# Create tables
python -c "
from app_clean import app, db
with app.app_context():
    db.create_all()
    print('Database tables created successfully!')
"
```

## Step 9: Monitoring and Logging

### 9.1 Set Up CloudWatch Agent

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure CloudWatch agent
sudo nano /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
```

### 9.2 Configure Log Rotation

```bash
sudo nano /etc/logrotate.d/tracetrack
```

Add:

```
/opt/tracetrack/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        systemctl reload tracetrack
    endscript
}
```

## Step 10: Backup Strategy

### 10.1 Database Backups

```bash
# Create backup script
sudo nano /opt/backup-db.sh
```

Add:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"
mkdir -p $BACKUP_DIR

pg_dump $DATABASE_URL > $BACKUP_DIR/tracetrack_backup_$DATE.sql
aws s3 cp $BACKUP_DIR/tracetrack_backup_$DATE.sql s3://your-backup-bucket/

# Keep only last 7 days of local backups
find $BACKUP_DIR -name "tracetrack_backup_*.sql" -mtime +7 -delete
```

### 10.2 Set Up Cron Job

```bash
# Add to crontab
crontab -e
```

Add:

```
0 2 * * * /opt/backup-db.sh
```

## Step 11: Security Hardening

### 11.1 Configure Firewall

```bash
# Install and configure UFW
sudo ufw enable
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
```

### 11.2 Fail2ban Setup

```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## Step 12: Performance Optimization

### 12.1 Configure Gunicorn for Production

Update `/etc/systemd/system/tracetrack.service`:

```ini
ExecStart=/opt/tracetrack/venv/bin/gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 4 \
    --worker-class gevent \
    --worker-connections 1000 \
    --timeout 300 \
    --keepalive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile /opt/tracetrack/logs/access.log \
    --error-logfile /opt/tracetrack/logs/error.log \
    --log-level info \
    main:app
```

## Step 13: Domain and DNS Configuration

### 13.1 Route 53 Setup (if using AWS DNS)

```bash
# Create hosted zone
aws route53 create-hosted-zone \
    --name your-domain.com \
    --caller-reference $(date +%s)

# Create A record pointing to your Load Balancer or EC2 IP
aws route53 change-resource-record-sets \
    --hosted-zone-id ZXXXXXXXXXXXXX \
    --change-batch file://dns-record.json
```

## Cost Optimization Tips

1. **Use Reserved Instances** for production workloads
2. **Enable CloudWatch** for monitoring and alerting
3. **Set up Auto Scaling** for handling traffic spikes
4. **Use S3** for static file storage
5. **Enable RDS Multi-AZ** for high availability

## Troubleshooting Common Issues

### Application Won't Start
```bash
# Check logs
sudo journalctl -u tracetrack -f
sudo tail -f /opt/tracetrack/logs/error.log
```

### Database Connection Issues
```bash
# Test database connection
psql $DATABASE_URL -c "SELECT version();"
```

### SSL Certificate Issues
```bash
# Renew certificates
sudo certbot renew --dry-run
```

This complete guide should get your TraceTrack application running on AWS with proper security, monitoring, and backup strategies in place.