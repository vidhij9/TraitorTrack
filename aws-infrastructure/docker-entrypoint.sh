#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database to be ready..."
until python -c "
import psycopg2
import os
import sys
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.close()
    print('Database is ready!')
except psycopg2.OperationalError:
    print('Database not ready yet...')
    sys.exit(1)
"; do
    sleep 2
done

# Initialize database tables
echo "Initializing database..."
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created successfully!')
"

# Start the application
echo "Starting TraceTrack application..."
exec "$@"