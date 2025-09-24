#!/bin/bash

# TraceTrack Database Migration Script
# Runs database migrations using ECS one-off task

set -e

# Default values
PROJECT_NAME="tracetrack"
ENVIRONMENT="production"
AWS_REGION="us-east-1"
MIGRATION_COMMAND="python -c \"from app_clean import db; db.create_all(); print('Database tables created successfully')\""

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
    echo "  -c, --command CMD           Migration command (default: create tables)"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e production"
    echo "  $0 -c \"python manage.py migrate\" -e staging"
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

get_stack_output() {
    local stack_name=$1
    local output_key=$2
    
    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$AWS_REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='$output_key'].OutputValue" \
        --output text 2>/dev/null || echo ""
}

run_migration_task() {
    local cluster_name=$1
    local task_definition_arn=$2
    local subnet_ids=$3
    local security_group_id=$4
    
    log "Running migration task..."
    
    # Run one-off ECS task for migration
    local task_arn=$(aws ecs run-task \
        --cluster "$cluster_name" \
        --task-definition "$task_definition_arn" \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$subnet_ids],securityGroups=[$security_group_id],assignPublicIp=DISABLED}" \
        --overrides "{\"containerOverrides\":[{\"name\":\"${PROJECT_NAME}-app\",\"command\":[\"sh\",\"-c\",\"$MIGRATION_COMMAND\"]}]}" \
        --region "$AWS_REGION" \
        --query 'tasks[0].taskArn' \
        --output text) || error "Failed to start migration task"
    
    log "Migration task started: $task_arn"
    
    # Wait for task to complete
    log "Waiting for migration task to complete..."
    aws ecs wait tasks-stopped \
        --cluster "$cluster_name" \
        --tasks "$task_arn" \
        --region "$AWS_REGION" || error "Migration task failed"
    
    # Check task exit code
    local exit_code=$(aws ecs describe-tasks \
        --cluster "$cluster_name" \
        --tasks "$task_arn" \
        --region "$AWS_REGION" \
        --query 'tasks[0].containers[0].exitCode' \
        --output text)
    
    if [[ "$exit_code" == "0" ]]; then
        success "Migration completed successfully"
    else
        error "Migration failed with exit code: $exit_code"
    fi
    
    # Show task logs
    log "Migration task logs:"
    local log_group="/ecs/${PROJECT_NAME}-${ENVIRONMENT}"
    local task_id=$(echo "$task_arn" | sed 's/.*\///')
    local log_stream="ecs/${PROJECT_NAME}-app/$task_id"
    
    aws logs get-log-events \
        --log-group-name "$log_group" \
        --log-stream-name "$log_stream" \
        --region "$AWS_REGION" \
        --query 'events[*].message' \
        --output text 2>/dev/null || warning "Could not retrieve task logs"
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
        -c|--command)
            MIGRATION_COMMAND="$2"
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

echo "🔄 TraceTrack Database Migration"
echo "==============================="
echo "Project Name: $PROJECT_NAME"
echo "Environment: $ENVIRONMENT"
echo "AWS Region: $AWS_REGION"
echo "Migration Command: $MIGRATION_COMMAND"
echo ""

# Check prerequisites
log "Checking prerequisites..."
if ! command -v aws &> /dev/null; then
    error "AWS CLI is not installed"
fi

if ! aws sts get-caller-identity &> /dev/null; then
    error "AWS credentials not configured"
fi

# Get infrastructure details
STACK_PREFIX="${PROJECT_NAME}-${ENVIRONMENT}"
CLUSTER_NAME=$(get_stack_output "${STACK_PREFIX}-application" "ClusterName")
TASK_DEFINITION_ARN=$(get_stack_output "${STACK_PREFIX}-application" "TaskDefinitionArn")

if [[ -z "$CLUSTER_NAME" ]]; then
    error "Could not find ECS cluster. Make sure application stack is deployed."
fi

if [[ -z "$TASK_DEFINITION_ARN" ]]; then
    error "Could not find task definition. Make sure application stack is deployed."
fi

# Get network configuration
PRIVATE_SUBNET_1=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_PREFIX}-infrastructure" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`PrivateSubnet1Id`].OutputValue' \
    --output text)

ECS_SECURITY_GROUP=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_PREFIX}-infrastructure" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ECSSecurityGroupId`].OutputValue' \
    --output text)

if [[ -z "$PRIVATE_SUBNET_1" ]]; then
    error "Could not find private subnet. Make sure infrastructure stack is deployed."
fi

if [[ -z "$ECS_SECURITY_GROUP" ]]; then
    error "Could not find ECS security group. Make sure infrastructure stack is deployed."
fi

# Run migration
run_migration_task "$CLUSTER_NAME" "$TASK_DEFINITION_ARN" "$PRIVATE_SUBNET_1" "$ECS_SECURITY_GROUP"

echo ""
success "🎉 Database migration completed successfully!"
echo ""
echo "📋 Migration Summary:"
echo "===================="
echo "Cluster: $CLUSTER_NAME"
echo "Task Definition: $TASK_DEFINITION_ARN"
echo "Command: $MIGRATION_COMMAND"
echo ""
echo "🔧 Next Steps:"
echo "=============="
echo "1. Verify application is working correctly"
echo "2. Check database tables were created properly"
echo "3. Test application functionality"