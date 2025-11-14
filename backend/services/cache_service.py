"""
Redis caching service for performance optimization.
Handles query result caching, embeddings, and session management.
"""
import json
import hashlib
import pickle
from typing import Any, Optional, Union, Dict, List
from datetime import timedelta
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError
import logging

from core.config import settings
from core.logging import get_logger
from core.exceptions import CacheError

logger = get_logger("cache_service")


class CacheService:
    """Redis-based caching service for RAG system."""
    
    # Cache key prefixes
    PREFIX_QUERY = "query:"
    PREFIX_EMBEDDING = "embedding:"
    PREFIX_DOCUMENT = "document:"
    PREFIX_SESSION = "session:"
    PREFIX_RATE_LIMIT = "rate_limit:"
    PREFIX_USER = "user:"
    
    # Default TTL values (in seconds)
    TTL_QUERY = 300  # 5 minutes for query results
    TTL_EMBEDDING = 3600  # 1 hour for embeddings
    TTL_DOCUMENT = 1800  # 30 minutes for document metadata
    TTL_SESSION = 7200  # 2 hours for session data
    TTL_RATE_LIMIT = 60  # 1 minute for rate limit windows
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize cache service.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url or settings.REDIS_URL or "redis://localhost:6379/0"
        self.client: Optional[redis.Redis] = None
        self.pool: Optional[ConnectionPool] = None
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            logger.info(f"Connecting to Redis at {self.redis_url}")
            
            # Create connection pool
            self.pool = redis.ConnectionPool.from_url(
                self.redis_url,
                decode_responses=False,  # We'll handle encoding ourselves
                max_connections=50,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 1,  # TCP_KEEPINTVL
                    3: 5,  # TCP_KEEPCNT
                }
            )
            
            # Create Redis client
            self.client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            await self.client.ping()
            logger.info("Redis connection established successfully")
            
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise CacheError(f"Redis connection failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error initializing cache: {e}")
            raise CacheError(f"Cache initialization failed: {e}")
    
    async def shutdown(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")
        if self.pool:
            await self.pool.disconnect()
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """
        Generate a cache key.
        
        Args:
            prefix: Key prefix
            identifier: Unique identifier
            
        Returns:
            Cache key
        """
        return f"{prefix}{identifier}"
    
    def _hash_query(self, query: str, filters: Optional[Dict] = None) -> str:
        """
        Generate hash for a query.
        
        Args:
            query: Query text
            filters: Optional query filters
            
        Returns:
            Query hash
        """
        content = query
        if filters:
            content += json.dumps(filters, sort_keys=True)
        
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if not self.client:
            logger.warning("Cache not initialized")
            return None
        
        try:
            value = await self.client.get(key)
            if value:
                try:
                    # Try to deserialize with pickle first
                    return pickle.loads(value)
                except:
                    # Fallback to JSON
                    return json.loads(value)
            return None
            
        except RedisError as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            Success status
        """
        if not self.client:
            logger.warning("Cache not initialized")
            return False
        
        try:
            # Serialize value
            try:
                serialized = pickle.dumps(value)
            except:
                serialized = json.dumps(value).encode()
            
            # Set with optional TTL
            if ttl:
                await self.client.setex(key, ttl, serialized)
            else:
                await self.client.set(key, serialized)
            
            return True
            
        except RedisError as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Success status
        """
        if not self.client:
            return False
        
        try:
            result = await self.client.delete(key)
            return result > 0
        except RedisError as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            Existence status
        """
        if not self.client:
            return False
        
        try:
            return await self.client.exists(key) > 0
        except RedisError:
            return False
    
    # Query Result Caching
    
    async def get_query_result(
        self,
        query: str,
        filters: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Get cached query result.
        
        Args:
            query: Query text
            filters: Query filters
            
        Returns:
            Cached result or None
        """
        query_hash = self._hash_query(query, filters)
        key = self._generate_key(self.PREFIX_QUERY, query_hash)
        
        result = await self.get(key)
        if result:
            logger.debug(f"Cache hit for query: {query[:50]}...")
        
        return result
    
    async def set_query_result(
        self,
        query: str,
        result: Dict,
        filters: Optional[Dict] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache query result.
        
        Args:
            query: Query text
            result: Query result
            filters: Query filters
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        query_hash = self._hash_query(query, filters)
        key = self._generate_key(self.PREFIX_QUERY, query_hash)
        
        ttl = ttl or self.TTL_QUERY
        success = await self.set(key, result, ttl)
        
        if success:
            logger.debug(f"Cached query result: {query[:50]}...")
        
        return success
    
    # Document Embedding Caching
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get cached embedding.
        
        Args:
            text: Text to embed
            
        Returns:
            Cached embedding or None
        """
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        key = self._generate_key(self.PREFIX_EMBEDDING, text_hash)
        
        return await self.get(key)
    
    async def set_embedding(
        self,
        text: str,
        embedding: List[float],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache embedding.
        
        Args:
            text: Source text
            embedding: Embedding vector
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        key = self._generate_key(self.PREFIX_EMBEDDING, text_hash)
        
        ttl = ttl or self.TTL_EMBEDDING
        return await self.set(key, embedding, ttl)
    
    # Session Management
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get cached session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None
        """
        key = self._generate_key(self.PREFIX_SESSION, session_id)
        return await self.get(key)
    
    async def set_session(
        self,
        session_id: str,
        session_data: Dict,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache session data.
        
        Args:
            session_id: Session identifier
            session_data: Session data
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        key = self._generate_key(self.PREFIX_SESSION, session_id)
        ttl = ttl or self.TTL_SESSION
        return await self.set(key, session_data, ttl)
    
    async def extend_session(self, session_id: str) -> bool:
        """
        Extend session TTL.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Success status
        """
        if not self.client:
            return False
        
        key = self._generate_key(self.PREFIX_SESSION, session_id)
        
        try:
            return await self.client.expire(key, self.TTL_SESSION)
        except RedisError:
            return False
    
    # Rate Limiting
    
    async def check_rate_limit(
        self,
        user_id: str,
        limit: int = 100,
        window: int = 60
    ) -> tuple[bool, int]:
        """
        Check and update rate limit.
        
        Args:
            user_id: User identifier
            limit: Request limit
            window: Time window in seconds
            
        Returns:
            Tuple of (allowed, remaining_requests)
        """
        if not self.client:
            return True, limit  # Allow if cache unavailable
        
        key = self._generate_key(self.PREFIX_RATE_LIMIT, user_id)
        
        try:
            pipe = self.client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            results = await pipe.execute()
            
            current_count = results[0]
            remaining = max(0, limit - current_count)
            
            if current_count <= limit:
                return True, remaining
            else:
                return False, 0
                
        except RedisError as e:
            logger.error(f"Rate limit check error: {e}")
            return True, limit  # Allow on error
    
    async def reset_rate_limit(self, user_id: str) -> bool:
        """
        Reset user's rate limit.
        
        Args:
            user_id: User identifier
            
        Returns:
            Success status
        """
        key = self._generate_key(self.PREFIX_RATE_LIMIT, user_id)
        return await self.delete(key)
    
    # Cache Management
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "query:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.client:
            return 0
        
        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self.client.delete(*keys)
            return 0
            
        except RedisError as e:
            logger.error(f"Clear pattern error: {e}")
            return 0
    
    async def clear_all_queries(self) -> int:
        """Clear all cached queries."""
        return await self.clear_pattern(f"{self.PREFIX_QUERY}*")
    
    async def clear_all_embeddings(self) -> int:
        """Clear all cached embeddings."""
        return await self.clear_pattern(f"{self.PREFIX_EMBEDDING}*")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Cache statistics
        """
        if not self.client:
            return {"status": "disconnected"}
        
        try:
            info = await self.client.info()
            
            # Count keys by prefix
            query_count = 0
            embedding_count = 0
            session_count = 0
            
            async for key in self.client.scan_iter():
                key_str = key.decode() if isinstance(key, bytes) else key
                if key_str.startswith(self.PREFIX_QUERY):
                    query_count += 1
                elif key_str.startswith(self.PREFIX_EMBEDDING):
                    embedding_count += 1
                elif key_str.startswith(self.PREFIX_SESSION):
                    session_count += 1
            
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_keys": await self.client.dbsize(),
                "query_cache_count": query_count,
                "embedding_cache_count": embedding_count,
                "session_count": session_count,
                "hit_rate": info.get("keyspace_hits", 0) / 
                           max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
            }
            
        except RedisError as e:
            logger.error(f"Stats error: {e}")
            return {"status": "error", "error": str(e)}


# Global cache service instance
cache_service = CacheService()


async def get_cache_service() -> CacheService:
    """
    Get cache service instance.
    
    Returns:
        Cache service instance
    """
    if not cache_service.client:
        await cache_service.initialize()
    return cache_service