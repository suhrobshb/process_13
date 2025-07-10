"""
Redis Client Integration
=======================

Provides Redis caching and distributed state management for the AI Automation Platform.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import redis
from redis.connection import ConnectionPool
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis client with caching, distributed state management, and circuit breaker integration
    """
    
    def __init__(self, url: str = None, max_connections: int = 10):
        """
        Initialize Redis client with connection pooling
        
        Args:
            url: Redis connection URL (defaults to environment variable)
            max_connections: Maximum number of connections in pool
        """
        self.url = url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.pool = ConnectionPool.from_url(
            self.url,
            max_connections=max_connections,
            retry_on_timeout=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            health_check_interval=30
        )
        self.client = redis.Redis(connection_pool=self.pool)
        self._connected = False
        
        # Test connection
        self._test_connection()
        
        # Cache configuration
        self.default_ttl = 3600  # 1 hour
        self.key_prefix = "ai_engine"
        
    def _test_connection(self):
        """Test Redis connection"""
        try:
            self.client.ping()
            self._connected = True
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self._connected = False
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self._connected
    
    def _make_key(self, key: str, prefix: str = None) -> str:
        """Create namespaced key"""
        namespace = prefix or self.key_prefix
        return f"{namespace}:{key}"
    
    # Basic Redis Operations
    def set(self, key: str, value: Any, ttl: int = None, prefix: str = None) -> bool:
        """
        Set a value in Redis with optional TTL
        
        Args:
            key: Redis key
            value: Value to store (will be JSON serialized)
            ttl: Time to live in seconds (default: 1 hour)
            prefix: Key prefix override
            
        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            return False
            
        try:
            redis_key = self._make_key(key, prefix)
            serialized_value = json.dumps(value, default=str)
            
            if ttl or self.default_ttl:
                return self.client.setex(redis_key, ttl or self.default_ttl, serialized_value)
            else:
                return self.client.set(redis_key, serialized_value)
                
        except Exception as e:
            logger.error(f"Redis SET failed for key {key}: {e}")
            return False
    
    def get(self, key: str, prefix: str = None) -> Optional[Any]:
        """
        Get a value from Redis
        
        Args:
            key: Redis key
            prefix: Key prefix override
            
        Returns:
            Deserialized value or None if not found
        """
        if not self._connected:
            return None
            
        try:
            redis_key = self._make_key(key, prefix)
            value = self.client.get(redis_key)
            
            if value is None:
                return None
                
            return json.loads(value.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"Redis GET failed for key {key}: {e}")
            return None
    
    def delete(self, key: str, prefix: str = None) -> bool:
        """
        Delete a key from Redis
        
        Args:
            key: Redis key
            prefix: Key prefix override
            
        Returns:
            True if deleted, False otherwise
        """
        if not self._connected:
            return False
            
        try:
            redis_key = self._make_key(key, prefix)
            return bool(self.client.delete(redis_key))
            
        except Exception as e:
            logger.error(f"Redis DELETE failed for key {key}: {e}")
            return False
    
    def exists(self, key: str, prefix: str = None) -> bool:
        """
        Check if key exists in Redis
        
        Args:
            key: Redis key
            prefix: Key prefix override
            
        Returns:
            True if key exists, False otherwise
        """
        if not self._connected:
            return False
            
        try:
            redis_key = self._make_key(key, prefix)
            return bool(self.client.exists(redis_key))
            
        except Exception as e:
            logger.error(f"Redis EXISTS failed for key {key}: {e}")
            return False
    
    def expire(self, key: str, ttl: int, prefix: str = None) -> bool:
        """
        Set TTL for existing key
        
        Args:
            key: Redis key
            ttl: Time to live in seconds
            prefix: Key prefix override
            
        Returns:
            True if TTL was set, False otherwise
        """
        if not self._connected:
            return False
            
        try:
            redis_key = self._make_key(key, prefix)
            return bool(self.client.expire(redis_key, ttl))
            
        except Exception as e:
            logger.error(f"Redis EXPIRE failed for key {key}: {e}")
            return False
    
    # Caching Helpers
    def cache_get_or_set(self, key: str, callable_func, ttl: int = None, prefix: str = None) -> Any:
        """
        Get value from cache or set it using callable
        
        Args:
            key: Cache key
            callable_func: Function to call if cache miss
            ttl: Time to live in seconds
            prefix: Key prefix override
            
        Returns:
            Cached value or result of callable
        """
        # Try to get from cache first
        cached_value = self.get(key, prefix)
        if cached_value is not None:
            return cached_value
        
        # Cache miss - call function and cache result
        try:
            result = callable_func()
            self.set(key, result, ttl, prefix)
            return result
        except Exception as e:
            logger.error(f"Cache miss callable failed for key {key}: {e}")
            return None
    
    def cache_workflow_result(self, workflow_id: str, execution_id: str, result: Dict[str, Any], ttl: int = 3600):
        """Cache workflow execution result"""
        key = f"workflow_result:{workflow_id}:{execution_id}"
        return self.set(key, result, ttl, "cache")
    
    def get_cached_workflow_result(self, workflow_id: str, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get cached workflow execution result"""
        key = f"workflow_result:{workflow_id}:{execution_id}"
        return self.get(key, "cache")
    
    # Distributed State Management
    def set_circuit_breaker_state(self, service_name: str, state: str, failures: int = 0, last_failure_time: datetime = None):
        """
        Set circuit breaker state for a service
        
        Args:
            service_name: Name of the service
            state: Circuit breaker state (closed, open, half-open)
            failures: Number of failures
            last_failure_time: Time of last failure
        """
        key = f"circuit_breaker:{service_name}"
        data = {
            "state": state,
            "failures": failures,
            "last_failure_time": last_failure_time.isoformat() if last_failure_time else None,
            "updated_at": datetime.now().isoformat()
        }
        return self.set(key, data, ttl=300, prefix="state")  # 5 minutes TTL
    
    def get_circuit_breaker_state(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get circuit breaker state for a service"""
        key = f"circuit_breaker:{service_name}"
        return self.get(key, "state")
    
    def increment_circuit_breaker_failures(self, service_name: str) -> int:
        """Increment failure count for circuit breaker"""
        key = f"circuit_breaker_failures:{service_name}"
        redis_key = self._make_key(key, "state")
        
        if not self._connected:
            return 0
            
        try:
            return int(self.client.incr(redis_key))
        except Exception as e:
            logger.error(f"Failed to increment circuit breaker failures for {service_name}: {e}")
            return 0
    
    def reset_circuit_breaker_failures(self, service_name: str):
        """Reset failure count for circuit breaker"""
        key = f"circuit_breaker_failures:{service_name}"
        return self.delete(key, "state")
    
    # Rate Limiting
    def check_rate_limit(self, identifier: str, limit: int, window: int = 60) -> bool:
        """
        Check if rate limit is exceeded
        
        Args:
            identifier: Unique identifier (user ID, IP, etc.)
            limit: Maximum number of requests
            window: Time window in seconds
            
        Returns:
            True if within limit, False if exceeded
        """
        if not self._connected:
            return True  # Allow if Redis is down
            
        try:
            key = f"rate_limit:{identifier}"
            redis_key = self._make_key(key, "limits")
            
            # Using sliding window with sorted sets
            now = datetime.now().timestamp()
            window_start = now - window
            
            # Remove old entries
            self.client.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current requests
            current_count = self.client.zcard(redis_key)
            
            if current_count >= limit:
                return False
            
            # Add current request
            self.client.zadd(redis_key, {str(now): now})
            self.client.expire(redis_key, window)
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check failed for {identifier}: {e}")
            return True  # Allow if error occurs
    
    def get_rate_limit_info(self, identifier: str, limit: int, window: int = 60) -> Dict[str, Any]:
        """Get rate limit information"""
        if not self._connected:
            return {"remaining": limit, "reset_time": None}
            
        try:
            key = f"rate_limit:{identifier}"
            redis_key = self._make_key(key, "limits")
            
            now = datetime.now().timestamp()
            window_start = now - window
            
            # Remove old entries
            self.client.zremrangebyscore(redis_key, 0, window_start)
            
            # Get current count
            current_count = self.client.zcard(redis_key)
            remaining = max(0, limit - current_count)
            
            # Get oldest request time for reset calculation
            oldest_requests = self.client.zrange(redis_key, 0, 0, withscores=True)
            reset_time = None
            if oldest_requests:
                oldest_time = oldest_requests[0][1]
                reset_time = datetime.fromtimestamp(oldest_time + window)
            
            return {
                "remaining": remaining,
                "reset_time": reset_time.isoformat() if reset_time else None,
                "current_count": current_count,
                "limit": limit
            }
            
        except Exception as e:
            logger.error(f"Rate limit info failed for {identifier}: {e}")
            return {"remaining": limit, "reset_time": None}
    
    # Session Management
    def set_session(self, session_id: str, user_data: Dict[str, Any], ttl: int = 3600):
        """Store user session data"""
        key = f"session:{session_id}"
        return self.set(key, user_data, ttl, "sessions")
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user session data"""
        key = f"session:{session_id}"
        return self.get(key, "sessions")
    
    def delete_session(self, session_id: str):
        """Delete user session"""
        key = f"session:{session_id}"
        return self.delete(key, "sessions")
    
    def extend_session(self, session_id: str, ttl: int = 3600):
        """Extend session TTL"""
        key = f"session:{session_id}"
        return self.expire(key, ttl, "sessions")
    
    # Pub/Sub for Real-time Updates
    def publish(self, channel: str, message: Dict[str, Any]):
        """Publish message to channel"""
        if not self._connected:
            return False
            
        try:
            serialized_message = json.dumps(message, default=str)
            return self.client.publish(channel, serialized_message)
        except Exception as e:
            logger.error(f"Redis publish failed for channel {channel}: {e}")
            return False
    
    def subscribe(self, channels: List[str]):
        """Subscribe to channels"""
        if not self._connected:
            return None
            
        try:
            pubsub = self.client.pubsub()
            pubsub.subscribe(*channels)
            return pubsub
        except Exception as e:
            logger.error(f"Redis subscribe failed: {e}")
            return None
    
    # Metrics and Monitoring
    def increment_metric(self, metric_name: str, value: int = 1, ttl: int = 86400):
        """Increment a metric counter"""
        key = f"metrics:{metric_name}"
        redis_key = self._make_key(key, "metrics")
        
        if not self._connected:
            return 0
            
        try:
            result = self.client.incrby(redis_key, value)
            self.client.expire(redis_key, ttl)
            return int(result)
        except Exception as e:
            logger.error(f"Metric increment failed for {metric_name}: {e}")
            return 0
    
    def get_metric(self, metric_name: str) -> int:
        """Get metric value"""
        key = f"metrics:{metric_name}"
        redis_key = self._make_key(key, "metrics")
        
        if not self._connected:
            return 0
            
        try:
            value = self.client.get(redis_key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Metric get failed for {metric_name}: {e}")
            return 0
    
    def get_all_metrics(self) -> Dict[str, int]:
        """Get all metrics"""
        if not self._connected:
            return {}
            
        try:
            pattern = self._make_key("metrics:*", "metrics")
            keys = self.client.keys(pattern)
            
            metrics = {}
            for key in keys:
                key_str = key.decode('utf-8')
                # Extract metric name from key
                metric_name = key_str.split(':', 2)[-1]  # Get part after "ai_engine:metrics:"
                value = self.client.get(key)
                metrics[metric_name] = int(value) if value else 0
            
            return metrics
        except Exception as e:
            logger.error(f"Get all metrics failed: {e}")
            return {}
    
    # Health Check
    def health_check(self) -> Dict[str, Any]:
        """Perform Redis health check"""
        try:
            start_time = datetime.now()
            
            # Test ping
            ping_result = self.client.ping()
            
            # Test set/get/delete
            test_key = "health_check_test"
            test_value = {"timestamp": start_time.isoformat()}
            
            self.set(test_key, test_value, ttl=60, prefix="health")
            retrieved_value = self.get(test_key, prefix="health")
            self.delete(test_key, prefix="health")
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            # Get Redis info
            info = self.client.info()
            
            return {
                "status": "healthy",
                "ping": ping_result,
                "response_time_ms": response_time,
                "test_operations": "passed",
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "total_commands_processed": info.get("total_commands_processed"),
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": self._connected
            }
    
    # Context Manager Support
    @contextmanager
    def pipeline(self):
        """Context manager for Redis pipeline"""
        if not self._connected:
            yield None
            return
            
        pipe = self.client.pipeline()
        try:
            yield pipe
        finally:
            pipe.reset()
    
    def close(self):
        """Close Redis connection"""
        if self.client:
            self.client.close()
        self._connected = False


# Singleton instance
_redis_client = None


def get_redis_client() -> RedisClient:
    """Get singleton Redis client instance"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client


def is_redis_available() -> bool:
    """Check if Redis is available"""
    try:
        client = get_redis_client()
        return client.is_connected()
    except Exception:
        return False


# Decorators
def cache_result(key_template: str, ttl: int = 3600, prefix: str = "cache"):
    """
    Decorator to cache function results
    
    Args:
        key_template: Template for cache key (can use function arguments)
        ttl: Time to live in seconds
        prefix: Cache key prefix
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Build cache key from template and arguments
            try:
                cache_key = key_template.format(*args, **kwargs)
            except (IndexError, KeyError):
                # If template formatting fails, use function name and args
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            redis_client = get_redis_client()
            
            # Try to get from cache
            cached_result = redis_client.get(cache_key, prefix)
            if cached_result is not None:
                return cached_result
            
            # Cache miss - call function and cache result
            result = func(*args, **kwargs)
            redis_client.set(cache_key, result, ttl, prefix)
            
            return result
        
        return wrapper
    return decorator


def rate_limit(identifier_func=None, limit: int = 100, window: int = 60):
    """
    Decorator for rate limiting
    
    Args:
        identifier_func: Function to extract identifier from arguments
        limit: Maximum number of requests
        window: Time window in seconds
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get identifier
            if identifier_func:
                identifier = identifier_func(*args, **kwargs)
            else:
                # Default: use function name
                identifier = func.__name__
            
            redis_client = get_redis_client()
            
            # Check rate limit
            if not redis_client.check_rate_limit(identifier, limit, window):
                raise Exception(f"Rate limit exceeded for {identifier}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test Redis client
    client = get_redis_client()
    print("Redis Health Check:", client.health_check())