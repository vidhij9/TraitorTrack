# TraceTrack AWS Deployment Guide

This guide will help you deploy your TraceTrack application to AWS using ECS, ECR, and CloudFormation.

## Prerequisites

1. **AWS Account**: You need an AWS account with appropriate permissions
2. **AWS CLI**: Install and configure AWS CLI
3. **Docker**: Docker must be installed and running
4. **Python**: Python 3.11+ with pip

## Required AWS Permissions

Your AWS user/role needs the following permissions:
- CloudFormation (Full access)
- ECS (Full access)
- ECR (Full access)
- IAM (Limited - for ECS task execution role)
- CloudWatch Logs (Full access)
- VPC, EC2, ALB (for infrastructure)

## Quick Deployment

### Option 1: Interactive Deployment (Recommended)

```bash
# Make the deployment script executable
chmod +x deploy.sh

# Run the deployment script
./deploy.sh
```

The script will:
1. Prompt for your AWS credentials if not set
2. Verify AWS credentials
3. Install required packages
4. Check Docker status
5. Deploy the application

### Option 2: Manual Deployment

If you prefer to set credentials manually:

```bash
# Set your AWS credentials
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_DEFAULT_REGION="ap-south-1"

# Install required packages
pip install boto3 docker

# Run the deployment
python deploy_aws_complete.py
```

## What Gets Deployed

The deployment creates the following AWS resources:

### Infrastructure (CloudFormation)
- **VPC** with public subnets
- **Application Load Balancer** (ALB)
- **Security Groups** for ALB and containers
- **Internet Gateway** and routing
- **Target Groups** for ECS service

### Application (ECS)
- **ECR Repository** for Docker images
- **ECS Cluster** (Fargate)
- **Task Definition** with container configuration
- **ECS Service** with load balancer integration
- **CloudWatch Log Group** for application logs

### Container Configuration
- **Docker Image**: Python 3.11 with all dependencies
- **Port**: 8000 (mapped to ALB)
- **Resources**: 1 vCPU, 2GB RAM
- **Health Check**: `/health` endpoint
- **Scaling**: 2 desired tasks with auto-scaling

## Deployment Process

1. **ECR Setup**: Creates container registry
2. **Docker Build**: Builds and pushes application image
3. **Infrastructure**: Creates VPC, ALB, security groups
4. **ECS Setup**: Creates cluster, task definition, and service
5. **Health Checks**: Verifies deployment success

## Monitoring and Logs

### CloudWatch Logs
- Log Group: `/ecs/tracetrack`
- Streams: Individual container logs
- URL: https://console.aws.amazon.com/cloudwatch/home#logsV2:log-groups/log-group/$252Fecs$252Ftracetrack

### Application Health
- Health Check: `http://your-alb-url/health`
- Production Health: `http://your-alb-url/production-health`

## Accessing Your Application

After successful deployment, you'll get:
- **Application URL**: Load balancer URL
- **Admin Access**: `admin/admin` (created automatically)

## Scaling and Performance

### Auto Scaling
- **Minimum**: 2 tasks
- **Maximum**: 10 tasks (configurable)
- **CPU Threshold**: 70% average
- **Memory Threshold**: 80% average

### Performance Optimizations
- **Connection Pooling**: Optimized database connections
- **Caching**: Redis-based caching layer
- **Load Balancing**: ALB with health checks
- **Container Optimization**: Multi-stage Docker build

## Troubleshooting

### Common Issues

1. **Docker Not Running**
   ```bash
   # Start Docker
   sudo systemctl start docker
   ```

2. **AWS Credentials Invalid**
   ```bash
   # Verify credentials
   aws sts get-caller-identity
   ```

3. **CloudFormation Stack Fails**
   - Check CloudFormation events in AWS Console
   - Verify IAM permissions
   - Check resource limits

4. **ECS Service Not Starting**
   - Check ECS service events
   - Verify task definition
   - Check CloudWatch logs

### Logs and Debugging

```bash
# Check ECS service status
aws ecs describe-services --cluster tracetrack-cluster --services tracetrack-service

# Check task logs
aws logs describe-log-streams --log-group-name /ecs/tracetrack

# Get task logs
aws logs get-log-events --log-group-name /ecs/tracetrack --log-stream-name <stream-name>
```

## Cleanup

To remove all deployed resources:

```bash
# Delete CloudFormation stack (removes all resources)
aws cloudformation delete-stack --stack-name tracetrack-production

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete --stack-name tracetrack-production
```

## Cost Estimation

Estimated monthly costs (ap-south-1 region):
- **ECS Fargate**: ~$30-50 (2 tasks running 24/7)
- **ALB**: ~$20
- **CloudWatch Logs**: ~$5-10
- **Data Transfer**: ~$5-15
- **Total**: ~$60-100/month

## Security Considerations

- **VPC**: Application runs in private subnets
- **Security Groups**: Minimal required ports open
- **IAM**: Least privilege access
- **Encryption**: ECR images encrypted at rest
- **HTTPS**: ALB terminates SSL (configure certificate)

## Support

If you encounter issues:
1. Check CloudWatch logs first
2. Verify AWS service limits
3. Review IAM permissions
4. Check application logs in ECS tasks

## Next Steps

After deployment:
1. Configure custom domain and SSL certificate
2. Set up monitoring and alerting
3. Configure backup strategies
4. Implement CI/CD pipeline
5. Set up production database (RDS/Aurora)