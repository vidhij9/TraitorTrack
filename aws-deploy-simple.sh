#!/bin/bash

# TraceTrack AWS Deployment Script - Simple version
# Deploys to AWS ap-south-1 (Mumbai)

set -e

# Configuration
PROJECT_NAME="tracetrack"
AWS_REGION="ap-south-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
IMAGE_TAG="latest"
STACK_NAME="${PROJECT_NAME}-stack"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Starting TraceTrack AWS Deployment${NC}"
echo "Region: $AWS_REGION"
echo "Account: $AWS_ACCOUNT_ID"

# Step 1: Create ECR repository if it doesn't exist
echo -e "\n${BLUE}Step 1: Setting up ECR repository...${NC}"
aws ecr describe-repositories --repository-names "$PROJECT_NAME" --region "$AWS_REGION" >/dev/null 2>&1 || \
aws ecr create-repository \
    --repository-name "$PROJECT_NAME" \
    --region "$AWS_REGION" \
    --image-scanning-configuration scanOnPush=true \
    >/dev/null

# Step 2: Login to ECR
echo -e "\n${BLUE}Step 2: Logging in to ECR...${NC}"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Step 3: Build Docker image
echo -e "\n${BLUE}Step 3: Building Docker image...${NC}"
docker build -t "$PROJECT_NAME:$IMAGE_TAG" .

# Step 4: Tag and push to ECR
echo -e "\n${BLUE}Step 4: Pushing to ECR...${NC}"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${PROJECT_NAME}:${IMAGE_TAG}"
docker tag "$PROJECT_NAME:$IMAGE_TAG" "$ECR_URI"
docker push "$ECR_URI"

# Step 5: Deploy infrastructure
echo -e "\n${BLUE}Step 5: Deploying infrastructure...${NC}"
aws cloudformation deploy \
    --template-file aws-deployment/cloudformation/infrastructure.yml \
    --stack-name "${STACK_NAME}-infrastructure" \
    --parameter-overrides \
        ProjectName="$PROJECT_NAME" \
        Environment="production" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$AWS_REGION" \
    --no-fail-on-empty-changeset

# Step 6: Get infrastructure outputs
VPC_ID=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}-infrastructure" \
    --query "Stacks[0].Outputs[?OutputKey=='VPCId'].OutputValue" \
    --output text \
    --region "$AWS_REGION")

PUBLIC_SUBNET1=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}-infrastructure" \
    --query "Stacks[0].Outputs[?OutputKey=='PublicSubnet1Id'].OutputValue" \
    --output text \
    --region "$AWS_REGION")

PUBLIC_SUBNET2=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}-infrastructure" \
    --query "Stacks[0].Outputs[?OutputKey=='PublicSubnet2Id'].OutputValue" \
    --output text \
    --region "$AWS_REGION")

PRIVATE_SUBNET1=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}-infrastructure" \
    --query "Stacks[0].Outputs[?OutputKey=='PrivateSubnet1Id'].OutputValue" \
    --output text \
    --region "$AWS_REGION")

PRIVATE_SUBNET2=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}-infrastructure" \
    --query "Stacks[0].Outputs[?OutputKey=='PrivateSubnet2Id'].OutputValue" \
    --output text \
    --region "$AWS_REGION")

# Step 7: Store secrets
echo -e "\n${BLUE}Step 7: Storing application secrets...${NC}"
aws ssm put-parameter \
    --name "/tracetrack/production/DATABASE_URL" \
    --type SecureString \
    --value "${PRODUCTION_DATABASE_URL}" \
    --overwrite \
    --region "$AWS_REGION" >/dev/null 2>&1 || true

aws ssm put-parameter \
    --name "/tracetrack/production/SESSION_SECRET" \
    --type SecureString \
    --value "tracetrack-aws-session-$(date +%s)" \
    --overwrite \
    --region "$AWS_REGION" >/dev/null 2>&1 || true

# Step 8: Deploy application
echo -e "\n${BLUE}Step 8: Deploying application to ECS...${NC}"
aws cloudformation deploy \
    --template-file aws-deployment/cloudformation/application.yml \
    --stack-name "${STACK_NAME}-application" \
    --parameter-overrides \
        ProjectName="$PROJECT_NAME" \
        Environment="production" \
        ImageURI="$ECR_URI" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$AWS_REGION" \
    --no-fail-on-empty-changeset

# Step 9: Get application URL
ALB_URL=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}-infrastructure" \
    --query "Stacks[0].Outputs[?OutputKey=='ALBDnsName'].OutputValue" \
    --output text \
    --region "$AWS_REGION")

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Application URL: ${GREEN}http://$ALB_URL${NC}"
echo -e "Health Check: ${GREEN}http://$ALB_URL/health${NC}"
echo ""
echo "Please wait a few minutes for the application to become available."
echo "Check the AWS Console for deployment status."