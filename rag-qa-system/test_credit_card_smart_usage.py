#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
신용카드알뜰이용법 검색 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain
from models.vectorstore import DualVectorStoreManager
from models.embeddings import EmbeddingManager

def test_credit_card_smart_usage():
    print("=== 신용카드알뜰이용법 검색 테스트 ===\n")
    
    # RAGChain 초기화
    rag = RAGChain()
    
    # 검색 쿼리
    query = "신용카드알뜰이용법"
    
    print(f"검색어: '{query}'")
    print("-" * 50)
    
    # 1. 현재 벡터DB에서 검색
    print("\n1. 현재 벡터DB 검색 결과:")
    
    # DualVectorStoreManager 사용
    embedding_manager = EmbeddingManager()
    dual_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
    
    # basic 컬렉션 검색
    basic_results = dual_manager.similarity_search_with_score(query, "basic", k=5)
    
    print("\n[기본 청킹 결과]")
    for i, (doc, score) in enumerate(basic_results, 1):
        content = doc.page_content
        print(f"\n순위 {i}: 점수 {score:.2%}")
        print(f"파일: {doc.metadata.get('source', 'Unknown')}")
        
        # 내용 미리보기
        print(f"내용 미리보기 (처음 300자):")
        print(content[:300])
        
        # 잘못된 내용이 포함되어 있는지 확인
        if "회원제 업소" in content and "신용카드알뜰이용법" in content:
            print("\n⚠️ 경고: '회원제 업소'와 '신용카드알뜰이용법'이 같은 청크에 있습니다!")
            
            # 두 섹션의 위치 확인
            idx1 = content.find("회원제 업소")
            idx2 = content.find("신용카드알뜰이용법")
            print(f"   - '회원제 업소' 위치: {idx1}")
            print(f"   - '신용카드알뜰이용법' 위치: {idx2}")
            print(f"   - 거리: {abs(idx2 - idx1)}자")
    
    # 2. RAG Chain으로 전체 쿼리 실행
    print("\n\n2. RAG Chain 전체 응답:")
    print("-" * 50)
    
    result = rag.query(query, use_memory=False, use_cache=False, search_mode='basic')
    
    if 'answer' in result:
        print(f"\n답변: {result['answer']}")
    
    if 'similarity_search' in result and result['similarity_search']['top_matches']:
        print(f"\n최고 유사도: {result['similarity_search']['top_matches'][0]['similarity_percentage']:.1f}%")
    
    # 3. 정확한 컨텐츠 찾기
    print("\n\n3. 정확한 '신용카드알뜰이용법' 컨텐츠 검색:")
    print("-" * 50)
    
    # 더 구체적인 검색어로 시도
    specific_queries = [
        "1-1) 일시불 구매",
        "1-2) 할부구매",
        "1-3) 단기카드대출",
        "신용카드 TIP"
    ]
    
    for specific_query in specific_queries:
        results = dual_manager.similarity_search_with_score(specific_query, "basic", k=1)
        if results:
            doc, score = results[0]
            print(f"\n'{specific_query}' 검색 결과:")
            print(f"점수: {score:.2%}")
            print(f"내용 일부: {doc.page_content[:200]}...")

if __name__ == "__main__":
    test_credit_card_smart_usage()