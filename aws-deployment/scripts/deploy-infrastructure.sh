#!/bin/bash

# TraceTrack AWS Infrastructure Deployment Script
# Deploys VPC, Subnets, Security Groups, Load Balancer, Database, and Application

set -e

# Default values
PROJECT_NAME="tracetrack"
ENVIRONMENT="production"
AWS_REGION="ap-south-1"
KEY_PAIR_NAME=""
# Database passwords are now managed by AWS RDS
STACK_PREFIX="${PROJECT_NAME}-${ENVIRONMENT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -p, --project-name NAME     Project name (default: tracetrack)"
    echo "  -e, --environment ENV       Environment (development/staging/production)"
    echo "  -r, --region REGION         AWS region (default: us-east-1)"
    echo "  -k, --key-pair KEY          EC2 Key Pair name (required)"
    echo "  # Database passwords are now automatically managed by AWS RDS"
    echo "  -i, --image-uri URI         ECR image URI (required for application)"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 -k my-key-pair -i 123456789012.dkr.ecr.ap-south-1.amazonaws.com/tracetrack:latest"
}

log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed"
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS credentials not configured"
    fi
    
    # Check required parameters
    if [[ -z "$KEY_PAIR_NAME" ]]; then
        error "Key pair name is required (-k option)"
    fi
    
    # Database passwords are automatically managed by AWS RDS
    
    success "Prerequisites check passed"
}

deploy_stack() {
    local template_file=$1
    local stack_name=$2
    local parameters=$3
    
    log "Deploying stack: $stack_name"
    
    if aws cloudformation describe-stacks --stack-name "$stack_name" --region "$AWS_REGION" &> /dev/null; then
        log "Stack $stack_name exists, updating..."
        aws cloudformation update-stack \
            --stack-name "$stack_name" \
            --template-body "file://$template_file" \
            --parameters "$parameters" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$AWS_REGION" || {
                if [[ $? -eq 255 ]]; then
                    warning "No updates for stack $stack_name"
                else
                    error "Failed to update stack $stack_name"
                fi
            }
    else
        log "Creating new stack: $stack_name"
        aws cloudformation create-stack \
            --stack-name "$stack_name" \
            --template-body "file://$template_file" \
            --parameters "$parameters" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$AWS_REGION" || error "Failed to create stack $stack_name"
    fi
    
    log "Waiting for stack $stack_name to complete..."
    aws cloudformation wait stack-update-complete \
        --stack-name "$stack_name" \
        --region "$AWS_REGION" 2>/dev/null || \
    aws cloudformation wait stack-create-complete \
        --stack-name "$stack_name" \
        --region "$AWS_REGION" || error "Stack $stack_name deployment failed"
    
    success "Stack $stack_name deployed successfully"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project-name)
            PROJECT_NAME="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -k|--key-pair)
            KEY_PAIR_NAME="$2"
            shift 2
            ;;
        -i|--image-uri)
            IMAGE_URI="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Update stack prefix
STACK_PREFIX="${PROJECT_NAME}-${ENVIRONMENT}"

echo "🚀 TraceTrack AWS Infrastructure Deployment"
echo "==========================================="
echo "Project Name: $PROJECT_NAME"
echo "Environment: $ENVIRONMENT"
echo "AWS Region: $AWS_REGION"
echo "Stack Prefix: $STACK_PREFIX"
echo ""

check_prerequisites

# Deploy infrastructure stack
log "Step 1: Deploying infrastructure (VPC, Subnets, Security Groups, Load Balancer)..."
deploy_stack \
    "cloudformation/infrastructure.yml" \
    "${STACK_PREFIX}-infrastructure" \
    "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME ParameterKey=Environment,ParameterValue=$ENVIRONMENT ParameterKey=KeyPairName,ParameterValue=$KEY_PAIR_NAME"

# Deploy database stack
log "Step 2: Deploying database infrastructure (RDS PostgreSQL, ElastiCache Redis)..."
deploy_stack \
    "cloudformation/database.yml" \
    "${STACK_PREFIX}-database" \
    "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME ParameterKey=Environment,ParameterValue=$ENVIRONMENT"

# Deploy application stack (if image URI provided)
if [[ -n "$IMAGE_URI" ]]; then
    log "Step 3: Deploying application (ECS Fargate Service)..."
    deploy_stack \
        "cloudformation/application.yml" \
        "${STACK_PREFIX}-application" \
        "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME ParameterKey=Environment,ParameterValue=$ENVIRONMENT ParameterKey=ImageURI,ParameterValue=$IMAGE_URI"
else
    warning "No image URI provided, skipping application deployment"
    warning "To deploy the application later, run:"
    warning "aws cloudformation create-stack --stack-name ${STACK_PREFIX}-application --template-body file://cloudformation/application.yml --parameters ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME ParameterKey=Environment,ParameterValue=$ENVIRONMENT ParameterKey=ImageURI,ParameterValue=YOUR_IMAGE_URI --capabilities CAPABILITY_NAMED_IAM --region $AWS_REGION"
fi

# Get outputs
log "Getting deployment outputs..."
ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_PREFIX}-infrastructure" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
    --output text)

DB_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_PREFIX}-database" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' \
    --output text)

REDIS_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_PREFIX}-database" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`RedisEndpoint`].OutputValue' \
    --output text)

echo ""
success "🎉 TraceTrack infrastructure deployed successfully!"
echo ""
echo "📋 Deployment Summary:"
echo "====================="
echo "Application URL: http://$ALB_DNS"
echo "Database Endpoint: $DB_ENDPOINT:5432"
echo "Redis Endpoint: $REDIS_ENDPOINT:6379"
echo ""
echo "🔧 Next Steps:"
echo "=============="
if [[ -z "$IMAGE_URI" ]]; then
    echo "1. Build and push your Docker image to ECR"
    echo "2. Deploy the application stack with the image URI"
fi
echo "3. Configure DNS (optional)"
echo "4. Set up SSL certificate (optional)"
echo "5. Configure monitoring and alerts"
echo ""
echo "📖 Documentation: README.md"