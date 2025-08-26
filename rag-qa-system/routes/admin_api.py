from flask_restx import Namespace, Resource, fields
from flask import request
from services.admin_config import AdminConfig
from services.cache_factory import CacheFactory
from functools import wraps
import jwt
import datetime

# Create namespace
api = Namespace('admin', description='관리자 설정 API')

# JWT Secret (in production, use environment variable)
JWT_SECRET = 'your-secret-key-change-this'

# Models
login_model = api.model('AdminLogin', {
    'password': fields.String(required=True, description='관리자 비밀번호')
})

token_response = api.model('TokenResponse', {
    'token': fields.String(description='JWT 토큰'),
    'expires_in': fields.Integer(description='만료 시간(초)')
})

settings_model = api.model('AdminSettings', {
    'cache_type': fields.String(description='캐시 타입 (sqlite/redis)'),
    'redis_config': fields.Raw(description='Redis 설정'),
    'chunk_strategy': fields.Raw(description='청크 전략'),
    'cache_config': fields.Raw(description='캐시 설정')
})

# Authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return {'error': '인증 토큰이 필요합니다'}, 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Verify token
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            
            # Check expiration
            exp_timestamp = payload.get('exp')
            if exp_timestamp and datetime.datetime.utcnow().timestamp() > exp_timestamp:
                return {'error': '토큰이 만료되었습니다'}, 401
                
        except jwt.InvalidTokenError:
            return {'error': '유효하지 않은 토큰입니다'}, 401
        
        return f(*args, **kwargs)
    
    return decorated

@api.route('/login')
class AdminLogin(Resource):
    @api.doc('admin_login')
    @api.expect(login_model)
    @api.marshal_with(token_response)
    def post(self):
        """관리자 로그인"""
        data = request.get_json()
        password = data.get('password')
        
        if not password:
            return {'error': '비밀번호를 입력하세요'}, 400
        
        # Verify password
        config = AdminConfig()
        if not config.verify_password(password):
            return {'error': '비밀번호가 일치하지 않습니다'}, 401
        
        # Generate JWT token
        expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        token = jwt.encode({
            'admin': True,
            'exp': expiration.timestamp()
        }, JWT_SECRET, algorithm='HS256')
        
        return {
            'token': token,
            'expires_in': 7200  # 2 hours
        }

@api.route('/settings')
class AdminSettings(Resource):
    @api.doc('get_settings')
    @admin_required
    def get(self):
        """관리자 설정 조회"""
        config = AdminConfig()
        settings = config.get_all_settings()
        
        # Add current cache type status
        settings['current_cache_type'] = CacheFactory.get_cache_type()
        
        return settings
    
    @api.doc('update_settings')
    @api.expect(settings_model)
    @admin_required
    def put(self):
        """관리자 설정 업데이트"""
        data = request.get_json()
        config = AdminConfig()
        
        try:
            # Update cache type if provided
            if 'cache_type' in data:
                config.set_cache_type(data['cache_type'])
                # Reload cache manager
                CacheFactory.reload_cache_manager()
            
            # Update Redis config if provided
            if 'redis_config' in data:
                redis_config = data['redis_config']
                config.set_redis_config(
                    host=redis_config.get('host'),
                    port=redis_config.get('port'),
                    password=redis_config.get('password')
                )
                # Reload if using Redis
                if config.get_cache_type() == 'redis':
                    CacheFactory.reload_cache_manager()
            
            # Update chunk strategy if provided
            if 'chunk_strategy' in data:
                chunk = data['chunk_strategy']
                config.set_chunk_strategy(
                    chunk_size=chunk.get('chunk_size'),
                    chunk_overlap=chunk.get('chunk_overlap'),
                    separator=chunk.get('separator')
                )
            
            # Update cache config if provided
            if 'cache_config' in data:
                config.settings['cache_config'] = data['cache_config']
                config.save_settings()
                # Reload cache manager with new TTL
                CacheFactory.reload_cache_manager()
            
            return {
                'message': '설정이 업데이트되었습니다',
                'settings': config.get_all_settings()
            }
            
        except Exception as e:
            return {'error': str(e)}, 400

