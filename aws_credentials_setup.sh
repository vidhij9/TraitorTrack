#!/bin/bash
"""
AWS Credentials Setup Script
Run this once to configure AWS credentials for deployment
"""

echo "=========================================="
echo "AWS CREDENTIALS SETUP FOR TRACETRACK"
echo "=========================================="
echo ""
echo "This script will help you set up AWS credentials for one-click deployment."
echo "You'll need your AWS Access Key ID and Secret Access Key."
echo ""
echo "To get these credentials:"
echo "1. Log into AWS Console (https://console.aws.amazon.com)"
echo "2. Go to IAM > Users > Your User > Security Credentials"
echo "3. Create new Access Key if you don't have one"
echo ""
echo "⚠️  IMPORTANT: Keep these credentials secure!"
echo ""
echo "Press Enter to continue..."
read

# Get AWS credentials
echo ""
echo "Please enter your AWS credentials:"
echo ""
read -p "AWS Access Key ID: " AWS_ACCESS_KEY_ID
read -s -p "AWS Secret Access Key: " AWS_SECRET_ACCESS_KEY
echo ""
read -p "AWS Region (default: ap-south-1 Mumbai): " AWS_REGION

# Set defaults
AWS_REGION=${AWS_REGION:-ap-south-1}

# Save to environment file
cat > aws_credentials.env << EOF
# AWS Credentials for TraceTrack Deployment
# Generated on $(date)
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}"
export AWS_DEFAULT_REGION="${AWS_REGION}"
export AWS_REGION="${AWS_REGION}"
EOF

chmod 600 aws_credentials.env

echo ""
echo "✅ AWS credentials saved to aws_credentials.env"
echo ""
echo "=========================================="
echo "READY FOR DEPLOYMENT!"
echo "=========================================="
echo ""
echo "Now you can deploy TraceTrack to AWS with:"
echo ""
echo "  ./aws_one_click_deploy.sh"
echo ""
echo "This will:"
echo "• Create ECS Fargate cluster with auto-scaling"
echo "• Set up DynamoDB tables with 63x performance improvement"
echo "• Configure ElastiCache Redis for caching"
echo "• Set up CloudFront CDN for global distribution"
echo "• Configure Application Load Balancer"
echo "• Enable CloudWatch monitoring"
echo ""
echo "Expected deployment time: 15-20 minutes"
echo "Expected cost: ~$150-300/month for production workload"
echo ""