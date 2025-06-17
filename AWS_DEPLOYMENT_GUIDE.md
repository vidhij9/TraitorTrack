# AWS Deployment Guide for TraceTrack

## Prerequisites
- AWS CLI configured with appropriate permissions
- Docker installed locally
- AWS account with VPC and subnets set up

## Option 1: Quick Deploy with ECS (Recommended)

### Step 1: Build and Push Docker Image
```bash
# Create ECR repository
aws ecr create-repository --repository-name tracetrack

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag image
docker build -t tracetrack .
docker tag tracetrack:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/tracetrack:latest

# Push image
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/tracetrack:latest
```

### Step 2: Deploy CloudFormation Stack
```bash
aws cloudformation create-stack \
  --stack-name tracetrack-app \
  --template-body file://aws-deploy.yml \
  --parameters ParameterKey=VpcId,ParameterValue=vpc-xxxxxxxx \
               ParameterKey=SubnetIds,ParameterValue=subnet-xxxxxxxx,subnet-yyyyyyyy \
               ParameterKey=DatabasePassword,ParameterValue=YourSecurePassword123 \
  --capabilities CAPABILITY_IAM
```

### Step 3: Get Application URL
```bash
aws cloudformation describe-stacks \
  --stack-name tracetrack-app \
  --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
  --output text
```

## Option 2: EC2 with Docker Compose

### Step 1: Launch EC2 Instance
- Use Amazon Linux 2 AMI
- Instance type: t3.small or larger
- Security group: Allow HTTP (80), SSH (22)
- Install Docker and Docker Compose

### Step 2: Deploy Application
```bash
# Copy files to EC2
scp -i your-key.pem docker-compose.yml ec2-user@your-instance-ip:~/
scp -i your-key.pem -r . ec2-user@your-instance-ip:~/tracetrack/

# SSH to instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Install Docker
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Start application
cd tracetrack
docker-compose up -d
```

## Option 3: AWS App Runner (Simplest)

### Step 1: Create apprunner.yaml
```yaml
version: 1.0
runtime: python3
build:
  commands:
    build:
      - pip install -r requirements.txt
run:
  runtime-version: 3.11
  command: gunicorn --bind 0.0.0.0:8000 main:app
  network:
    port: 8000
    env: PORT
  env:
    - name: DATABASE_URL
      value: "your-database-url"
    - name: SESSION_SECRET
      value: "your-session-secret"
```

### Step 2: Deploy via AWS Console
1. Go to AWS App Runner service
2. Create new service
3. Connect to your GitHub repository
4. Configure build settings
5. Set environment variables
6. Deploy

## Environment Variables Required
- `DATABASE_URL`: PostgreSQL connection string
- `SESSION_SECRET`: Secret key for sessions
- `FLASK_ENV`: Set to 'production'

## Database Setup
For production, use AWS RDS PostgreSQL:
1. Create RDS PostgreSQL instance
2. Configure security groups
3. Create database and user
4. Update DATABASE_URL environment variable

## Domain and SSL
1. Register domain in Route 53
2. Create SSL certificate in ACM
3. Configure ALB to use HTTPS
4. Update security groups for port 443

## Monitoring
- CloudWatch logs are automatically configured
- Set up CloudWatch alarms for health checks
- Consider AWS X-Ray for distributed tracing

## Scaling
- ECS: Adjust desired count in service
- EC2: Use Auto Scaling Groups
- App Runner: Automatic scaling included

## Cost Optimization
- Use t3.micro for development
- Consider Reserved Instances for production
- Set up billing alerts
- Use AWS Cost Explorer for monitoring
