import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
import os

class CacheManager:
    def __init__(self, cache_db_path='data/cache/query_cache.db', ttl_hours=24):
        """
        Initialize cache manager with SQLite backend
        
        Args:
            cache_db_path: Path to cache database
            ttl_hours: Time to live for cache entries in hours
        """
        self.cache_db_path = cache_db_path
        self.ttl_hours = ttl_hours
        
        # Create cache directory if it doesn't exist
        os.makedirs(os.path.dirname(cache_db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize cache database"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        # Create cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS query_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                similarity_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hit_count INTEGER DEFAULT 0,
                llm_model TEXT,
                vector_count INTEGER
            )
        ''')
        
        # Create index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON query_cache(created_at)
        ''')
        
        conn.commit()
        conn.close()
    
    def _generate_cache_key(self, query, llm_model=None):
        """Generate unique cache key for query"""
        # Normalize query for better cache hits
        normalized_query = query.lower().strip()
        
        # Include model in cache key if specified
        cache_input = f"{normalized_query}:{llm_model}" if llm_model else normalized_query
        
        # Create hash
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def get(self, query, llm_model=None):
        """
        Get cached response for query
        
        Returns:
            dict or None: Cached response if exists and not expired
        """
        cache_key = self._generate_cache_key(query, llm_model)
        
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        # Get cache entry
        cursor.execute('''
            SELECT response, similarity_data, created_at, hit_count
            FROM query_cache
            WHERE query_hash = ?
        ''', (cache_key,))
        
        result = cursor.fetchone()
        
        if result:
            response_json, similarity_json, created_at, hit_count = result
            
            # Check if cache is expired
            created_time = datetime.fromisoformat(created_at)
            if datetime.now() - created_time > timedelta(hours=self.ttl_hours):
                # Cache expired, delete it
                cursor.execute('DELETE FROM query_cache WHERE query_hash = ?', (cache_key,))
                conn.commit()
                conn.close()
                return None
            
            # Update hit count and access time
            cursor.execute('''
                UPDATE query_cache 
                SET hit_count = ?, accessed_at = CURRENT_TIMESTAMP
                WHERE query_hash = ?
            ''', (hit_count + 1, cache_key))
            conn.commit()
            conn.close()
            
            # Parse and return cached data
            response = json.loads(response_json)
            if similarity_json:
                response['similarity_search'] = json.loads(similarity_json)
            
            # Add cache metadata
            response['_cache_hit'] = True
            response['_cache_created'] = created_at
            response['_hit_count'] = hit_count + 1
            
            return response
        
        conn.close()
        return None
    
    def set(self, query, response, llm_model=None):
        """
        Cache query response
        
        Args:
            query: Original query
            response: Response data to cache
            llm_model: LLM model used
        """
        cache_key = self._generate_cache_key(query, llm_model)
        
        # Separate similarity data if exists
        similarity_data = response.get('similarity_search')
        
        # Prepare response for caching (remove similarity for main response)
        cache_response = {k: v for k, v in response.items() if k != 'similarity_search'}
        
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        # Insert or replace cache entry
        cursor.execute('''
            INSERT OR REPLACE INTO query_cache 
            (query_hash, query, response, similarity_data, llm_model, vector_count)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            cache_key,
            query,
            json.dumps(cache_response, ensure_ascii=False),
            json.dumps(similarity_data, ensure_ascii=False) if similarity_data else None,
            llm_model,
            len(similarity_data.get('top_matches', [])) if similarity_data else 0
        ))
        
        conn.commit()
        conn.close()
    
    def clear_expired(self):
        """Clear expired cache entries"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        expiry_time = datetime.now() - timedelta(hours=self.ttl_hours)
        
        cursor.execute('''
            DELETE FROM query_cache
            WHERE created_at < ?
        ''', (expiry_time.isoformat(),))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def clear_all(self):
        """Clear all cache entries"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM query_cache')
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def get_stats(self):
        """Get cache statistics"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        # Total cache entries
        cursor.execute('SELECT COUNT(*) FROM query_cache')
        total_entries = cursor.fetchone()[0]
        
        # Total hits
        cursor.execute('SELECT SUM(hit_count) FROM query_cache')
        total_hits = cursor.fetchone()[0] or 0
        
        # Most frequently accessed
        cursor.execute('''
            SELECT query, hit_count, created_at
            FROM query_cache
            ORDER BY hit_count DESC
            LIMIT 10
        ''')
        top_queries = cursor.fetchall()
        
        # Cache size
        cursor.execute('''
            SELECT SUM(LENGTH(response) + LENGTH(COALESCE(similarity_data, '')))
            FROM query_cache
        ''')
        cache_size_bytes = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_entries': total_entries,
            'total_hits': total_hits,
            'cache_size_mb': round(cache_size_bytes / 1024 / 1024, 2),
            'top_queries': [
                {
                    'query': q[0],
                    'hits': q[1],
                    'created': q[2]
                } for q in top_queries
            ]
        }
    
    def get_popular_queries(self, limit=5):
        """Get most popular cached queries"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT query, hit_count
            FROM query_cache
            WHERE hit_count > 0
            ORDER BY hit_count DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{'query': q[0], 'hits': q[1]} for q in results]