#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain

def test_tip_search():
    print("=== 신용카드알뜰이용법 검색 테스트 ===\n")
    
    rag = RAGChain()
    
    # 검색 쿼리
    query = "신용카드알뜰이용법"
    
    print(f"검색 쿼리: {query}")
    
    print("\n=== similarity_search_with_score 직접 호출 ===")
    similarity_results = rag.vectorstore_manager.similarity_search_with_score(query, k=10)
    
    print(f"결과 수: {len(similarity_results)}")
    for i, (doc, score) in enumerate(similarity_results, 1):
        filename = doc.metadata.get('filename', 'Unknown')
        print(f"{i}. 점수: {score:.4f} ({score*100:.2f}%) | 파일: {filename}")
        content_preview = doc.page_content[:300]
        print(f"   내용: {content_preview}...")
        
        # 일시불 관련 내용인지 확인
        if "일시불" in content_preview:
            print("   *** 일시불 관련 내용 발견! ***")
        print()

    # 이제 "TIP"로도 검색
    print("\n=== 'TIP' 검색 테스트 ===")
    tip_results = rag.vectorstore_manager.similarity_search_with_score("TIP", k=5)
    
    for i, (doc, score) in enumerate(tip_results, 1):
        filename = doc.metadata.get('filename', 'Unknown')
        print(f"{i}. 점수: {score:.4f} ({score*100:.2f}%) | 파일: {filename}")
        content_preview = doc.page_content[:300]
        print(f"   내용: {content_preview}...")
        print()

if __name__ == "__main__":
    test_tip_search()