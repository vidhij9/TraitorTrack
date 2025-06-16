#!/bin/bash
# Switch to Production Environment
echo "Switching to Production Environment..."
export ENVIRONMENT=production
export PROD_DATABASE_URL="postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech:5432/neondb_prod"
export SESSION_SECRET="prod-session-daf812fb3e23b08a"

echo "Environment: $ENVIRONMENT"
echo "Database: Production"
echo "⚠️  WARNING: You are now using PRODUCTION data!"