@api.route('/password')
class AdminPassword(Resource):
    @api.doc('change_password')
    @admin_required
    def put(self):
        """관리자 비밀번호 변경"""
        data = request.get_json()
        new_password = data.get('new_password')
        
        if not new_password:
            return {'error': '새 비밀번호를 입력하세요'}, 400
        
        if len(new_password) < 6:
            return {'error': '비밀번호는 최소 6자 이상이어야 합니다'}, 400
        
        config = AdminConfig()
        config.set_password(new_password)
        
        return {'message': '비밀번호가 변경되었습니다'}

@api.route('/cache/switch')
class CacheSwitch(Resource):
    @api.doc('switch_cache')
    @admin_required
    def post(self):
        """캐시 타입 전환"""
        data = request.get_json()
        cache_type = data.get('cache_type')
        
        if cache_type not in ['sqlite', 'redis']:
            return {'error': '캐시 타입은 sqlite 또는 redis여야 합니다'}, 400
        
        config = AdminConfig()
        config.set_cache_type(cache_type)
        
        # Reload cache manager
        CacheFactory.reload_cache_manager()
        current_type = CacheFactory.get_cache_type()
        
        return {
            'message': f'캐시가 {current_type}로 전환되었습니다',
            'current_type': current_type
        }

@api.route('/cache/test-redis')
class TestRedis(Resource):
    @api.doc('test_redis')
    @admin_required
    def post(self):
        """Redis 연결 테스트"""
        data = request.get_json()
        
        from services.redis_cache_manager import RedisCacheManager
        
        try:
            # Test connection with provided config
            redis_manager = RedisCacheManager(
                host=data.get('host', 'localhost'),
                port=data.get('port', 6379),
                password=data.get('password')
            )
            
            if redis_manager.is_connected():
                return {
                    'connected': True,
                    'message': 'Redis 연결 성공'
                }
            else:
                return {
                    'connected': False,
                    'message': 'Redis 연결 실패'
                }
                
        except Exception as e:
            return {
                'connected': False,
                'message': f'Redis 연결 오류: {str(e)}'
            }

@api.route('/cache/validate-documents')
class ValidateDocuments(Resource):
    @api.doc('validate_documents')
    @admin_required
    def post(self):
        """문서 변경 감지 및 캐시 무효화 (수동 실행)"""
        try:
            from services.cache_factory import CacheFactory
            
            result = CacheFactory.validate_documents_now()
            
            return {
                'message': '문서 검증 완료',
                'result': result
            }
            
        except Exception as e:
            return {
                'error': f'문서 검증 오류: {str(e)}'
            }, 500

@api.route('/cache/hybrid-stats')
class HybridCacheStats(Resource):
    @api.doc('hybrid_cache_stats')
    @admin_required
    def get(self):
        """하이브리드 캐시 통계 조회"""
        try:
            from services.cache_factory import CacheFactory
            
            cache_manager = CacheFactory.get_cache_manager()
            stats = cache_manager.get_stats()
            
            return stats
            
        except Exception as e:
            return {
                'error': f'통계 조회 오류: {str(e)}'
            }, 500

