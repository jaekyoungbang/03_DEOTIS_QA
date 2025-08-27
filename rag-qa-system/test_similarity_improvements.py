#!/usr/bin/env python3
"""
개선된 유사도 시스템 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.dual_vectorstore import DualVectorStoreManager
from models.embeddings import EmbeddingManager
from services.enhanced_query_processor import EnhancedQueryProcessor
from services.similarity_response_handler import SimilarityResponseHandler

def test_similarity_improvements():
    """유사도 개선 효과 테스트"""
    print("🚀 유사도 개선 효과 테스트 시작\n")
    
    # 시스템 초기화
    print("🔧 시스템 초기화...")
    embedding_manager = EmbeddingManager()
    vectorstore_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
    query_processor = EnhancedQueryProcessor()
    similarity_handler = SimilarityResponseHandler()
    
    # 벡터DB 상태 확인
    doc_counts = vectorstore_manager.get_document_count()
    print(f"📊 벡터DB 상태:")
    print(f"   - Basic (s3): {doc_counts['basic']}개 청크")
    print(f"   - Custom (s3-chunking): {doc_counts['custom']}개 청크")
    print(f"   - 전체: {doc_counts['total']}개 청크\n")
    
    # 테스트 쿼리들
    test_queries = [
        {
            "query": "나는 김명정인데 BC카드 발급받고 싶어",
            "type": "개인화 카드 발급",
            "expected_improvement": "HIGH"
        },
        {
            "query": "BC카드 신청 방법 알려줘",
            "type": "일반 카드 발급",
            "expected_improvement": "MEDIUM"
        },
        {
            "query": "카드발급 절차 안내해줘",
            "type": "동의어 확장",
            "expected_improvement": "MEDIUM"
        },
        {
            "query": "회원은행별 카드 발급 정보",
            "type": "키워드 매칭",
            "expected_improvement": "HIGH"
        }
    ]
    
    print("="*80)
    print("📋 테스트 결과 비교")
    print("="*80)
    
    for i, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        query_type = test_case["type"]
        expected = test_case["expected_improvement"]
        
        print(f"\n🔍 테스트 {i}: {query_type}")
        print(f"   질의: \"{query}\"")
        print(f"   예상 개선도: {expected}")
        print("-" * 60)
        
        try:
            # 1. 질의 확장 테스트
            print("1️⃣ 질의 확장 결과:")
            expanded_queries = query_processor.expand_query(query)
            for j, exp_q in enumerate(expanded_queries[:3]):
                print(f"   {j+1}. {exp_q}")
            
            # 2. 의도 키워드 추출 테스트
            print("\n2️⃣ 의도 키워드 추출:")
            intents = query_processor.extract_intent_keywords(query)
            for intent_type, keywords in intents.items():
                if keywords:
                    print(f"   {intent_type}: {keywords}")
            
            # 3. Basic 컬렉션 검색 (s3 폴더)
            print("\n3️⃣ Basic 컬렉션 (s3) 검색 결과:")
            basic_results = vectorstore_manager.similarity_search_with_score(query, "basic", k=3)
            for j, (doc, score) in enumerate(basic_results, 1):
                print(f"   {j}. 유사도: {score:.2%} | 출처: {doc.metadata.get('source', 'unknown')}")
                print(f"      미리보기: {doc.page_content[:100]}...")
                print()
            
            # 4. Custom 컬렉션 검색 (s3-chunking 폴더)
            print("4️⃣ Custom 컬렉션 (s3-chunking) 검색 결과:")
            custom_results = vectorstore_manager.similarity_search_with_score(query, "custom", k=3)
            for j, (doc, score) in enumerate(custom_results, 1):
                print(f"   {j}. 유사도: {score:.2%} | 출처: {doc.metadata.get('source', 'unknown')}")
                print(f"      미리보기: {doc.page_content[:100]}...")
                print()
            
            # 5. 듀얼 검색 (통합 검색) 테스트
            print("5️⃣ 듀얼 검색 (통합) 결과:")
            dual_results = vectorstore_manager.dual_search(query, k=5)
            max_similarity = dual_results[0][1] if dual_results else 0.0
            print(f"   최고 유사도: {max_similarity:.2%}")
            
            for j, (doc, score) in enumerate(dual_results[:3], 1):
                search_source = doc.metadata.get('search_source', 'unknown')
                print(f"   {j}. 유사도: {score:.2%} | 검색소스: {search_source}")
                print(f"      미리보기: {doc.page_content[:100]}...")
                print()
            
            # 6. 유사도 임계값 처리 테스트
            print("6️⃣ 유사도 임계값 처리:")
            similarity_result = similarity_handler.process_search_results(
                dual_results, query, "basic"
            )
            print(f"   응답 유형: {similarity_result['response_type']}")
            print(f"   답변 가능: {similarity_result['should_answer']}")
            print(f"   최고 유사도: {similarity_result['max_similarity']:.2%}")
            print(f"   임계값 통과: {similarity_result['threshold_met']}")
            
            # 개선 효과 평가
            print("\n📈 개선 효과 평가:")
            if max_similarity >= 0.80:
                improvement = "🟢 EXCELLENT (80%+)"
            elif max_similarity >= 0.70:
                improvement = "🟡 GOOD (70-80%)"
            elif max_similarity >= 0.60:
                improvement = "🟠 FAIR (60-70%)"
            else:
                improvement = "🔴 POOR (<60%)"
                
            print(f"   실제 결과: {improvement}")
            print(f"   예상 개선도: {expected}")
            
        except Exception as e:
            print(f"❌ 테스트 오류: {e}")
            import traceback
            print(traceback.format_exc())
        
        print("="*80)
    
    print("\n🎯 테스트 완료!")
    print("\n💡 개선사항 요약:")
    print("   ✅ BGE-M3 최적화 유사도 계산")
    print("   ✅ 질의 확장 및 동의어 처리")
    print("   ✅ 개인화 키워드 매칭 강화")
    print("   ✅ 듀얼 벡터스토어 통합 검색")
    print("   ✅ 임계값 조정 (일반 75%, 개인화 65%)")

if __name__ == "__main__":
    test_similarity_improvements()