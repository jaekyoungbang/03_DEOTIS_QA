import sqlite3
import redis
import json
import hashlib
from datetime import datetime, timedelta
import os
import threading
import time
from services.cache_manager import CacheManager as SQLiteCacheManager
# from services.redis_cache_manager import RedisCacheManager

class HybridCacheManager:
    """
    하이브리드 캐시 시스템:
    1. Redis: 임시 캐시 (24시간)
    2. RDB: 인기 질문 영구 저장 (5회 이상 조회)
    3. 문서 변경 감지: 매일 RDB 내용 검증
    """
    
    def __init__(self, popular_threshold=5):
        self.popular_threshold = popular_threshold
        
        # Redis cache (temporary) - gracefully handle connection failures
        # Redis disabled - using dummy cache
        print(f"⚠️ Redis disabled - using SQLite only")
        # Create a dummy cache manager to avoid errors
        class DummyCache:
            def __init__(self):
                self.connected = False
            def get(self, *args, **kwargs):
                return None
            def set(self, *args, **kwargs):
                return False
            def clear_all(self):
                return 0
            def get_stats(self):
                return {'connected': False, 'error': 'Redis disabled'}
        self.redis_cache = DummyCache()
        
        # SQLite cache for popular queries (permanent)
        self.popular_cache_db_path = 'data/cache/popular_cache.db'
        self.init_popular_cache_db()
        
        # 기존 SQLiteCacheManager는 query_cache 테이블을 생성하므로 사용하지 않음
        self.popular_cache = SQLiteCacheManager(
            cache_db_path='data/cache/popular_cache.db',
            ttl_hours=24*365  # 1년 (실질적으로 영구)
        )
        
        # Document validation DB
        self.validation_db_path = 'data/cache/document_validation.db'
        self.init_validation_db()
        
        # Start background validation thread
        self.start_validation_thread()
        
        # Start daily cleanup thread
        self.start_daily_cleanup_thread()
    
    def init_popular_cache_db(self):
        """인기 질문 DB 초기화 - popular_questions 테이블 생성"""
        os.makedirs(os.path.dirname(self.popular_cache_db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.popular_cache_db_path)
        cursor = conn.cursor()
        
        # popular_questions 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS popular_questions (
                query_hash TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                similarity_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hit_count INTEGER DEFAULT 5,
                llm_model TEXT,
                vector_count INTEGER
            )
        ''')
        
        # 인덱스 생성
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_hit_count 
            ON popular_questions(hit_count DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_last_accessed 
            ON popular_questions(last_accessed)
        ''')
        
        conn.commit()
        conn.close()
        print("✅ popular_questions 테이블 초기화 완료")
    
    def init_validation_db(self):
        """문서 검증용 DB 초기화"""
        os.makedirs(os.path.dirname(self.validation_db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.validation_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_checksums (
                document_id TEXT PRIMARY KEY,
                document_path TEXT,
                checksum TEXT,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS validation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                validation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                documents_checked INTEGER,
                changes_detected INTEGER,
                cache_cleared INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get(self, query, llm_model=None):
        """
        캐시에서 응답 조회 - 검색 횟수 추적
        1. 검색 횟수 증가 (전체 카운팅)
        2. RDB (인기 질문) 확인 - 5회 이상
        3. Redis 확인 - 1~4회
        4. 둘 다 없으면 None 반환 (RAG 검색 필요)
        """
        # 검색 횟수 증가 (전체 카운팅)
        search_count = self._increment_search_count(query, llm_model)
        
        # 1. RDB 인기 질문 확인 (5회 이상)
        popular_result = self._get_from_popular_db(query, llm_model)
        if popular_result:
            self._increment_popular_hit_count(query, llm_model)
            popular_result['_from_cache'] = True
            popular_result['_cache_source'] = 'RDB'
            popular_result['_search_count'] = search_count
            popular_result['_note'] = f"RDB에서 응답 (총 {search_count}번째 검색)"
            print(f"🎯 RDB에서 응답: {query[:30]}... (총 {search_count}번째 검색)")
            return popular_result
        
        # 2. Redis 확인 (1~4회)
        if hasattr(self.redis_cache, 'connected') and self.redis_cache.connected:
            redis_result = self.redis_cache.get(query, llm_model)
            if redis_result:
                # Redis 조회수 증가
                redis_hit_count = self._increment_redis_hit_count(query, llm_model)
                
                # 5회가 되면 RDB로 이동
                if search_count >= self.popular_threshold:
                    self._promote_to_popular(query, redis_result, llm_model, search_count)
                    self._remove_from_redis(query, llm_model)
                    print(f"🔄 Redis → RDB 이동 완료: {query[:30]}... (5회 도달)")
                    
                    # RDB에서 다시 조회하여 반환
                    return self.get(query, llm_model)
                
                redis_result['_from_cache'] = True
                redis_result['_cache_source'] = 'Redis'
                redis_result['_search_count'] = search_count
                redis_result['_redis_hit_count'] = redis_hit_count
                redis_result['_note'] = f"Redis에서 응답 (총 {search_count}번째 검색)"
                print(f"⚡ Redis에서 응답: {query[:30]}... (총 {search_count}번째 검색)")
                return redis_result
        
        # 3. 캐시 없음 - RAG 검색 필요
        print(f"🔍 새로운 질문: {query[:30]}... ({search_count}번째 검색 - RAG에서 검색)")
        return None
    
    def _increment_search_count(self, query, llm_model):
        """질문별 전체 검색 횟수 증가"""
        try:
            cache_key = f"search_count:{self._generate_cache_key(query, llm_model)}"
            
            if hasattr(self.redis_cache, 'redis_client'):
                # Redis에서 카운터 증가
                current_count = self.redis_cache.redis_client.incr(cache_key)
                # 카운터에 TTL 설정 (30일)
                self.redis_cache.redis_client.expire(cache_key, 30 * 24 * 3600)
                return current_count
            else:
                # Redis 없으면 SQLite로 대체
                return self._increment_search_count_sqlite(query, llm_model)
                
        except Exception as e:
            print(f"⚠️ 검색 횟수 증가 오류: {e}")
            return 1
    
    def _increment_search_count_sqlite(self, query, llm_model):
        """SQLite를 사용한 검색 횟수 관리 (Redis 백업)"""
        try:
            cache_key = self._generate_cache_key(query, llm_model)
            
            conn = sqlite3.connect(self.popular_cache_db_path)
            cursor = conn.cursor()
            
            # search_counts 테이블 생성 (없으면)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_counts (
                    query_hash TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    search_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_searched TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 검색 횟수 증가 또는 새로 생성
            cursor.execute('''
                INSERT INTO search_counts (query_hash, question, search_count, last_searched)
                VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(query_hash) DO UPDATE SET
                    search_count = search_count + 1,
                    last_searched = CURRENT_TIMESTAMP
            ''', (cache_key, query))
            
            # 현재 카운트 조회
            cursor.execute('SELECT search_count FROM search_counts WHERE query_hash = ?', (cache_key,))
            result = cursor.fetchone()
            current_count = result[0] if result else 1
            
            conn.commit()
            conn.close()
            
            return current_count
            
        except Exception as e:
            print(f"⚠️ SQLite 검색 횟수 관리 오류: {e}")
            return 1
    
    def set(self, query, response, llm_model=None):
        """
        RAG 검색 결과 캐시에 저장 (첫 검색 시)
        - 응답에 RAG 검색 정보 추가
        - Redis에 저장 (1~4회차 검색용)
        """
        try:
            # 현재 검색 횟수 조회
            search_count = self._get_current_search_count(query, llm_model)
            
            # 응답에 RAG 검색 정보 추가
            if isinstance(response, dict):
                response['_from_cache'] = False
                response['_cache_source'] = 'RAG'
                response['_search_count'] = search_count
                response['_note'] = f"RAG에서 검색 (총 {search_count}번째 검색)"
            
            # 먼저 RDB에 있는지 확인 (이미 인기 질문인지)
            if self._get_from_popular_db(query, llm_model):
                print(f"ℹ️ 이미 인기 질문 RDB에 존재: {query[:30]}...")
                return True
            
            # Redis에 저장 (첫 저장은 항상 Redis)
            if hasattr(self.redis_cache, 'connected') and self.redis_cache.connected:
                success = self.redis_cache.set(query, response, llm_model)
                if success:
                    # Redis 조회수 1로 초기화
                    cache_key = self._generate_redis_hit_key(query, llm_model)
                    self.redis_cache.redis_client.setex(cache_key, 7*24*3600, 1)
                    print(f"📥 RAG 결과 Redis 저장: {query[:30]}... ({search_count}번째 검색)")
                return success
            else:
                # Redis가 없으면 SQLite 캐시에 저장 (Fallback)
                from services.cache_manager import CacheManager as SQLiteCacheManager
                sqlite_cache = SQLiteCacheManager(ttl_hours=24)
                success = sqlite_cache.set(query, response, llm_model)
                print(f"⚠️ Redis 불가능 - SQLite에 저장: {query[:30]}... ({search_count}번째 검색)")
                return success
                
        except Exception as e:
            print(f"⚠️ 캐시 저장 오류: {e}")
            return False
    
    def _get_current_search_count(self, query, llm_model):
        """현재 검색 횟수 조회 (증가 없이)"""
        try:
            cache_key = f"search_count:{self._generate_cache_key(query, llm_model)}"
            
            if hasattr(self.redis_cache, 'redis_client'):
                count = self.redis_cache.redis_client.get(cache_key)
                return int(count) if count else 1
            else:
                # SQLite에서 조회
                cache_key_hash = self._generate_cache_key(query, llm_model)
                conn = sqlite3.connect(self.popular_cache_db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT search_count FROM search_counts WHERE query_hash = ?', (cache_key_hash,))
                result = cursor.fetchone()
                conn.close()
                return result[0] if result else 1
                
        except Exception as e:
            print(f"⚠️ 검색 횟수 조회 오료: {e}")
            return 1
    
    def _increment_redis_hit_count(self, query, llm_model):
        """Redis에서 조회수 증가 및 새로운 조회수 반환"""
        try:
            cache_key = self._generate_redis_hit_key(query, llm_model)
            
            if hasattr(self.redis_cache, 'connected') and self.redis_cache.connected:
                # Redis에서 현재 조회수 가져오기
                current_hits = self.redis_cache.redis_client.get(cache_key)
                current_hits = int(current_hits) if current_hits else 0
                new_hits = current_hits + 1
                
                # 조회수 업데이트 (7일 TTL)
                self.redis_cache.redis_client.setex(cache_key, 7*24*3600, new_hits)
                
                print(f"🔄 Redis 조회수 증가: {query[:30]}... ({new_hits}회)")
                return new_hits
                    
        except Exception as e:
            print(f"⚠️ 조회수 처리 오류: {e}")
        return 1
    
    def _get_from_popular_db(self, query, llm_model):
        """popular_questions 테이블에서 직접 조회"""
        try:
            cache_key = self._generate_cache_key(query, llm_model)
            
            conn = sqlite3.connect(self.popular_cache_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT answer, similarity_data, hit_count 
                FROM popular_questions 
                WHERE query_hash = ?
            ''', (cache_key,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                answer, similarity_data, hit_count = result
                response = {'answer': answer}
                
                if similarity_data:
                    try:
                        response['similarity_search'] = json.loads(similarity_data)
                    except:
                        pass
                
                response['_hit_count'] = hit_count
                return response
                
        except Exception as e:
            print(f"⚠️ popular_questions 조회 오류: {e}")
        return None
    
    def _increment_popular_hit_count(self, query, llm_model):
        """인기 질문 DB 조회수 증가"""
        try:
            cache_key = self._generate_cache_key(query, llm_model)
            
            conn = sqlite3.connect(self.popular_cache_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE popular_questions 
                SET hit_count = hit_count + 1,
                    last_accessed = CURRENT_TIMESTAMP
                WHERE query_hash = ?
            ''', (cache_key,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ 인기 질문 조회수 증가 오류: {e}")
    
    def _generate_cache_key(self, query, llm_model):
        """캐시 키 생성"""
        normalized_query = query.lower().strip()
        cache_input = f"{normalized_query}:{llm_model}" if llm_model else normalized_query
        hash_key = hashlib.md5(cache_input.encode()).hexdigest()
        return hash_key
    
    def _generate_redis_hit_key(self, query, llm_model):
        """Redis 조회수 키 생성"""
        hash_key = self._generate_cache_key(query, llm_model)
        return f"rag:hits:{hash_key}"
    
    def _promote_to_popular(self, query, response, llm_model, hit_count):
        """Redis에서 인기 질문 DB로 승격"""
        try:
            # popular_questions 테이블에 직접 저장
            cache_key = self._generate_cache_key(query, llm_model)
            
            conn = sqlite3.connect(self.popular_cache_db_path)
            cursor = conn.cursor()
            
            # response가 dict인 경우 처리
            if isinstance(response, dict):
                answer = response.get('answer', '')
                similarity_data = json.dumps(response.get('similarity_search', {}))
                vector_count = response.get('similarity_search', {}).get('total_results', 0)
            else:
                answer = str(response)
                similarity_data = None
                vector_count = 0
            
            cursor.execute('''
                INSERT OR REPLACE INTO popular_questions 
                (query_hash, question, answer, similarity_data, hit_count, llm_model, vector_count, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (cache_key, query, answer, similarity_data, hit_count, llm_model, vector_count))
            
            conn.commit()
            conn.close()
            
            print(f"⭐ 인기 질문 승격: {query[:30]}... ({hit_count}회)")
            
        except Exception as e:
            print(f"⚠️ 인기 질문 승격 오류: {e}")
    
    def _remove_from_redis(self, query, llm_model):
        """Redis에서 질문과 조회수 모두 제거 (SQLite로 이동 후)"""
        try:
            if hasattr(self.redis_cache, 'connected') and self.redis_cache.connected:
                # 질문 캐시 삭제
                query_removed = self.redis_cache.delete(query, llm_model)
                
                # 조회수 삭제
                hit_key = self._generate_redis_hit_key(query, llm_model)
                hit_removed = self.redis_cache.redis_client.delete(hit_key)
                
                print(f"🗑️ Redis에서 삭제 완료: 질문={query_removed}, 조회수={hit_removed}")
                return query_removed or hit_removed
                
        except Exception as e:
            print(f"⚠️ Redis 제거 오류: {e}")
        return False
    
    def _old_increment_and_check_popularity(self, query, llm_model=None):
        """기존 조회수 증가 함수 (호환성)"""
        try:
            # Redis에서 조회수 증가 (Redis가 연결된 경우만)
            if self.redis_cache.connected:
                cache_key = self._generate_cache_key(query, llm_model)
                hit_key = f"{cache_key}:hits"
                
                hit_count = self.redis_cache.redis_client.get(hit_key)
                if hit_count and int(hit_count) >= self.popular_threshold:
                    # 인기 질문이 된 경우 RDB에 저장
                    self._promote_to_popular(query, llm_model)
                    
        except Exception as e:
            print(f"Error checking popularity: {e}")
    
    
    def _store_document_info(self, response):
        """응답에 포함된 문서 정보 저장"""
        try:
            source_docs = response.get('source_documents', [])
            
            conn = sqlite3.connect(self.validation_db_path)
            cursor = conn.cursor()
            
            for doc in source_docs:
                metadata = doc.get('metadata', {})
                doc_id = metadata.get('filename', metadata.get('title', 'unknown'))
                
                # 문서 체크섬 계산 (내용 기반)
                content = doc.get('content', '')
                checksum = hashlib.md5(content.encode()).hexdigest()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO document_checksums 
                    (document_id, checksum, last_checked)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (doc_id, checksum))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error storing document info: {e}")
    
    def validate_documents(self):
        """
        문서 변경 감지 및 캐시 무효화
        매일 실행되어 문서가 변경되었는지 확인
        """
        try:
            print("🔍 문서 변경 감지 시작...")
            
            from models.embeddings import EmbeddingManager
            from models.vectorstore import VectorStoreManager
            
            # 현재 벡터DB의 문서들 가져오기
            embedding_manager = EmbeddingManager()
            vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
            
            # 샘플 검색으로 현재 문서들 확인
            sample_docs = vectorstore_manager.similarity_search("test", k=50)
            
            conn = sqlite3.connect(self.validation_db_path)
            cursor = conn.cursor()
            
            changes_detected = 0
            documents_checked = 0
            
            for doc in sample_docs:
                metadata = doc.metadata
                doc_id = metadata.get('filename', metadata.get('title', 'unknown'))
                content = doc.page_content
                current_checksum = hashlib.md5(content.encode()).hexdigest()
                
                # 이전 체크섬과 비교
                cursor.execute('''
                    SELECT checksum FROM document_checksums 
                    WHERE document_id = ?
                ''', (doc_id,))
                
                result = cursor.fetchone()
                if result and result[0] != current_checksum:
                    changes_detected += 1
                    print(f"📝 문서 변경 감지: {doc_id}")
                    
                    # 체크섬 업데이트
                    cursor.execute('''
                        UPDATE document_checksums 
                        SET checksum = ?, last_checked = CURRENT_TIMESTAMP
                        WHERE document_id = ?
                    ''', (current_checksum, doc_id))
                
                documents_checked += 1
            
            # 변경이 감지되면 관련 캐시 무효화
            cache_cleared = 0
            if changes_detected > 0:
                print(f"⚠️ {changes_detected}개 문서 변경 감지 - 캐시 정리 중...")
                
                # Redis 캐시 전체 삭제
                self.redis_cache.clear_all()
                
                # 인기 질문 캐시도 무효화 (선택적)
                cache_cleared = self.popular_cache.clear_all()
                
                print(f"🧹 {cache_cleared}개 캐시 항목 삭제 완료")
            
            # 검증 로그 저장
            cursor.execute('''
                INSERT INTO validation_log 
                (documents_checked, changes_detected, cache_cleared)
                VALUES (?, ?, ?)
            ''', (documents_checked, changes_detected, cache_cleared))
            
            conn.commit()
            conn.close()
            
            print(f"✅ 문서 검증 완료: {documents_checked}개 확인, {changes_detected}개 변경")
            
            return {
                'documents_checked': documents_checked,
                'changes_detected': changes_detected,
                'cache_cleared': cache_cleared
            }
            
        except Exception as e:
            print(f"❌ 문서 검증 오류: {e}")
            return {'error': str(e)}
    
    def start_validation_thread(self):
        """백그라운드에서 매일 문서 검증 실행"""
        def validation_worker():
            while True:
                try:
                    # 24시간 대기
                    time.sleep(24 * 60 * 60)  # 24 hours
                    
                    # 문서 검증 실행
                    self.validate_documents()
                    
                except Exception as e:
                    print(f"Validation thread error: {e}")
                    # 오류 발생 시 1시간 후 재시도
                    time.sleep(60 * 60)
        
        validation_thread = threading.Thread(target=validation_worker, daemon=True)
        validation_thread.start()
        print("🕒 문서 검증 스레드 시작 (24시간 간격)")
    
    def get_stats(self):
        """캐시 통계 정보"""
        redis_stats = self.redis_cache.get_stats()
        popular_stats = self.popular_cache.get_stats()
        
        # 검증 로그 조회
        try:
            conn = sqlite3.connect(self.validation_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT validation_date, documents_checked, changes_detected, cache_cleared
                FROM validation_log 
                ORDER BY validation_date DESC 
                LIMIT 5
            ''')
            
            validation_history = cursor.fetchall()
            conn.close()
            
        except:
            validation_history = []
        
        return {
            'redis_cache': redis_stats,
            'popular_cache': popular_stats,
            'validation_history': [
                {
                    'date': row[0],
                    'checked': row[1],
                    'changes': row[2],
                    'cleared': row[3]
                } for row in validation_history
            ],
            'cache_strategy': {
                'redis_ttl': '24시간',
                'popular_threshold': f'{self.popular_threshold}회 이상',
                'validation_interval': '24시간'
            }
        }
    
    def clear_all(self):
        """모든 캐시 삭제 (Redis + RDB 전체)"""
        # Redis 캐시 삭제
        redis_cleared = self.redis_cache.clear_all()
        
        # RDB 캐시 삭제 (popular_questions 포함)
        popular_cleared = 0
        try:
            conn = sqlite3.connect(self.popular_cache_db_path)
            cursor = conn.cursor()
            
            # popular_questions 테이블 완전 삭제
            cursor.execute('DELETE FROM popular_questions')
            popular_cleared = cursor.rowcount
            
            # query_cache 테이블도 삭제 (있다면)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='query_cache'")
            if cursor.fetchone():
                cursor.execute('DELETE FROM query_cache')
                popular_cleared += cursor.rowcount
            
            conn.commit()
            conn.close()
            
            print(f"✅ RDB 전체 삭제 완료: {popular_cleared}개 항목")
            
        except Exception as e:
            print(f"⚠️ RDB 삭제 오류: {e}")
        
        # 검색 횟수 카운터도 초기화
        self._clear_search_counters()
        
        return {
            'redis_cleared': redis_cleared,
            'rdb_cleared': popular_cleared,
            'total': redis_cleared + popular_cleared,
            'message': 'Redis + RDB 전체 캐시 삭제 완료'
        }
    
    def _clear_search_counters(self):
        """검색 횟수 카운터 초기화"""
        try:
            # Redis에서 검색 횟수 키들 삭제
            if hasattr(self.redis_cache, 'redis_client'):
                pattern = "search_count:*"
                keys = self.redis_cache.redis_client.keys(pattern)
                if keys:
                    self.redis_cache.redis_client.delete(*keys)
                    print(f"✅ 검색 횟수 카운터 {len(keys)}개 초기화")
        except Exception as e:
            print(f"⚠️ 검색 카운터 초기화 오류: {e}")
    
    def start_daily_cleanup_thread(self):
        """매일 00시 캐시 정리 스레드 시작"""
        def daily_cleanup():
            while True:
                # 다음 00시까지 대기
                now = datetime.now()
                tomorrow_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                seconds_until_midnight = (tomorrow_midnight - now).total_seconds()
                
                time.sleep(seconds_until_midnight)
                
                try:
                    print("🕛 매일 00시 캐시 정리 시작...")
                    self.daily_cache_cleanup()
                except Exception as e:
                    print(f"❌ 매일 캐시 정리 오류: {e}")
        
        cleanup_thread = threading.Thread(target=daily_cleanup, daemon=True)
        cleanup_thread.start()
        print("✅ 매일 캐시 정리 스케줄 시작됨")
    
    def daily_cache_cleanup(self):
        """매일 00시 실행되는 캐시 정리"""
        print("🧹 Redis 캐시 정리 중...")
        
        # 1. 문서 변경 검증
        self.validate_documents()
        
        # 2. Redis에서 조회수 5회 미만 데이터는 TTL로 자동 삭제됨
        redis_cleared = 0
        if hasattr(self.redis_cache, 'connected') and self.redis_cache.connected:
            try:
                stats = self.redis_cache.get_stats()
                print(f"📊 Redis 상태: {stats.get('keys_count', 0)}개 키 존재")
            except Exception as e:
                print(f"⚠️ Redis 통계 조회 실패: {e}")
        
        # 3. 인기 질문 DB 검증 (5회 이상 조회된 항목들 유지)
        popular_verified = self._verify_popular_cache()
        
        print(f"✅ 매일 정리 완료 - 인기질문 {popular_verified}개 검증됨")
        
        # 정리 로그 저장
        self._log_daily_cleanup(redis_cleared, popular_verified)
    
    def _verify_popular_cache(self):
        """인기 질문 캐시 검증 - 5회 미만 항목 삭제"""
        try:
            conn = sqlite3.connect(self.popular_cache.cache_db_path)
            cursor = conn.cursor()
            
            # 조회수가 threshold 미만인 항목들 찾기
            cursor.execute('''
                SELECT id, hit_count FROM cache 
                WHERE hit_count < ? 
            ''', (self.popular_threshold,))
            
            low_hit_items = cursor.fetchall()
            
            # threshold 미만 항목들 삭제
            if low_hit_items:
                item_ids = [str(item[0]) for item in low_hit_items]
                cursor.execute(f'''
                    DELETE FROM cache 
                    WHERE id IN ({','.join(['?' for _ in item_ids])})
                ''', item_ids)
                print(f"🗑️ 조회수 {self.popular_threshold}회 미만 {len(low_hit_items)}개 항목 삭제")
            
            # 현재 남은 항목 수 확인
            cursor.execute('SELECT COUNT(*) FROM cache')
            remaining_count = cursor.fetchone()[0]
            
            conn.commit()
            conn.close()
            
            return remaining_count
            
        except Exception as e:
            print(f"⚠️ 인기 캐시 검증 오류: {e}")
            return 0
    
    def _log_daily_cleanup(self, redis_cleared, popular_verified):
        """매일 정리 로그 기록"""
        try:
            conn = sqlite3.connect(self.validation_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO validation_log (
                    validation_date, documents_checked, changes_detected, cache_cleared
                ) VALUES (?, ?, ?, ?)
            ''', (datetime.now(), 0, 0, popular_verified))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ 정리 로그 저장 오류: {e}")