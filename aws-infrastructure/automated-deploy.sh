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

# Function to start CodeBuild
start_build() {
    local project_name=$1
    
    log "Starting CodeBuild project: $project_name"
    
    BUILD_ID=$(aws codebuild start-build \
        --project-name "$project_name" \
        --region "$AWS_REGION" \
        --query 'build.id' \
        --output text)
    
    log "Build started with ID: $BUILD_ID"
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

# Step 3: Deploy Database and Redis Infrastructure
log "Step 3: Deploying database and Redis infrastructure..."
deploy_stack \
    "../aws-deployment/cloudformation/database.yml" \
    "${STACK_PREFIX}-database" \
    "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME ParameterKey=Environment,ParameterValue=$ENVIRONMENT"

# Step 4: Build and Push Docker Image
log "Step 4: Building and pushing Docker image..."
start_build "tracetrack-build"

# Step 5: Deploy Application (ECS Service)
log "Step 5: Deploying ECS application..."
deploy_stack \
    "../aws-deployment/cloudformation/application.yml" \
    "${STACK_PREFIX}-application" \
    "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME ParameterKey=Environment,ParameterValue=$ENVIRONMENT ParameterKey=ImageURI,ParameterValue=$ECR_REPOSITORY:latest"

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