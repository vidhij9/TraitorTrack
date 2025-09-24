# TraceTrack AWS Deployment Guide

Complete AWS deployment configuration for TraceTrack using containerized infrastructure with PostgreSQL RDS and production-ready monitoring.

## 🏗️ Architecture Overview

### Infrastructure Components
- **VPC**: Multi-AZ setup with public and private subnets
- **Load Balancer**: Application Load Balancer with health checks
- **Container Service**: ECS Fargate for scalable container deployment
- **Database**: RDS PostgreSQL with automated backups and monitoring
- **Cache**: ElastiCache Redis for session storage and caching
- **Monitoring**: CloudWatch dashboards, alarms, and logging
- **Security**: Security groups, IAM roles, and Secrets Manager

### Networking
```
┌─── Public Subnets (ALB) ───┐    ┌─── Private Subnets (ECS) ───┐    ┌─── Private Subnets (RDS) ───┐
│ AZ-1a: 10.0.1.0/24        │    │ AZ-1a: 10.0.3.0/24          │    │ AZ-1a: Database              │
│ AZ-1b: 10.0.2.0/24        │    │ AZ-1b: 10.0.4.0/24          │    │ AZ-1b: Database (Multi-AZ)   │
└────────────────────────────┘    └──────────────────────────────┘    └──────────────────────────────┘
              │                                   │                                   │
         Internet Gateway                    NAT Gateway                        Security Groups
```

## 🚀 Quick Deployment

### Prerequisites
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Configure AWS credentials
aws configure

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

### One-Command Deployment
```bash
cd aws-deployment/scripts
./deploy-complete.sh \
  -e production \
  -k your-ec2-key-pair \
  -d "YourSecureDBPassword123!"
```

### Step-by-Step Deployment

#### 1. Build and Push Container Image
```bash
# Build and push to ECR
./build-and-push.sh -t v1.0.0

# Output: ECR image URI
# 123456789.dkr.ecr.us-east-1.amazonaws.com/tracetrack:v1.0.0
```

#### 2. Deploy Infrastructure
```bash
# Deploy VPC, Security Groups, Load Balancer, Database
./deploy-infrastructure.sh \
  -k your-ec2-key-pair \
  -d "YourSecureDBPassword123!" \
  -i "123456789.dkr.ecr.us-east-1.amazonaws.com/tracetrack:v1.0.0"
```

#### 3. Configure Secrets and Parameters
```bash
# Set up environment variables and secrets
./setup-secrets.sh \
  -e production \
  --sendgrid-key "SG.your-sendgrid-api-key" \
  --sendgrid-email "noreply@yourtracetrack.com"
```

#### 4. Setup Monitoring
```bash
# Deploy monitoring dashboards and alerts
./setup-monitoring.sh \
  -e production \
  -a "admin@yourtracetrack.com" \
  -s "https://hooks.slack.com/your-webhook"
```

## 📋 CloudFormation Stacks

### Infrastructure Stack (`infrastructure.yml`)
- VPC with public/private subnets across multiple AZs
- Internet Gateway and NAT Gateways
- Security Groups for ALB, ECS, RDS, and Redis
- Application Load Balancer with target groups
- Route tables and network ACLs

### Database Stack (`database.yml`)
- RDS PostgreSQL with Multi-AZ for production
- ElastiCache Redis cluster
- Database subnet groups and parameter groups
- Automated backups and maintenance windows
- Secrets Manager for database credentials

### Application Stack (`application.yml`)
- ECS Fargate cluster and service
- Task definition with container configuration
- Auto Scaling policies for CPU and memory
- CloudWatch log groups
- IAM roles and policies

### Monitoring Stack (`monitoring.yml`)
- CloudWatch dashboards and alarms
- SNS topics for alerting
- Custom metrics and log insights
- Performance monitoring for all components

## 🔐 Security Configuration

### IAM Roles
- **Task Execution Role**: Pulls images and accesses secrets
- **Task Role**: Application runtime permissions
- **Monitoring Role**: CloudWatch metrics and logs

### Secrets Management
- Database credentials in Secrets Manager
- Application secrets in Parameter Store
- Encrypted storage and transit
- Fine-grained access control

### Network Security
- Private subnets for application and database
- Security groups with minimal required access
- No direct internet access to application containers
- Load balancer in public subnets only

## 📊 Monitoring and Alerting

### CloudWatch Dashboards
- Application performance metrics
- Infrastructure health status
- Database and cache monitoring
- Custom business metrics

### Alerts
- High response time (>2 seconds)
- 5XX error rate threshold
- High CPU/memory utilization
- Database connection limits
- Failed health checks

### Log Aggregation
- Centralized application logs
- Structured logging with JSON format
- Log retention policies
- CloudWatch Insights queries

## 🔧 Operations

