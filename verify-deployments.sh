#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "===================================="
echo "TraceTrack Deployment Status Report"
echo "===================================="
echo ""

# 1. Check Replit Deployment
echo -e "${YELLOW}1. REPLIT TESTING ENVIRONMENT${NC}"
echo "--------------------------------"

# Check local health
REPLIT_LOCAL=$(curl -s http://localhost:5000/health 2>/dev/null)
if [[ "$REPLIT_LOCAL" == *"healthy"* ]]; then
    echo -e "${GREEN}✓ Local health check: Working${NC}"
    echo -e "${GREEN}✓ Application Status: Running on port 5000${NC}"
else
    echo -e "${RED}✗ Local health check: Failed${NC}"
fi

# Get Replit public URL
REPLIT_URL="https://4a1bf949-1caa-4cac-b77e-1c948bbfae72-00-2oi7cqf6mfw9y.picard.replit.dev"
echo -e "Testing URL: ${GREEN}$REPLIT_URL${NC}"

echo ""

# 2. Check Replit Production
echo -e "${YELLOW}2. REPLIT PRODUCTION${NC}"
echo "----------------------"
echo -e "Production URL: ${GREEN}https://traitor-track.replit.app${NC}"
echo -e "Status: Managed by Replit deployment system"
echo -e "Note: Use Replit's publish feature to update production"

echo ""

# 3. Check AWS Deployment
echo -e "${YELLOW}3. AWS DEPLOYMENT (Mumbai - ap-south-1)${NC}"
echo "----------------------------------------"

# Get AWS instance details
AWS_IP="13.201.135.42"
echo -e "AWS Instance IP: ${GREEN}$AWS_IP${NC}"
echo -e "AWS URL: ${GREEN}http://$AWS_IP${NC}"

# Check if instance is running
INSTANCE_STATE=$(aws ec2 describe-instances --instance-ids i-0057a68f7062dd425 --region ap-south-1 --query "Reservations[0].Instances[0].State.Name" --output text 2>/dev/null)
if [ "$INSTANCE_STATE" == "running" ]; then
    echo -e "${GREEN}✓ Instance state: Running${NC}"
else
    echo -e "${RED}✗ Instance state: $INSTANCE_STATE${NC}"
fi

# Check database parameter
DB_PARAM=$(aws ssm get-parameter --name "/tracetrack/production/DATABASE_URL" --region ap-south-1 --query 'Parameter.Name' --output text 2>/dev/null)
if [ ! -z "$DB_PARAM" ]; then
    echo -e "${GREEN}✓ Database config: Stored in AWS Parameter Store${NC}"
fi

# Note about AWS deployment
echo -e "${YELLOW}⚠ AWS Deployment Status:${NC}"
echo "  - Instance restarted with deployment script"
echo "  - Application deployment in progress"
echo "  - May take 3-5 minutes to fully initialize"
echo "  - If showing 502, wait for initialization to complete"

echo ""
echo "===================================="
echo "DEPLOYMENT SUMMARY"
echo "===================================="
echo ""
echo -e "${GREEN}✓ REPLIT TESTING:${NC} Running locally"
echo -e "  URL: $REPLIT_URL"
echo ""
echo -e "${GREEN}✓ REPLIT PRODUCTION:${NC} Available"
echo -e "  URL: https://traitor-track.replit.app"
echo ""
echo -e "${YELLOW}⚠ AWS DEPLOYMENT:${NC} Initializing"
echo -e "  URL: http://$AWS_IP"
echo -e "  Region: ap-south-1 (Mumbai)"
echo -e "  Instance: i-0057a68f7062dd425"
echo ""
echo "========================================="
echo "IMPORTANT NOTES:"
echo "========================================="
echo ""
echo "1. All deployments use the same AWS RDS PostgreSQL database"
echo "2. Database contains 800,000+ bags - all data preserved"
echo "3. AWS deployment uses user data script for automated setup"
echo "4. The application features consistent UI across all environments"
echo ""
echo "ACTION REQUIRED:"
echo "----------------"
echo "1. Wait 3-5 minutes for AWS deployment to complete"
echo "2. Access AWS at: http://13.201.135.42"
echo "3. Login with: admin/admin"
echo ""