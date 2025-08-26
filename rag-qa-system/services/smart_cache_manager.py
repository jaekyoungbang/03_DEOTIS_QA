import redis
import sqlite3
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import os

class SmartCacheManager:
    """스마트 캐싱 전략: 1-5회는 Redis, 5회 이상은 RDB"""
    
    def __init__(self):
        # Redis 설정
        try:
            self.redis_client = redis.Redis(
                host='localhost', 
                port=6379, 
                db=2,  # 캐시 전용 DB
                decode_responses=True
            )
            self.redis_client.ping()
            self.redis_available = True
        except:
            self.redis_client = None
            self.redis_available = False
            print("⚠️ Redis가 사용 불가능합니다. 파일 기반 캐시를 사용합니다.")
        
        # SQLite RDB 설정
        self.db_path = "./data/smart_cache.db"
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_database()
        
        # 캐시 설정
        self.redis_ttl = 3600  # 1시간
        self.rdb_ttl = 86400 * 7  # 7일
        self.promotion_threshold = 5  # 5회 이상 시 RDB 승격
    
    def init_database(self):
        """SQLite 데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 캐시 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    access_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # 인덱스 생성
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_access_count ON cache_entries(access_count)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache_entries(last_accessed)')
            
            conn.commit()
    
    def _generate_cache_key(self, question: str, **kwargs) -> str:
        """캐시 키 생성"""
        # 질문과 추가 파라미터를 결합하여 해시 생성
        key_data = {
            'question': question.lower().strip(),
            **kwargs
        }
        
        key_string = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def get(self, question: str, **kwargs) -> Optional[Dict[str, Any]]:
        """캐시에서 데이터 조회 (스마트 전략)"""
        cache_key = self._generate_cache_key(question, **kwargs)
        
        # 1. Redis에서 먼저 조회 (빠른 캐시)
        if self.redis_available:
            redis_data = self._get_from_redis(cache_key)
            if redis_data:
                # 접근 횟수 증가
                self._increment_access_count(cache_key)
                return redis_data
        
        # 2. RDB에서 조회 (영구 캐시)
        rdb_data = self._get_from_rdb(cache_key)
        if rdb_data:
            # 접근 횟수 증가
            self._increment_access_count(cache_key)
            
            # 자주 사용되는 데이터면 Redis에도 캐시
            if rdb_data.get('_cache_metadata', {}).get('access_count', 0) >= 2:
                self._set_to_redis(cache_key, rdb_data)
            
            return rdb_data
        
        return None
    
    def set(self, question: str, data: Dict[str, Any], **kwargs) -> bool:
        """캐시에 데이터 저장"""
        cache_key = self._generate_cache_key(question, **kwargs)
        
        # 메타데이터 추가
        cached_data = {
            **data,
            '_cache_metadata': {
                'cached_at': datetime.now().isoformat(),
                'cache_key': cache_key,
                'question': question,
                'access_count': 1
            }
        }
        
        # 1. Redis에 저장 (1회차)
        redis_success = self._set_to_redis(cache_key, cached_data)
        
        # 2. RDB에도 기록 (추적용)
        rdb_success = self._track_in_rdb(cache_key, cached_data, question)
        
        return redis_success or rdb_success
    
    def _get_from_redis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Redis에서 데이터 조회"""
        if not self.redis_available:
            return None
        
        try:
            data = self.redis_client.get(f"cache:{cache_key}")
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"Redis 조회 오류: {e}")
        
        return None
    
    def _set_to_redis(self, cache_key: str, data: Dict[str, Any]) -> bool:
        """Redis에 데이터 저장"""
        if not self.redis_available:
            return False
        
        try:
            self.redis_client.setex(
                f"cache:{cache_key}",
                self.redis_ttl,
                json.dumps(data, ensure_ascii=False)
            )
            return True
        except Exception as e:
            print(f"Redis 저장 오류: {e}")
            return False
    
    def _get_from_rdb(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """RDB에서 데이터 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT content, access_count, metadata 
                    FROM cache_entries 
                    WHERE cache_key = ? AND (expires_at IS NULL OR expires_at > ?)
                ''', (cache_key, datetime.now()))
                
                result = cursor.fetchone()
                if result:
                    content_str, access_count, metadata_str = result
                    
                    try:
                        data = json.loads(content_str)
                        
                        # 메타데이터 업데이트
                        if '_cache_metadata' not in data:
                            data['_cache_metadata'] = {}
                        
                        data['_cache_metadata'].update({
                            'access_count': access_count,
                            'source': 'rdb_cache'
                        })
                        
                        return data
                    except json.JSONDecodeError:
                        return None
        except Exception as e:
            print(f"RDB 조회 오류: {e}")
        
        return None
    
    def _track_in_rdb(self, cache_key: str, data: Dict[str, Any], question: str) -> bool:
        """RDB에 캐시 정보 추적 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 기존 항목 확인
                cursor.execute('SELECT cache_key FROM cache_entries WHERE cache_key = ?', (cache_key,))
                exists = cursor.fetchone() is not None
                
                if exists:
                    # 업데이트
                    cursor.execute('''
                        UPDATE cache_entries 
                        SET content = ?, updated_at = CURRENT_TIMESTAMP,
                            last_accessed = CURRENT_TIMESTAMP
                        WHERE cache_key = ?
                    ''', (json.dumps(data, ensure_ascii=False), cache_key))
                else:
                    # 새로 삽입
                    expires_at = datetime.now() + timedelta(seconds=self.rdb_ttl)
                    
                    cursor.execute('''
                        INSERT INTO cache_entries 
                        (cache_key, content, expires_at, metadata)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        cache_key, 
                        json.dumps(data, ensure_ascii=False),
                        expires_at,
                        json.dumps({'question': question}, ensure_ascii=False)
                    ))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"RDB 추적 오류: {e}")
            return False
    
    def _increment_access_count(self, cache_key: str):
        """접근 횟수 증가 및 승격 처리"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 접근 횟수 증가
                cursor.execute('''
                    UPDATE cache_entries 
                    SET access_count = access_count + 1,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE cache_key = ?
                ''', (cache_key,))
                
                # 현재 접근 횟수 확인
                cursor.execute('SELECT access_count FROM cache_entries WHERE cache_key = ?', (cache_key,))
                result = cursor.fetchone()
                
                if result and result[0] >= self.promotion_threshold:
                    # 5회 이상 접근 시 RDB에 영구 저장
                    self._promote_to_rdb(cache_key)
                
                conn.commit()
        except Exception as e:
            print(f"접근 횟수 업데이트 오류: {e}")
    
    def _promote_to_rdb(self, cache_key: str):
        """자주 사용되는 캐시를 RDB로 승격"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 만료일을 더 길게 연장
                new_expires_at = datetime.now() + timedelta(days=30)  # 30일
                
                cursor.execute('''
                    UPDATE cache_entries 
                    SET expires_at = ?
                    WHERE cache_key = ?
                ''', (new_expires_at, cache_key))
                
                conn.commit()
                print(f"🎯 인기 캐시 승격: {cache_key}")
        except Exception as e:
            print(f"RDB 승격 오류: {e}")
    
    def clear_expired(self) -> Dict[str, int]:
        """만료된 캐시 정리"""
        cleared_count = 0
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 만료된 항목 삭제
                cursor.execute('''
                    DELETE FROM cache_entries 
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                ''', (datetime.now(),))
                
                cleared_count = cursor.rowcount
                conn.commit()
        except Exception as e:
            print(f"만료된 캐시 정리 오류: {e}")
        
        return {
            'rdb_cleared': cleared_count,
            'redis_cleared': 0  # Redis는 자동 만료
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        stats = {
            'redis_available': self.redis_available,
            'redis_keys': 0,
            'rdb_entries': 0,
            'popular_entries': 0,
            'total_access': 0
        }
        
        # Redis 통계
        if self.redis_available:
            try:
                stats['redis_keys'] = len(self.redis_client.keys("cache:*"))
            except:
                pass
        
        # RDB 통계
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 전체 항목 수
                cursor.execute('SELECT COUNT(*) FROM cache_entries')
                stats['rdb_entries'] = cursor.fetchone()[0]
                
                # 인기 항목 수 (5회 이상)
                cursor.execute('SELECT COUNT(*) FROM cache_entries WHERE access_count >= ?', 
                             (self.promotion_threshold,))
                stats['popular_entries'] = cursor.fetchone()[0]
                
                # 총 접근 횟수
                cursor.execute('SELECT SUM(access_count) FROM cache_entries')
                result = cursor.fetchone()
                stats['total_access'] = result[0] if result[0] else 0
                
        except Exception as e:
            print(f"캐시 통계 조회 오류: {e}")
        
        return stats
    
    def clear_all_cache(self) -> Dict[str, int]:
        """모든 캐시 삭제"""
        redis_cleared = 0
        rdb_cleared = 0
        
        # Redis 삭제
        if self.redis_available:
            try:
                keys = self.redis_client.keys("cache:*")
                if keys:
                    redis_cleared = self.redis_client.delete(*keys)
            except Exception as e:
                print(f"Redis 캐시 삭제 오류: {e}")
        
        # RDB 삭제
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM cache_entries')
                rdb_cleared = cursor.fetchone()[0]
                cursor.execute('DELETE FROM cache_entries')
                conn.commit()
        except Exception as e:
            print(f"RDB 캐시 삭제 오류: {e}")
        
        return {
            'redis_cleared': redis_cleared,
            'rdb_cleared': rdb_cleared
        }