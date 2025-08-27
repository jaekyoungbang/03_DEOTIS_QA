"""
Redis 기반 캐시 매니저
- 70% 이상 유사도 결과 캐싱
- 5회 이상 검색 시 MySQL 인기 질문 저장
- 애플리케이션 시작 시 캐시 초기화
"""

import json
import redis
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import time
from .enhanced_logger import get_enhanced_logger

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger()

class RedisCacheManager:
    """Redis 캐시 관리자"""
    
    def __init__(self, host='localhost', port=6379, db=0):
        """Redis 연결 초기화"""
        try:
            self.redis_client = redis.Redis(
                host=host, 
                port=port, 
                db=db, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 연결 테스트
            start_time = time.time()
            self.redis_client.ping()
            duration = time.time() - start_time
            
            enhanced_logger.system_operation(
                "INIT", "REDIS", "SUCCESS", 
                details={
                    "host": f"{host}:{port}",
                    "database": db,
                    "connection_time": f"{duration:.3f}s"
                }
            )
        except Exception as e:
            enhanced_logger.system_operation(
                "INIT", "REDIS", "FAILED", 
                error=str(e)
            )
            self.redis_client = None
    
    def is_connected(self) -> bool:
        """Redis 연결 상태 확인"""
        if self.redis_client is None:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def _generate_cache_key(self, query: str) -> str:
        """쿼리를 기반으로 캐시 키 생성"""
        # 쿼리를 정규화하여 해시 생성
        normalized_query = query.strip().lower().replace(" ", "")
        hash_key = hashlib.md5(normalized_query.encode('utf-8')).hexdigest()
        return f"qa_cache:{hash_key}"
    
    def _generate_count_key(self, query: str) -> str:
        """검색 횟수 카운트 키 생성"""
        normalized_query = query.strip().lower().replace(" ", "")
        hash_key = hashlib.md5(normalized_query.encode('utf-8')).hexdigest()
        return f"qa_count:{hash_key}"
    
    def get_cached_result(self, query: str) -> Optional[Dict]:
        """캐시된 결과 조회"""
        if not self.is_connected():
            return None
            
        try:
            start_time = time.time()
            cache_key = self._generate_cache_key(query)
            cached_data = self.redis_client.get(cache_key)
            duration = time.time() - start_time
            
            if cached_data:
                data = json.loads(cached_data)
                # 조회 시간 업데이트
                data['last_accessed'] = datetime.now().isoformat()
                
                enhanced_logger.redis_operation(
                    "HIT", query, result=data, duration=duration
                )
                
                # 정형화된 박스 로그 추가
                enhanced_logger.redis_data_box("CACHE HIT", query, {
                    'cached_at': data.get('cached_at', 'Unknown'),
                    'similarity_score': data.get('similarity_score', 0),
                    'duration': duration,
                    'access_count': data.get('access_count', 1)
                })
                return data
            else:
                enhanced_logger.redis_operation(
                    "MISS", query, duration=duration
                )
                return None
            
        except Exception as e:
            enhanced_logger.redis_operation(
                "GET", query, error=str(e)
            )
            return None
    
    def cache_result(self, query: str, result_data: Dict, similarity_score: float) -> bool:
        """결과를 캐시에 저장 (70% 이상만)"""
        if not self.is_connected():
            return False
            
        if similarity_score < 0.70:
            enhanced_logger.redis_operation(
                "SKIP", query, 
                result={'reason': 'Low similarity', 'similarity': similarity_score}
            )
            return False
            
        try:
            start_time = time.time()
            cache_key = self._generate_cache_key(query)
            
            # 캐시 데이터 구성
            cache_data = {
                'query': query,
                'result': result_data,
                'similarity_score': similarity_score,
                'cached_at': datetime.now().isoformat(),
                'last_accessed': datetime.now().isoformat(),
                'access_count': 1
            }
            
            # 1시간 TTL로 캐시 저장
            self.redis_client.setex(
                cache_key, 
                timedelta(hours=1), 
                json.dumps(cache_data, ensure_ascii=False)
            )
            
            duration = time.time() - start_time
            
            enhanced_logger.redis_operation(
                "SET", query, 
                result={'similarity_score': similarity_score, 'ttl': '1 hour'}, 
                duration=duration
            )
            
            # 정형화된 박스 로그 추가
            enhanced_logger.redis_data_box("CACHE SET", query, {
                'similarity_score': similarity_score,
                'ttl': '1 hour',
                'duration': duration,
                'current_count': 1
            })
            
            # 검색 횟수 증가
            self._increment_search_count(query)
            
            return True
            
        except Exception as e:
            enhanced_logger.redis_operation(
                "SET", query, error=str(e)
            )
            return False
    
    def _increment_search_count(self, query: str) -> int:
        """검색 횟수 증가"""
        if not self.is_connected():
            return 0
            
        try:
            count_key = self._generate_count_key(query)
            current_count = self.redis_client.incr(count_key)
            
            # 카운트 키도 1시간 TTL 설정
            if current_count == 1:  # 처음 생성된 경우
                self.redis_client.expire(count_key, timedelta(hours=1))
            
            enhanced_logger.redis_operation(
                "COUNT", query, 
                result={'current_count': current_count, 'ttl': '1 hour'}
            )
            
            # 중요한 임계값에서만 박스 로그 표시
            if current_count >= 5 or current_count == 3:
                enhanced_logger.redis_data_box("SEARCH COUNT", query, {
                    'current_count': current_count,
                    'ttl': '1 hour',
                    'status': 'Popular Threshold Reached!' if current_count >= 5 else 'Getting Popular'
                })
            
            return current_count
            
        except Exception as e:
            enhanced_logger.redis_operation(
                "COUNT", query, error=str(e)
            )
            return 0
    
    def get_search_count(self, query: str) -> int:
        """검색 횟수 조회"""
        if not self.is_connected():
            return 0
            
        try:
            count_key = self._generate_count_key(query)
            count = self.redis_client.get(count_key)
            return int(count) if count else 0
            
        except Exception as e:
            logger.error(f"검색 횟수 조회 오류: {e}")
            return 0
    
    def get_popular_queries(self, limit: int = 10) -> List[Dict]:
        """인기 질문 목록 조회"""
        if not self.is_connected():
            return []
            
        try:
            # 모든 카운트 키 조회
            count_keys = self.redis_client.keys("qa_count:*")
            popular_queries = []
            
            for key in count_keys:
                count = int(self.redis_client.get(key) or 0)
                if count >= 5:  # 5회 이상만
                    # 원본 쿼리를 캐시에서 찾기
                    hash_part = key.replace("qa_count:", "")
                    cache_key = f"qa_cache:{hash_part}"
                    cached_data = self.redis_client.get(cache_key)
                    
                    if cached_data:
                        data = json.loads(cached_data)
                        popular_queries.append({
                            'query': data['query'],
                            'count': count,
                            'last_searched': data['last_accessed']
                        })
            
            # 검색 횟수 기준으로 정렬
            popular_queries.sort(key=lambda x: x['count'], reverse=True)
            return popular_queries[:limit]
            
        except Exception as e:
            logger.error(f"인기 질문 조회 오류: {e}")
            return []
    
    def clear_cache(self) -> bool:
        """전체 캐시 초기화"""
        if not self.is_connected():
            enhanced_logger.system_operation(
                "CLEAR", "REDIS", "SKIPPED", 
                error="Redis not connected"
            )
            return False
            
        try:
            start_time = time.time()
            # 모든 캐시 키 삭제
            cache_keys = self.redis_client.keys("qa_cache:*")
            count_keys = self.redis_client.keys("qa_count:*")
            
            all_keys = cache_keys + count_keys
            if all_keys:
                deleted_count = self.redis_client.delete(*all_keys)
                duration = time.time() - start_time
                
                enhanced_logger.system_operation(
                    "CLEAR", "REDIS", "SUCCESS",
                    details={
                        "deleted_keys": deleted_count,
                        "cache_keys": len(cache_keys),
                        "count_keys": len(count_keys),
                        "duration": f"{duration:.3f}s"
                    }
                )
            else:
                enhanced_logger.system_operation(
                    "CLEAR", "REDIS", "EMPTY",
                    details={"message": "Cache already empty"}
                )
                
            return True
            
        except Exception as e:
            enhanced_logger.system_operation(
                "CLEAR", "REDIS", "FAILED", error=str(e)
            )
            return False
    
    def get_cache_stats(self) -> Dict:
        """캐시 통계 정보"""
        if not self.is_connected():
            return {'connected': False}
            
        try:
            start_time = time.time()
            cache_keys = self.redis_client.keys("qa_cache:*")
            count_keys = self.redis_client.keys("qa_count:*")
            
            total_cached = len(cache_keys)
            total_searches = 0
            popular_count = 0
            
            for key in count_keys:
                count = int(self.redis_client.get(key) or 0)
                total_searches += count
                if count >= 5:
                    popular_count += 1
            
            duration = time.time() - start_time
            
            stats = {
                'connected': True,
                'cached_queries': total_cached,
                'total_searches': total_searches,
                'popular_queries': popular_count
            }
            
            enhanced_logger.redis_operation(
                "STATS", "Cache Statistics", 
                result=stats, duration=duration
            )
            
            return stats
            
        except Exception as e:
            enhanced_logger.redis_operation(
                "STATS", "Cache Statistics", error=str(e)
            )
            return {'connected': False, 'error': str(e)}