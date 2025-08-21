
-- Add critical indexes for performance
CREATE INDEX IF NOT EXISTS idx_bag_qr_type ON bag(qr_id, type);
CREATE INDEX IF NOT EXISTS idx_scan_timestamp ON scan(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_bill_status_created ON bill(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_role ON "user"(role);
CREATE INDEX IF NOT EXISTS idx_link_composite ON link(parent_bag_id, child_bag_id);

-- Update PostgreSQL settings for better performance
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '128MB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET max_connections = 1000;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET max_worker_processes = 8;
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 8;
