#!/bin/bash

# TraceTrack Complete AWS Deployment Script
# End-to-end deployment: Build, Push, and Deploy

set -e

# Default values
PROJECT_NAME="tracetrack"
ENVIRONMENT="production"
AWS_REGION="us-east-1"
IMAGE_TAG="$(date +%Y%m%d_%H%M%S)"
KEY_PAIR_NAME=""
DATABASE_PASSWORD=""

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
    echo "  -t, --tag TAG              Image tag (default: timestamp)"
    echo "  -k, --key-pair KEY          EC2 Key Pair name (required)"
    echo "  -d, --db-password PASS      Database password (required)"
    echo "  --skip-build               Skip Docker build and push"
    echo "  --skip-infrastructure      Skip infrastructure deployment"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 -e production -k my-key-pair -d MySecurePassword123"
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

SKIP_BUILD=false
SKIP_INFRASTRUCTURE=false

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
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -k|--key-pair)
            KEY_PAIR_NAME="$2"
            shift 2
            ;;
        -d|--db-password)
            DATABASE_PASSWORD="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-infrastructure)
            SKIP_INFRASTRUCTURE=true
            shift
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

echo "🚀 TraceTrack Complete AWS Deployment"
echo "====================================="
echo "Project Name: $PROJECT_NAME"
echo "Environment: $ENVIRONMENT"
echo "AWS Region: $AWS_REGION"
echo "Image Tag: $IMAGE_TAG"
echo "Skip Build: $SKIP_BUILD"
echo "Skip Infrastructure: $SKIP_INFRASTRUCTURE"
echo ""

# Validate required parameters
if [[ "$SKIP_INFRASTRUCTURE" == "false" ]]; then
    if [[ -z "$KEY_PAIR_NAME" ]]; then
        error "Key pair name is required (-k option) for infrastructure deployment"
    fi
    
    # Database password will be auto-generated for security
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Step 1: Build and push Docker image
if [[ "$SKIP_BUILD" == "false" ]]; then
    log "Step 1: Building and pushing Docker image..."
    "$SCRIPT_DIR/build-and-push.sh" \
        -p "$PROJECT_NAME" \
        -r "$AWS_REGION" \
        -t "$IMAGE_TAG"
    success "Build and push completed"
else
    warning "Skipping Docker build and push"
fi

# Get image URI
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME:$IMAGE_TAG"

# Step 2: Deploy infrastructure
if [[ "$SKIP_INFRASTRUCTURE" == "false" ]]; then
    log "Step 2: Deploying AWS infrastructure..."
    cd "$SCRIPT_DIR"
    ./deploy-infrastructure.sh \
        -p "$PROJECT_NAME" \
        -e "$ENVIRONMENT" \
        -r "$AWS_REGION" \
        -k "$KEY_PAIR_NAME" \
        --generate-password \
        -i "$IMAGE_URI"
    success "Infrastructure deployment completed"
else
    warning "Skipping infrastructure deployment"
    
    # Just deploy/update the application if infrastructure exists
    log "Updating application with new image..."
    cd "$SCRIPT_DIR"
    STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}-application"
    
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" &> /dev/null; then
        aws cloudformation update-stack \
            --stack-name "$STACK_NAME" \
            --template-body "file://cloudformation/application.yml" \
            --parameters "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME" \
                        "ParameterKey=Environment,ParameterValue=$ENVIRONMENT" \
                        "ParameterKey=ImageURI,ParameterValue=$IMAGE_URI" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$AWS_REGION" || error "Failed to update application stack"
        
        log "Waiting for application update to complete..."
        aws cloudformation wait stack-update-complete \
            --stack-name "$STACK_NAME" \
            --region "$AWS_REGION" || error "Application update failed"
        
        success "Application updated successfully"
    else
        error "Application stack does not exist. Run with full infrastructure deployment first."
    fi
fi

# Step 3: Get deployment information
log "Getting deployment information..."

if aws cloudformation describe-stacks --stack-name "${PROJECT_NAME}-${ENVIRONMENT}-infrastructure" --region "$AWS_REGION" &> /dev/null; then
    ALB_DNS=$(aws cloudformation describe-stacks \
        --stack-name "${PROJECT_NAME}-${ENVIRONMENT}-infrastructure" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
        --output text)
    
    DB_ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name "${PROJECT_NAME}-${ENVIRONMENT}-database" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' \
        --output text)
    
    # Test application health
    log "Testing application health..."
    sleep 30  # Wait for deployment to settle
    
    for i in {1..12}; do  # Try for 2 minutes
        if curl -sf "http://$ALB_DNS/health" &> /dev/null; then
            success "Application is healthy and responding"
            break
        else
            log "Waiting for application to be ready... (attempt $i/12)"
            sleep 10
        fi
    done
fi

echo ""
success "🎉 TraceTrack deployment completed successfully!"
echo ""
echo "📋 Deployment Summary:"
echo "====================="
echo "Environment: $ENVIRONMENT"
echo "Image: $IMAGE_URI"
if [[ -n "$ALB_DNS" ]]; then
    echo "Application URL: http://$ALB_DNS"
    echo "Health Check: http://$ALB_DNS/health"
fi
if [[ -n "$DB_ENDPOINT" ]]; then
    echo "Database: $DB_ENDPOINT:5432"
fi
echo ""
echo "🔧 Management Commands:"
echo "======================"
echo "View ECS Service:"
echo "  aws ecs describe-services --cluster ${PROJECT_NAME}-${ENVIRONMENT}-cluster --services ${PROJECT_NAME}-${ENVIRONMENT}-service --region $AWS_REGION"
echo ""
echo "View Logs:"
echo "  aws logs tail /ecs/${PROJECT_NAME}-${ENVIRONMENT} --follow --region $AWS_REGION"
echo ""
echo "Update Application (new deployment):"
echo "  $0 --skip-infrastructure -t NEW_TAG"
echo ""
echo "📖 Documentation: README.md"