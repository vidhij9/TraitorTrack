#!/bin/bash

# TraceTrack Monitoring Setup Script
# Deploys CloudWatch dashboards, alarms, and monitoring configuration

set -e

# Default values
PROJECT_NAME="tracetrack"
ENVIRONMENT="production"
AWS_REGION="us-east-1"
ALERT_EMAIL=""

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
    echo "  -a, --alert-email EMAIL     Email for alerts (required)"
    echo "  -s, --slack-webhook URL     Slack webhook URL (optional)"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 -e production -a admin@example.com -s https://hooks.slack.com/..."
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

deploy_monitoring_stack() {
    local stack_name="${PROJECT_NAME}-${ENVIRONMENT}-monitoring"
    local template_file="cloudformation/monitoring.yml"
    
    log "Deploying monitoring stack: $stack_name"
    
    # Get required parameters from other stacks
    local infrastructure_stack="${PROJECT_NAME}-${ENVIRONMENT}-infrastructure"
    local database_stack="${PROJECT_NAME}-${ENVIRONMENT}-database"
    local application_stack="${PROJECT_NAME}-${ENVIRONMENT}-application"
    
    local alb_dns=$(get_stack_output "$infrastructure_stack" "LoadBalancerDNS")
    local service_name=$(get_stack_output "$application_stack" "ServiceName")
    local cluster_name=$(get_stack_output "$application_stack" "ClusterName")
    
    if [[ -z "$alb_dns" ]]; then
        error "Could not get load balancer DNS from infrastructure stack"
    fi
    
    if [[ -z "$service_name" ]]; then
        error "Could not get service name from application stack"
    fi
    
    if [[ -z "$cluster_name" ]]; then
        error "Could not get cluster name from application stack"
    fi
    
    # Extract load balancer full name from ARN
    local alb_arn=$(get_stack_output "$infrastructure_stack" "LoadBalancerArn")
    local alb_full_name=$(echo "$alb_arn" | sed 's/.*loadbalancer\///')
    
    # Database instance ID
    local db_instance_id="${PROJECT_NAME}-${ENVIRONMENT}-postgres"
    
    # Build parameters
    local parameters="ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME"
    parameters="$parameters ParameterKey=Environment,ParameterValue=$ENVIRONMENT"
    parameters="$parameters ParameterKey=AlertEmail,ParameterValue=$ALERT_EMAIL"
    parameters="$parameters ParameterKey=LoadBalancerFullName,ParameterValue=$alb_full_name"
    parameters="$parameters ParameterKey=ServiceName,ParameterValue=$service_name"
    parameters="$parameters ParameterKey=ClusterName,ParameterValue=$cluster_name"
    parameters="$parameters ParameterKey=DatabaseInstanceId,ParameterValue=$db_instance_id"
    
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        parameters="$parameters ParameterKey=SlackWebhookURL,ParameterValue=$SLACK_WEBHOOK"
    fi
    
    if aws cloudformation describe-stacks --stack-name "$stack_name" --region "$AWS_REGION" &> /dev/null; then
        log "Updating existing monitoring stack..."
        aws cloudformation update-stack \
            --stack-name "$stack_name" \
            --template-body "file://$template_file" \
            --parameters $parameters \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$AWS_REGION" || {
                if [[ $? -eq 255 ]]; then
                    warning "No updates for monitoring stack"
                else
                    error "Failed to update monitoring stack"
                fi
            }
    else
        log "Creating monitoring stack..."
        aws cloudformation create-stack \
            --stack-name "$stack_name" \
            --template-body "file://$template_file" \
            --parameters $parameters \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$AWS_REGION" || error "Failed to create monitoring stack"
    fi
    
    log "Waiting for monitoring stack to complete..."
    aws cloudformation wait stack-update-complete \
        --stack-name "$stack_name" \
        --region "$AWS_REGION" 2>/dev/null || \
    aws cloudformation wait stack-create-complete \
        --stack-name "$stack_name" \
        --region "$AWS_REGION" || error "Monitoring stack deployment failed"
    
    success "Monitoring stack deployed successfully"
}

