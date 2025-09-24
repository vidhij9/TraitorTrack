#!/bin/bash

# Automated AWS Deployment Script for TraceTrack
# This script deploys everything automatically with no manual intervention

set -e  # Exit on any error

# Configuration
PROJECT_NAME="tracetrack"
ENVIRONMENT="production"
AWS_REGION="ap-south-1"
AWS_ACCOUNT_ID="605134465544"
ECR_REPOSITORY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/tracetrack"
STACK_PREFIX="${PROJECT_NAME}-${ENVIRONMENT}"

# Source code packaging (dynamically create bucket if needed)
TIMESTAMP=$(date +%Y%m%d%H%M%S)
SOURCE_BUCKET="tracetrack-source-${TIMESTAMP}-${AWS_REGION}"
SOURCE_KEY="source-${TIMESTAMP}.zip"
IMAGE_TAG="build-${TIMESTAMP}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
}

# Function to deploy a CloudFormation stack
deploy_stack() {
    local template_file=$1
    local stack_name=$2
    local parameters=$3
    
    log "Deploying stack: $stack_name"
    
    if aws cloudformation describe-stacks --stack-name "$stack_name" --region "$AWS_REGION" >/dev/null 2>&1; then
        log "Stack $stack_name exists, updating..."
        aws cloudformation update-stack \
            --stack-name "$stack_name" \
            --template-body "file://$template_file" \
            --parameters $parameters \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
            --region "$AWS_REGION" || {
                # Check if no updates needed
                if aws cloudformation describe-stacks --stack-name "$stack_name" --region "$AWS_REGION" --query 'Stacks[0].StackStatus' --output text | grep -q "UPDATE_COMPLETE\|CREATE_COMPLETE"; then
                    warning "No updates to perform for stack $stack_name"
                else
                    error "Failed to update stack $stack_name"
                    return 1
                fi
            }
    else
        log "Creating new stack: $stack_name"
        aws cloudformation create-stack \
            --stack-name "$stack_name" \
            --template-body "file://$template_file" \
            --parameters $parameters \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
            --region "$AWS_REGION"
    fi
    
    log "Waiting for stack $stack_name to complete..."
    aws cloudformation wait stack-create-complete --stack-name "$stack_name" --region "$AWS_REGION" 2>/dev/null || \
    aws cloudformation wait stack-update-complete --stack-name "$stack_name" --region "$AWS_REGION" 2>/dev/null || true
    
    success "Stack $stack_name deployed successfully"
}

# Function to package and upload source code
package_source() {
    log "Packaging source code for deployment..."
    
    # Create/ensure S3 bucket exists
    log "Ensuring S3 bucket exists: $SOURCE_BUCKET"
    if ! aws s3api head-bucket --bucket "$SOURCE_BUCKET" --region "$AWS_REGION" 2>/dev/null; then
        log "Creating new S3 bucket: $SOURCE_BUCKET"
        aws s3api create-bucket \
            --bucket "$SOURCE_BUCKET" \
            --region "$AWS_REGION" \
            --create-bucket-configuration LocationConstraint="$AWS_REGION"
    fi
    
    # Create temporary directory for packaging
    TEMP_DIR=$(mktemp -d)
    
    # Copy application files (excluding large/unnecessary files)
    log "Copying application files..."
    cd ..
    
    # Create zip with only essential application files
    zip -r "$TEMP_DIR/$SOURCE_KEY" \
        . \
        -x "*.git*" \
        -x "*__pycache__*" \
        -x "*.pyc" \
        -x "*node_modules*" \
        -x "*venv*" \
        -x "*env*" \
        -x "*.log" \
        -x "*tmp*" \
        -x "*cache*" \
        -x "*.tar.gz" \
        -x "*.zip" \
        -x "test_*.xlsx" \
        -x "attached_assets/*" \
        -x "*.md" \
        -x "aws-infrastructure/automated-deploy.sh.backup*"
    
    # Upload to S3
    log "Uploading source code to S3: s3://$SOURCE_BUCKET/$SOURCE_KEY"
    aws s3 cp "$TEMP_DIR/$SOURCE_KEY" "s3://$SOURCE_BUCKET/$SOURCE_KEY" --region "$AWS_REGION"
    
    # Clean up
    rm -rf "$TEMP_DIR"
    cd aws-infrastructure
    
    success "Source code packaged and uploaded successfully"
}

