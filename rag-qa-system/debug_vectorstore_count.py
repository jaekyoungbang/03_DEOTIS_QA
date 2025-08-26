#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
벡터스토어 문서 카운트 문제 디버깅
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.vectorstore import VectorStoreManager, DualVectorStoreManager
from models.embeddings import EmbeddingManager

def debug_vectorstore_count():
    """벡터스토어 문서 카운트 확인"""
    
    print("=== 벡터스토어 문서 카운트 디버깅 ===\n")
    
    # 임베딩 매니저 초기화
    embedding_manager = EmbeddingManager()
    embeddings = embedding_manager.get_embeddings()
    
    print("1. VectorStoreManager 테스트:")
    try:
        vectorstore_manager = VectorStoreManager(embeddings)
        count = vectorstore_manager.get_document_count()
        print(f"   VectorStoreManager 문서 수: {count}")
    except Exception as e:
        print(f"   VectorStoreManager 오류: {e}")
    
    print("\n2. DualVectorStoreManager 테스트:")
    try:
        dual_manager = DualVectorStoreManager(embeddings)
        counts = dual_manager.get_document_count()
        print(f"   DualVectorStoreManager 결과: {counts}")
        print(f"   Basic 컬렉션: {counts.get('basic', 0)}")
        print(f"   Custom 컬렉션: {counts.get('custom', 0)}")
        print(f"   Total: {counts.get('total', 0)}")
    except Exception as e:
        print(f"   DualVectorStoreManager 오류: {e}")
    
    print("\n3. 개별 컬렉션 테스트:")
    try:
        dual_manager = DualVectorStoreManager(embeddings)
        
        # Basic 컬렉션 직접 테스트
        basic_docs = dual_manager.similarity_search("test", "basic", k=1)
        print(f"   Basic 컬렉션 검색 결과: {len(basic_docs)}개")
        
        # Custom 컬렉션 직접 테스트
        custom_docs = dual_manager.similarity_search("test", "custom", k=1)
        print(f"   Custom 컬렉션 검색 결과: {len(custom_docs)}개")
        
    except Exception as e:
        print(f"   개별 컬렉션 테스트 오류: {e}")

if __name__ == "__main__":
    debug_vectorstore_count()