setup_log_insights_queries() {
    log "Setting up CloudWatch Insights queries..."
    
    local log_group="/ecs/${PROJECT_NAME}-${ENVIRONMENT}"
    
    # Save useful queries for easy access
    cat > "/tmp/log_insights_queries.txt" << EOF
# Application Errors (Last 1 Hour)
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100

# Response Time Analysis
fields @timestamp, @duration
| filter @message like /response_time/
| stats avg(@duration), max(@duration), min(@duration) by bin(5m)

# Request Volume by Endpoint
fields @timestamp, @message
| filter @message like /GET|POST|PUT|DELETE/
| parse @message /(?<method>GET|POST|PUT|DELETE) (?<endpoint>\/[^ ]*)/
| stats count() by endpoint
| sort count desc

# Health Check Status
fields @timestamp, @message
| filter @message like /health/
| stats count() by bin(1m)
| sort @timestamp desc

# Database Query Performance
fields @timestamp, @message
| filter @message like /SQL/
| parse @message /duration: (?<duration>[0-9.]+)/
| stats avg(duration), max(duration) by bin(5m)
EOF

    log "Saved CloudWatch Insights queries to /tmp/log_insights_queries.txt"
}

create_custom_dashboard() {
    log "Creating custom application dashboard..."
    
    local dashboard_body=$(cat << EOF
{
  "widgets": [
    {
      "type": "log",
      "x": 0,
      "y": 0,
      "width": 24,
      "height": 6,
      "properties": {
        "query": "SOURCE '/ecs/${PROJECT_NAME}-${ENVIRONMENT}' | fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 20",
        "region": "${AWS_REGION}",
        "title": "Recent Application Errors",
        "view": "table"
      }
    },
    {
      "type": "metric",
      "x": 0,
      "y": 6,
      "width": 8,
      "height": 6,
      "properties": {
        "metrics": [
          [ "TraceTrack/Application", "QRScansPerMinute" ],
          [ ".", "UserRegistrations" ],
          [ ".", "BagsProcessed" ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "${AWS_REGION}",
        "title": "Application Metrics",
        "period": 300
      }
    },
    {
      "type": "metric",
      "x": 8,
      "y": 6,
      "width": 8,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AWS/ApplicationELB", "HealthyHostCount", "TargetGroup", "${PROJECT_NAME}-${ENVIRONMENT}-tg" ],
          [ ".", "UnHealthyHostCount", ".", "." ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "${AWS_REGION}",
        "title": "Target Health",
        "period": 300
      }
    },
    {
      "type": "metric",
      "x": 16,
      "y": 6,
      "width": 8,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AWS/ECS", "RunningTaskCount", "ServiceName", "${PROJECT_NAME}-${ENVIRONMENT}-service", "ClusterName", "${PROJECT_NAME}-${ENVIRONMENT}-cluster" ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "${AWS_REGION}",
        "title": "Running Tasks",
        "period": 300
      }
    }
  ]
}
EOF
    )
    
    aws cloudwatch put-dashboard \
        --dashboard-name "${PROJECT_NAME}-${ENVIRONMENT}-application" \
        --dashboard-body "$dashboard_body" \
        --region "$AWS_REGION" || warning "Failed to create custom dashboard"
    
    success "Custom application dashboard created"
}

# Parse command line arguments
SLACK_WEBHOOK=""

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
        -a|--alert-email)
            ALERT_EMAIL="$2"
            shift 2
            ;;
        -s|--slack-webhook)
            SLACK_WEBHOOK="$2"
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

echo "📊 TraceTrack Monitoring Setup"
echo "=============================="
echo "Project Name: $PROJECT_NAME"
echo "Environment: $ENVIRONMENT"
echo "AWS Region: $AWS_REGION"
echo "Alert Email: $ALERT_EMAIL"
echo ""

# Validate required parameters
if [[ -z "$ALERT_EMAIL" ]]; then
    error "Alert email is required (-a option)"
fi

# Check prerequisites
log "Checking prerequisites..."
if ! command -v aws &> /dev/null; then
    error "AWS CLI is not installed"
fi

if ! aws sts get-caller-identity &> /dev/null; then
    error "AWS credentials not configured"
fi

# Change to correct directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Deploy monitoring
deploy_monitoring_stack
setup_log_insights_queries
create_custom_dashboard

# Get dashboard URL
DASHBOARD_URL="https://${AWS_REGION}.console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:name=${PROJECT_NAME}-${ENVIRONMENT}-dashboard"

echo ""
success "🎉 Monitoring setup completed successfully!"
echo ""
echo "📋 Monitoring Summary:"
echo "====================="
echo "Dashboard URL: $DASHBOARD_URL"
echo "Alert Email: $ALERT_EMAIL"
if [[ -n "$SLACK_WEBHOOK" ]]; then
    echo "Slack Webhook: Configured"
fi
echo ""
echo "🔧 Next Steps:"
echo "=============="
echo "1. Visit the dashboard to view metrics"
echo "2. Test alerts by triggering threshold breaches"
echo "3. Customize alert thresholds as needed"
echo "4. Set up additional custom metrics in your application"
echo ""
echo "📖 CloudWatch Console:"
echo "   https://$AWS_REGION.console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION"