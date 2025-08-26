from flask import Blueprint, request, jsonify, session
from models.session_manager import SessionManager
import uuid

session_bp = Blueprint('session', __name__)
session_manager = SessionManager()

@session_bp.route('/create', methods=['POST'])
def create_session():
    """새 채팅 세션 생성"""
    try:
        # 사용자 ID (세션 또는 쿠키에서)
        user_id = session.get('user_id')
        if not user_id:
            user_id = str(uuid.uuid4())
            session['user_id'] = user_id
        
        # 새 세션 생성
        session_id = session_manager.create_session(user_id)
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'user_id': user_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@session_bp.route('/list', methods=['GET'])
def list_sessions():
    """사용자의 세션 목록 조회"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'sessions': []})
        
        sessions = session_manager.get_user_sessions(user_id)
        
        return jsonify({
            'status': 'success',
            'sessions': sessions,
            'total': len(sessions)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@session_bp.route('/<session_id>', methods=['GET'])
def get_session(session_id):
    """특정 세션의 전체 대화 내용 조회"""
    try:
        session_data = session_manager.get_session(session_id)
        
        if not session_data:
            return jsonify({'error': '세션을 찾을 수 없습니다.'}), 404
        
        # 사용자 권한 확인
        user_id = session.get('user_id')
        if session_data.get('user_id') != user_id and user_id != 'admin':
            return jsonify({'error': '권한이 없습니다.'}), 403
        
        return jsonify({
            'status': 'success',
            'session': session_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@session_bp.route('/<session_id>/messages', methods=['POST'])
def add_message(session_id):
    """세션에 메시지 추가"""
    try:
        data = request.get_json()
        role = data.get('role', 'user')
        content = data.get('content', '')
        metadata = data.get('metadata', {})
        
        if not content:
            return jsonify({'error': '메시지 내용이 필요합니다.'}), 400
        
        # 세션 확인
        session_data = session_manager.get_session(session_id)
        if not session_data:
            return jsonify({'error': '세션을 찾을 수 없습니다.'}), 404
        
        # 권한 확인
        user_id = session.get('user_id')
        if session_data.get('user_id') != user_id:
            return jsonify({'error': '권한이 없습니다.'}), 403
        
        # 메시지 추가
        success = session_manager.add_message(session_id, role, content, metadata)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': '메시지가 추가되었습니다.'
            })
        else:
            return jsonify({'error': '메시지 추가 실패'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@session_bp.route('/<session_id>/history', methods=['GET'])
def get_history(session_id):
    """세션의 최근 대화 기록 조회"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # 세션 확인
        session_data = session_manager.get_session(session_id)
        if not session_data:
            return jsonify({'error': '세션을 찾을 수 없습니다.'}), 404
        
        # 권한 확인
        user_id = session.get('user_id')
        if session_data.get('user_id') != user_id:
            return jsonify({'error': '권한이 없습니다.'}), 403
        
        history = session_manager.get_session_history(session_id, limit)
        
        return jsonify({
            'status': 'success',
            'history': history,
            'count': len(history)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@session_bp.route('/search', methods=['POST'])
def search_sessions():
    """세션 내용 검색"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'results': []})
        
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': '검색어가 필요합니다.'}), 400
        
        results = session_manager.search_sessions(user_id, query)
        
        return jsonify({
            'status': 'success',
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@session_bp.route('/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """세션 삭제"""
    try:
        # 세션 확인
        session_data = session_manager.get_session(session_id)
        if not session_data:
            return jsonify({'error': '세션을 찾을 수 없습니다.'}), 404
        
        # 권한 확인
        user_id = session.get('user_id')
        if session_data.get('user_id') != user_id:
            return jsonify({'error': '권한이 없습니다.'}), 403
        
        success = session_manager.delete_session(session_id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': '세션이 삭제되었습니다.'
            })
        else:
            return jsonify({'error': '세션 삭제 실패'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500