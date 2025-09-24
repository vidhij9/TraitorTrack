#!/bin/bash

# TraceTrack AWS Secrets Management Script
# Sets up environment variables in AWS Systems Manager Parameter Store

set -e

# Default values
PROJECT_NAME="tracetrack"
ENVIRONMENT="production"
AWS_REGION="us-east-1"

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
    echo "  --sendgrid-key KEY          SendGrid API key"
    echo "  --sendgrid-email EMAIL      SendGrid from email"
    echo "  --custom-domain DOMAIN      Custom domain name"
    echo "  --ssl-cert-arn ARN          SSL certificate ARN"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 -e production --sendgrid-key SG.xxx --sendgrid-email noreply@example.com"
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

set_parameter() {
    local name=$1
    local value=$2
    local type=${3:-"String"}
    local description=$4
    
    log "Setting parameter: $name"
    
    aws ssm put-parameter \
        --name "$name" \
        --value "$value" \
        --type "$type" \
        --description "$description" \
        --overwrite \
        --region "$AWS_REGION" \
        --tags "Key=Project,Value=$PROJECT_NAME" "Key=Environment,Value=$ENVIRONMENT" || error "Failed to set parameter $name"
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

# Parse command line arguments
SENDGRID_KEY=""
SENDGRID_EMAIL=""
CUSTOM_DOMAIN=""
SSL_CERT_ARN=""

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
        --sendgrid-key)
            SENDGRID_KEY="$2"
            shift 2
            ;;
        --sendgrid-email)
            SENDGRID_EMAIL="$2"
            shift 2
            ;;
        --custom-domain)
            CUSTOM_DOMAIN="$2"
            shift 2
            ;;
        --ssl-cert-arn)
            SSL_CERT_ARN="$2"
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

echo "🔐 TraceTrack AWS Secrets Management"
echo "==================================="
echo "Project Name: $PROJECT_NAME"
echo "Environment: $ENVIRONMENT"
echo "AWS Region: $AWS_REGION"
echo ""

# Check prerequisites
log "Checking prerequisites..."
if ! command -v aws &> /dev/null; then
    error "AWS CLI is not installed"
fi

if ! aws sts get-caller-identity &> /dev/null; then
    error "AWS credentials not configured"
fi

# Parameter prefix
PARAM_PREFIX="/${PROJECT_NAME}/${ENVIRONMENT}"

# Get infrastructure outputs
STACK_PREFIX="${PROJECT_NAME}-${ENVIRONMENT}"
ALB_DNS=$(get_stack_output "${STACK_PREFIX}-infrastructure" "LoadBalancerDNS")
DB_ENDPOINT=$(get_stack_output "${STACK_PREFIX}-database" "DatabaseEndpoint")
REDIS_ENDPOINT=$(get_stack_output "${STACK_PREFIX}-database" "RedisEndpoint")

# Set core application parameters
log "Setting core application parameters..."

if [[ -n "$ALB_DNS" ]]; then
    set_parameter "${PARAM_PREFIX}/application/domain" "$ALB_DNS" "String" "Application domain name"
fi

if [[ -n "$CUSTOM_DOMAIN" ]]; then
    set_parameter "${PARAM_PREFIX}/application/custom_domain" "$CUSTOM_DOMAIN" "String" "Custom domain name"
fi

if [[ -n "$SSL_CERT_ARN" ]]; then
    set_parameter "${PARAM_PREFIX}/application/ssl_cert_arn" "$SSL_CERT_ARN" "String" "SSL certificate ARN"
fi

# Set database parameters
if [[ -n "$DB_ENDPOINT" ]]; then
    log "Setting database parameters..."
    set_parameter "${PARAM_PREFIX}/database/host" "$DB_ENDPOINT" "String" "Database host"
    set_parameter "${PARAM_PREFIX}/database/port" "5432" "String" "Database port"
    set_parameter "${PARAM_PREFIX}/database/name" "tracetrack" "String" "Database name"
    set_parameter "${PARAM_PREFIX}/database/username" "tracetrack_user" "String" "Database username"
fi

# Set Redis parameters
if [[ -n "$REDIS_ENDPOINT" ]]; then
    log "Setting Redis parameters..."
    set_parameter "${PARAM_PREFIX}/redis/host" "$REDIS_ENDPOINT" "String" "Redis host"
    set_parameter "${PARAM_PREFIX}/redis/port" "6379" "String" "Redis port"
fi

# Set SendGrid parameters
if [[ -n "$SENDGRID_KEY" ]]; then
    log "Setting SendGrid parameters..."
    set_parameter "${PARAM_PREFIX}/sendgrid/api_key" "$SENDGRID_KEY" "SecureString" "SendGrid API key"
fi

if [[ -n "$SENDGRID_EMAIL" ]]; then
    set_parameter "${PARAM_PREFIX}/sendgrid/from_email" "$SENDGRID_EMAIL" "String" "SendGrid from email"
fi

# Set application configuration
log "Setting application configuration parameters..."
set_parameter "${PARAM_PREFIX}/app/environment" "$ENVIRONMENT" "String" "Application environment"
set_parameter "${PARAM_PREFIX}/app/debug" "false" "String" "Debug mode"
set_parameter "${PARAM_PREFIX}/app/log_level" "INFO" "String" "Application log level"

# Set security parameters
log "Setting security parameters..."
set_parameter "${PARAM_PREFIX}/security/session_cookie_secure" "true" "String" "Secure session cookies"
set_parameter "${PARAM_PREFIX}/security/session_cookie_httponly" "true" "String" "HTTP-only session cookies"
set_parameter "${PARAM_PREFIX}/security/csrf_protection" "true" "String" "CSRF protection enabled"

# Generate additional secrets if needed
log "Generating additional application secrets..."

# API rate limit settings
set_parameter "${PARAM_PREFIX}/rate_limit/default_rate" "100" "String" "Default API rate limit per minute"
set_parameter "${PARAM_PREFIX}/rate_limit/login_rate" "5" "String" "Login rate limit per minute"

# Health check settings
set_parameter "${PARAM_PREFIX}/health/check_timeout" "30" "String" "Health check timeout in seconds"
set_parameter "${PARAM_PREFIX}/health/check_interval" "60" "String" "Health check interval in seconds"

# List all parameters
log "Listing all parameters for verification..."
aws ssm get-parameters-by-path \
    --path "$PARAM_PREFIX" \
    --recursive \
    --region "$AWS_REGION" \
    --query 'Parameters[*].[Name,Type,Value]' \
    --output table || warning "Could not list parameters"

echo ""
success "🎉 AWS secrets and parameters configured successfully!"
echo ""
echo "📋 Configuration Summary:"
echo "========================"
echo "Parameter Prefix: $PARAM_PREFIX"
echo "Region: $AWS_REGION"
if [[ -n "$ALB_DNS" ]]; then
    echo "Application Domain: $ALB_DNS"
fi
if [[ -n "$CUSTOM_DOMAIN" ]]; then
    echo "Custom Domain: $CUSTOM_DOMAIN"
fi
echo ""
echo "🔧 Next Steps:"
echo "=============="
echo "1. Update ECS task definition to use these parameters"
echo "2. Configure application to read from Parameter Store"
echo "3. Test application with new configuration"
echo ""
echo "📖 View parameters in AWS Console:"
echo "   https://$AWS_REGION.console.aws.amazon.com/systems-manager/parameters?region=$AWS_REGION"