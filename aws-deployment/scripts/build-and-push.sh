#!/bin/bash

# TraceTrack ECR Build and Push Script
# Builds Docker image and pushes to Amazon ECR

set -e

# Default values
PROJECT_NAME="tracetrack"
AWS_REGION="us-east-1"
IMAGE_TAG="latest"
ECR_REPOSITORY="${PROJECT_NAME}"

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
    echo "  -r, --region REGION         AWS region (default: us-east-1)"
    echo "  -t, --tag TAG              Image tag (default: latest)"
    echo "  -R, --repository REPO       ECR repository name (default: project name)"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 -t v1.0.0 -r us-west-2"
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
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS credentials not configured"
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
    fi
    
    success "Prerequisites check passed"
}

create_ecr_repository() {
    log "Checking ECR repository: $ECR_REPOSITORY"
    
    if ! aws ecr describe-repositories --repository-names "$ECR_REPOSITORY" --region "$AWS_REGION" &> /dev/null; then
        log "Creating ECR repository: $ECR_REPOSITORY"
        aws ecr create-repository \
            --repository-name "$ECR_REPOSITORY" \
            --region "$AWS_REGION" \
            --image-scanning-configuration scanOnPush=true \
            --encryption-configuration encryptionType=AES256 \
            --tags Key=Project,Value="$PROJECT_NAME" Key=ManagedBy,Value=Script || error "Failed to create ECR repository"
        success "ECR repository created"
    else
        log "ECR repository already exists"
    fi
}

get_ecr_login() {
    log "Getting ECR login token..."
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
    
    # Login to ECR
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$ECR_URI" || error "Failed to login to ECR"
    
    success "Successfully logged in to ECR"
}

build_image() {
    log "Building Docker image..."
    
    # Build image with multiple tags
    docker build \
        -t "$PROJECT_NAME:$IMAGE_TAG" \
        -t "$PROJECT_NAME:latest" \
        -t "$ECR_URI/$ECR_REPOSITORY:$IMAGE_TAG" \
        -t "$ECR_URI/$ECR_REPOSITORY:latest" \
        . || error "Failed to build Docker image"
    
    success "Docker image built successfully"
    
    # Show image info
    log "Image information:"
    docker images | grep "$PROJECT_NAME" | head -5
}

push_image() {
    log "Pushing image to ECR..."
    
    # Push all tags
    docker push "$ECR_URI/$ECR_REPOSITORY:$IMAGE_TAG" || error "Failed to push image with tag $IMAGE_TAG"
    
    if [[ "$IMAGE_TAG" != "latest" ]]; then
        docker push "$ECR_URI/$ECR_REPOSITORY:latest" || error "Failed to push image with latest tag"
    fi
    
    success "Image pushed successfully to ECR"
}

scan_image() {
    log "Starting security scan..."
    
    aws ecr start-image-scan \
        --repository-name "$ECR_REPOSITORY" \
        --image-id "imageTag=$IMAGE_TAG" \
        --region "$AWS_REGION" || warning "Failed to start image scan"
    
    log "Security scan initiated (results available in ECR console)"
}

cleanup_local_images() {
    log "Cleaning up local images..."
    
    # Remove intermediate images
    docker system prune -f || warning "Failed to clean up Docker system"
    
    success "Local cleanup completed"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project-name)
            PROJECT_NAME="$2"
            ECR_REPOSITORY="$2"
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
        -R|--repository)
            ECR_REPOSITORY="$2"
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

echo "🐳 TraceTrack Docker Build and Push"
echo "==================================="
echo "Project Name: $PROJECT_NAME"
echo "AWS Region: $AWS_REGION"
echo "Image Tag: $IMAGE_TAG"
echo "ECR Repository: $ECR_REPOSITORY"
echo ""

check_prerequisites
create_ecr_repository

# Get AWS account ID for ECR URI
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
FULL_IMAGE_URI="$ECR_URI/$ECR_REPOSITORY:$IMAGE_TAG"

get_ecr_login
build_image
push_image
scan_image
cleanup_local_images

echo ""
success "🎉 Build and push completed successfully!"
echo ""
echo "📋 Build Summary:"
echo "================"
echo "Image URI: $FULL_IMAGE_URI"
echo "ECR Repository: $ECR_URI/$ECR_REPOSITORY"
echo "Image Tag: $IMAGE_TAG"
echo ""
echo "🔧 Next Steps:"
echo "=============="
echo "1. Deploy/update your ECS service with this image:"
echo "   aws ecs update-service --cluster YOUR_CLUSTER --service YOUR_SERVICE --task-definition YOUR_TASK_DEF"
echo ""
echo "2. Or use the image URI in CloudFormation:"
echo "   $FULL_IMAGE_URI"
echo ""
echo "📖 View image in ECR console:"
echo "   https://$AWS_REGION.console.aws.amazon.com/ecr/repositories/$ECR_REPOSITORY"