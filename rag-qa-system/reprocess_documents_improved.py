#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
개선된 청킹 전략으로 문서 재처리
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.document_processor import DocumentProcessor
from services.chunking_strategies import get_chunking_strategy
from models.embeddings import EmbeddingManager
from models.vectorstore import DualVectorStoreManager
import shutil
from config import Config

def reprocess_documents():
    """개선된 청킹 전략으로 문서 재처리"""
    
    print("🔄 개선된 청킹 전략으로 문서 재처리 시작...")
    
    # VectorDB 백업
    persist_dir = Config.CHROMA_PERSIST_DIRECTORY
    backup_dir = persist_dir + "_backup_before_improved_chunking"
    
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
    
    # 컴포넌트 초기화
    print("\n🔧 시스템 초기화 중...")
    doc_processor = DocumentProcessor()
    embedding_manager = EmbeddingManager()
    vectorstore_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
    
    # S3 폴더들 경로
    s3_folders = {
        "s3": "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3",
        "s3-chunking": "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3-chunking"
    }
    
    # 지원되는 파일 확장자
    supported_extensions = ['.txt', '.docx', '.pdf', '.md']
    
    # 각 폴더별 문서 처리
    for folder_type, s3_folder in s3_folders.items():
        print(f"\n📂 폴더 처리 중: {s3_folder} ({folder_type})")
        
        if not os.path.exists(s3_folder):
            print(f"⚠️ 폴더가 존재하지 않습니다: {s3_folder}")
            continue
        
        documents_loaded = 0
        total_chunks = 0
        
        for root, dirs, files in os.walk(s3_folder):
            for file in files:
                file_path = os.path.join(root, file)
                file_extension = os.path.splitext(file)[1].lower()
                
                # 임시 파일 제외
                if file.startswith('~$') or file.startswith('.'):
                    continue
                
                if file_extension in supported_extensions:
                    print(f"\n📄 처리 중: {file}")
                    
                    try:
                        # 문서 읽기
                        documents = doc_processor.load_document(file_path)
                        
                        if documents:
                            # 개선된 청킹 전략 적용
                            if folder_type == "s3":
                                # 기본 청킹 (개선된 버전)
                                strategy = get_chunking_strategy('basic')
                                chunks = strategy.split_documents(documents)
                                collection_name = "basic"
                            else:
                                # 커스텀 청킹
                                strategy = get_chunking_strategy('custom_delimiter')
                                chunks = strategy.split_documents(documents)
                                collection_name = "custom"
                            
                            # 메타데이터 추가
                            for chunk in chunks:
                                chunk.metadata['source'] = file_path
                                chunk.metadata['filename'] = file
                            
                            # 청크 분석 (신용카드알뜰이용법 관련)
                            problematic_chunks = 0
                            for chunk in chunks:
                                chunk_content = chunk.page_content
                                if "회원제 업소" in chunk_content and "신용카드알뜰이용법" in chunk_content:
                                    problematic_chunks += 1
                            
                            if problematic_chunks > 0:
                                print(f"   ⚠️ 경고: {problematic_chunks}개 청크에서 '회원제 업소'와 '신용카드알뜰이용법'이 함께 발견됨")
                            
                            # 벡터 저장소에 추가
                            vectorstore_manager.add_documents(chunks, collection_name)
                            
                            print(f"   ✅ {len(chunks)}개 청크 저장 완료 ({collection_name})")
                            documents_loaded += 1
                            total_chunks += len(chunks)
                            
                    except Exception as e:
                        print(f"   ❌ 처리 실패: {str(e)}")
        
        print(f"\n📊 {folder_type} 폴더 처리 완료:")
        print(f"   - 문서 수: {documents_loaded}개")
        print(f"   - 청크 수: {total_chunks}개")
    
    # 전체 통계
    counts = vectorstore_manager.get_document_count()
    print(f"\n📈 전체 저장 통계:")
    print(f"   - 기본 청킹: {counts.get('basic', 0)}개")
    print(f"   - 커스텀 청킹: {counts.get('custom', 0)}개")
    print(f"   - 전체: {counts.get('total', 0)}개")
    
    # 신용카드알뜰이용법 검색 테스트
    print("\n🔍 '신용카드알뜰이용법' 검색 테스트:")
    test_results = vectorstore_manager.similarity_search_with_score("신용카드알뜰이용법", "basic", k=3)
    
    for i, (doc, score) in enumerate(test_results, 1):
        content = doc.page_content
        print(f"\n순위 {i}: 점수 {score:.2%}")
        print(f"파일: {doc.metadata.get('source', 'Unknown')}")
        
        # 문제가 있는지 확인
        if "회원제 업소" in content and "신용카드알뜰이용법" in content:
            print("⚠️ 경고: 여전히 '회원제 업소'와 '신용카드알뜰이용법'이 같은 청크에 있습니다!")
            idx1 = content.find("회원제 업소")
            idx2 = content.find("신용카드알뜰이용법")
            print(f"   거리: {abs(idx2 - idx1)}자")
        else:
            print("✅ 정상: 섹션이 올바르게 분리되었습니다.")
        
        print(f"내용 미리보기: {content[:200]}...")

if __name__ == "__main__":
    reprocess_documents()