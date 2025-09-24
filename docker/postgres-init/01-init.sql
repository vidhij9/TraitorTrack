-- TraceTrack PostgreSQL initialization script
-- This script runs when the PostgreSQL container starts for the first time

-- Create the database if it doesn't exist
SELECT 'CREATE DATABASE tracetrack_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'tracetrack_db')\gexec

-- Connect to the database
\c tracetrack_db;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE tracetrack_db TO tracetrack_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tracetrack_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tracetrack_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO tracetrack_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO tracetrack_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO tracetrack_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO tracetrack_user;