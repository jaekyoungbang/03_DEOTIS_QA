#!/usr/bin/env python3
"""
이중 벡터스토어 테스트 스크립트
"""

import os
import sys

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.embeddings import EmbeddingManager
from models.vectorstore import DualVectorStoreManager

def test_dual_vectorstore():
    """이중 벡터스토어 테스트"""
    
    print("🔧 이중 벡터스토어 테스트 시작...")
    
    # 초기화
    embedding_manager = EmbeddingManager()
    dual_vectorstore = DualVectorStoreManager(embedding_manager.get_embeddings())
    
    # 문서 수 확인
    doc_counts = dual_vectorstore.get_document_count()
    print(f"📊 현재 문서 수:")
    print(f"- 기본 청킹: {doc_counts['basic']}개")
    print(f"- 커스텀 청킹: {doc_counts['custom']}개")
    print(f"- 전체: {doc_counts['total']}개")
    
    # 테스트 쿼리
    test_queries = [
        "BC카드 신용카드 발급 절차",
        "카드 결제 한도",
        "BC카드 고객센터 연락처"
    ]
    
    for query in test_queries:
        print(f"\n🔍 테스트 쿼리: '{query}'")
        
        # 기본 청킹 검색
        basic_results = dual_vectorstore.similarity_search_with_score(query, "basic", k=3)
        print(f"📝 기본 청킹 결과 ({len(basic_results)}개):")
        for i, (doc, score) in enumerate(basic_results[:2]):
            print(f"  {i+1}. 점수: {score:.3f}, 내용: {doc.page_content[:100]}...")
        
        # 커스텀 청킹 검색
        custom_results = dual_vectorstore.similarity_search_with_score(query, "custom", k=3)
        print(f"🎯 커스텀 청킹 결과 ({len(custom_results)}개):")
        for i, (doc, score) in enumerate(custom_results[:2]):
            print(f"  {i+1}. 점수: {score:.3f}, 내용: {doc.page_content[:100]}...")
        
        # 이중 검색
        dual_results = dual_vectorstore.dual_search(query, k=4)
        print(f"🔄 이중 검색 결과 ({len(dual_results)}개):")
        for i, (doc, score) in enumerate(dual_results[:2]):
            source_type = doc.metadata.get('search_source', 'unknown')
            print(f"  {i+1}. [{source_type}] 점수: {score:.3f}, 내용: {doc.page_content[:100]}...")
        
        print("-" * 80)

if __name__ == "__main__":
    try:
        test_dual_vectorstore()
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        sys.exit(1)