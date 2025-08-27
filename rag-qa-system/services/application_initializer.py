"""
애플리케이션 초기화 서비스
- 시작 시 Redis, MySQL 초기화
- 시스템 컴포넌트 상태 확인
"""

import logging
from typing import Dict
from .redis_cache_manager import RedisCacheManager
from .popular_question_manager import PopularQuestionManager

logger = logging.getLogger(__name__)

class ApplicationInitializer:
    """애플리케이션 초기화 관리자"""
    
    def __init__(self):
        """초기화 관리자 생성"""
        self.redis_manager = None
        self.popular_manager = None
        self.initialization_status = {}
    
    def initialize_application(self, clear_cache: bool = True) -> Dict:
        """애플리케이션 전체 초기화"""
        logger.info("🚀 RAG QA 시스템 초기화 시작")
        
        status = {
            'redis': {'initialized': False, 'error': None},
            'mysql': {'initialized': False, 'error': None},
            'overall': {'success': False, 'message': ''}
        }
        
        try:
            # 1. Redis 초기화
            logger.info("1️⃣ Redis 캐시 시스템 초기화")
            status['redis'] = self._initialize_redis_cache(clear_cache)
            
            # 2. MySQL 초기화  
            logger.info("2️⃣ MySQL 인기질문 시스템 초기화")
            status['mysql'] = self._initialize_mysql_system(clear_cache)
            
            # 3. 전체 상태 확인
            redis_ok = status['redis']['initialized']
            mysql_ok = status['mysql']['initialized']
            
            if redis_ok and mysql_ok:
                status['overall'] = {
                    'success': True,
                    'message': '✅ 모든 시스템이 성공적으로 초기화되었습니다.'
                }
                logger.info("✅ RAG QA 시스템 초기화 완료")
                
            elif redis_ok or mysql_ok:
                status['overall'] = {
                    'success': True,
                    'message': f"⚠️ 부분 초기화 완료 (Redis: {'✅' if redis_ok else '❌'}, MySQL: {'✅' if mysql_ok else '❌'})"
                }
                logger.warning("⚠️ RAG QA 시스템 부분 초기화")
                
            else:
                status['overall'] = {
                    'success': False,
                    'message': '❌ 시스템 초기화에 실패했습니다.'
                }
                logger.error("❌ RAG QA 시스템 초기화 실패")
                
            self.initialization_status = status
            return status
            
        except Exception as e:
            logger.error(f"애플리케이션 초기화 중 오류: {e}")
            status['overall'] = {
                'success': False,
                'message': f'❌ 초기화 중 예외 발생: {str(e)}'
            }
            return status
    
    def _initialize_redis_cache(self, clear_cache: bool) -> Dict:
        """Redis 캐시 시스템 초기화"""
        try:
            self.redis_manager = RedisCacheManager()
            
            if not self.redis_manager.is_connected():
                return {
                    'initialized': False,
                    'error': 'Redis 서버 연결 실패',
                    'message': '❌ Redis 연결 실패 - 캐싱 기능 비활성화'
                }
            
            # 캐시 초기화 (옵션)
            if clear_cache:
                clear_result = self.redis_manager.clear_cache()
                if clear_result:
                    logger.info("🗑️ Redis 캐시 초기화 완료")
                else:
                    logger.warning("⚠️ Redis 캐시 초기화 실패")
            
            # 연결 상태 재확인
            if self.redis_manager.is_connected():
                stats = self.redis_manager.get_cache_stats()
                return {
                    'initialized': True,
                    'error': None,
                    'message': f'✅ Redis 초기화 완료',
                    'stats': stats
                }
            else:
                return {
                    'initialized': False,
                    'error': 'Redis 연결 상태 불안정',
                    'message': '❌ Redis 연결 불안정'
                }
                
        except Exception as e:
            logger.error(f"Redis 초기화 오류: {e}")
            return {
                'initialized': False,
                'error': str(e),
                'message': f'❌ Redis 초기화 실패: {str(e)}'
            }
    
    def _initialize_mysql_system(self, clear_data: bool) -> Dict:
        """MySQL 인기질문 시스템 초기화"""
        try:
            self.popular_manager = PopularQuestionManager()
            
            if not self.popular_manager.is_connected():
                return {
                    'initialized': False,
                    'error': 'MySQL 데이터베이스 연결 실패',
                    'message': '❌ MySQL 연결 실패 - 인기질문 기능 비활성화'
                }
            
            # 데이터 초기화 (옵션)
            if clear_data:
                clear_result = self.popular_manager.clear_popular_questions()
                if clear_result:
                    logger.info("🗑️ MySQL 인기질문 데이터 초기화 완료")
                else:
                    logger.warning("⚠️ MySQL 데이터 초기화 실패")
            
            # 연결 상태 재확인
            if self.popular_manager.is_connected():
                stats = self.popular_manager.get_question_stats()
                return {
                    'initialized': True,
                    'error': None,
                    'message': f'✅ MySQL 초기화 완료',
                    'stats': stats
                }
            else:
                return {
                    'initialized': False,
                    'error': 'MySQL 연결 상태 불안정',
                    'message': '❌ MySQL 연결 불안정'
                }
                
        except Exception as e:
            logger.error(f"MySQL 초기화 오류: {e}")
            return {
                'initialized': False,
                'error': str(e),
                'message': f'❌ MySQL 초기화 실패: {str(e)}'
            }
    
    def get_system_status(self) -> Dict:
        """시스템 전체 상태 조회"""
        status = {
            'redis': {'connected': False, 'stats': {}},
            'mysql': {'connected': False, 'stats': {}},
            'last_initialization': self.initialization_status
        }
        
        try:
            # Redis 상태
            if self.redis_manager:
                status['redis']['connected'] = self.redis_manager.is_connected()
                if status['redis']['connected']:
                    status['redis']['stats'] = self.redis_manager.get_cache_stats()
            
            # MySQL 상태
            if self.popular_manager:
                status['mysql']['connected'] = self.popular_manager.is_connected()
                if status['mysql']['connected']:
                    status['mysql']['stats'] = self.popular_manager.get_question_stats()
            
            return status
            
        except Exception as e:
            logger.error(f"시스템 상태 조회 오류: {e}")
            return status
    
    def get_managers(self) -> tuple:
        """초기화된 매니저들 반환"""
        return self.redis_manager, self.popular_manager
    
    def shutdown(self):
        """애플리케이션 종료 시 정리"""
        logger.info("🔄 RAG QA 시스템 종료 중...")
        
        try:
            if self.popular_manager:
                self.popular_manager.close_connection()
                
            # Redis는 자동으로 연결 해제됨
            
            logger.info("✅ RAG QA 시스템 정리 완료")
            
        except Exception as e:
            logger.error(f"시스템 종료 오류: {e}")


# 전역 초기화 인스턴스
_app_initializer = None

def get_application_initializer() -> ApplicationInitializer:
    """전역 초기화 인스턴스 반환"""
    global _app_initializer
    if _app_initializer is None:
        _app_initializer = ApplicationInitializer()
    return _app_initializer

def initialize_on_startup(clear_cache: bool = True) -> Dict:
    """애플리케이션 시작 시 호출할 초기화 함수"""
    initializer = get_application_initializer()
    return initializer.initialize_application(clear_cache)

def get_system_status() -> Dict:
    """시스템 상태 조회"""
    initializer = get_application_initializer()
    return initializer.get_system_status()

def shutdown_application():
    """애플리케이션 종료시 호출할 함수"""
    global _app_initializer
    if _app_initializer:
        _app_initializer.shutdown()
        _app_initializer = None