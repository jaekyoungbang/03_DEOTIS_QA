#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
민원접수방법 검색 문제 디버깅
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain
from models.vectorstore import DualVectorStoreManager
from models.embeddings import EmbeddingManager

def debug_complaint_search():
    """민원접수방법 검색 문제 분석"""
    
    print("=== 민원접수방법 검색 문제 디버깅 ===\n")
    
    # 초기화
    embedding_manager = EmbeddingManager()
    dual_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
    
    query = "민원접수방법 안내"
    print(f"검색어: '{query}'")
    print("-" * 50)
    
    # 1. 직접 벡터 검색으로 원본 데이터 확인
    print("\n1. 직접 벡터 검색 결과:")
    
    # basic 컬렉션 검색
    basic_results = dual_manager.similarity_search_with_score(query, "basic", k=5)
    
    print(f"\n[Basic 컬렉션] 검색 결과 {len(basic_results)}개:")
    for i, (doc, score) in enumerate(basic_results, 1):
        content = doc.page_content
        print(f"\n순위 {i}: 점수 {score:.2%}")
        print(f"문서 길이: {len(content)}자")
        print(f"메타데이터: {doc.metadata}")
        print(f"내용 전체:\n{content}")
        print("=" * 80)
    
    # custom 컬렉션 검색
    custom_results = dual_manager.similarity_search_with_score(query, "custom", k=5)
    
    print(f"\n[Custom 컬렉션] 검색 결과 {len(custom_results)}개:")
    for i, (doc, score) in enumerate(custom_results, 1):
        content = doc.page_content
        print(f"\n순위 {i}: 점수 {score:.2%}")
        print(f"문서 길이: {len(content)}자")
        print(f"메타데이터: {doc.metadata}")
        print(f"내용 전체:\n{content}")
        print("=" * 80)
    
    # 2. RAG Chain으로 검색
    print("\n2. RAG Chain 검색 결과:")
    
    rag = RAGChain()
    
    # basic 모드 테스트
    print("\n[Basic 모드]")
    result_basic = rag.query(query, use_memory=False, use_cache=False, search_mode='basic')
    
    print(f"답변: {result_basic.get('answer', 'No answer')}")
    
    if 'similarity_search' in result_basic and result_basic['similarity_search']['top_matches']:
        print(f"\n유사도 검색 결과:")
        for match in result_basic['similarity_search']['top_matches']:
            rank = match['rank']
            score = match['similarity_percentage']
            content = match['content_preview']
            
            print(f"\n순위 {rank}: {score:.1f}%")
            print(f"내용 길이: {len(content)}자")
            print(f"내용: {content}")
    
    # custom 모드 테스트
    print("\n\n[Custom 모드]")
    result_custom = rag.query(query, use_memory=False, use_cache=False, search_mode='custom')
    
    print(f"답변: {result_custom.get('answer', 'No answer')}")
    
    if 'similarity_search' in result_custom and result_custom['similarity_search']['top_matches']:
        print(f"\n유사도 검색 결과:")
        for match in result_custom['similarity_search']['top_matches']:
            rank = match['rank']
            score = match['similarity_percentage']
            content = match['content_preview']
            
            print(f"\n순위 {rank}: {score:.1f}%")
            print(f"내용 길이: {len(content)}자")
            print(f"내용: {content}")

    # 3. 전체 문서에서 민원접수 관련 내용 찾기
    print("\n\n3. 전체 문서에서 '민원접수' 키워드 찾기:")
    
    # basic에서 "민원접수" 키워드 포함 문서 찾기
    all_basic = dual_manager.similarity_search("민원접수", "basic", k=50)
    found_basic = [doc for doc in all_basic if "민원접수" in doc.page_content]
    
    print(f"\nBasic 컬렉션에서 '민원접수' 포함 문서: {len(found_basic)}개")
    for i, doc in enumerate(found_basic[:3], 1):
        content = doc.page_content
        print(f"\n문서 {i}:")
        print(f"길이: {len(content)}자")
        print(f"내용: {content[:500]}...")
    
    # custom에서 "민원접수" 키워드 포함 문서 찾기
    all_custom = dual_manager.similarity_search("민원접수", "custom", k=50)
    found_custom = [doc for doc in all_custom if "민원접수" in doc.page_content]
    
    print(f"\nCustom 컬렉션에서 '민원접수' 포함 문서: {len(found_custom)}개")
    for i, doc in enumerate(found_custom[:3], 1):
        content = doc.page_content
        print(f"\n문서 {i}:")
        print(f"길이: {len(content)}자")
        print(f"내용: {content[:500]}...")

if __name__ == "__main__":
    debug_complaint_search()