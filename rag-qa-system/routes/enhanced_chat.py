from flask import Blueprint, request, jsonify, session
from services.similarity_suggestions import SimilaritySuggestionRAG
from services.data_based_summary import DataBasedSummaryRAG
from services.smart_cache_manager import SmartCacheManager
from models.session_manager import SessionManager
import time
import uuid

enhanced_chat_bp = Blueprint('enhanced_chat', __name__)

# 전역 인스턴스들
_suggestion_rag = None
_summary_rag = None
_smart_cache = None
_session_manager = None

def get_services():
    """필요한 서비스 인스턴스들을 싱글톤으로 관리"""
    global _suggestion_rag, _summary_rag, _smart_cache, _session_manager
    
    if _suggestion_rag is None:
        _suggestion_rag = SimilaritySuggestionRAG()
    if _summary_rag is None:
        _summary_rag = DataBasedSummaryRAG()
    if _smart_cache is None:
        _smart_cache = SmartCacheManager()
    if _session_manager is None:
        _session_manager = SessionManager()
    
    return _suggestion_rag, _summary_rag, _smart_cache, _session_manager

@enhanced_chat_bp.route('/smart-query', methods=['POST'])
def smart_query():
    """스마트 쿼리 - 모든 기능이 통합된 엔드포인트"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON 데이터가 필요합니다.'}), 400
        
        question = data.get('question')
        if not question:
            return jsonify({'error': '질문이 필요합니다.'}), 400
        
        # 옵션들
        use_suggestions = data.get('use_suggestions', True)
        use_summary_mode = data.get('use_summary_mode', False)
        use_memory = data.get('use_memory', False)
        use_cache = data.get('use_cache', True)
        similarity_threshold = data.get('similarity_threshold', 0.8)
        session_id = data.get('session_id')
        
        # 서비스 인스턴스 가져오기
        suggestion_rag, summary_rag, smart_cache, session_manager = get_services()
        
        start_time = time.time()
        
        # 1. 캐시 확인 (use_cache가 True인 경우)
        cache_result = None
        if use_cache:
            cache_key_params = {
                'use_suggestions': use_suggestions,
                'use_summary_mode': use_summary_mode,
                'similarity_threshold': similarity_threshold
            }
            cache_result = smart_cache.get(question, **cache_key_params)
        
        if cache_result:
            # 캐시에서 발견
            processing_time = time.time() - start_time
            cache_result['processing_time'] = processing_time
            cache_result['_from_cache'] = True
            
            # 세션에 기록
            if session_id:
                session_manager.add_message(session_id, 'user', question)
                session_manager.add_message(session_id, 'assistant', cache_result.get('answer', ''), 
                                          {'from_cache': True, 'cache_type': 'smart_cache'})
            
            return jsonify({
                'status': 'success',
                'result': cache_result,
                'source': 'cache'
            })
        
        # 2. 요약 모드 처리
        if use_summary_mode:
            result = summary_rag.summarize_from_data(question)
        else:
            # 3. 유사도 기반 추천 처리
            if use_suggestions:
                result = suggestion_rag.query_with_suggestions(
                    question=question,
                    use_memory=use_memory,
                    threshold=similarity_threshold
                )
            else:
                # 기본 RAG 처리
                result = suggestion_rag.query(question, use_memory)
        
        # 4. 캐시에 저장
        if use_cache and result and not result.get('error'):
            smart_cache.set(question, result, **cache_key_params)
        
        # 5. 세션에 기록
        if session_id:
            session_manager.add_message(session_id, 'user', question)
            session_manager.add_message(session_id, 'assistant', result.get('answer', ''), 
                                      {'mode': 'summary' if use_summary_mode else 'normal',
                                       'suggestions_used': use_suggestions})
        
        return jsonify({
            'status': 'success',
            'result': result,
            'source': 'computed'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@enhanced_chat_bp.route('/suggestion-select', methods=['POST'])
def suggestion_select():
    """추천 선택지 선택 처리"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON 데이터가 필요합니다.'}), 400
        
        suggestion_id = data.get('suggestion_id')
        original_question = data.get('original_question')
        session_id = data.get('session_id')
        use_cache = data.get('use_cache', True)
        
        if not suggestion_id or not original_question:
            return jsonify({'error': 'suggestion_id와 original_question이 필요합니다.'}), 400
        
        suggestion_rag, _, smart_cache, session_manager = get_services()
        
        # 캐시 확인
        cache_result = None
        if use_cache:
            cache_key = f"suggestion_{suggestion_id}_{original_question}"
            cache_result = smart_cache.get(cache_key)
        
        if cache_result:
            # 세션 기록
            if session_id:
                session_manager.add_message(session_id, 'user', f"추천 선택: {suggestion_id}")
                session_manager.add_message(session_id, 'assistant', cache_result.get('answer', ''),
                                          {'from_cache': True, 'suggestion_id': suggestion_id})
            
            return jsonify({
                'status': 'success',
                'result': cache_result,
                'source': 'cache'
            })
        
        # 추천 선택 처리
        result = suggestion_rag.query_suggestion(suggestion_id, original_question)
        
        # 캐시 저장
        if use_cache and result and not result.get('error'):
            cache_key = f"suggestion_{suggestion_id}_{original_question}"
            smart_cache.set(cache_key, result)
        
        # 세션 기록
        if session_id:
            session_manager.add_message(session_id, 'user', f"추천 선택: {suggestion_id}")
            session_manager.add_message(session_id, 'assistant', result.get('answer', ''),
                                      {'suggestion_id': suggestion_id, 'multi_search': True})
        
        return jsonify({
            'status': 'success',
            'result': result,
            'source': 'computed'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@enhanced_chat_bp.route('/new-session', methods=['POST'])
def create_new_session():
    """새 채팅 세션 생성"""
    try:
        # 사용자 ID 확인/생성
        user_id = session.get('user_id')
        if not user_id:
            user_id = str(uuid.uuid4())
            session['user_id'] = user_id
        
        _, _, _, session_manager = get_services()
        
        # 새 세션 생성
        session_id = session_manager.create_session(user_id)
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'user_id': user_id,
            'message': '새 채팅 세션이 생성되었습니다.'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@enhanced_chat_bp.route('/session-history', methods=['GET'])
def get_session_history():
    """사용자의 세션 목록 조회"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'status': 'success',
                'sessions': [],
                'message': '로그인된 사용자가 없습니다.'
            })
        
        _, _, _, session_manager = get_services()
        
        # 세션 목록 조회
        sessions = session_manager.get_user_sessions(user_id)
        
        return jsonify({
            'status': 'success',
            'sessions': sessions,
            'user_id': user_id,
            'total': len(sessions)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@enhanced_chat_bp.route('/session/<session_id>', methods=['GET'])
def get_session_detail(session_id):
    """특정 세션의 대화 내용 조회"""
    try:
        user_id = session.get('user_id')
        _, _, _, session_manager = get_services()
        
        # 세션 조회
        session_data = session_manager.get_session(session_id)
        
        if not session_data:
            return jsonify({'error': '세션을 찾을 수 없습니다.'}), 404
        
        # 권한 확인
        if session_data.get('user_id') != user_id:
            return jsonify({'error': '접근 권한이 없습니다.'}), 403
        
        return jsonify({
            'status': 'success',
            'session': session_data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@enhanced_chat_bp.route('/cache-stats', methods=['GET'])
def get_cache_statistics():
    """캐시 통계 조회"""
    try:
        _, _, smart_cache, _ = get_services()
        
        stats = smart_cache.get_cache_stats()
        
        return jsonify({
            'status': 'success',
            'cache_stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@enhanced_chat_bp.route('/clear-cache', methods=['DELETE'])
def clear_cache():
    """캐시 삭제"""
    try:
        cache_type = request.args.get('type', 'all')  # all, expired
        
        _, _, smart_cache, _ = get_services()
        
        if cache_type == 'expired':
            result = smart_cache.clear_expired()
            message = '만료된 캐시가 삭제되었습니다.'
        else:
            result = smart_cache.clear_all_cache()
            message = '모든 캐시가 삭제되었습니다.'
        
        return jsonify({
            'status': 'success',
            'message': message,
            'cleared': result
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@enhanced_chat_bp.route('/health', methods=['GET'])
def health_check():
    """전체 시스템 건강상태 체크"""
    try:
        suggestion_rag, summary_rag, smart_cache, session_manager = get_services()
        
        # 각 서비스 상태 확인
        health_status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'services': {
                'similarity_suggestions': {
                    'available': True,
                    'document_count': suggestion_rag.vectorstore_manager.get_document_count()
                },
                'data_summary': {
                    'available': True,
                    'mode': 'data_only'
                },
                'smart_cache': {
                    'available': True,
                    'redis_available': smart_cache.redis_available,
                    'stats': smart_cache.get_cache_stats()
                },
                'session_management': {
                    'available': True,
                    'redis_available': session_manager.use_redis
                }
            },
            'features': [
                'smart_caching',
                'similarity_suggestions', 
                'data_based_summary',
                'session_management',
                'multi_vectorstore_search'
            ]
        }
        
        return jsonify(health_status)
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500