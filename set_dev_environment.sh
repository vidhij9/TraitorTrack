#!/bin/bash
# Set development environment variables for database separation

export FLASK_ENV=development
export DEV_DATABASE_URL="postgresql://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/tracetrack_dev"
export PROD_DATABASE_URL="postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech/neondb?sslmode=require"

echo "Development environment configured:"
echo "FLASK_ENV: $FLASK_ENV"
echo "Development Database: tracetrack_dev"
echo "Production Database: neondb (original)"
echo ""
echo "Databases are now separated!"