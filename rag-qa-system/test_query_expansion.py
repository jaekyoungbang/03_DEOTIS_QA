#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain

def test_query_expansion():
    print("=== 쿼리 확장 테스트 ===\n")
    
    rag = RAGChain()
    
    # 쿼리 확장: 관련 키워드 추가
    expanded_query = "일시불 구매 신용카드 TIP 알뜰이용법"
    
    print(f"확장된 검색 쿼리: {expanded_query}")
    
    print("\n=== RAG query 테스트 ===")
    response = rag.query(expanded_query, use_cache=False)
    
    print(f"답변: {response['answer'][:500]}...")
    print(f"\n검색된 상위 매치:")
    for match in response.get('similarity_search', {}).get('top_matches', []):
        print(f"순위 {match['rank']}: {match['similarity_percentage']}% | {match['document_title']}")
        print(f"   내용: {match['content_preview']}")
        if "TIP" in match['content_preview'] or "알뜰이용법" in match['content_preview']:
            print("   *** TIP 내용 발견! ***")
        print()

    print("\n=== 원본 질문 테스트 ===")
    original_response = rag.query("일시불 구매", use_cache=False) 
    print(f"답변: {original_response['answer'][:300]}...")

if __name__ == "__main__":
    test_query_expansion()