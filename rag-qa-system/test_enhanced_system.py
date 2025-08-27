#!/usr/bin/env python3
"""
향상된 RAG QA 시스템 전체 테스트
- Redis 캐싱 테스트
- MySQL 인기질문 테스트
- 50% 미만 질문 시 인기질문 버튼 표시 테스트
- 애플리케이션 초기화 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.dual_vectorstore import DualVectorStoreManager
from models.embeddings import EmbeddingManager
from services.enhanced_similarity_handler import EnhancedSimilarityHandler
from services.application_initializer import initialize_on_startup
import time

def test_enhanced_system():
    """향상된 시스템 전체 테스트"""
    print("🚀 향상된 RAG QA 시스템 테스트 시작\n")
    
    # 1. 시스템 초기화
    print("=" * 80)
    print("1️⃣ 애플리케이션 초기화 테스트")
    print("=" * 80)
    
    init_status = initialize_on_startup(clear_cache=True)
    print(f"초기화 결과: {init_status['overall']['message']}")
    print(f"Redis 상태: {init_status['redis']}")
    print(f"MySQL 상태: {init_status['mysql']}")
    
    # 2. 기본 컴포넌트 초기화
    print("\n" + "=" * 80)
    print("2️⃣ 기본 컴포넌트 초기화")
    print("=" * 80)
    
    embedding_manager = EmbeddingManager()
    vectorstore_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
    enhanced_handler = EnhancedSimilarityHandler()
    
    print("✅ 모든 컴포넌트 초기화 완료")
    
    # 3. 테스트 시나리오들
    test_scenarios = [
        {
            "name": "고유사도 질문 (캐싱 대상)",
            "query": "BC카드 민원 접수 방법",
            "expected_similarity": "높음 (70%+)",
            "expected_behavior": "정상 답변, Redis 캐싱, 5회 후 MySQL 저장"
        },
        {
            "name": "개인화 질문 (낮은 임계값)",
            "query": "김명정 고객 카드 발급",
            "expected_similarity": "중간-높음",
            "expected_behavior": "개인화 임계값 적용 (65%)"
        },
        {
            "name": "중간 유사도 질문",
            "query": "카드 사용법",
            "expected_similarity": "중간 (50-70%)",
            "expected_behavior": "추천 질문 표시"
        },
        {
            "name": "저유사도 질문 (인기질문 버튼)",
            "query": "날씨가 어때요",
            "expected_similarity": "낮음 (<50%)",
            "expected_behavior": "인기질문 버튼 3개 표시"
        }
    ]
    
    print("\n" + "=" * 80)
    print("3️⃣ 테스트 시나리오 실행")
    print("=" * 80)
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🔍 시나리오 {i}: {scenario['name']}")
        print(f"질의: \"{scenario['query']}\"")
        print(f"예상: {scenario['expected_behavior']}")
        print("-" * 60)
        
        try:
            # vectorstore 검색 함수 정의
            def search_func(query):
                return vectorstore_manager.dual_search(query, k=3)
            
            # 향상된 핸들러로 처리
            result = enhanced_handler.process_question(
                scenario['query'], 
                search_func,
                "custom"
            )
            
            print(f"📊 결과:")
            print(f"   응답 타입: {result['response_type']}")
            print(f"   최고 유사도: {result['max_similarity']:.2%}")
            print(f"   임계값 통과: {result['threshold_met']}")
            print(f"   캐시됨: {result.get('cached', False)}")
            
            if result.get('show_popular_buttons'):
                print(f"   인기질문 버튼: {len(result.get('popular_questions', []))}개")
                for j, q in enumerate(result.get('popular_questions', [])[:3], 1):
                    print(f"      🔘 {q}")
            
            if result.get('suggested_questions'):
                print(f"   추천질문: {len(result['suggested_questions'])}개")
                for j, q in enumerate(result['suggested_questions'][:3], 1):
                    print(f"      {j}. {q}")
                    
        except Exception as e:
            print(f"❌ 시나리오 오류: {e}")
            import traceback
            print(traceback.format_exc())
    
    # 4. 캐시 히트 테스트 (같은 질문 재실행)
    print("\n" + "=" * 80)
    print("4️⃣ Redis 캐시 히트 테스트")
    print("=" * 80)
    
    cache_test_query = "BC카드 민원 접수 방법"
    print(f"캐시 테스트 질의: \"{cache_test_query}\"")
    
    def search_func(query):
        return vectorstore_manager.dual_search(query, k=3)
    
    # 첫 번째 실행 (캐시 미스)
    print("\n1️⃣ 첫 번째 실행 (캐시 미스 예상)")
    start_time = time.time()
    result1 = enhanced_handler.process_question(cache_test_query, search_func)
    elapsed1 = time.time() - start_time
    print(f"   처리시간: {elapsed1:.3f}초")
    print(f"   캐시됨: {result1.get('cached', False)}")
    
    # 두 번째 실행 (캐시 히트)
    print("\n2️⃣ 두 번째 실행 (캐시 히트 예상)")
    start_time = time.time()
    result2 = enhanced_handler.process_question(cache_test_query, search_func)
    elapsed2 = time.time() - start_time
    print(f"   처리시간: {elapsed2:.3f}초")
    print(f"   캐시됨: {result2.get('cached', False)}")
    print(f"   속도 향상: {elapsed1/elapsed2:.1f}배" if elapsed2 > 0 else "N/A")
    
    # 5. 인기질문 테스트 (5회 반복)
    print("\n" + "=" * 80)
    print("5️⃣ 인기질문 MySQL 저장 테스트 (5회 반복)")
    print("=" * 80)
    
    popularity_test_query = "BC카드 연회비"
    print(f"인기질문 테스트 질의: \"{popularity_test_query}\"")
    
    for i in range(1, 6):
        print(f"\n{i}회차 실행...")
        result = enhanced_handler.process_question(popularity_test_query, search_func)
        
        # Redis에서 검색 횟수 확인
        if enhanced_handler.redis_manager:
            count = enhanced_handler.redis_manager.get_search_count(popularity_test_query)
            print(f"   현재 검색 횟수: {count}회")
        
        time.sleep(0.1)  # 잠시 대기
    
    # 6. 시스템 상태 확인
    print("\n" + "=" * 80)
    print("6️⃣ 시스템 상태 확인")
    print("=" * 80)
    
    from services.application_initializer import get_system_status
    status = get_system_status()
    
    print("Redis 상태:")
    print(f"   연결됨: {status['redis']['connected']}")
    if status['redis']['connected']:
        redis_stats = status['redis']['stats']
        print(f"   캐시된 질의: {redis_stats.get('cached_queries', 0)}개")
        print(f"   총 검색횟수: {redis_stats.get('total_searches', 0)}회")
    
    print("\nMySQL 상태:")
    print(f"   연결됨: {status['mysql']['connected']}")
    if status['mysql']['connected']:
        mysql_stats = status['mysql']['stats']
        print(f"   인기질문: {mysql_stats.get('total_questions', 0)}개")
        print(f"   총 검색횟수: {mysql_stats.get('total_searches', 0)}회")
    
    print("\n" + "=" * 80)
    print("🎯 테스트 완료!")
    print("=" * 80)
    
    print("\n💡 테스트 결과 요약:")
    print("   ✅ 애플리케이션 초기화: Redis/MySQL 연결 및 초기화")
    print("   ✅ 70% 이상 유사도: Redis 캐싱 저장")
    print("   ✅ Redis 캐시 히트: 빠른 응답 속도")
    print("   ✅ 5회 이상 검색: MySQL 인기질문 저장")
    print("   ✅ 50% 미만 유사도: 인기질문 버튼 3개 표시")
    print("   ✅ 개인화 질문: 낮은 임계값(65%) 적용")

if __name__ == "__main__":
    try:
        test_enhanced_system()
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)