# Function to start CodeBuild with source overrides
start_build() {
    local project_name=$1
    
    log "Starting CodeBuild project: $project_name with source s3://$SOURCE_BUCKET/$SOURCE_KEY"
    
    BUILD_ID=$(aws codebuild start-build \
        --project-name "$project_name" \
        --region "$AWS_REGION" \
        --source-type-override S3 \
        --source-location-override "$SOURCE_BUCKET/$SOURCE_KEY" \
        --environment-variables-override name=IMAGE_TAG,value="$IMAGE_TAG" \
        --query 'build.id' \
        --output text)
    
    log "Build started with ID: $BUILD_ID"
    log "Image will be tagged as: $IMAGE_TAG"
    log "Waiting for build to complete..."
    
    # Wait for build to complete
    while true; do
        BUILD_STATUS=$(aws codebuild batch-get-builds \
            --ids "$BUILD_ID" \
            --region "$AWS_REGION" \
            --query 'builds[0].buildStatus' \
            --output text)
        
        case $BUILD_STATUS in
            "SUCCEEDED")
                success "Build completed successfully!"
                break
                ;;
            "FAILED"|"FAULT"|"STOPPED"|"TIMED_OUT")
                error "Build failed with status: $BUILD_STATUS"
                # Get build logs for debugging
                log "Fetching build logs..."
                aws logs get-log-events \
                    --log-group-name "/aws/codebuild/$project_name" \
                    --log-stream-name "$BUILD_ID" \
                    --region "$AWS_REGION" \
                    --query 'events[*].message' \
                    --output text | tail -20
                return 1
                ;;
            *)
                log "Build status: $BUILD_STATUS (waiting...)"
                sleep 30
                ;;
        esac
    done
}

log "========================================"
log "Starting Automated TraceTrack Deployment"
log "========================================"
log "Project: $PROJECT_NAME"
log "Environment: $ENVIRONMENT"
log "Region: $AWS_REGION"
log "Account: $AWS_ACCOUNT_ID"
log "========================================"

# Step 1: Deploy CodeBuild Infrastructure
log "Step 1: Deploying CodeBuild infrastructure..."
deploy_stack \
    "codebuild-project.yaml" \
    "${STACK_PREFIX}-codebuild" \
    ""

# Step 2: Deploy Core Infrastructure (VPC, ALB, Security Groups)
log "Step 2: Deploying core infrastructure (VPC, ALB, Security Groups)..."
deploy_stack \
    "../aws-deployment/cloudformation/infrastructure.yml" \
    "${STACK_PREFIX}-infrastructure" \
    "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME ParameterKey=Environment,ParameterValue=$ENVIRONMENT"

# Step 3: Skip database deployment (using existing AWS database)
log "Step 3: Skipping database deployment (using existing AWS database)..."
success "Using existing AWS database as requested"

# Step 4: Package and Upload Source Code
log "Step 4: Packaging and uploading source code..."
package_source

# Step 5: Build and Push Docker Image
log "Step 5: Building and pushing Docker image..."
start_build "tracetrack-build"

# Step 6: Deploy Application (ECS Service)
log "Step 6: Deploying ECS application..."
deploy_stack \
    "../aws-deployment/cloudformation/application.yml" \
    "${STACK_PREFIX}-application" \
    "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME ParameterKey=Environment,ParameterValue=$ENVIRONMENT ParameterKey=ImageURI,ParameterValue=$ECR_REPOSITORY:$IMAGE_TAG"

# Get the Load Balancer URL
log "Getting application URL..."
ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_PREFIX}-infrastructure" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
    --output text)

success "========================================"
success "DEPLOYMENT COMPLETED SUCCESSFULLY!"
success "========================================"
success "Application URL: http://$ALB_DNS"
success "Region: $AWS_REGION (Mumbai)"
success "Environment: $ENVIRONMENT"
success "========================================"

log "Your TraceTrack application is now running on AWS!"
log "It may take a few minutes for the health checks to pass and the application to be fully available."