@api.route('/vectordb/reset')
class VectorDBReset(Resource):
    @api.doc('vectordb_reset')
    @admin_required
    def post(self):
        """벡터 DB 전체 리셋 후 BGE-M3로 문서 자동 재로드 (관리자용)"""
        try:
            import os
            import shutil
            from pathlib import Path
            from models.embeddings import EmbeddingManager
            from models.vectorstore import VectorStoreManager
            from utils.error_handler import detect_error_type, format_error_response
            
            # 1. 임베딩 모델 정보 확인
            embedding_manager = EmbeddingManager()
            embedding_info = embedding_manager.get_embedding_info()
            
            # 2. 기존 벡터DB 백업 및 완전 삭제
            vectordb_path = Path('./data/vectordb')
            backup_path = None
            old_doc_count = 0
            
            if vectordb_path.exists():
                try:
                    # 기존 문서 수 확인 시도
                    vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
                    old_doc_count = vectorstore_manager.get_document_count()
                except:
                    old_doc_count = 0
                
                # 백업 생성
                import time
                backup_name = f"vectordb_backup_{int(time.time())}"
                backup_path = Path(f'./data/backup/{backup_name}')
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    shutil.move(str(vectordb_path), str(backup_path))
                except:
                    # 이동 실패 시 강제 삭제
                    shutil.rmtree(vectordb_path, ignore_errors=True)
            
            # 3. 새 벡터DB 디렉토리 생성
            vectordb_path.mkdir(parents=True, exist_ok=True)
            
            # 4. 캐시 초기화
            cache_path = Path('./data/cache')
            if cache_path.exists():
                shutil.rmtree(cache_path, ignore_errors=True)
                cache_path.mkdir(parents=True, exist_ok=True)
            
            # 5. 새 임베딩 매니저로 벡터스토어 초기화
            embedding_manager = EmbeddingManager()
            vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
            vectorstore_manager.initialize_vectorstore()
            
            # 6. 문서 자동 재로드
            try:
                from load_documents_new import main as reload_documents
                reload_result = reload_documents()
                
                return {
                    "message": f"벡터 DB가 {embedding_info['type']} ({embedding_info['dimension']}차원)으로 완전 초기화 및 문서 재로드 완료",
                    "embedding_model": embedding_info,
                    "old_document_count": old_doc_count,
                    "backup_path": str(backup_path) if backup_path else None,
                    "reload_result": reload_result,
                    "status": "success",
                    "timestamp": datetime.datetime.now().isoformat()
                }
            except Exception as reload_error:
                return {
                    "message": f"벡터 DB는 {embedding_info['type']}으로 초기화되었으나 문서 재로드 실패",
                    "embedding_model": embedding_info,
                    "old_document_count": old_doc_count,
                    "backup_path": str(backup_path) if backup_path else None,
                    "error": str(reload_error),
                    "status": "partial_failure",
                    "timestamp": datetime.datetime.now().isoformat()
                }, 207  # Multi-Status
            
        except Exception as e:
            return {
                'error': f'벡터 DB 초기화 오류: {str(e)}',
                'timestamp': datetime.datetime.now().isoformat()
            }, 500

@api.route('/cache/clear-rdb')
class ClearRDBCache(Resource):
    @api.doc('clear_rdb_cache')
    @admin_required
    def delete(self):
        """RDB 캐시 전체 초기화 (관리자용)"""
        try:
            from services.cache_factory import CacheFactory
            
            cache_manager = CacheFactory.get_cache_manager()
            
            if hasattr(cache_manager, 'popular_cache'):
                # 인기 질문 DB 초기화
                popular_cleared = cache_manager.popular_cache.clear_all()
                
                # 일반 쿼리 캐시 DB도 초기화 (있다면)
                try:
                    from services.cache_manager import CacheManager as SQLiteCacheManager
                    sqlite_cache = SQLiteCacheManager()
                    query_cleared = sqlite_cache.clear_all()
                except:
                    query_cleared = 0
                
                # 문서 검증 로그 초기화
                validation_cleared = 0
                try:
                    import os
                    validation_db_path = 'data/cache/document_validation.db'
                    if os.path.exists(validation_db_path):
                        import sqlite3
                        conn = sqlite3.connect(validation_db_path)
                        cursor = conn.cursor()
                        cursor.execute('DELETE FROM document_checksums')
                        cursor.execute('DELETE FROM validation_log')
                        conn.commit()
                        validation_cleared = cursor.rowcount
                        conn.close()
                except Exception as e:
                    print(f"⚠️ 검증 로그 초기화 오류: {e}")
                
                return {
                    "message": "RDB 캐시 전체 초기화 완료",
                    "popular_cache_cleared": popular_cleared,
                    "query_cache_cleared": query_cleared,
                    "validation_logs_cleared": validation_cleared,
                    "total_cleared": popular_cleared + query_cleared + validation_cleared,
                    "timestamp": datetime.datetime.now().isoformat()
                }
            else:
                return {
                    "error": "RDB 캐시 매니저를 찾을 수 없음",
                    "timestamp": datetime.datetime.now().isoformat()
                }, 404
                
        except Exception as e:
            return {
                'error': f'RDB 캐시 초기화 오류: {str(e)}',
                'timestamp': datetime.datetime.now().isoformat()
            }, 500

