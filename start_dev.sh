#!/bin/bash
# Start application with development database environment

export FLASK_ENV=development
export DEV_DATABASE_URL="postgresql://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/tracetrack_dev"
export PROD_DATABASE_URL="postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech/neondb?sslmode=require"

echo "Starting with development database: tracetrack_dev"
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app