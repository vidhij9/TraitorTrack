#!/bin/bash
set -e

# AWS Deployment Script for TraceTrack
# Deploys the complete AWS infrastructure and application

# Configuration
STACK_NAME="tracetrack-production"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
APP_NAME="tracetrack"
ENVIRONMENT="production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install AWS CLI."
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure'."
        exit 1
    fi
    
    # Check required environment variables
    if [[ -z "${DATABASE_PASSWORD}" ]]; then
        log_error "DATABASE_PASSWORD environment variable not set."
        exit 1
    fi
    
    # Check for jq
    if ! command -v jq &> /dev/null; then
        log_error "jq not found. Please install jq for JSON processing."
        exit 1
    fi
    
    log_success "All prerequisites met."
}

# Get ECR repository URI from CloudFormation
get_ecr_repository() {
    log_info "Getting ECR repository information from CloudFormation..."
    
    # Get ECR repository URI from CloudFormation outputs
    REPOSITORY_URI=$(aws cloudformation describe-stacks \
        --stack-name "${STACK_NAME}" \
        --region "${REGION}" \
        --query 'Stacks[0].Outputs[?OutputKey==`ECRRepositoryURI`].OutputValue' \
        --output text 2>/dev/null || echo "")
    
    if [[ -z "${REPOSITORY_URI}" ]]; then
        log_error "ECR repository not found. Deploy infrastructure first."
        exit 1
    fi
    
    log_info "Using ECR repository: ${REPOSITORY_URI}"
    echo "${REPOSITORY_URI}"
}

# Build and push Docker image
build_and_push_image() {
    local repository_uri=$1
    log_info "Building and pushing Docker image..."
    
    # Login to ECR
    aws ecr get-login-password --region "${REGION}" | \
        docker login --username AWS --password-stdin "${repository_uri%/*}"
    
    # Build image
    log_info "Building Docker image..."
    docker build -f aws-infrastructure/Dockerfile -t "${APP_NAME}:latest" .
    
    # Tag image
    docker tag "${APP_NAME}:latest" "${repository_uri}:latest"
    
    # Push image
    log_info "Pushing image to ECR..."
    docker push "${repository_uri}:latest"
    
    log_success "Docker image pushed to ECR: ${repository_uri}:latest"
}

# Deploy CloudFormation stack
deploy_infrastructure() {
    log_info "Deploying AWS infrastructure..."
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "${STACK_NAME}" --region "${REGION}" &> /dev/null; then
        log_info "Updating existing CloudFormation stack..."
        OPERATION="update-stack"
    else
        log_info "Creating new CloudFormation stack..."
        OPERATION="create-stack"
    fi
    
    # Deploy stack
    aws cloudformation "${OPERATION}" \
        --stack-name "${STACK_NAME}" \
        --template-body file://aws-infrastructure/cloudformation-template.yaml \
        --parameters \
            ParameterKey=Environment,ParameterValue="${ENVIRONMENT}" \
            ParameterKey=AppName,ParameterValue="${APP_NAME}" \
            ParameterKey=DatabasePassword,ParameterValue="${DATABASE_PASSWORD}" \
        --capabilities CAPABILITY_IAM \
        --region "${REGION}" \
        --tags \
            Key=Environment,Value="${ENVIRONMENT}" \
            Key=Application,Value="${APP_NAME}" \
            Key=ManagedBy,Value=CloudFormation
    
    # Wait for stack to complete
    log_info "Waiting for stack operation to complete..."
    if [[ "${OPERATION}" == "create-stack" ]]; then
        aws cloudformation wait stack-create-complete \
            --stack-name "${STACK_NAME}" \
            --region "${REGION}"
    else
        aws cloudformation wait stack-update-complete \
            --stack-name "${STACK_NAME}" \
            --region "${REGION}"
    fi
    
    log_success "CloudFormation stack operation completed."
}

