#!/bin/bash

# TraceTrack AWS Deployment Script
set -e

echo "🚀 Starting TraceTrack deployment to AWS..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Get AWS account info
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo "📋 Account ID: $ACCOUNT_ID"
echo "📍 Region: $REGION"

# Create ECR repository
echo "📦 Creating ECR repository..."
aws ecr create-repository --repository-name tracetrack --region $REGION 2>/dev/null || echo "Repository already exists"

# Get ECR login
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t tracetrack .

# Tag and push image
echo "📤 Pushing image to ECR..."
docker tag tracetrack:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/tracetrack:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/tracetrack:latest

# Get default VPC and subnets
echo "🌐 Getting VPC information..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)
SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0:2].SubnetId' --output text | tr '\t' ',')

echo "VPC ID: $VPC_ID"
echo "Subnets: $SUBNETS"

# Generate random password
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Deploy CloudFormation stack
echo "☁️ Deploying CloudFormation stack..."
aws cloudformation create-stack \
    --stack-name tracetrack-app \
    --template-body file://aws-deploy.yml \
    --parameters \
        ParameterKey=VpcId,ParameterValue=$VPC_ID \
        ParameterKey=SubnetIds,ParameterValue="$SUBNETS" \
        ParameterKey=DatabasePassword,ParameterValue=$DB_PASSWORD \
    --capabilities CAPABILITY_IAM \
    --region $REGION

echo "⏳ Waiting for stack creation to complete..."
aws cloudformation wait stack-create-complete --stack-name tracetrack-app --region $REGION

# Get application URL
echo "🌍 Getting application URL..."
APP_URL=$(aws cloudformation describe-stacks \
    --stack-name tracetrack-app \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
    --output text \
    --region $REGION)

echo ""
echo "✅ Deployment complete!"
echo "🌐 Application URL: http://$APP_URL"
echo "🔑 Database password: $DB_PASSWORD"
echo ""
echo "Note: It may take a few minutes for the application to be fully available."
echo "You can check the ECS service status in the AWS console."