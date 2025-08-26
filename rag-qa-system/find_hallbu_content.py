#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain

def find_hallbu_content():
    print("=== '할부구매' 키워드 검색 분석 ===\n")
    
    rag = RAGChain()
    
    # 1. 모든 문서에서 '할부구매' 포함된 문서 찾기
    print("1. 전체 문서에서 '할부구매' 키워드 포함 검색:")
    
    # 더 많은 문서를 가져와서 확인
    all_results = rag.vectorstore_manager.similarity_search("할부구매", k=50)
    
    found_hallbu = []
    for i, doc in enumerate(all_results):
        if '할부구매' in doc.page_content:
            found_hallbu.append((i+1, doc))
            print(f"   순위 {i+1}: ✅ '할부구매' 포함")
            print(f"     파일: {doc.metadata.get('filename', 'Unknown')}")
            content = doc.page_content[:300]
            print(f"     내용: {content}...")
            print()
    
    if not found_hallbu:
        print("   ⚠️ '할부구매' 키워드가 포함된 문서를 찾을 수 없습니다!")
        
        # 대안으로 '할부' 키워드로 검색
        print("\n2. '할부' 키워드로 재검색:")
        hallbu_results = rag.vectorstore_manager.similarity_search("할부", k=10)
        
        for i, doc in enumerate(hallbu_results, 1):
            if '할부' in doc.page_content:
                print(f"   순위 {i}: ✅ '할부' 포함")
                print(f"     파일: {doc.metadata.get('filename', 'Unknown')}")
                content = doc.page_content[:200]
                print(f"     내용: {content}...")
                
                # '할부구매'가 포함되어 있는지 확인
                if '할부구매' in doc.page_content:
                    print(f"     🎯 이 문서에 '할부구매'도 포함!")
                print()
    
    # 3. dual vectorstore에서도 확인
    print("\n3. DualVectorStore에서 검색:")
    if hasattr(rag, 'dual_vectorstore_manager'):
        dual_manager = rag.dual_vectorstore_manager
        
        # basic 컬렉션
        print("   basic 컬렉션:")
        basic_results = dual_manager.similarity_search("할부구매", "basic", k=10)
        for i, doc in enumerate(basic_results, 1):
            if '할부구매' in doc.page_content:
                print(f"     순위 {i}: ✅ '할부구매' 포함 (basic)")
                content = doc.page_content[:200]
                print(f"     내용: {content}...")
        
        # custom 컬렉션
        print("   custom 컬렉션:")
        custom_results = dual_manager.similarity_search("할부구매", "custom", k=10)
        for i, doc in enumerate(custom_results, 1):
            if '할부구매' in doc.page_content:
                print(f"     순위 {i}: ✅ '할부구매' 포함 (custom)")
                content = doc.page_content[:200]
                print(f"     내용: {content}...")
    
    # 4. 문서 메타데이터 분석
    print("\n4. 문서 메타데이터 분석:")
    sample_docs = rag.vectorstore_manager.similarity_search("", k=20)
    
    file_counts = {}
    for doc in sample_docs:
        filename = doc.metadata.get('filename', 'Unknown')
        file_counts[filename] = file_counts.get(filename, 0) + 1
    
    print("   파일별 문서 조각 수:")
    for filename, count in file_counts.items():
        print(f"     {filename}: {count}개 조각")

if __name__ == "__main__":
    find_hallbu_content()