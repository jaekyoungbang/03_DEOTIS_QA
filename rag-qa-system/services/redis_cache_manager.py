import redis
import json
import hashlib
from datetime import datetime
import os

class RedisCacheManager:
    def __init__(self, host='127.0.0.1', port=6379, db=0, ttl_hours=24, password=None):
        """
        Initialize Redis cache manager
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            ttl_hours: Time to live for cache entries in hours
            password: Redis password if required
        """
        self.ttl_seconds = ttl_hours * 3600
        
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            self.redis_client.ping()
            self.connected = True
        except (redis.ConnectionError, redis.TimeoutError):
            print("⚠️ Redis not available, cache disabled")
            self.connected = False
    
    def _generate_cache_key(self, query, llm_model=None):
        """Generate unique cache key for query"""
        normalized_query = query.lower().strip()
        cache_input = f"{normalized_query}:{llm_model}" if llm_model else normalized_query
        hash_key = hashlib.md5(cache_input.encode()).hexdigest()
        return f"rag:query:{hash_key}"
    
    def get(self, query, llm_model=None):
        """
        Get cached response for query
        
        Returns:
            dict or None: Cached response if exists
        """
        if not self.connected:
            return None
            
        try:
            cache_key = self._generate_cache_key(query, llm_model)
            
            # Get cached response
            cached_json = self.redis_client.get(cache_key)
            if not cached_json:
                return None
            
            # Increment hit counter
            hit_key = f"{cache_key}:hits"
            hit_count = self.redis_client.incr(hit_key)
            
            # Update access time
            self.redis_client.zadd(
                "rag:recent_queries", 
                {query: datetime.now().timestamp()}
            )
            
            # Parse response
            response = json.loads(cached_json)
            
            # Add cache metadata
            response['_cache_hit'] = True
            response['_cache_type'] = 'redis'
            response['_hit_count'] = hit_count
            
            # Update TTL on access (refresh expiry)
            self.redis_client.expire(cache_key, self.ttl_seconds)
            self.redis_client.expire(hit_key, self.ttl_seconds)
            
            return response
            
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    
    def set(self, query, response, llm_model=None):
        """
        Cache query response
        
        Args:
            query: Original query
            response: Response data to cache
            llm_model: LLM model used
        """
        if not self.connected:
            return False
            
        try:
            cache_key = self._generate_cache_key(query, llm_model)
            
            # Store response with TTL
            response_json = json.dumps(response, ensure_ascii=False)
            self.redis_client.setex(
                cache_key,
                self.ttl_seconds,
                response_json
            )
            
            # Store metadata
            metadata_key = f"{cache_key}:metadata"
            metadata = {
                'query': query,
                'llm_model': llm_model,
                'created_at': datetime.now().isoformat(),
                'ttl_hours': self.ttl_seconds / 3600
            }
            self.redis_client.hset(
                metadata_key,
                mapping=metadata
            )
            self.redis_client.expire(metadata_key, self.ttl_seconds)
            
            # Initialize hit counter
            hit_key = f"{cache_key}:hits"
            self.redis_client.set(hit_key, 0)
            self.redis_client.expire(hit_key, self.ttl_seconds)
            
            # Add to popular queries sorted set
            self.redis_client.zadd(
                "rag:popular_queries",
                {query: 0}
            )
            
            # Add to recent queries
            self.redis_client.zadd(
                "rag:recent_queries",
                {query: datetime.now().timestamp()}
            )
            
            # Keep only top 1000 queries
            self.redis_client.zremrangebyrank("rag:popular_queries", 0, -1001)
            self.redis_client.zremrangebyrank("rag:recent_queries", 0, -1001)
            
            return True
            
        except Exception as e:
            print(f"Redis set error: {e}")
            return False
    
    def clear_all(self):
        """Clear all cache entries"""
        if not self.connected:
            return 0
            
        try:
            # Get all RAG cache keys
            keys = self.redis_client.keys("rag:*")
            if keys:
                deleted = self.redis_client.delete(*keys)
                return deleted
            return 0
            
        except Exception as e:
            print(f"Redis clear error: {e}")
            return 0
    
    def get_stats(self):
        """Get cache statistics"""
        if not self.connected:
            return {
                'connected': False,
                'error': 'Redis not available'
            }
            
        try:
            # Get all cache keys
            query_keys = self.redis_client.keys("rag:query:*")
            query_keys = [k for k in query_keys if not k.endswith((':hits', ':metadata'))]
            
            total_entries = len(query_keys)
            
            # Calculate total hits
            total_hits = 0
            for key in query_keys:
                hit_key = f"{key}:hits"
                hits = self.redis_client.get(hit_key)
                if hits:
                    total_hits += int(hits)
            
            # Get popular queries
            popular = self.redis_client.zrevrange(
                "rag:popular_queries", 
                0, 9, 
                withscores=True
            )
            
            # Get recent queries
            recent = self.redis_client.zrevrange(
                "rag:recent_queries",
                0, 4,
                withscores=True
            )
            
            # Get memory usage (approximate)
            info = self.redis_client.info('memory')
            memory_mb = round(info.get('used_memory', 0) / 1024 / 1024, 2)
            
            return {
                'connected': True,
                'total_entries': total_entries,
                'total_hits': total_hits,
                'memory_usage_mb': memory_mb,
                'top_queries': [
                    {'query': q, 'score': int(s)} 
                    for q, s in popular
                ],
                'recent_queries': [
                    {'query': q, 'timestamp': datetime.fromtimestamp(s).isoformat()} 
                    for q, s in recent
                ]
            }
            
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def get_popular_queries(self, limit=5):
        """Get most popular cached queries"""
        if not self.connected:
            return []
            
        try:
            popular = self.redis_client.zrevrange(
                "rag:popular_queries",
                0,
                limit - 1,
                withscores=True
            )
            
            results = []
            for query, score in popular:
                # Get hit count
                cache_key = self._generate_cache_key(query)
                hit_key = f"{cache_key}:hits"
                hits = self.redis_client.get(hit_key)
                
                results.append({
                    'query': query,
                    'hits': int(hits) if hits else 0
                })
            
            return results
            
        except Exception as e:
            print(f"Redis popular queries error: {e}")
            return []
    
    def is_connected(self):
        """Check if Redis is connected"""
        if not self.connected:
            return False
            
        try:
            self.redis_client.ping()
            return True
        except:
            self.connected = False
            return False