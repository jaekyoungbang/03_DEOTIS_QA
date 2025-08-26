#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
개선된 청킹 전략으로 VectorDB 재생성
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import shutil
from load_documents import load_and_chunk_documents
from models.embeddings import EmbeddingManager
from models.vectorstore import DualVectorStoreManager
import chromadb
from config import Config

def recreate_vectordb():
    """개선된 청킹 전략으로 VectorDB 재생성"""
    
    print("🔄 개선된 청킹 전략으로 VectorDB 재생성 시작...")
    
    # 1. 기존 VectorDB 백업
    persist_dir = Config.CHROMA_PERSIST_DIRECTORY
    backup_dir = persist_dir + "_backup_before_improved"
    
    if os.path.exists(persist_dir):
        print(f"📁 기존 VectorDB 백업 중... ({backup_dir})")
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        shutil.copytree(persist_dir, backup_dir)
        print("✅ 백업 완료")
        
        # 기존 VectorDB 삭제
        print("🗑️ 기존 VectorDB 삭제 중...")
        shutil.rmtree(persist_dir)
        print("✅ 삭제 완료")
    
    # 2. 문서 로드 및 청킹
    print("\n📄 문서 로드 및 개선된 청킹 시작...")
    
    # s3 폴더 문서 처리 (기본 청킹)
    s3_chunks = load_and_chunk_documents(
        directory="s3",
        chunk_size=800,
        chunk_overlap=150,
        strategy="basic"  # 개선된 BasicChunkingStrategy 사용
    )
    print(f"✅ s3 폴더: {len(s3_chunks)}개 청크 생성")
    
    # s3-chunking 폴더 문서 처리 (커스텀 청킹)
    s3_chunking_chunks = load_and_chunk_documents(
        directory="s3-chunking",
        chunk_size=1000,
        chunk_overlap=200,
        strategy="custom_delimiter"
    )
    print(f"✅ s3-chunking 폴더: {len(s3_chunking_chunks)}개 청크 생성")
    
    # 3. 임베딩 및 저장
    print("\n🔢 임베딩 생성 및 저장 중...")
    
    # Embedding Manager 초기화
    embedding_manager = EmbeddingManager()
    embeddings = embedding_manager.get_embeddings()
    
    # DualVectorStoreManager 초기화
    dual_manager = DualVectorStoreManager(embeddings)
    
    # 기본 청킹 저장
    print("📊 기본 청킹 데이터 저장 중...")
    dual_manager.add_documents(s3_chunks, "basic")
    
    # 커스텀 청킹 저장
    print("📊 커스텀 청킹 데이터 저장 중...")
    dual_manager.add_documents(s3_chunking_chunks, "custom")
    
    # 4. 검증
    print("\n✅ VectorDB 재생성 완료!")
    
    # 문서 수 확인
    counts = dual_manager.get_document_count()
    print(f"\n📈 저장된 문서 통계:")
    print(f"   - 기본 청킹: {counts.get('basic', 0)}개")
    print(f"   - 커스텀 청킹: {counts.get('custom', 0)}개")
    print(f"   - 전체: {counts.get('total', 0)}개")
    
    # 5. 신용카드알뜰이용법 검색 테스트
    print("\n🔍 '신용카드알뜰이용법' 검색 테스트:")
    test_results = dual_manager.similarity_search_with_score("신용카드알뜰이용법", "basic", k=3)
    
    for i, (doc, score) in enumerate(test_results, 1):
        content = doc.page_content
        print(f"\n순위 {i}: 점수 {score:.2%}")
        
        # 문제가 있는지 확인
        if "회원제 업소" in content and "신용카드알뜰이용법" in content:
            print("⚠️ 경고: 여전히 '회원제 업소'와 '신용카드알뜰이용법'이 같은 청크에 있습니다!")
        else:
            print("✅ 정상: 섹션이 올바르게 분리되었습니다.")
        
        print(f"내용 미리보기: {content[:200]}...")

if __name__ == "__main__":
    recreate_vectordb()