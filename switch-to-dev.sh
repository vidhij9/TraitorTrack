#!/bin/bash
# Switch to Development Environment
echo "Switching to Development Environment..."
export ENVIRONMENT=development
export DEV_DATABASE_URL="postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech:5432/neondb_dev"
export SESSION_SECRET="dev-session-b957b2b0c5ce33e7"

echo "Environment: $ENVIRONMENT"
echo "Database: Development"
echo "Ready for development testing!"
