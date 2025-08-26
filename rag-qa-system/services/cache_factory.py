from services.cache_manager import CacheManager as SQLiteCacheManager
# from services.redis_cache_manager import RedisCacheManager  
from services.hybrid_cache_manager import HybridCacheManager
# from services.admin_config import AdminConfig

class CacheFactory:
    """Factory to create appropriate cache manager based on configuration"""
    
    _instance = None
    _cache_manager = None
    
    @classmethod
    def get_cache_manager(cls, force_reload=False):
        """
        Get cache manager instance - now always returns HybridCacheManager
        
        Args:
            force_reload: Force reload configuration and recreate cache manager
            
        Returns:
            HybridCacheManager instance (Redis + RDB)
        """
        if cls._cache_manager is None or force_reload:
            # Always use hybrid cache system
            cache_config = {}
            
            # Get popular threshold from config (default 5)
            popular_threshold = cache_config.get('popular_threshold', 5)
            
            try:
                cls._cache_manager = HybridCacheManager(
                    popular_threshold=popular_threshold
                )
                print("✅ Using Hybrid Cache System (Redis + RDB)")
                print(f"   - Redis TTL: 24시간")
                print(f"   - 인기 질문 기준: {popular_threshold}회 이상")
                print(f"   - 문서 변경 감지: 24시간 간격")
                
            except Exception as e:
                # Fallback to SQLite only
                print(f"⚠️ Hybrid cache error: {e}, falling back to SQLite only")
                cls._cache_manager = SQLiteCacheManager(
                    ttl_hours=cache_config.get('ttl_hours', 24)
                )
                print("✅ Using SQLite cache (fallback)")
        
        return cls._cache_manager
    
    @classmethod
    def get_cache_type(cls):
        """Get current cache type being used"""
        if cls._cache_manager is None:
            cls.get_cache_manager()
        
        if isinstance(cls._cache_manager, HybridCacheManager):
            return 'hybrid'
        # elif isinstance(cls._cache_manager, RedisCacheManager):
        #     return 'redis'
        else:
            return 'sqlite'
    
    @classmethod
    def reload_cache_manager(cls):
        """Reload cache manager with new configuration"""
        cls._cache_manager = None
        return cls.get_cache_manager(force_reload=True)
    
    @classmethod
    def validate_documents_now(cls):
        """수동으로 문서 검증 실행"""
        cache_manager = cls.get_cache_manager()
        if isinstance(cache_manager, HybridCacheManager):
            return cache_manager.validate_documents()
        else:
            return {'error': 'Hybrid cache not available'}