### Deployment Commands
```bash
# Update application with new image
./deploy-complete.sh --skip-infrastructure -t v1.1.0

# Scale service manually
aws ecs update-service \
  --cluster tracetrack-production-cluster \
  --service tracetrack-production-service \
  --desired-count 4

# View logs in real-time
aws logs tail /ecs/tracetrack-production --follow

# Execute command in running container
aws ecs execute-command \
  --cluster tracetrack-production-cluster \
  --task TASK_ID \
  --container tracetrack-app \
  --interactive \
  --command "/bin/bash"
```

### Database Operations
```bash
# Connect to database
aws rds describe-db-instances --db-instance-identifier tracetrack-production-postgres

# Create database backup
aws rds create-db-snapshot \
  --db-instance-identifier tracetrack-production-postgres \
  --db-snapshot-identifier tracetrack-backup-$(date +%Y%m%d)

# Monitor database performance
aws rds describe-db-log-files \
  --db-instance-identifier tracetrack-production-postgres
```

### Monitoring Commands
```bash
# View CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=tracetrack-production-service \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# Check alarm status
aws cloudwatch describe-alarms \
  --alarm-names tracetrack-production-high-cpu

# View dashboard
open "https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=tracetrack-production-dashboard"
```

## 🏥 Health Checks and Troubleshooting

### Application Health
- Health endpoint: `/health` returns service status
- Load balancer health checks every 30 seconds
- Container health checks with curl command
- Automatic service recovery on failures

### Common Issues

#### Service Won't Start
```bash
# Check ECS service events
aws ecs describe-services \
  --cluster tracetrack-production-cluster \
  --services tracetrack-production-service

# Check task definition
aws ecs describe-task-definition \
  --task-definition tracetrack-production:latest

# View container logs
aws logs get-log-events \
  --log-group-name /ecs/tracetrack-production \
  --log-stream-name ecs/tracetrack-app/TASK_ID
```

#### Database Connection Issues
```bash
# Test database connectivity
aws rds describe-db-instances \
  --db-instance-identifier tracetrack-production-postgres \
  --query 'DBInstances[0].DBInstanceStatus'

# Check security groups
aws ec2 describe-security-groups \
  --group-names tracetrack-production-db-sg
```

#### High Response Times
```bash
# Check ECS metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=tracetrack-production-service

# Check ALB metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=LOAD_BALANCER_FULL_NAME
```

## 💰 Cost Optimization

### Right-Sizing Resources
- Start with t3.micro for development
- Monitor utilization and scale as needed
- Use Fargate Spot for non-critical workloads
- Enable RDS storage auto-scaling

### Cost Monitoring
- Set up AWS Cost Explorer alerts
- Tag all resources for cost allocation
- Review monthly AWS bills
- Use Reserved Instances for predictable workloads

## 🔄 Disaster Recovery

### Backup Strategy
- Automated RDS backups (7-day retention)
- Cross-region snapshot copies
- Application state stored in database
- Infrastructure as code for quick rebuilding

### Recovery Procedures
1. **Database Recovery**: Restore from RDS snapshot
2. **Application Recovery**: Deploy from ECR image
3. **Infrastructure Recovery**: Re-run CloudFormation stacks
4. **Data Recovery**: Import from backup if needed

## 📈 Scaling

### Horizontal Scaling
- ECS Service Auto Scaling based on CPU/memory
- Application Load Balancer distributes traffic
- Multi-AZ deployment for high availability
- Database read replicas for read scaling

### Vertical Scaling
- Increase ECS task CPU/memory
- Upgrade RDS instance class
- Scale Redis cache node type
- Adjust connection pool sizes

## 🌐 Custom Domain Setup

### SSL Certificate
```bash
# Request SSL certificate
aws acm request-certificate \
  --domain-name yourtracetrack.com \
  --validation-method DNS \
  --subject-alternative-names www.yourtracetrack.com

# Update load balancer listener
aws elbv2 modify-listener \
  --listener-arn LISTENER_ARN \
  --certificates CertificateArn=CERTIFICATE_ARN
```

### DNS Configuration
```bash
# Create Route 53 hosted zone
aws route53 create-hosted-zone \
  --name yourtracetrack.com \
  --caller-reference $(date +%s)

# Create alias record
aws route53 change-resource-record-sets \
  --hosted-zone-id ZONE_ID \
  --change-batch file://dns-change-batch.json
```

## 🤝 Support

### Documentation
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS RDS Documentation](https://docs.aws.amazon.com/rds/)
- [CloudFormation Templates](./cloudformation/)

### Monitoring Dashboards
- Application Performance: CloudWatch Dashboard
- Infrastructure Health: AWS Systems Manager
- Cost Analysis: AWS Cost Explorer

For additional support, check the application logs and monitoring dashboards first, then refer to the troubleshooting section above.