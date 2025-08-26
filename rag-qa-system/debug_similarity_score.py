#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
유사도 점수 계산 문제 디버깅
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.vectorstore import DualVectorStoreManager
from models.embeddings import EmbeddingManager

def debug_similarity_scores():
    """유사도 점수 계산 문제 분석"""
    
    print("=== 유사도 점수 디버깅 ===\n")
    
    # 초기화
    embedding_manager = EmbeddingManager()
    dual_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
    
    query = "민원접수방법 안내"
    print(f"검색어: '{query}'")
    print("-" * 50)
    
    # Basic 컬렉션에서 점수와 함께 검색
    print("\n1. Basic 컬렉션 유사도 점수 상세 분석:")
    basic_results = dual_manager.similarity_search_with_score(query, "basic", k=10)
    
    for i, (doc, score) in enumerate(basic_results, 1):
        content = doc.page_content
        print(f"\n순위 {i}: 점수 {score:.4f} ({score*100:.2f}%)")
        print(f"문서 길이: {len(content)}자")
        print(f"내용: {repr(content[:100])}...")
        
        # 정확한 매칭인지 확인
        if content.strip() == query:
            print("🎯 완전 매칭!")
        elif query in content:
            print("🔍 부분 매칭")
        else:
            print("❌ 매칭 없음")
    
    print("\n" + "="*50)
    print("2. Custom 컬렉션 유사도 점수 상세 분석:")
    custom_results = dual_manager.similarity_search_with_score(query, "custom", k=10)
    
    for i, (doc, score) in enumerate(custom_results, 1):
        content = doc.page_content
        print(f"\n순위 {i}: 점수 {score:.4f} ({score*100:.2f}%)")
        print(f"문서 길이: {len(content)}자")
        print(f"내용: {repr(content[:100])}...")
        
        # 정확한 매칭인지 확인
        if content.strip() == query:
            print("🎯 완전 매칭!")
        elif query in content:
            print("🔍 부분 매칭")
        else:
            print("❌ 매칭 없음")
    
    print("\n" + "="*50)
    print("3. 임베딩 벡터 거리 직접 계산:")
    
    # 쿼리 임베딩
    embeddings = embedding_manager.get_embeddings()
    query_vector = embeddings.embed_query(query)
    print(f"쿼리 벡터 차원: {len(query_vector)}")
    
    # 상위 3개 문서의 벡터와 거리 계산
    print("\nBasic 컬렉션 상위 3개 거리:")
    for i, (doc, score) in enumerate(basic_results[:3], 1):
        doc_vector = embeddings.embed_query(doc.page_content)
        
        # 코사인 유사도 직접 계산
        import numpy as np
        cos_sim = np.dot(query_vector, doc_vector) / (np.linalg.norm(query_vector) * np.linalg.norm(doc_vector))
        
        print(f"문서 {i}: ChromaDB 점수={score:.4f}, 직접계산 코사인유사도={cos_sim:.4f}")
        print(f"  내용: {repr(doc.page_content[:50])}...")

if __name__ == "__main__":
    debug_similarity_scores()