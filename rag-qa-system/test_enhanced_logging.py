#!/usr/bin/env python3
"""
향상된 로깅 시스템 테스트
- 직관적이고 색상이 적용된 로그 출력 테스트
- Redis/MySQL 작업 로그 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.enhanced_logger import get_enhanced_logger
from services.redis_cache_manager import RedisCacheManager
from models.dual_vectorstore import DualVectorStoreManager
from models.embeddings import EmbeddingManager
from services.enhanced_similarity_handler import EnhancedSimilarityHandler
import time

def test_enhanced_logging():
    """향상된 로깅 시스템 테스트"""
    
    enhanced_logger = get_enhanced_logger()
    
    enhanced_logger.separator("향상된 로깅 시스템 테스트")
    
    # 1. 시스템 초기화 로그 테스트
    print("\n🚀 시스템 초기화 로그 테스트")
    
    enhanced_logger.system_operation(
        "INIT", "APPLICATION", "SUCCESS",
        details={
            "version": "1.0.0",
            "components": "Redis, MySQL, Vector DB",
            "startup_time": "2.5s"
        }
    )
    
    enhanced_logger.system_operation(
        "INIT", "REDIS", "FAILED",
        error="Connection refused to localhost:6379"
    )
    
    # 2. Redis 작업 로그 테스트  
    print("\n💾 Redis 작업 로그 테스트")
    
    enhanced_logger.redis_operation(
        "SET", "BC카드 민원접수 방법 알려줘", 
        result={'similarity_score': 0.85, 'ttl': '1 hour'}, 
        duration=0.045
    )
    
    enhanced_logger.redis_operation(
        "HIT", "BC카드 민원접수 방법 알려줘",
        result={'cached_at': '2024-01-15T14:30:25'}, 
        duration=0.002
    )
    
    enhanced_logger.redis_operation(
        "MISS", "새로운 질문입니다", duration=0.003
    )
    
    enhanced_logger.redis_operation(
        "COUNT", "BC카드 연회비 얼마인가요",
        result={'current_count': 3, 'ttl': '1 hour'}
    )
    
    enhanced_logger.redis_operation(
        "STATS", "Cache Statistics",
        result={
            'cached_queries': 15,
            'total_searches': 42,
            'popular_queries': 3
        },
        duration=0.012
    )
    
    # 3. MySQL 작업 로그 테스트
    print("\n🗄️  MySQL 작업 로그 테스트")
    
    enhanced_logger.mysql_operation(
        "INSERT", "BC카드 발급 절차 알려주세요",
        result={'category': 'card', 'similarity': 0.78},
        count=5
    )
    
    enhanced_logger.mysql_operation(
        "SELECT", "Popular Questions Query",
        result=[
            {'query': 'BC카드 연회비', 'count': 8},
            {'query': '카드 발급 절차', 'count': 6},
            {'query': '민원 접수 방법', 'count': 5}
        ]
    )
    
    enhanced_logger.mysql_operation(
        "DELETE", "", count=12
    )
    
    enhanced_logger.mysql_operation(
        "INSERT", "에러 테스트 질문", 
        error="Duplicate entry for key 'query_hash'"
    )
    
    # 4. 검색 작업 로그 테스트
    print("\n🔍 검색 작업 로그 테스트")
    
    enhanced_logger.search_operation(
        "BC카드 고객센터 번호 알려주세요", 0.92, "custom", 
        cached=False, duration=0.156
    )
    
    enhanced_logger.search_operation(
        "BC카드 고객센터 번호 알려주세요", 0.92, "Redis Cache", 
        cached=True, duration=0.008
    )
    
    enhanced_logger.search_operation(
        "오늘 날씨 어때요", 0.23, "basic", duration=0.089
    )
    
    # 5. 질문 처리 플로우 로그 테스트
    print("\n🎬 질문 처리 플로우 로그 테스트")
    
    test_query = "김명정 고객 카드 발급 신청"
    
    enhanced_logger.question_flow(test_query, "START", {})
    
    enhanced_logger.question_flow(test_query, "CACHE_CHECK", {"hit": False})
    
    enhanced_logger.question_flow(test_query, "VECTOR_SEARCH", {"similarity": 0.78})
    
    enhanced_logger.question_flow(test_query, "RESPONSE_TYPE", {
        "type": "normal",
        "threshold_met": True,
        "show_popular_buttons": False
    })
    
    enhanced_logger.question_flow(test_query, "END", {
        "cached": True,
        "popular_saved": False
    })
    
    # 6. 성능 메트릭 로그 테스트
    print("\n📊 성능 메트릭 로그 테스트")
    
    enhanced_logger.performance_metrics("QUESTION_PROCESSING", {
        "total_time": 0.234,
        "search_time": 0.156,
        "cache_check_time": 0.003,
        "processing_time": 0.075,
        "similarity_score": 0.78,
        "vector_db_size": 508
    })
    
    # 7. 실제 시스템과 통합 테스트
    print("\n🧪 실제 시스템 통합 테스트")
    
    try:
        # Redis 매니저 테스트
        redis_manager = RedisCacheManager()
        
        # 벡터 검색 시스템 테스트  
        embedding_manager = EmbeddingManager()
        vectorstore_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
        
        # 향상된 핸들러 테스트
        enhanced_handler = EnhancedSimilarityHandler()
        
        # 실제 질문 처리
        def search_func(query):
            return vectorstore_manager.dual_search(query, k=3)
        
        test_queries = [
            "BC카드 민원접수 방법",
            "김명정 고객 정보", 
            "오늘 날씨 어때요"
        ]
        
        for query in test_queries:
            enhanced_logger.separator(f"질문: {query}")
            result = enhanced_handler.process_question(query, search_func)
            time.sleep(0.5)  # 로그 가독성을 위한 대기
            
    except Exception as e:
        enhanced_logger.system_operation(
            "TEST", "INTEGRATION", "FAILED", error=str(e)
        )
    
    enhanced_logger.separator("로깅 테스트 완료")
    
    print(f"\n🎯 향상된 로깅 시스템 특징:")
    print(f"   ✅ 색상 코딩: 레벨별 다른 색상")
    print(f"   ✅ 아이콘 표시: 직관적인 시각적 구분") 
    print(f"   ✅ 구조화된 정보: Redis/MySQL 작업 상세 표시")
    print(f"   ✅ 성능 메트릭: 처리 시간 및 통계")
    print(f"   ✅ 플로우 추적: 질문 처리 과정 단계별 로그")

if __name__ == "__main__":
    test_enhanced_logging()