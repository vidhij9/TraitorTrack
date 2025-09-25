#!/bin/bash

# TraceTrack EC2 Deployment Script
# Deploys directly to AWS EC2 in ap-south-1 (Mumbai)

set -e

# Configuration
AWS_REGION="ap-south-1"
STACK_NAME="tracetrack-ec2-production"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Deploying TraceTrack to AWS EC2 in ${AWS_REGION}${NC}"

# Deploy CloudFormation stack
echo -e "\n${BLUE}Creating EC2 instance and deploying application...${NC}"
aws cloudformation deploy \
    --template-file aws-ec2-deployment.yml \
    --stack-name "$STACK_NAME" \
    --parameter-overrides \
        InstanceType="t2.medium" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$AWS_REGION" \
    --no-fail-on-empty-changeset

# Get outputs
echo -e "\n${BLUE}Getting deployment information...${NC}"
INSTANCE_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue" \
    --output text \
    --region "$AWS_REGION")

PUBLIC_IP=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='PublicIP'].OutputValue" \
    --output text \
    --region "$AWS_REGION")

# Wait for instance to be running
echo -e "\n${BLUE}Waiting for instance to be ready...${NC}"
aws ec2 wait instance-status-ok --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" 2>/dev/null || true

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Instance ID: ${GREEN}$INSTANCE_ID${NC}"
echo -e "Public IP: ${GREEN}$PUBLIC_IP${NC}"
echo ""
echo -e "Application URL: ${GREEN}http://$PUBLIC_IP${NC}"
echo -e "Health Check: ${GREEN}http://$PUBLIC_IP/health${NC}"
echo ""
echo "The application should be available in 2-3 minutes."
echo "Default login: admin / admin"