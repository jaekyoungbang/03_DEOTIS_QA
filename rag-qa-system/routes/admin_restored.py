from flask import Blueprint, jsonify, request
from models.vectorstore import get_vectorstore, reset_vectorstore
import os
import json
import shutil
from datetime import datetime

admin_restored_bp = Blueprint('admin_restored', __name__)

@admin_restored_bp.route('/clear-redis', methods=['DELETE'])
def clear_redis():
    """Redis 캐시 삭제"""
    try:
        # Redis 연결 시도
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            keys_deleted = r.flushdb()
            return jsonify({
                'status': 'success',
                'message': 'Redis 캐시가 삭제되었습니다.',
                'keys_deleted': len(r.keys()) if keys_deleted else 0
            })
        except Exception as redis_error:
            # Redis가 없는 경우 파일 기반 캐시 삭제
            cache_dirs = ['data/cache', 'cache']
            deleted_files = 0
            
            for cache_dir in cache_dirs:
                if os.path.exists(cache_dir):
                    for filename in os.listdir(cache_dir):
                        if filename.endswith('.json') or filename.endswith('.cache'):
                            os.remove(os.path.join(cache_dir, filename))
                            deleted_files += 1
            
            return jsonify({
                'status': 'success',
                'message': f'파일 기반 캐시가 삭제되었습니다. (Redis 미연결: {str(redis_error)})',
                'files_deleted': deleted_files
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Redis 캐시 삭제 실패: {str(e)}'
        }), 500

@admin_restored_bp.route('/clear-rdb', methods=['DELETE'])
def clear_rdb():
    """RDB(SQLite) 기록 삭제"""
    try:
        deleted_files = []
        
        # SQLite 데이터베이스 파일들 삭제
        db_files = [
            'data/search_stats.db',
            'data/cache.db',
            'data/popular_questions.db',
            'search_stats.db',
            'cache.db'
        ]
        
        for db_file in db_files:
            if os.path.exists(db_file):
                os.remove(db_file)
                deleted_files.append(db_file)
        
        # JSON 기록 파일들도 삭제
        json_files = [
            'data/query_usage.json',
            'data/benchmark_results.json',
            'benchmark_results.json'
        ]
        
        for json_file in json_files:
            if os.path.exists(json_file):
                os.remove(json_file)
                deleted_files.append(json_file)
        
        return jsonify({
            'status': 'success',
            'message': 'RDB 기록이 삭제되었습니다.',
            'deleted_files': deleted_files,
            'deleted_count': len(deleted_files)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'RDB 삭제 실패: {str(e)}'
        }), 500

@admin_restored_bp.route('/clear-vectordb', methods=['DELETE'])
def clear_vectordb():
    """벡터 DB 삭제"""
    try:
        # 벡터스토어 가져오기
        vectorstore = get_vectorstore()
        
        # 문서 수 확인
        doc_count = 0
        try:
            if hasattr(vectorstore, '_collection'):
                doc_count = vectorstore._collection.count()
        except:
            pass
        
        # 벡터 DB 디렉토리 삭제
        vectordb_dirs = [
            'data/vectordb',
            './data/vectordb',
            'vectordb'
        ]
        
        deleted_dirs = []
        for vectordb_dir in vectordb_dirs:
            if os.path.exists(vectordb_dir):
                shutil.rmtree(vectordb_dir)
                deleted_dirs.append(vectordb_dir)
        
        # 벡터스토어 인스턴스 리셋
        reset_vectorstore()
        
        return jsonify({
            'status': 'success',
            'message': '벡터 데이터베이스가 삭제되었습니다.',
            'previous_doc_count': doc_count,
            'deleted_directories': deleted_dirs,
            'note': '문서를 다시 로드해야 합니다.'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'벡터 DB 삭제 실패: {str(e)}'
        }), 500

