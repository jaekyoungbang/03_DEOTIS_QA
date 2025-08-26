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

def load_s3_documents(clear_before_load=False):
    """S3 폴더와 S3-chunking 폴더의 문서를 분리하여 벡터 DB에 저장"""
    
    # S3 폴더들 경로 (Windows/WSL 환경 자동 감지)
    import platform
    if platform.system() == "Windows":
        s3_folders = {
            "s3": "D:\\99_DEOTIS_QA_SYSTEM\\03_DEOTIS_QA\\s3",
            "s3-chunking": "D:\\99_DEOTIS_QA_SYSTEM\\03_DEOTIS_QA\\s3-chunking"
        }
    else:
        s3_folders = {
            "s3": "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3",
            "s3-chunking": "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3-chunking"
        }
    
    # 컴포넌트 초기화
    print("🔧 시스템 초기화 중...")
    doc_processor = DocumentProcessor()
    embedding_manager = EmbeddingManager()
    vectorstore_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
    
    # 벡터DB 초기화 (필요시) - 안전한 방법으로
    if clear_before_load:
        print("🗑️ 기존 벡터DB 데이터 삭제 중...")
        try:
            # 기본 컬렉션 데이터 삭제 (컬렉션은 유지)
            if hasattr(vectorstore_manager, 'basic_vectorstore'):
                try:
                    # 모든 문서 ID 가져와서 삭제
                    collection = vectorstore_manager.basic_vectorstore._collection
                    if collection.count() > 0:
                        all_data = collection.get()
                        if all_data['ids']:
                            collection.delete(ids=all_data['ids'])
                    print("✅ basic 컬렉션 데이터 삭제 완료")
                except:
                    print("⚠️ basic 컬렉션이 비어있거나 삭제 불가")
            
            # 커스텀 컬렉션 데이터 삭제 (컬렉션은 유지)
            if hasattr(vectorstore_manager, 'custom_vectorstore'):
                try:
                    collection = vectorstore_manager.custom_vectorstore._collection
                    if collection.count() > 0:
                        all_data = collection.get()
                        if all_data['ids']:
                            collection.delete(ids=all_data['ids'])
                    print("✅ custom 컬렉션 데이터 삭제 완료")
                except:
                    print("⚠️ custom 컬렉션이 비어있거나 삭제 불가")
            
            print("✅ 벡터DB 데이터 초기화 완료")
        except Exception as e:
            print(f"⚠️ 벡터DB 초기화 오류 (무시하고 진행): {e}")
    
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
                            print(f"🔍 MD 파일 처리 시작: {file}")
                            # MD 파일을 위한 load_s3_chunking_md.py 사용
                            from load_s3_chunking_md import OptimizedMarkdownChunker
                            s3_chunker = OptimizedMarkdownChunker(chunk_size_limit=1500, chunk_overlap=250)
                            custom_chunks = s3_chunker.chunk_markdown_file(file_path)
                            custom_result = {"chunks": custom_chunks}
                            custom_chunks = custom_result["chunks"]
                            print(f"📊 MD 청킹 결과: {len(custom_chunks)}개 청크 생성")
                            
                            if len(custom_chunks) > 0:
                                # 메타데이터 필터링 (ChromaDB 호환성을 위해)
                                filtered_chunks = []
                                for chunk in custom_chunks:
                                    # 메타데이터에서 list, dict 등 복잡한 타입 제거
                                    clean_metadata = {}
                                    for key, value in chunk.metadata.items():
                                        if isinstance(value, (str, int, float, bool)):
                                            clean_metadata[key] = value
                                        elif isinstance(value, list) and len(value) == 0:
                                            # 빈 리스트는 제거
                                            continue
                                        elif isinstance(value, list) and all(isinstance(item, (str, int, float, bool)) for item in value):
                                            # 간단한 값들의 리스트는 문자열로 변환
                                            clean_metadata[key] = ', '.join(str(item) for item in value)
                                        else:
                                            # 복잡한 타입은 문자열로 변환
                                            clean_metadata[key] = str(value)
                                    
                                    # 새로운 Document 객체 생성 (깨끗한 메타데이터로)
                                    from langchain.schema import Document
                                    clean_chunk = Document(
                                        page_content=chunk.page_content,
                                        metadata=clean_metadata
                                    )
                                    filtered_chunks.append(clean_chunk)
                                
                                vectorstore_manager.add_documents(filtered_chunks, chunking_type="custom")
                                total_chunks += len(filtered_chunks)
                                print(f"✅ s3-chunking 성공: 커스텀청킹 {len(filtered_chunks)}개 청크를 custom 컬렉션에 저장")
                            else:
                                print(f"⚠️ s3-chunking 실패: MD 파일에서 청크가 생성되지 않음")
                        
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