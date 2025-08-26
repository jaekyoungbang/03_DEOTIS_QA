#!/usr/bin/env python3
"""
벡터DB 삭제/재로드 문제 진단 스크립트
"""

import os
import shutil
from models.vectorstore import VectorStoreManager
from models.embeddings import EmbeddingManager
from config import Config

def test_vectordb_persistence():
    """벡터DB 삭제 후 데이터 잔존 문제 테스트"""
    print("="*60)
    print("🔍 벡터DB 삭제/재로드 문제 진단")
    print("="*60)
    
    # 1. 초기 상태 확인
    print("\n1️⃣ 초기 상태 확인")
    print(f"벡터DB 경로: {Config.CHROMA_PERSIST_DIRECTORY}")
    print(f"컬렉션명: {Config.CHROMA_COLLECTION_NAME}")
    
    # 물리적 디렉토리 확인
    if os.path.exists(Config.CHROMA_PERSIST_DIRECTORY):
        files = os.listdir(Config.CHROMA_PERSIST_DIRECTORY)
        print(f"현재 파일: {files}")
    else:
        print("벡터DB 디렉토리가 없습니다.")
    
    # 2. 벡터스토어 초기화
    print("\n2️⃣ 벡터스토어 초기화")
    embedding_manager = EmbeddingManager()
    vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
    
    # 문서 수 확인
    doc_count = vectorstore_manager.get_document_count()
    print(f"현재 문서 수: {doc_count}")
    
    # 3. 삭제 테스트
    print("\n3️⃣ delete_collection() 실행")
    vectorstore_manager.delete_collection(clear_cache=False)
    
    # 삭제 후 문서 수 확인
    doc_count_after = vectorstore_manager.get_document_count()
    print(f"삭제 후 문서 수: {doc_count_after}")
    
    # 4. 물리적 디렉토리 확인
    print("\n4️⃣ 물리적 파일 확인")
    if os.path.exists(Config.CHROMA_PERSIST_DIRECTORY):
        files_after = os.listdir(Config.CHROMA_PERSIST_DIRECTORY)
        print(f"삭제 후 파일: {files_after}")
        
        # ChromaDB SQLite 파일 확인
        db_file = os.path.join(Config.CHROMA_PERSIST_DIRECTORY, "chroma.sqlite3")
        if os.path.exists(db_file):
            size = os.path.getsize(db_file) / 1024 / 1024  # MB
            print(f"⚠️  chroma.sqlite3 파일이 여전히 존재합니다 (크기: {size:.2f}MB)")
    
    # 5. 완전 삭제 테스트
    print("\n5️⃣ 물리적 디렉토리 완전 삭제 테스트")
    if os.path.exists(Config.CHROMA_PERSIST_DIRECTORY):
        try:
            shutil.rmtree(Config.CHROMA_PERSIST_DIRECTORY)
            print("✅ 벡터DB 디렉토리를 완전히 삭제했습니다.")
        except Exception as e:
            print(f"❌ 디렉토리 삭제 실패: {e}")
    
    # 재초기화
    os.makedirs(Config.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
    vectorstore_manager2 = VectorStoreManager(embedding_manager.get_embeddings())
    doc_count_final = vectorstore_manager2.get_document_count()
    print(f"재초기화 후 문서 수: {doc_count_final}")
    
    # 6. 결론
    print("\n📊 진단 결과:")
    if doc_count > 0 and doc_count_after > 0:
        print("❌ 문제 발견: delete_collection()이 제대로 작동하지 않습니다.")
        print("   ChromaDB가 데이터를 SQLite에 영구 저장하고 있어 삭제가 불완전합니다.")
        print("\n💡 해결 방법:")
        print("   1. 물리적 디렉토리 삭제 후 재생성")
        print("   2. ChromaDB 클라이언트 재초기화")
    else:
        print("✅ 정상: delete_collection()이 올바르게 작동합니다.")

def test_dual_vectorstore():
    """이중 벡터스토어 테스트"""
    print("\n\n" + "="*60)
    print("🔍 이중 벡터스토어 (기본/커스텀 청킹) 테스트")
    print("="*60)
    
    from models.vectorstore import DualVectorStoreManager
    
    embedding_manager = EmbeddingManager()
    dual_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
    
    print(f"\n기본 청킹 컬렉션: {dual_manager.basic_collection_name}")
    print(f"커스텀 청킹 컬렉션: {dual_manager.custom_collection_name}")
    
    # 각각의 문서 수 확인
    basic_count = 0
    custom_count = 0
    
    try:
        basic_count = dual_manager.basic_vectorstore._collection.count()
        print(f"기본 청킹 문서 수: {basic_count}")
    except:
        print("기본 청킹 컬렉션이 없습니다.")
    
    try:
        custom_count = dual_manager.custom_vectorstore._collection.count()
        print(f"커스텀 청킹 문서 수: {custom_count}")
    except:
        print("커스텀 청킹 컬렉션이 없습니다.")
    
    print("\n💡 이중 벡터스토어 구현 제안:")
    print("   - 기본 청킹: 표준 chunk_size로 분할")
    print("   - 커스텀 청킹: 의미 단위 또는 문서 구조 기반 분할")
    print("   - 검색 시 두 컬렉션 모두에서 검색 후 병합")

if __name__ == "__main__":
    test_vectordb_persistence()
    test_dual_vectorstore()