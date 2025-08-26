#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain
import chromadb

def verify_vectordb_details():
    print("=== 벡터DB 상세 검증 ===\n")
    
    rag = RAGChain()
    
    # 1. 직접 ChromaDB 클라이언트로 접근
    print("1. ChromaDB 직접 접근:")
    client = chromadb.PersistentClient(path="./data/vectordb")
    
    # 컬렉션 목록
    collections = client.list_collections()
    print(f"   컬렉션 목록: {[col.name for col in collections]}")
    
    # rag_documents 컬렉션 확인
    try:
        collection = client.get_collection("rag_documents")
        print(f"   rag_documents 컬렉션 문서 수: {collection.count()}")
        
        # 샘플 문서 가져오기
        print("\n2. 샘플 문서 확인 (처음 10개):")
        results = collection.get(limit=10, include=["documents", "metadatas"])
        
        for i, (doc, metadata) in enumerate(zip(results['documents'], results['metadatas']), 1):
            print(f"\n   문서 {i}:")
            print(f"   파일명: {metadata.get('filename', 'Unknown')}")
            print(f"   청킹 타입: {metadata.get('chunking_type', 'Unknown')}")
            print(f"   소스: {metadata.get('source', 'Unknown')}")
            print(f"   내용: {doc[:200]}...")
            
    except Exception as e:
        print(f"   rag_documents 컬렉션 오류: {e}")
    
    # 3. "할부구매" 직접 검색
    print("\n3. '할부구매' 직접 검색 (ChromaDB):")
    try:
        # 임베딩 생성
        from models.embeddings import EmbeddingManager
        embedding_manager = EmbeddingManager()
        embeddings = embedding_manager.get_embeddings()
        
        query_embedding = embeddings.embed_query("할부구매")
        
        # 직접 검색
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=10,
            include=["documents", "metadatas", "distances"]
        )
        
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0], 
            results['metadatas'][0], 
            results['distances'][0]
        ), 1):
            similarity = 1 - distance  # 거리를 유사도로 변환
            print(f"\n   순위 {i}: {similarity:.4f} ({similarity*100:.2f}%)")
            print(f"   파일: {metadata.get('filename', 'Unknown')}")
            print(f"   내용: {doc[:200]}...")
            if '할부구매' in doc:
                print(f"   ✅ '할부구매' 키워드 포함!")
    except Exception as e:
        print(f"   검색 오류: {e}")
    
    # 4. 특정 파일의 모든 청크 확인
    print("\n4. BC카드(카드이용안내).docx 파일의 모든 청크:")
    try:
        results = collection.get(
            where={"filename": "BC카드(카드이용안내).docx"},
            limit=100,
            include=["documents", "metadatas"]
        )
        
        print(f"   총 {len(results['documents'])}개 청크")
        
        # 할부구매 포함 청크 찾기
        hallbu_chunks = []
        for i, (doc, metadata) in enumerate(zip(results['documents'], results['metadatas'])):
            if '할부구매' in doc:
                hallbu_chunks.append((i, doc, metadata))
        
        print(f"   '할부구매' 포함 청크: {len(hallbu_chunks)}개")
        
        for idx, (i, doc, metadata) in enumerate(hallbu_chunks[:3], 1):
            print(f"\n   할부구매 청크 {idx}:")
            print(f"   내용: {doc[:300]}...")
            
    except Exception as e:
        print(f"   파일별 청크 확인 오류: {e}")
    
    # 5. DualVectorStore 확인
    print("\n5. DualVectorStore 컬렉션 확인:")
    for collection_name in ["basic_rag_documents", "custom_rag_documents"]:
        try:
            col = client.get_collection(collection_name)
            print(f"   {collection_name}: {col.count()}개 문서")
            
            # 샘플 확인
            results = col.get(limit=3, include=["documents", "metadatas"])
            for i, (doc, metadata) in enumerate(zip(results['documents'], results['metadatas']), 1):
                print(f"     샘플 {i}: {metadata.get('filename', 'Unknown')} - {doc[:100]}...")
                
        except Exception as e:
            print(f"   {collection_name} 오류: {e}")

if __name__ == "__main__":
    verify_vectordb_details()