import uuid
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import redis
from config import Config

class SessionManager:
    """채팅 세션 관리자"""
    
    def __init__(self):
        self.sessions_dir = "./data/sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)
        
        # Redis 연결 (선택사항)
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
            self.redis_client.ping()
            self.use_redis = True
        except:
            self.redis_client = None
            self.use_redis = False
    
    def create_session(self, user_id: str = None) -> str:
        """새 세션 생성"""
        session_id = str(uuid.uuid4())
        session_data = {
            'id': session_id,
            'user_id': user_id or 'anonymous',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'messages': [],
            'first_message': None,
            'summary': None
        }
        
        # 세션 저장
        self._save_session(session_id, session_data)
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Dict = None):
        """세션에 메시지 추가"""
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        message = {
            'id': str(uuid.uuid4()),
            'role': role,  # 'user' or 'assistant'
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        session_data['messages'].append(message)
        session_data['updated_at'] = datetime.now().isoformat()
        
        # 첫 메시지인 경우 요약으로 저장
        if role == 'user' and not session_data['first_message']:
            session_data['first_message'] = content[:100] + "..." if len(content) > 100 else content
            session_data['summary'] = self._generate_summary(content)
        
        self._save_session(session_id, session_data)
        return True
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """세션 데이터 가져오기"""
        if self.use_redis:
            # Redis에서 먼저 확인
            data = self.redis_client.get(f"session:{session_id}")
            if data:
                return json.loads(data)
        
        # 파일에서 확인
        file_path = os.path.join(self.sessions_dir, f"{session_id}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def get_user_sessions(self, user_id: str, limit: int = 20) -> List[Dict]:
        """사용자의 모든 세션 목록 가져오기"""
        sessions = []
        
        # 파일 시스템에서 세션 검색
        for filename in os.listdir(self.sessions_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.sessions_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    if session_data.get('user_id') == user_id:
                        # 목록용 간략 정보만 추출
                        sessions.append({
                            'id': session_data['id'],
                            'created_at': session_data['created_at'],
                            'updated_at': session_data['updated_at'],
                            'first_message': session_data.get('first_message', '새 대화'),
                            'summary': session_data.get('summary', ''),
                            'message_count': len(session_data.get('messages', []))
                        })
        
        # 최신순 정렬
        sessions.sort(key=lambda x: x['updated_at'], reverse=True)
        return sessions[:limit]
    
    def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        # Redis에서 삭제
        if self.use_redis:
            self.redis_client.delete(f"session:{session_id}")
        
        # 파일 삭제
        file_path = os.path.join(self.sessions_dir, f"{session_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        
        return False
    
    def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """세션의 최근 대화 기록 가져오기"""
        session_data = self.get_session(session_id)
        if not session_data:
            return []
        
        messages = session_data.get('messages', [])
        return messages[-limit:] if limit else messages
    
    def _save_session(self, session_id: str, session_data: Dict):
        """세션 데이터 저장"""
        # 파일로 저장
        file_path = os.path.join(self.sessions_dir, f"{session_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        # Redis에도 저장 (캐시)
        if self.use_redis:
            self.redis_client.setex(
                f"session:{session_id}",
                3600 * 24,  # 24시간 캐시
                json.dumps(session_data, ensure_ascii=False)
            )
    
    def _generate_summary(self, text: str) -> str:
        """텍스트 요약 생성 (간단한 버전)"""
        # 실제로는 LLM을 사용할 수 있지만, 여기서는 간단히 처리
        if len(text) <= 50:
            return text
        
        # 첫 50자 + 주요 키워드 추출
        summary = text[:50]
        
        # 질문 형태인 경우
        if '?' in text:
            question_part = text.split('?')[0] + '?'
            if len(question_part) <= 100:
                summary = question_part
        
        return summary
    
    def search_sessions(self, user_id: str, query: str) -> List[Dict]:
        """세션 내용 검색"""
        sessions = self.get_user_sessions(user_id, limit=100)
        results = []
        
        query_lower = query.lower()
        
        for session_info in sessions:
            session_data = self.get_session(session_info['id'])
            if not session_data:
                continue
            
            # 메시지 내용에서 검색
            for message in session_data.get('messages', []):
                if query_lower in message['content'].lower():
                    results.append({
                        'session_id': session_info['id'],
                        'session_summary': session_info['summary'],
                        'message': message,
                        'created_at': session_info['created_at']
                    })
                    break  # 세션당 하나만
        
        return results[:20]  # 최대 20개 결과