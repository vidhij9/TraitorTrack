"""
Async Database Operations for 100+ Concurrent Users
Implements non-blocking database queries to reduce connection hold time
"""

import asyncio
import asyncpg
import os
from typing import List, Dict, Any, Optional
import logging
from functools import wraps
import time

logger = logging.getLogger(__name__)

class AsyncDatabasePool:
    """Async PostgreSQL connection pool for non-blocking operations"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False
    
    async def init_pool(self):
        """Initialize async connection pool"""
        if self._initialized:
            return
        
        try:
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                logger.warning("DATABASE_URL not set, async pool not initialized")
                return
            
            # Create async connection pool with optimized settings
            self.pool = await asyncpg.create_pool(
                database_url,
                min_size=10,  # Minimum connections
                max_size=50,  # Maximum connections for async operations
                max_queries=50000,  # Queries per connection
                max_inactive_connection_lifetime=300,  # 5 minutes
                command_timeout=15,  # 15 second query timeout
                server_settings={
                    'jit': 'on',
                    'work_mem': '8MB',
                    'random_page_cost': '1.1',
                }
            )
            
            self._initialized = True
            logger.info("✅ Async database pool initialized (10-50 connections)")
            
        except Exception as e:
            logger.error(f"Failed to initialize async pool: {e}")
    
    async def close_pool(self):
        """Close async connection pool"""
        if self.pool:
            await self.pool.close()
            self._initialized = False
            logger.info("Async database pool closed")
    
    async def fetch_one(self, query: str, *args) -> Optional[Dict]:
        """Fetch single row async"""
        if not self.pool:
            await self.init_pool()
        
        if not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Async fetch_one error: {e}")
            return None
    
    async def fetch_all(self, query: str, *args) -> List[Dict]:
        """Fetch all rows async"""
        if not self.pool:
            await self.init_pool()
        
        if not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Async fetch_all error: {e}")
            return []
    
    async def execute(self, query: str, *args) -> bool:
        """Execute query async"""
        if not self.pool:
            await self.init_pool()
        
        if not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, *args)
                return True
        except Exception as e:
            logger.error(f"Async execute error: {e}")
            return False

# Global async pool instance
async_pool = AsyncDatabasePool()

def run_async(func):
    """Decorator to run async functions in sync context"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(func(*args, **kwargs))
    
    return wrapper

class AsyncQueryOptimizer:
    """Optimize database queries with async operations"""
    
    @staticmethod
    async def get_dashboard_stats_async() -> Dict[str, Any]:
        """Get dashboard statistics using async queries"""
        try:
            # Run queries in parallel using asyncio
            tasks = [
                async_pool.fetch_one("SELECT COUNT(*) as count FROM bags"),
                async_pool.fetch_one("SELECT COUNT(*) as count FROM scans"),
                async_pool.fetch_one("SELECT COUNT(*) as count FROM bills"),
                async_pool.fetch_one(
                    "SELECT COUNT(DISTINCT user_id) as count FROM scans WHERE user_id IS NOT NULL"
                ),
            ]
            
            results = await asyncio.gather(*tasks)
            
            return {
                'total_bags': results[0]['count'] if results[0] else 0,
                'total_scans': results[1]['count'] if results[1] else 0,
                'total_bills': results[2]['count'] if results[2] else 0,
                'active_users': results[3]['count'] if results[3] else 0,
            }
        except Exception as e:
            logger.error(f"Async dashboard stats error: {e}")
            return {
                'total_bags': 0,
                'total_scans': 0,
                'total_bills': 0,
                'active_users': 0,
            }
    
    @staticmethod
    async def search_bags_async(search_term: str, limit: int = 100) -> List[Dict]:
        """Search bags using async query"""
        try:
            query = """
                SELECT id, qr_id, name, type, created_at 
                FROM bags 
                WHERE qr_id ILIKE $1 OR name ILIKE $1
                ORDER BY created_at DESC
                LIMIT $2
            """
            return await async_pool.fetch_all(query, f"%{search_term}%", limit)
        except Exception as e:
            logger.error(f"Async bag search error: {e}")
            return []
    
    @staticmethod
    async def get_recent_scans_async(limit: int = 10) -> List[Dict]:
        """Get recent scans using async query"""
        try:
            query = """
                SELECT s.id, s.timestamp, s.user_id, u.username,
                       COALESCE(pb.qr_id, cb.qr_id) as qr_id,
                       CASE WHEN s.parent_bag_id IS NOT NULL THEN 'parent' ELSE 'child' END as scan_type
                FROM scans s
                LEFT JOIN users u ON s.user_id = u.id
                LEFT JOIN bags pb ON s.parent_bag_id = pb.id
                LEFT JOIN bags cb ON s.child_bag_id = cb.id
                ORDER BY s.timestamp DESC
                LIMIT $1
            """
            return await async_pool.fetch_all(query, limit)
        except Exception as e:
            logger.error(f"Async recent scans error: {e}")
            return []

# Sync wrappers for easy integration
@run_async
async def get_dashboard_stats_async():
    """Sync wrapper for async dashboard stats"""
    return await AsyncQueryOptimizer.get_dashboard_stats_async()

@run_async
async def search_bags_async(search_term: str, limit: int = 100):
    """Sync wrapper for async bag search"""
    return await AsyncQueryOptimizer.search_bags_async(search_term, limit)

@run_async
async def get_recent_scans_async(limit: int = 10):
    """Sync wrapper for async recent scans"""
    return await AsyncQueryOptimizer.get_recent_scans_async(limit)
