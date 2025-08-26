#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain

def test_thrifty_usage_search():
    print("=== 신용카드알뜰이용법 검색 테스트 ===\n")
    
    rag = RAGChain()
    
    # 다양한 검색 쿼리 테스트
    queries = [
        "신용카드알뜰이용법",
        "신용카드 알뜰 이용법",
        "알뜰이용법",
        "카드 알뜰하게 사용하는 방법",
        "신용카드 절약"
    ]
    
    print(f"벡터 스토어 문서 수: {rag.vectorstore_manager.get_document_count()}")
    print()
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"검색 쿼리: '{query}'")
        print(f"{'='*60}")
        
        # similarity_search_with_score 직접 호출
        print("\n=== similarity_search_with_score 결과 ===")
        similarity_results = rag.vectorstore_manager.similarity_search_with_score(query, k=5)
        
        print(f"결과 수: {len(similarity_results)}")
        for i, (doc, score) in enumerate(similarity_results, 1):
            filename = doc.metadata.get('filename', 'Unknown')
            print(f"\n{i}. 점수: {score:.4f} ({score*100:.2f}%) | 파일: {filename}")
            content_preview = doc.page_content[:300].replace('\n', ' ')
            print(f"   내용: {content_preview}...")
            
            # 관련 내용 체크
            if "알뜰" in content_preview or "신용카드알뜰이용법" in content_preview:
                print("   *** 알뜰이용법 관련 내용 발견! ***")
            elif "회원제" in content_preview and "업소" in content_preview:
                print("   *** 회원제 업소 내용 (관련 없음) ***")
            elif "일시불" in content_preview or "할부" in content_preview:
                print("   *** 구체적인 이용법 내용일 수 있음 ***")
    
    # 특정 쿼리로 RAG 전체 응답 테스트
    print("\n\n=== RAG 전체 응답 테스트 ===")
    query = "신용카드알뜰이용법"
    response = rag.query(query, use_cache=False)
    
    print(f"\n질문: {query}")
    print(f"답변: {response['answer']}")
    
    print("\n검색된 문서:")
    for match in response.get('similarity_search', {}).get('top_matches', []):
        print(f"\n순위 {match['rank']}: {match['similarity_percentage']}% | {match['document_title']}")
        print(f"   내용: {match['content_preview'][:200]}...")

if __name__ == "__main__":
    test_thrifty_usage_search()