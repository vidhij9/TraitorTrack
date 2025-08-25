"""
FastAPI Async Application - Ultra-fast async endpoints for production
Target: <100ms response times with 50+ concurrent users
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncpg
import aioredis
import asyncio
import time
import json
import os
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="TraceTrack Ultra-Fast API",
    description="Async API for millisecond response times",
    version="2.0.0"
)

# Global connections
db_pool: Optional[asyncpg.Pool] = None
redis_pool: Optional[aioredis.Redis] = None

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:pass@localhost/db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Parse database URL for asyncpg
import urllib.parse
parsed = urllib.parse.urlparse(DATABASE_URL)
ASYNC_DATABASE_CONFIG = {
    'host': parsed.hostname or 'localhost',
    'port': parsed.port or 5432,
    'user': parsed.username or 'postgres',
    'password': parsed.password or '',
    'database': parsed.path[1:] if parsed.path else 'postgres',
    'min_size': 10,
    'max_size': 50,
    'command_timeout': 10,
    'max_queries': 50000,
    'max_inactive_connection_lifetime': 300
}

@app.on_event("startup")
async def startup():
    """Initialize database and Redis pools on startup"""
    global db_pool, redis_pool
    
    # Create database pool
    try:
        db_pool = await asyncpg.create_pool(**ASYNC_DATABASE_CONFIG)
        logger.info("✅ Async database pool created")
    except Exception as e:
        logger.error(f"❌ Failed to create database pool: {e}")
    
    # Create Redis pool
    try:
        redis_pool = await aioredis.create_redis_pool(
            'redis://localhost:6379',
            minsize=5,
            maxsize=20,
            encoding='utf-8'
        )
        await redis_pool.ping()
        logger.info("✅ Async Redis pool created")
    except Exception as e:
        logger.warning(f"⚠️ Redis not available: {e}")
        redis_pool = None

@app.on_event("shutdown")
async def shutdown():
    """Cleanup pools on shutdown"""
    global db_pool, redis_pool
    
    if db_pool:
        await db_pool.close()
    if redis_pool:
        redis_pool.close()
        await redis_pool.wait_closed()

# Pydantic models for request/response
class ScanRequest(BaseModel):
    parent_qr: str
    child_qr: str
    user_id: Optional[int] = 1

class BagResponse(BaseModel):
    id: int
    qr_id: str
    type: str
    created_at: Optional[datetime]

# Caching decorator
async def cache_get(key: str):
    """Get from cache"""
    if redis_pool:
        try:
            value = await redis_pool.get(key)
            if value:
                return json.loads(value)
        except:
            pass
    return None

async def cache_set(key: str, value: Any, ttl: int = 60):
    """Set in cache"""
    if redis_pool:
        try:
            await redis_pool.setex(key, ttl, json.dumps(value))
        except:
            pass

# Ultra-fast endpoints
@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/v3/stats")
async def get_stats():
    """Ultra-fast stats endpoint with caching"""
    start = time.time()
    
    # Try cache first
    cached = await cache_get("stats:dashboard")
    if cached:
        cached['cached'] = True
        cached['response_time_ms'] = (time.time() - start) * 1000
        return cached
    
    # Query database
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 
                (SELECT COUNT(*) FROM scan WHERE timestamp > NOW() - INTERVAL '7 days') as recent_scans,
                (SELECT COUNT(*) FROM bag WHERE type = 'parent') as parent_bags,
                (SELECT COUNT(*) FROM bag WHERE type = 'child') as child_bags,
                (SELECT COUNT(*) FROM bill) as bills,
                (SELECT COUNT(DISTINCT user_id) FROM scan WHERE timestamp > NOW() - INTERVAL '1 day') as active_users,
                (SELECT COUNT(*) FROM link) as total_links
        """)
    
    stats = dict(row) if row else {}
    stats['cached'] = False
    stats['response_time_ms'] = (time.time() - start) * 1000
    
    # Cache for 30 seconds
    await cache_set("stats:dashboard", stats, 30)
    
    return stats

