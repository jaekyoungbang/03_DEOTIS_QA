#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain

def verify_vectordb():
    print("=== 벡터DB 임베딩 데이터 검증 ===\n")
    
    rag = RAGChain()
    
    # 1. 데이터베이스 기본 정보
    doc_count = rag.vectorstore_manager.get_document_count()
    print(f"1. 전체 문서 수: {doc_count}")
    
    # 2. 컬렉션 정보 확인
    vectorstore = rag.vectorstore_manager.vectorstore
    print(f"2. 컬렉션 이름: {rag.vectorstore_manager.collection_name}")
    
    # 3. 임베딩 모델 정보
    print(f"3. 임베딩 모델: text-embedding-3-small (OpenAI)")
    
    # 4. 몇 가지 정확한 키워드 검색 테스트
    test_queries = [
        "할부구매",
        "신용카드",
        "일시불",
        "BC카드",
        "TIP"
    ]
    
    print("\n4. 키워드 검색 테스트:")
    for query in test_queries:
        results = rag.vectorstore_manager.similarity_search_with_score(query, k=3)
        top_score = results[0][1] if results else 0
        print(f"   '{query}': 최고 유사도 {top_score:.4f} ({top_score*100:.2f}%)")
        
        # 첫 번째 결과의 내용 일부 출력
        if results:
            doc, score = results[0]
            content_preview = doc.page_content[:100].replace('\n', ' ')
            print(f"     → {content_preview}...")
    
    # 5. 특정 문서 내용 검색
    print(f"\n5. '할부구매' 관련 문서 내용 상세 분석:")
    hallbu_results = rag.vectorstore_manager.similarity_search_with_score("할부구매", k=5)
    
    for i, (doc, score) in enumerate(hallbu_results, 1):
        filename = doc.metadata.get('filename', 'Unknown')
        print(f"   순위 {i}: {score:.4f} ({score*100:.2f}%) | {filename}")
        content = doc.page_content[:200]
        print(f"     내용: {content}...")
        
        # '할부구매' 단어가 실제로 포함되어 있는지 확인
        if '할부구매' in content:
            print(f"     ✅ '할부구매' 키워드 직접 포함")
        else:
            print(f"     ⚠️ '할부구매' 키워드 직접 포함되지 않음")
        print()

    # 6. 벡터스토어에 실제로 저장된 문서 샘플 확인
    print("6. 저장된 문서 메타데이터 샘플:")
    all_docs = rag.vectorstore_manager.similarity_search("", k=10)  # 빈 문자열로 검색하면 무작위 문서들 반환
    
    filenames = set()
    for doc in all_docs:
        filename = doc.metadata.get('filename', 'Unknown')
        filenames.add(filename)
    
    print(f"   저장된 파일들: {list(filenames)}")
    
    # 7. Dual vector store 확인
    print(f"\n7. Dual VectorStore 확인:")
    if hasattr(rag, 'dual_vectorstore_manager'):
        dual_manager = rag.dual_vectorstore_manager
        print(f"   dual_vectorstore_manager 존재: Yes")
        
        # basic 컬렉션 테스트
        try:
            basic_results = dual_manager.similarity_search("할부구매", "basic", k=3)
            print(f"   basic 컬렉션 문서 수: {len(basic_results)}")
        except Exception as e:
            print(f"   basic 컬렉션 오류: {e}")
        
        # custom 컬렉션 테스트
        try:
            custom_results = dual_manager.similarity_search("할부구매", "custom", k=3)
            print(f"   custom 컬렉션 문서 수: {len(custom_results)}")
        except Exception as e:
            print(f"   custom 컬렉션 오류: {e}")
    else:
        print(f"   dual_vectorstore_manager 존재: No")

if __name__ == "__main__":
    verify_vectordb()