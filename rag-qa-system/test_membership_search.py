#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain

def test_membership_search():
    print("=== 회원제 업소 관련 검색 테스트 ===\n")
    
    rag = RAGChain()
    
    # 회원제 업소 관련 검색
    query = "회원제 업소 할부 이용"
    
    print(f"검색 쿼리: '{query}'")
    print(f"벡터 스토어 문서 수: {rag.vectorstore_manager.get_document_count()}")
    
    print("\n=== similarity_search_with_score 결과 ===")
    similarity_results = rag.vectorstore_manager.similarity_search_with_score(query, k=10)
    
    print(f"결과 수: {len(similarity_results)}")
    for i, (doc, score) in enumerate(similarity_results, 1):
        filename = doc.metadata.get('filename', 'Unknown')
        print(f"\n{i}. 점수: {score:.4f} ({score*100:.2f}%) | 파일: {filename}")
        content_preview = doc.page_content[:500].replace('\n', ' ')
        print(f"   내용: {content_preview}...")
        
        # 문서가 정말 회원제 업소 관련인지 확인
        if "회원제" in content_preview and "업소" in content_preview:
            print("   *** 회원제 업소 관련 내용 확인됨 ***")
    
    # 이제 "신용카드 TIP" 섹션 전체를 찾아보자
    print("\n\n=== 신용카드 TIP 섹션 검색 ===")
    tip_query = "신용카드 TIP"
    tip_results = rag.vectorstore_manager.similarity_search_with_score(tip_query, k=10)
    
    print(f"결과 수: {len(tip_results)}")
    for i, (doc, score) in enumerate(tip_results, 1):
        filename = doc.metadata.get('filename', 'Unknown')
        content_preview = doc.page_content[:500].replace('\n', ' ')
        
        # TIP 섹션이면서 알뜰이용법이 포함된 경우
        if "신용카드알뜰이용법" in content_preview or ("TIP" in content_preview and "알뜰" in content_preview):
            print(f"\n{i}. 점수: {score:.4f} ({score*100:.2f}%) | 파일: {filename}")
            print(f"   내용: {content_preview}...")
            print("   *** 신용카드 TIP/알뜰이용법 관련 내용! ***")

if __name__ == "__main__":
    test_membership_search()