@app.get("/api/v3/scans")
async def get_recent_scans(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get recent scans with ultra-fast response"""
    start = time.time()
    
    cache_key = f"scans:{limit}:{offset}"
    cached = await cache_get(cache_key)
    if cached:
        cached['cached'] = True
        cached['response_time_ms'] = (time.time() - start) * 1000
        return cached
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                s.id,
                s.timestamp,
                u.username,
                pb.qr_id as parent_qr,
                cb.qr_id as child_qr
            FROM scan s
            LEFT JOIN "user" u ON s.user_id = u.id
            LEFT JOIN bag pb ON s.parent_bag_id = pb.id
            LEFT JOIN bag cb ON s.child_bag_id = cb.id
            ORDER BY s.timestamp DESC
            LIMIT $1 OFFSET $2
        """, limit, offset)
    
    scans = [dict(row) for row in rows]
    result = {
        'scans': scans,
        'count': len(scans),
        'cached': False,
        'response_time_ms': (time.time() - start) * 1000
    }
    
    await cache_set(cache_key, result, 10)
    return result

@app.post("/api/v3/scan")
async def process_scan(scan: ScanRequest):
    """Ultra-fast async scan processing"""
    start = time.time()
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            # Check parent exists
            parent = await conn.fetchrow(
                "SELECT id FROM bag WHERE qr_id = $1 AND type = 'parent'",
                scan.parent_qr
            )
            
            if not parent:
                # Create parent
                parent_id = await conn.fetchval(
                    "INSERT INTO bag (qr_id, type, created_at, updated_at) VALUES ($1, 'parent', NOW(), NOW()) RETURNING id",
                    scan.parent_qr
                )
            else:
                parent_id = parent['id']
            
            # Check/create child
            child = await conn.fetchrow(
                "SELECT id FROM bag WHERE qr_id = $1",
                scan.child_qr
            )
            
            if not child:
                child_id = await conn.fetchval(
                    "INSERT INTO bag (qr_id, type, created_at, updated_at) VALUES ($1, 'child', NOW(), NOW()) RETURNING id",
                    scan.child_qr
                )
            else:
                child_id = child['id']
            
            # Create link
            await conn.execute(
                "INSERT INTO link (parent_bag_id, child_bag_id, created_at) VALUES ($1, $2, NOW()) ON CONFLICT DO NOTHING",
                parent_id, child_id
            )
            
            # Create scan record
            scan_id = await conn.fetchval(
                "INSERT INTO scan (user_id, parent_bag_id, child_bag_id, timestamp) VALUES ($1, $2, $3, NOW()) RETURNING id",
                scan.user_id, parent_id, child_id
            )
    
    # Invalidate cache
    if redis_pool:
        await redis_pool.delete("stats:dashboard")
    
    return {
        'success': True,
        'scan_id': scan_id,
        'parent_id': parent_id,
        'child_id': child_id,
        'response_time_ms': (time.time() - start) * 1000
    }

@app.get("/api/v3/bags")
async def get_bags(
    bag_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """Get bags with filtering"""
    start = time.time()
    
    cache_key = f"bags:{bag_type}:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        cached['cached'] = True
        cached['response_time_ms'] = (time.time() - start) * 1000
        return cached
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with db_pool.acquire() as conn:
        if bag_type:
            rows = await conn.fetch(
                "SELECT id, qr_id, type, created_at FROM bag WHERE type = $1 ORDER BY created_at DESC LIMIT $2",
                bag_type, limit
            )
        else:
            rows = await conn.fetch(
                "SELECT id, qr_id, type, created_at FROM bag ORDER BY created_at DESC LIMIT $1",
                limit
            )
    
    bags = [dict(row) for row in rows]
    result = {
        'bags': bags,
        'count': len(bags),
        'cached': False,
        'response_time_ms': (time.time() - start) * 1000
    }
    
    await cache_set(cache_key, result, 60)
    return result

@app.get("/api/v3/health")
async def health_check():
    """Comprehensive health check"""
    health = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': False,
        'redis': False
    }
    
    # Check database
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                health['database'] = True
        except:
            pass
    
    # Check Redis
    if redis_pool:
        try:
            await redis_pool.ping()
            health['redis'] = True
        except:
            pass
    
    if not health['database']:
        health['status'] = 'degraded'
    
    return health

@app.get("/api/v3/performance")
async def performance_test():
    """Test endpoint performance"""
    results = {}
    
    # Test database query
    start = time.time()
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT COUNT(*) FROM bag")
    results['database_ms'] = (time.time() - start) * 1000
    
    # Test Redis
    start = time.time()
    if redis_pool:
        await redis_pool.ping()
    results['redis_ms'] = (time.time() - start) * 1000
    
    # Test cache
    start = time.time()
    await cache_get("test:key")
    results['cache_get_ms'] = (time.time() - start) * 1000
    
    return results

# Run with: uvicorn fastapi_app:app --host 0.0.0.0 --port 8000 --workers 4