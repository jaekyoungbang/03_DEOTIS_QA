#!/usr/bin/env python3
"""
Vector DB 데이터 확인 스크립트
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.embeddings import EmbeddingManager
from models.vectorstore import DualVectorStoreManager
import chromadb
from config import Config

def check_vectordb():
    print("🔍 Vector DB 데이터 확인 중...")
    print("=" * 60)
    
    # ChromaDB 직접 연결
    persist_directory = Config.CHROMA_PERSIST_DIRECTORY
    client = chromadb.PersistentClient(path=persist_directory)
    
    print(f"📁 Vector DB 경로: {persist_directory}")
    print(f"📊 컬렉션 목록:")
    
    # 모든 컬렉션 확인
    collections = client.list_collections()
    for idx, col in enumerate(collections, 1):
        print(f"\n{idx}. 컬렉션명: {col.name}")
        print(f"   - 문서 수: {col.count()}")
        
        # 메타데이터 확인
        if col.count() > 0:
            # 샘플 문서 가져오기
            sample = col.get(limit=3)
            
            print(f"   - 샘플 문서 ID: {sample['ids'][:3]}")
            
            # 메타데이터 키 확인
            if sample['metadatas']:
                metadata_keys = set()
                for meta in sample['metadatas']:
                    metadata_keys.update(meta.keys())
                print(f"   - 메타데이터 필드: {list(metadata_keys)}")
                
                # 첫 번째 문서의 상세 정보
                print(f"\n   📄 첫 번째 문서 상세:")
                first_doc = sample['metadatas'][0]
                for key, value in first_doc.items():
                    if key == 'content':
                        print(f"      - {key}: {value[:100]}..." if len(str(value)) > 100 else f"      - {key}: {value}")
                    else:
                        print(f"      - {key}: {value}")
    
    # DualVectorStoreManager로 확인
    print("\n" + "=" * 60)
    print("🔄 DualVectorStoreManager로 확인:")
    
    try:
        embedding_manager = EmbeddingManager()
        vectorstore_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
        
        counts = vectorstore_manager.get_document_count()
        print(f"\n📊 문서 수 통계:")
        print(f"   - 기본 청킹: {counts.get('basic', 0)}개")
        print(f"   - 커스텀 청킹: {counts.get('custom', 0)}개")
        print(f"   - 전체: {counts.get('total', 0)}개")
        
        # 샘플 검색 테스트
        test_query = "연회비"
        print(f"\n🔍 테스트 검색: '{test_query}'")
        
        # 기본 청킹 검색
        basic_results = vectorstore_manager.similarity_search_with_score(test_query, "basic", k=2)
        print(f"\n📌 기본 청킹 검색 결과 (상위 2개):")
        for idx, (doc, score) in enumerate(basic_results, 1):
            print(f"\n   {idx}. 유사도 점수: {score:.4f}")
            print(f"      소스: {doc.metadata.get('source', 'Unknown')}")
            print(f"      청킹: {doc.metadata.get('chunking_strategy', 'Unknown')}")
            print(f"      내용: {doc.page_content[:150]}...")
        
        # 커스텀 청킹 검색
        custom_results = vectorstore_manager.similarity_search_with_score(test_query, "custom", k=2)
        print(f"\n📌 커스텀 청킹 검색 결과 (상위 2개):")
        for idx, (doc, score) in enumerate(custom_results, 1):
            print(f"\n   {idx}. 유사도 점수: {score:.4f}")
            print(f"      소스: {doc.metadata.get('source', 'Unknown')}")
            print(f"      구분자: {doc.metadata.get('delimiter_used', 'Unknown')}")
            print(f"      내용: {doc.page_content[:150]}...")
            
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    
    # 디스크 사용량 확인
    print("\n" + "=" * 60)
    print("💾 디스크 사용량:")
    
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(persist_directory):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)
    
    print(f"   - Vector DB 총 크기: {total_size / 1024 / 1024:.2f} MB")
    
    # 파일 구조 확인
    print(f"\n📁 Vector DB 파일 구조:")
    for root, dirs, files in os.walk(persist_directory):
        level = root.replace(persist_directory, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 2 * (level + 1)
        for file in files[:5]:  # 처음 5개만
            print(f'{subindent}{file}')
        if len(files) > 5:
            print(f'{subindent}... ({len(files)-5} more files)')

if __name__ == "__main__":
    check_vectordb()