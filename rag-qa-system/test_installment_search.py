#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain

def test_installment_search():
    print("=== 일시불 구매 검색 테스트 ===\n")
    
    rag = RAGChain()
    
    # 검색 쿼리
    query = "일시불 구매"
    
    print(f"검색 쿼리: {query}")
    print(f"RAG 체인 vectorstore 주소: {id(rag.vectorstore_manager.vectorstore)}")
    print(f"RAG 체인 collection 이름: {rag.vectorstore_manager.collection_name}")
    print(f"RAG 체인 문서 수: {rag.vectorstore_manager.get_document_count()}")
    
    print("\n=== similarity_search_with_score 직접 호출 ===")
    similarity_results = rag.vectorstore_manager.similarity_search_with_score(query, k=10)
    
    print(f"결과 수: {len(similarity_results)}")
    for i, (doc, score) in enumerate(similarity_results, 1):
        filename = doc.metadata.get('filename', 'Unknown')
        print(f"{i}. 점수: {score:.4f} ({score*100:.2f}%) | 파일: {filename}")
        content_preview = doc.page_content[:200].replace('\n', ' ')
        print(f"   내용: {content_preview}...")
        
        # 신용카드 TIP나 일시불 관련 내용인지 확인
        if "신용카드" in content_preview and ("일시불" in content_preview or "TIP" in content_preview):
            print("   *** 관련 내용 발견! ***")
        print()
    
    # 이제 실제 RAG query도 테스트
    print("\n=== RAG query 테스트 ===")
    response = rag.query(query, use_cache=False)
    
    print(f"답변: {response['answer'][:300]}...")
    print(f"\n검색된 상위 매치:")
    for match in response.get('similarity_search', {}).get('top_matches', []):
        print(f"순위 {match['rank']}: {match['similarity_percentage']}% | {match['document_title']}")
        print(f"   내용: {match['content_preview']}")
        if "신용카드" in match['content_preview'] and ("일시불" in match['content_preview'] or "TIP" in match['content_preview']):
            print("   *** 관련 내용! ***")
        print()

if __name__ == "__main__":
    test_installment_search()