@admin_restored_bp.route('/clear-all', methods=['DELETE'])
def clear_all():
    """전체 초기화 (문서 파일 제외)"""
    try:
        results = {
            'redis': {'status': 'not_attempted'},
            'rdb': {'status': 'not_attempted'},
            'vectordb': {'status': 'not_attempted'}
        }
        
        # Redis 삭제
        try:
            redis_result = clear_redis()
            if redis_result[1] == 200:  # HTTP 200 OK
                results['redis'] = {'status': 'success', 'data': redis_result[0].get_json()}
            else:
                results['redis'] = {'status': 'failed', 'error': redis_result[0].get_json()}
        except Exception as e:
            results['redis'] = {'status': 'failed', 'error': str(e)}
        
        # RDB 삭제
        try:
            rdb_result = clear_rdb()
            if rdb_result[1] == 200:
                results['rdb'] = {'status': 'success', 'data': rdb_result[0].get_json()}
            else:
                results['rdb'] = {'status': 'failed', 'error': rdb_result[0].get_json()}
        except Exception as e:
            results['rdb'] = {'status': 'failed', 'error': str(e)}
        
        # 벡터 DB 삭제
        try:
            vectordb_result = clear_vectordb()
            if vectordb_result[1] == 200:
                results['vectordb'] = {'status': 'success', 'data': vectordb_result[0].get_json()}
            else:
                results['vectordb'] = {'status': 'failed', 'error': vectordb_result[0].get_json()}
        except Exception as e:
            results['vectordb'] = {'status': 'failed', 'error': str(e)}
        
        # 성공 여부 판단
        success_count = sum(1 for r in results.values() if r['status'] == 'success')
        
        return jsonify({
            'status': 'success' if success_count >= 2 else 'partial',
            'message': f'전체 초기화 완료. 성공: {success_count}/3',
            'details': results,
            'timestamp': datetime.now().isoformat(),
            'note': '문서 파일은 삭제되지 않았습니다. 필요시 다시 로드하세요.'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'전체 초기화 실패: {str(e)}'
        }), 500

@admin_restored_bp.route('/system-status', methods=['GET'])
def get_system_status():
    """시스템 상태 조회"""
    try:
        status = {
            'redis': {'available': False, 'info': None},
            'rdb': {'available': False, 'files': []},
            'vectordb': {'available': False, 'doc_count': 0},
            'documents': {'available': False, 'file_count': 0}
        }
        
        # Redis 상태
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.ping()
            status['redis']['available'] = True
            status['redis']['info'] = {
                'keys': len(r.keys()),
                'memory_usage': r.info().get('used_memory_human', 'Unknown')
            }
        except:
            # 파일 기반 캐시 확인
            cache_files = []
            if os.path.exists('data/cache'):
                cache_files = [f for f in os.listdir('data/cache') if f.endswith('.json')]
            status['redis']['info'] = {'cache_files': len(cache_files)}
        
        # RDB 상태
        db_files = [
            'data/search_stats.db',
            'data/cache.db',
            'data/popular_questions.db',
            'data/query_usage.json',
            'data/benchmark_results.json'
        ]
        
        existing_files = [f for f in db_files if os.path.exists(f)]
        status['rdb']['available'] = len(existing_files) > 0
        status['rdb']['files'] = existing_files
        
        # 벡터 DB 상태
        try:
            vectorstore = get_vectorstore()
            if hasattr(vectorstore, '_collection'):
                doc_count = vectorstore._collection.count()
                status['vectordb']['available'] = doc_count > 0
                status['vectordb']['doc_count'] = doc_count
        except:
            pass
        
        # 문서 파일 상태
        doc_dirs = ['s3', 'data/documents', 'documents']
        total_files = 0
        for doc_dir in doc_dirs:
            if os.path.exists(doc_dir):
                files = [f for f in os.listdir(doc_dir) 
                        if f.endswith(('.pdf', '.docx', '.txt', '.md'))]
                total_files += len(files)
        
        status['documents']['available'] = total_files > 0
        status['documents']['file_count'] = total_files
        
        return jsonify({
            'status': 'success',
            'system_status': status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'시스템 상태 조회 실패: {str(e)}'
        }), 500

@admin_restored_bp.route('/reload-documents', methods=['POST'])
def reload_documents():
    """문서 다시 로드"""
    try:
        # 기존 load_documents.py의 load_s3_documents 함수 호출
        from load_documents import load_s3_documents
        
        # 벡터 DB 초기화 후 다시 로드
        clear_vectordb()
        
        # 문서 로드 실행
        documents_loaded, total_chunks = load_s3_documents()
        
        return jsonify({
            'status': 'success',
            'message': '문서가 다시 로드되었습니다.',
            'documents_loaded': documents_loaded,
            'total_chunks': total_chunks,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'문서 로드 실패: {str(e)}'
        }), 500