#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain

def test_chunking_type():
    print("=== chunking_type 디버깅 ===\n")
    
    rag = RAGChain()
    
    # 테스트 질문
    question = "할부구매"
    
    # basic 모드 테스트
    print("1. basic 검색 모드 테스트")
    response = rag.query(question, search_mode="basic", use_cache=False)
    print(f"Response keys: {list(response.keys())}")
    print(f"chunking_type in response: {'chunking_type' in response}")
    if 'chunking_type' in response:
        print(f"chunking_type value: {response['chunking_type']}")
    print()
    
    # custom 모드 테스트
    print("2. custom 검색 모드 테스트")
    response = rag.query(question, search_mode="custom", use_cache=False)
    print(f"Response keys: {list(response.keys())}")
    print(f"chunking_type in response: {'chunking_type' in response}")
    if 'chunking_type' in response:
        print(f"chunking_type value: {response['chunking_type']}")
    print()

    # RAG 체인에서 직접 검색하는 방법 확인
    print("3. RAG chain search methods:")
    print(f"Available methods: {[method for method in dir(rag) if 'search' in method.lower()]}")
    
    # DualVectorStoreManager 확인
    print(f"\n4. DualVectorStoreManager:")
    print(f"dual_vectorstore_manager exists: {hasattr(rag, 'dual_vectorstore_manager')}")
    if hasattr(rag, 'dual_vectorstore_manager'):
        dual_manager = rag.dual_vectorstore_manager
        print(f"dual_manager methods: {[method for method in dir(dual_manager) if 'search' in method.lower()]}")

if __name__ == "__main__":
    test_chunking_type()