#!/bin/bash
set -e

echo "============================================"
echo "TRACETRACK AWS DEPLOYMENT"
echo "============================================"
echo ""

# Check if AWS credentials are provided
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "❌ AWS credentials not found in environment variables"
    echo ""
    echo "Please provide your AWS credentials:"
    echo ""
    read -p "Enter AWS Access Key ID: " aws_access_key
    read -s -p "Enter AWS Secret Access Key: " aws_secret_key
    echo ""
    read -p "Enter AWS Region (default: ap-south-1): " aws_region
    
    # Set default region if not provided
    aws_region=${aws_region:-ap-south-1}
    
    # Export credentials
    export AWS_ACCESS_KEY_ID="$aws_access_key"
    export AWS_SECRET_ACCESS_KEY="$aws_secret_key"
    export AWS_DEFAULT_REGION="$aws_region"
    
    echo "✅ AWS credentials configured"
fi

# Verify AWS credentials
echo "🔐 Verifying AWS credentials..."
aws sts get-caller-identity > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Invalid AWS credentials"
    exit 1
fi

echo "✅ AWS credentials verified"
echo ""

# Install required packages
echo "📦 Installing required packages..."
pip install boto3 docker --quiet

# Check if Docker is running
echo "🐳 Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Run the deployment
echo "🚀 Starting deployment..."
python deploy_aws_complete.py

echo ""
echo "============================================"
echo "DEPLOYMENT COMPLETED"
echo "============================================"
echo ""
echo "Your application should now be deployed on AWS!"
echo ""
echo "To check the status:"
echo "1. AWS Console: https://console.aws.amazon.com/ecs/home"
echo "2. CloudFormation: https://console.aws.amazon.com/cloudformation/home"
echo "3. ECR: https://console.aws.amazon.com/ecr/home"
echo ""
echo "To clean up resources when done:"
echo "aws cloudformation delete-stack --stack-name tracetrack-production"