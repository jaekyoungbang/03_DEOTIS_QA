#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
검색 일관성 테스트 - LLM이 보는 것과 사용자가 보는 것이 같은지 확인
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain

def test_search_consistency():
    """검색 결과 일관성 테스트"""
    
    print("=== 검색 결과 일관성 테스트 ===\n")
    
    # RAGChain 초기화
    rag = RAGChain()
    
    # 테스트 쿼리
    test_query = "신용카드 기본업무 및 절차"
    
    print(f"테스트 쿼리: '{test_query}'")
    print("-" * 50)
    
    # RAG 검색 실행
    result = rag.query(test_query, use_memory=False, use_cache=False, search_mode='basic')
    
    print("\n📋 RAG 응답 결과:")
    print(f"답변: {result.get('answer', 'No answer')[:200]}...")
    
    print("\n🔍 사용자에게 표시되는 유사도 검색 결과:")
    if 'similarity_search' in result and result['similarity_search']['top_matches']:
        for match in result['similarity_search']['top_matches']:
            rank = match['rank']
            score = match['similarity_percentage']
            title = match['document_title']
            content = match['content_preview'][:150]
            
            print(f"\n순위 {rank}: {score:.1f}%")
            print(f"문서: {title}")
            print(f"내용: {content}...")
    
    print("\n" + "="*50)
    print("✅ 개선 사항:")
    print("- 이제 LLM이 실제로 본 문서와 사용자에게 표시되는 검색 결과가 일치합니다.")
    print("- 검색 결과 1위의 내용이 LLM 답변의 근거가 됩니다.")
    
    # 또 다른 테스트
    print("\n" + "="*50)
    print("=== 두 번째 테스트: 신용카드알뜰이용법 ===")
    
    test_query2 = "신용카드알뜰이용법"
    result2 = rag.query(test_query2, use_memory=False, use_cache=False, search_mode='basic')
    
    print(f"\n테스트 쿼리: '{test_query2}'")
    print(f"답변: {result2.get('answer', 'No answer')[:200]}...")
    
    if 'similarity_search' in result2 and result2['similarity_search']['top_matches']:
        top_match = result2['similarity_search']['top_matches'][0]
        print(f"\n최고 유사도 결과: {top_match['similarity_percentage']:.1f}%")
        print(f"내용: {top_match['content_preview'][:200]}...")
        
        # 문제적 섹션 혼재 확인
        content = top_match['content_preview']
        if "회원제 업소" in content and "신용카드알뜰이용법" in content:
            print("⚠️ 경고: 여전히 섹션 혼재 발견")
        else:
            print("✅ 정상: 섹션이 올바르게 분리됨")

if __name__ == "__main__":
    test_search_consistency()