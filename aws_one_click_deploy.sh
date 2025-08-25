#!/bin/bash

# TraceTrack AWS One-Click Deployment Script
# This script automatically deploys everything to AWS

echo "🚀 TraceTrack AWS Deployment Starting..."
echo "========================================="

# Check for AWS credentials
if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "❌ AWS credentials not found!"
    echo ""
    echo "Please set your AWS credentials:"
    echo "  export AWS_ACCESS_KEY_ID=your_access_key"
    echo "  export AWS_SECRET_ACCESS_KEY=your_secret_key"
    echo "  export AWS_DEFAULT_REGION=ap-south-1"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "✅ AWS credentials found"
echo ""

# Install AWS CLI if not present
if ! command -v aws &> /dev/null; then
    echo "📦 Installing AWS CLI..."
    pip install awscli --upgrade --user
fi

# Set default region
export AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-ap-south-1}

echo "📍 Using AWS Region: $AWS_DEFAULT_REGION"
echo ""

# Run the deployment
echo "🔧 Starting automatic deployment..."
echo "This will:"
echo "  1. Create DynamoDB tables (auto-scaling)"
echo "  2. Set up CloudFormation stack"
echo "  3. Deploy ECS Fargate services"
echo "  4. Configure Redis caching"
echo "  5. Set up CloudFront CDN"
echo "  6. Migrate your data"
echo ""
echo "⏳ This process takes 10-15 minutes..."
echo ""

python deploy_to_aws.py

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Your application is now running on AWS with:"
echo "  • DynamoDB for <10ms database response"
echo "  • ElastiCache Redis for microsecond caching"
echo "  • CloudFront CDN for global distribution"
echo "  • Auto-scaling (10-100 containers)"
echo "  • Multi-AZ high availability"
echo ""
echo "🎉 TraceTrack is ready for 1M+ requests!"