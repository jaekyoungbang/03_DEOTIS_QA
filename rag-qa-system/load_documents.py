#!/usr/bin/env python3
"""
S3 폴더의 문서들을 자동으로 로드하여 벡터 DB에 저장하는 스크립트
"""

import os
import sys
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.document_processor import DocumentProcessor
from models.embeddings import EmbeddingManager
from models.vectorstore import DualVectorStoreManager
from config import Config

def load_s3_documents():
    """S3 폴더와 S3-chunking 폴더의 문서를 분리하여 벡터 DB에 저장"""
    
    # S3 폴더들 경로 (WSL 환경)
    s3_folders = {
        "s3": "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3",
        "s3-chunking": "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3-chunking"
    }
    
    # 컴포넌트 초기화
    print("🔧 시스템 초기화 중...")
    doc_processor = DocumentProcessor()
    embedding_manager = EmbeddingManager()
    vectorstore_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
    
    # 지원되는 파일 확장자
    supported_extensions = ['.txt', '.docx', '.pdf', '.md']
    
    # 각 폴더별 파일 찾기
    documents_loaded = 0
    total_chunks = 0
    
    for folder_type, s3_folder in s3_folders.items():
        print(f"\n📂 폴더 검색 중: {s3_folder} ({folder_type})")
        
        if not os.path.exists(s3_folder):
            print(f"⚠️ 폴더가 존재하지 않습니다: {s3_folder}")
            continue
            
        for root, dirs, files in os.walk(s3_folder):
            for file in files:
                file_path = os.path.join(root, file)
                file_extension = os.path.splitext(file)[1].lower()
                
                if file_extension in supported_extensions:
                    print(f"\n📄 처리 중: {file} ({folder_type})")
                    
                    try:
                        # 문서 처리 - 폴더 타입에 따라 적절한 청킹 전략과 컬렉션 사용
                        metadata = {
                            "source": folder_type,  # 's3' 또는 's3-chunking'
                            "filename": file,
                            "path": file_path
                        }
                        
                        if folder_type == "s3":
                            # s3 폴더: 기본 청킹으로 basic 컬렉션에 저장
                            basic_result = doc_processor.process_file(file_path, metadata, chunking_strategy="basic")
                            basic_chunks = basic_result["chunks"]
                            vectorstore_manager.add_documents(basic_chunks, chunking_type="basic")
                            total_chunks += len(basic_chunks)
                            print(f"✅ s3 성공: 기본청킹 {len(basic_chunks)}개 청크를 basic 컬렉션에 저장")
                            
                        elif folder_type == "s3-chunking":
                            # s3-chunking 폴더: 커스텀 청킹으로 custom 컬렉션에 저장
                            custom_result = doc_processor.process_file(file_path, metadata, chunking_strategy="custom_delimiter")
                            custom_chunks = custom_result["chunks"]
                            vectorstore_manager.add_documents(custom_chunks, chunking_type="custom")
                            total_chunks += len(custom_chunks)
                            print(f"✅ s3-chunking 성공: 커스텀청킹 {len(custom_chunks)}개 청크를 custom 컬렉션에 저장")
                        
                        documents_loaded += 1
                        
                    except Exception as e:
                        print(f"❌ 오류 발생: {e}")
    
    print(f"\n" + "="*50)
    print(f"📊 로딩 완료!")
    print(f"- 처리된 문서: {documents_loaded}개")
    print(f"- 생성된 청크: {total_chunks}개")
    
    # 이중 벡터스토어 문서 수 조회
    doc_counts = vectorstore_manager.get_document_count()
    print(f"- 기본 청킹 벡터 DB: {doc_counts['basic']}개 문서")
    print(f"- 커스텀 청킹 벡터 DB: {doc_counts['custom']}개 문서")
    print(f"- 전체 문서 수: {doc_counts['total']}개")
    print("="*50)
    
    return documents_loaded, total_chunks

if __name__ == "__main__":
    try:
        load_s3_documents()
    except Exception as e:
        print(f"❌ 프로그램 오류: {e}")
        sys.exit(1)