# Update ECS service with new image
update_ecs_service() {
    log_info "Updating ECS service..."
    
    # Get cluster and service names from CloudFormation outputs
    CLUSTER_NAME=$(aws cloudformation describe-stacks \
        --stack-name "${STACK_NAME}" \
        --region "${REGION}" \
        --query 'Stacks[0].Outputs[?OutputKey==`ECSClusterName`].OutputValue' \
        --output text)
    
    SERVICE_NAME="${APP_NAME}-${ENVIRONMENT}-service"
    
    # Force new deployment
    aws ecs update-service \
        --cluster "${CLUSTER_NAME}" \
        --service "${SERVICE_NAME}" \
        --force-new-deployment \
        --region "${REGION}"
    
    log_info "Waiting for service to stabilize..."
    aws ecs wait services-stable \
        --cluster "${CLUSTER_NAME}" \
        --services "${SERVICE_NAME}" \
        --region "${REGION}"
    
    log_success "ECS service updated successfully."
}

# Get deployment outputs
get_deployment_outputs() {
    log_info "Getting deployment information..."
    
    # Get CloudFormation outputs
    OUTPUTS=$(aws cloudformation describe-stacks \
        --stack-name "${STACK_NAME}" \
        --region "${REGION}" \
        --query 'Stacks[0].Outputs')
    
    ALB_DNS=$(echo "${OUTPUTS}" | jq -r '.[] | select(.OutputKey=="ALBDNSName") | .OutputValue')
    CLOUDFRONT_URL=$(echo "${OUTPUTS}" | jq -r '.[] | select(.OutputKey=="CloudFrontURL") | .OutputValue')
    
    log_success "Deployment completed successfully!"
    echo
    echo "================================="
    echo "DEPLOYMENT INFORMATION"
    echo "================================="
    echo "Application Load Balancer: http://${ALB_DNS}"
    echo "CloudFront URL: ${CLOUDFRONT_URL}"
    echo "Region: ${REGION}"
    echo "Stack Name: ${STACK_NAME}"
    echo "================================="
}

# Validate deployment
validate_deployment() {
    log_info "Validating deployment..."
    
    # Get ALB DNS name
    ALB_DNS=$(aws cloudformation describe-stacks \
        --stack-name "${STACK_NAME}" \
        --region "${REGION}" \
        --query 'Stacks[0].Outputs[?OutputKey==`ALBDNSName`].OutputValue' \
        --output text)
    
    # Test health endpoint
    local health_url="http://${ALB_DNS}/health"
    local max_attempts=30
    local attempt=1
    
    log_info "Testing health endpoint: ${health_url}"
    
    while [[ ${attempt} -le ${max_attempts} ]]; do
        if curl -f -s "${health_url}" > /dev/null; then
            log_success "Health check passed!"
            break
        else
            log_info "Attempt ${attempt}/${max_attempts}: Health check failed, retrying in 10 seconds..."
            sleep 10
            ((attempt++))
        fi
    done
    
    if [[ ${attempt} -gt ${max_attempts} ]]; then
        log_error "Health check failed after ${max_attempts} attempts."
        return 1
    fi
    
    # Run performance tests if available
    if [[ -f "aws-infrastructure/migration-scripts/performance-test.py" ]]; then
        log_info "Running performance tests..."
        export AWS_APP_URL="http://${ALB_DNS}"
        python3 aws-infrastructure/migration-scripts/performance-test.py || log_warning "Performance tests completed with warnings."
    fi
}

# Clean up old resources
cleanup() {
    log_info "Cleaning up old Docker images..."
    docker system prune -f || true
    log_success "Cleanup completed."
}

# Main deployment function
main() {
    echo "================================="
    echo "AWS DEPLOYMENT SCRIPT"
    echo "TraceTrack QR Code Scanning System"
    echo "================================="
    echo
    
    check_prerequisites
    
    # Deploy infrastructure first (includes ECR repository)
    deploy_infrastructure
    
    # Get ECR repository and build image
    REPOSITORY_URI=$(get_ecr_repository)
    build_and_push_image "${REPOSITORY_URI}"
    
    # Update ECS service with new image
    update_ecs_service
    
    # Get deployment information
    get_deployment_outputs
    
    # Validate deployment
    validate_deployment
    
    # Cleanup
    cleanup
    
    log_success "AWS deployment completed successfully!"
    
    echo
    echo "================================="
    echo "NEXT STEPS"
    echo "================================="
    echo "1. Update your DNS to point to the CloudFront URL"
    echo "2. Configure SSL certificate for custom domain (optional)"
    echo "3. Set up monitoring alerts in CloudWatch"
    echo "4. Run migration scripts to import existing data"
    echo "5. Update environment variables in your CI/CD pipeline"
    echo "================================="
}

# Handle script termination
trap 'log_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"