@api.route('/system/reset-all')
class ResetAllData(Resource):
    @api.doc('reset_all_data')
    @admin_required
    def delete(self):
        """전체 시스템 데이터 삭제 (Chroma DB + Redis + SQLite + 모든 캐시)"""
        try:
            result = {
                "message": "전체 시스템 데이터 삭제 완료",
                "chroma_db": {"status": "failed"},
                "redis": {"status": "failed"},
                "sqlite": {"status": "failed"},
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # 1. Chroma DB 초기화
            try:
                from models.embeddings import EmbeddingManager
                from models.vectorstore import VectorStoreManager
                
                embedding_manager = EmbeddingManager()
                vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
                old_doc_count = vectorstore_manager.get_document_count()
                vectorstore_manager.delete_collection()
                vectorstore_manager.initialize_vectorstore()
                
                result["chroma_db"] = {
                    "status": "success",
                    "deleted_documents": old_doc_count
                }
            except Exception as e:
                result["chroma_db"] = {
                    "status": "failed",
                    "error": str(e)
                }
            
            # 2. Redis 초기화
            try:
                from services.cache_factory import CacheFactory
                cache_manager = CacheFactory.get_cache_manager()
                
                if hasattr(cache_manager, 'redis_cache') and cache_manager.redis_cache:
                    redis_cleared = cache_manager.redis_cache.clear_all()
                    result["redis"] = {
                        "status": "success",
                        "cleared_keys": redis_cleared
                    }
                else:
                    result["redis"] = {
                        "status": "skipped",
                        "message": "Redis 캐시가 활성화되지 않음"
                    }
            except Exception as e:
                result["redis"] = {
                    "status": "failed",
                    "error": str(e)
                }
            
            # 3. SQLite 캐시 초기화
            try:
                sqlite_results = {}
                
                # 쿼리 캐시 초기화
                from services.cache_manager import CacheManager as SQLiteCacheManager
                sqlite_cache = SQLiteCacheManager()
                query_cleared = sqlite_cache.clear_all()
                sqlite_results["query_cache"] = query_cleared
                
                # 인기 질문 캐시 초기화
                from services.cache_factory import CacheFactory
                cache_manager = CacheFactory.get_cache_manager()
                if hasattr(cache_manager, 'popular_cache'):
                    popular_cleared = cache_manager.popular_cache.clear_all()
                    sqlite_results["popular_cache"] = popular_cleared
                
                # 검색 통계 초기화
                import os
                stats_db_path = 'data/search_stats.db'
                if os.path.exists(stats_db_path):
                    import sqlite3
                    conn = sqlite3.connect(stats_db_path)
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM search_stats')
                    cursor.execute('UPDATE global_stats SET total_searches=0, total_cache_hits=0, avg_query_time=0.0')
                    conn.commit()
                    stats_cleared = cursor.rowcount
                    conn.close()
                    sqlite_results["search_stats"] = stats_cleared
                
                # 문서 검증 로그 초기화
                validation_db_path = 'data/cache/document_validation.db'
                if os.path.exists(validation_db_path):
                    import sqlite3
                    conn = sqlite3.connect(validation_db_path)
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM document_checksums')
                    cursor.execute('DELETE FROM validation_log')
                    conn.commit()
                    validation_cleared = cursor.rowcount
                    conn.close()
                    sqlite_results["validation_logs"] = validation_cleared
                
                result["sqlite"] = {
                    "status": "success",
                    "details": sqlite_results,
                    "total_cleared": sum(sqlite_results.values())
                }
                
            except Exception as e:
                result["sqlite"] = {
                    "status": "failed",
                    "error": str(e)
                }
            
            return result
            
        except Exception as e:
            return {
                'error': f'전체 데이터 삭제 오류: {str(e)}',
                'timestamp': datetime.datetime.now().isoformat()
            }, 500

@api.route('/cache/clear-all')
class ClearAllCache(Resource):
    @api.doc('clear_all_cache')
    @admin_required
    def delete(self):
        """모든 캐시 초기화 (Redis + RDB + Logs)"""
        try:
            from services.cache_factory import CacheFactory
            
            cache_manager = CacheFactory.get_cache_manager()
            
            # 하이브리드 캐시 전체 삭제
            result = cache_manager.clear_all()
            
            # 문서 검증 로그도 초기화
            validation_cleared = 0
            try:
                import os
                validation_db_path = 'data/cache/document_validation.db'
                if os.path.exists(validation_db_path):
                    import sqlite3
                    conn = sqlite3.connect(validation_db_path)
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM document_checksums')
                    cursor.execute('DELETE FROM validation_log')
                    conn.commit()
                    validation_cleared = cursor.rowcount
                    conn.close()
            except Exception as e:
                print(f"⚠️ 검증 로그 초기화 오류: {e}")
            
            # 캐시 초기화 후 문서 자동 재로드
            document_reload_result = None
            try:
                from load_documents import load_s3_documents
                documents_loaded, total_chunks = load_s3_documents()
                document_reload_result = {
                    "documents_loaded": documents_loaded,
                    "total_chunks": total_chunks
                }
                print(f"✅ 캐시 초기화 후 문서 자동 재로드: {documents_loaded}개 문서, {total_chunks}개 청크")
                
                # RAG 체인도 재초기화
                import sys
                if 'app' in sys.modules:
                    sys.modules['app'].rag_chain = None
                    from app import get_rag_chain
                    new_chain = get_rag_chain(force_reload=True)
                    print(f"✅ RAG 체인 재초기화 완료")
                    
            except Exception as reload_error:
                print(f"⚠️ 문서 자동 재로드 실패: {reload_error}")
                document_reload_result = {"error": str(reload_error)}
            
            return {
                "message": "모든 캐시 초기화 및 문서 재로드 완료",
                "redis_cleared": result.get('redis_cleared', 0),
                "rdb_cleared": result.get('popular_cleared', 0),
                "validation_logs_cleared": validation_cleared,
                "total_cleared": result.get('total', 0) + validation_cleared,
                "document_reload": document_reload_result,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'전체 캐시 초기화 오류: {str(e)}',
                'timestamp': datetime.datetime.now().isoformat()
            }, 500

@api.route('/cache/clear-redis')
class ClearRedisCache(Resource):
    @api.doc('clear_redis_cache')
    @admin_required
    def delete(self):
        """Redis 캐시만 초기화"""
        try:
            from services.cache_factory import CacheFactory
            
            cache_manager = CacheFactory.get_cache_manager()
            
            if hasattr(cache_manager, 'redis_cache') and cache_manager.redis_cache:
                redis_cleared = cache_manager.redis_cache.clear_all()
                
                return {
                    "message": "Redis 캐시 초기화 완료",
                    "redis_cleared": redis_cleared,
                    "timestamp": datetime.datetime.now().isoformat()
                }
            else:
                return {
                    "message": "Redis 캐시가 활성화되지 않음",
                    "redis_cleared": 0,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'error': f'Redis 캐시 초기화 오류: {str(e)}',
                'timestamp': datetime.datetime.now().isoformat()
            }, 500