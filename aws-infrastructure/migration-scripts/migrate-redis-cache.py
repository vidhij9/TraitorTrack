#!/usr/bin/env python3
"""
Redis Cache Migration Script
Migrates from local Redis to AWS ElastiCache Redis
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# Try to import redis with fallback
try:
    import redis
    from redis import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisMigration:
    def __init__(self):
        if not REDIS_AVAILABLE:
            raise ImportError("Redis library not available. Please install redis-py")
        
        # Local Redis (current)
        self.local_redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        self.local_redis = None
        self.aws_redis = None
        
        # Initialize local Redis connection
        try:
            if redis is None:
                raise ImportError("Redis module not available")
            self.local_redis = redis.from_url(
                self.local_redis_url, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        except Exception as e:
            logger.error(f"Failed to initialize local Redis connection: {e}")
            raise
        
        # AWS ElastiCache Redis (target)
        self.aws_redis_url = os.environ.get('AWS_REDIS_URL')
        if self.aws_redis_url:
            try:
                if redis is None:
                    raise ImportError("Redis module not available")
                self.aws_redis = redis.from_url(
                    self.aws_redis_url, 
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            except Exception as e:
                logger.error(f"Failed to initialize AWS Redis connection: {e}")
                self.aws_redis = None
        else:
            logger.warning("AWS_REDIS_URL not set. Migration will be simulated.")
    
    def test_connections(self) -> Dict[str, bool]:
        """Test connections to both Redis instances"""
        results = {}
        
        # Test local Redis
        try:
            if self.local_redis is not None:
                self.local_redis.ping()
                results['local'] = True
                logger.info("✅ Local Redis connection successful")
            else:
                results['local'] = False
                logger.error("❌ Local Redis client not initialized")
        except Exception as e:
            results['local'] = False
            logger.error(f"❌ Local Redis connection failed: {e}")
        
        # Test AWS Redis
        if self.aws_redis is not None:
            try:
                self.aws_redis.ping()
                results['aws'] = True
                logger.info("✅ AWS Redis connection successful")
            except Exception as e:
                results['aws'] = False
                logger.error(f"❌ AWS Redis connection failed: {e}")
        else:
            results['aws'] = False
            logger.info("⚠️ AWS Redis not configured")
        
        return results
    
    def get_cache_keys(self) -> List[str]:
        """Get all cache keys from local Redis"""
        try:
            if not self.local_redis:
                logger.error("Local Redis connection not available")
                return []
            
            keys_result = self.local_redis.keys('*')
            # Ensure keys are strings and handle both sync and potential async results
            if keys_result is None:
                keys = []
            elif hasattr(keys_result, '__iter__') and not isinstance(keys_result, str):
                keys = [str(key) for key in keys_result]
            else:
                keys = []
            logger.info(f"Found {len(keys)} keys in local Redis")
            return keys
        except Exception as e:
            logger.error(f"Failed to get keys from local Redis: {e}")
            return []
    
    def analyze_cache_data(self) -> Dict[str, Any]:
        """Analyze cache data patterns"""
        keys = self.get_cache_keys()
        analysis = {
            'total_keys': len(keys),
            'key_patterns': {},
            'data_types': {},
            'memory_usage': 0
        }
        
        for key in keys:
            # Analyze key patterns
            pattern = key.split(':')[0] if ':' in key else 'simple'
            analysis['key_patterns'][pattern] = analysis['key_patterns'].get(pattern, 0) + 1
            
            # Analyze data types
            try:
                if self.local_redis is not None:
                    key_type = self.local_redis.type(key)
                    analysis['data_types'][key_type] = analysis['data_types'].get(key_type, 0) + 1
                    
                    # Estimate memory usage
                    if key_type == 'string':
                        value = self.local_redis.get(key)
                        analysis['memory_usage'] += len(str(value)) if value else 0
                
            except Exception as e:
                logger.warning(f"Could not analyze key {key}: {e}")
        
        return analysis
    
    def export_cache_data(self, filename: Optional[str] = None) -> str:
        """Export cache data to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'redis_export_{timestamp}.json'
        
        keys = self.get_cache_keys()
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'total_keys': len(keys),
            'data': {}
        }
        
        for key in keys:
            try:
                if self.local_redis is None:
                    continue
                
                key_type = self.local_redis.type(key)
                ttl = self.local_redis.ttl(key)
                
                if key_type == 'string':
                    value = self.local_redis.get(key)
                elif key_type == 'hash':
                    value = self.local_redis.hgetall(key)
                elif key_type == 'list':
                    value = self.local_redis.lrange(key, 0, -1)
                elif key_type == 'set':
                    members_result = self.local_redis.smembers(key)
                    if members_result and hasattr(members_result, '__iter__'):
                        value = list(members_result)
                    else:
                        value = []
                elif key_type == 'zset':
                    zset_result = self.local_redis.zrange(key, 0, -1, withscores=True)
                    if zset_result and hasattr(zset_result, '__iter__'):
                        value = list(zset_result)
                    else:
                        value = []
                else:
                    value = None
                
                export_data['data'][key] = {
                    'type': key_type,
                    'value': value,
                    'ttl': ttl
                }
                
            except Exception as e:
                logger.error(f"Failed to export key {key}: {e}")
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Cache data exported to {filename}")
        return filename
    
    def import_cache_data(self, filename: str) -> bool:
        """Import cache data to AWS Redis"""
        if not self.aws_redis:
            logger.error("AWS Redis not configured")
            return False
        
        try:
            with open(filename, 'r') as f:
                import_data = json.load(f)
            
            total_keys = len(import_data['data'])
            imported = 0
            
            for key, data in import_data['data'].items():
                try:
                    key_type = data['type']
                    value = data['value']
                    ttl = data['ttl']
                    
                    # Import based on data type
                    if key_type == 'string':
                        self.aws_redis.set(key, value)
                    elif key_type == 'hash':
                        if value and isinstance(value, dict):
                            self.aws_redis.hset(key, mapping=value)
                    elif key_type == 'list':
                        if value and isinstance(value, list):
                            # Clear existing list first
                            self.aws_redis.delete(key)
                            if value:
                                self.aws_redis.lpush(key, *reversed(value))
                    elif key_type == 'set':
                        if value and isinstance(value, list):
                            # Clear existing set first
                            self.aws_redis.delete(key)
                            if value:
                                self.aws_redis.sadd(key, *value)
                    elif key_type == 'zset':
                        if value and isinstance(value, list):
                            # Clear existing zset first
                            self.aws_redis.delete(key)
                            if value:
                                # Convert list of tuples to dict for zadd
                                if all(isinstance(item, (list, tuple)) and len(item) == 2 for item in value):
                                    zset_dict = {item[0]: item[1] for item in value}
                                    self.aws_redis.zadd(key, zset_dict)
                                else:
                                    logger.warning(f"Invalid zset data for key {key}: {value}")
                    
                    # Set TTL if it exists
                    if ttl and ttl > 0:
                        self.aws_redis.expire(key, ttl)
                    
                    imported += 1
                    
                except Exception as e:
                    logger.error(f"Failed to import key {key}: {e}")
            
            logger.info(f"Imported {imported}/{total_keys} keys to AWS Redis")
            return imported == total_keys
            
        except Exception as e:
            logger.error(f"Failed to import cache data: {e}")
            return False
    
    def sync_cache_data(self) -> bool:
        """Sync cache data from local to AWS Redis"""
        if not self.aws_redis:
            logger.error("AWS Redis not configured")
            return False
        
        keys = self.get_cache_keys()
        synced = 0
        
        for key in keys:
            try:
                if self.local_redis is None or self.aws_redis is None:
                    continue
                
                key_type = self.local_redis.type(key)
                ttl = self.local_redis.ttl(key)
                
                if key_type == 'string':
                    value = self.local_redis.get(key)
                    self.aws_redis.set(key, value)
                elif key_type == 'hash':
                    value = self.local_redis.hgetall(key)
                    self.aws_redis.delete(key)  # Clear existing
                    if value and isinstance(value, dict):
                        self.aws_redis.hset(key, mapping=value)
                elif key_type == 'list':
                    value = self.local_redis.lrange(key, 0, -1)
                    self.aws_redis.delete(key)  # Clear existing
                    if value and isinstance(value, list):
                        self.aws_redis.lpush(key, *reversed(value))
                elif key_type == 'set':
                    members_result = self.local_redis.smembers(key)
                    if members_result and hasattr(members_result, '__iter__'):
                        value = list(members_result)
                    else:
                        value = []
                    self.aws_redis.delete(key)  # Clear existing
                    if value:
                        self.aws_redis.sadd(key, *value)
                elif key_type == 'zset':
                    zset_result = self.local_redis.zrange(key, 0, -1, withscores=True)
                    self.aws_redis.delete(key)  # Clear existing
                    if zset_result and hasattr(zset_result, '__iter__'):
                        zset_data = list(zset_result)
                        # Convert to dict format for zadd
                        if all(isinstance(item, (list, tuple)) and len(item) == 2 for item in zset_data):
                            zset_dict = {item[0]: item[1] for item in zset_data}
                            self.aws_redis.zadd(key, zset_dict)
                        else:
                            logger.warning(f"Invalid zset data for key {key}: {zset_data}")
                
                # Set TTL if it exists
                if ttl and ttl > 0:
                    self.aws_redis.expire(key, ttl)
                
                synced += 1
                
            except Exception as e:
                logger.error(f"Failed to sync key {key}: {e}")
        
        logger.info(f"Synced {synced}/{len(keys)} keys to AWS Redis")
        return synced == len(keys)
    
    def validate_migration(self) -> Dict[str, Union[bool, str]]:
        """Validate that migration was successful"""
        if not self.aws_redis:
            return {'validation': False, 'reason': 'AWS Redis not configured'}
        
        results = {
            'key_count_match': False,
            'sample_data_match': False,
            'validation': False
        }
        
        try:
            if self.local_redis is None or self.aws_redis is None:
                logger.error("Redis connections not available for validation")
                return {'validation': False, 'reason': 'Missing Redis connections'}
            
            # Check key count
            local_keys_raw = self.local_redis.keys('*')
            aws_keys_raw = self.aws_redis.keys('*')
            
            # Ensure keys are strings and convert to sets
            local_keys = set()
            if local_keys_raw and hasattr(local_keys_raw, '__iter__'):
                local_keys = set(str(key) for key in local_keys_raw)
            
            aws_keys = set()
            if aws_keys_raw and hasattr(aws_keys_raw, '__iter__'):
                aws_keys = set(str(key) for key in aws_keys_raw)
            
            results['key_count_match'] = len(local_keys) == len(aws_keys)
            logger.info(f"Key count - Local: {len(local_keys)}, AWS: {len(aws_keys)}")
            
            # Sample data validation
            sample_keys = list(local_keys)[:10] if local_keys else []
            sample_matches = 0
            
            for key in sample_keys:
                try:
                    if self.local_redis is not None and self.aws_redis is not None:
                        local_value = self.local_redis.get(key)
                        aws_value = self.aws_redis.get(key)
                        
                        if local_value == aws_value:
                            sample_matches += 1
                        
                except Exception as e:
                    logger.warning(f"Could not validate key {key}: {e}")
            
            results['sample_data_match'] = sample_matches == len(sample_keys) if sample_keys else True
            results['validation'] = results['key_count_match'] and results['sample_data_match']
            
            logger.info(f"Sample validation: {sample_matches}/{len(sample_keys)} keys match")
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            results['validation'] = False
        
        return results
    
    def run_migration(self) -> bool:
        """Run complete migration process"""
        logger.info("🚀 Starting Redis cache migration...")
        
        # Test connections
        connections = self.test_connections()
        if not connections.get('local'):
            logger.error("Cannot proceed without local Redis connection")
            return False
        
        if not connections.get('aws'):
            logger.error("Cannot proceed without AWS Redis connection")
            return False
        
        # Analyze current cache
        analysis = self.analyze_cache_data()
        logger.info(f"Cache analysis: {analysis}")
        
        # Export data (backup)
        export_file = self.export_cache_data()
        logger.info(f"Backup created: {export_file}")
        
        # Sync data to AWS
        sync_success = self.sync_cache_data()
        if not sync_success:
            logger.error("Cache sync failed")
            return False
        
        # Validate migration
        validation = self.validate_migration()
        if not validation.get('validation'):
            logger.error(f"Migration validation failed: {validation}")
            return False
        
        logger.info("✅ Redis cache migration completed successfully!")
        return True

def main():
    """Main migration function"""
    migration = RedisMigration()
    
    # Check if this is a dry run
    dry_run = os.environ.get('DRY_RUN', 'false').lower() == 'true'
    
    if dry_run:
        logger.info("🔍 Running in DRY RUN mode...")
        connections = migration.test_connections()
        analysis = migration.analyze_cache_data()
        export_file = migration.export_cache_data()
        
        logger.info("Dry run complete. Set DRY_RUN=false to execute migration.")
        return True
    else:
        return migration.run_migration()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)