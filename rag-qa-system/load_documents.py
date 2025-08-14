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
from models.vectorstore import VectorStoreManager
from config import Config

def load_s3_documents():
    """S3 폴더의 모든 문서를 로드하여 벡터 DB에 저장"""
    
    # S3 폴더 경로 - Windows CMD에서 실행하므로 Windows 경로 사용
    s3_folder = "D:\\99_DEOTIS_QA_SYSTEM\\03_DEOTIS_QA\\s3"
    # s3_folder = "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3"
    
    # 컴포넌트 초기화
    print("🔧 시스템 초기화 중...")
    doc_processor = DocumentProcessor()
    embedding_manager = EmbeddingManager()
    vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
    
    # 지원되는 파일 확장자
    supported_extensions = ['.txt', '.docx', '.pdf', '.md']
    
    # S3 폴더의 모든 파일 찾기
    documents_loaded = 0
    total_chunks = 0
    
    print(f"📂 폴더 검색 중: {s3_folder}")
    
    for root, dirs, files in os.walk(s3_folder):
        for file in files:
            file_path = os.path.join(root, file)
            file_extension = os.path.splitext(file)[1].lower()
            
            if file_extension in supported_extensions:
                print(f"\n📄 처리 중: {file}")
                
                try:
                    # 문서 처리
                    metadata = {
                        "source": "s3",
                        "filename": file,
                        "path": file_path
                    }
                    
                    chunks = doc_processor.process_file(file_path, metadata)
                    
                    # 벡터 DB에 추가
                    vectorstore_manager.add_documents(chunks)
                    
                    documents_loaded += 1
                    total_chunks += len(chunks)
                    
                    print(f"✅ 성공: {len(chunks)}개 청크 생성됨")
                    
                except Exception as e:
                    print(f"❌ 오류 발생: {e}")
    
    print(f"\n" + "="*50)
    print(f"📊 로딩 완료!")
    print(f"- 처리된 문서: {documents_loaded}개")
    print(f"- 생성된 청크: {total_chunks}개")
    print(f"- 전체 벡터 DB 문서 수: {vectorstore_manager.get_document_count()}개")
    print("="*50)
    
    return documents_loaded, total_chunks

if __name__ == "__main__":
    try:
        load_s3_documents()
    except Exception as e:
        print(f"❌ 프로그램 오류: {e}")
        sys.exit(1)