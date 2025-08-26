#!/usr/bin/env python3
"""
통합 문서 로딩 시스템 - s3-chunking MD 파일 우선
- s3 폴더: 기본 청킹으로 Word/PDF 문서 처리
- s3-chunking 폴더: 최적화된 MD 파일만 처리 (이미지 경로 포함)
"""

import os
import sys
from pathlib import Path
import time
from datetime import datetime

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.document_processor import DocumentProcessor
from services.chunking_strategies import get_chunking_strategy
from models.embeddings import EmbeddingManager
from models.vectorstore import DualVectorStoreManager
from config import Config

# s3-chunking MD 로더 import
from load_s3_chunking_md import S3ChunkingMDLoader


def load_all_documents_with_md_priority(clear_before_load=True):
    """s3-chunking MD 파일을 우선으로 모든 문서 로드"""
    
    print("🚀 통합 문서 로딩 시스템 시작 (MD 파일 우선)...")
    print("=" * 60)
    
    start_time = time.time()
    
    # S3 폴더들 경로 설정
    import platform
    if platform.system() == "Windows" or os.name == "nt":
        s3_folders = {
            "s3": r"D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\s3",
            "s3-chunking": r"D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\s3-chunking"
        }
        print("🪟 Windows 환경에서 실행 중")
    else:
        s3_folders = {
            "s3": "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3",
            "s3-chunking": "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3-chunking"
        }
        print("🐧 WSL/Linux 환경에서 실행 중")
    
    # 기존 데이터 삭제 (옵션)
    if clear_before_load:
        print("\n🗑️ 기존 벡터 DB 데이터 삭제 중...")
        try:
            from models.vectorstore import reset_vectorstore
            reset_vectorstore()
            print("✅ 기존 데이터 삭제 완료")
        except Exception as e:
            print(f"⚠️ 기존 데이터 삭제 실패: {e}")
    
    # 1단계: s3-chunking MD 파일 로드 (우선순위)
    print("\n" + "="*60)
    print("📁 1단계: s3-chunking MD 파일 로드")
    print("="*60)
    
    try:
        md_loader = S3ChunkingMDLoader()
        # clear_before_load=False로 설정 (이미 위에서 삭제함)
        md_loader.load_s3_chunking_md_files(clear_before_load=False)
        print("✅ s3-chunking MD 파일 로드 완료")
    except Exception as e:
        print(f"❌ s3-chunking MD 파일 로드 실패: {e}")
        import traceback
        traceback.print_exc()
    
    # 2단계: s3 폴더 일반 문서 로드
    print("\n" + "="*60)
    print("📁 2단계: s3 폴더 일반 문서 로드")
    print("="*60)
    
    # 컴포넌트 초기화
    doc_processor = DocumentProcessor()
    embedding_manager = EmbeddingManager()
    vectorstore_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
    
    # 지원되는 파일 확장자 (MD 제외)
    supported_extensions = ['.txt', '.docx', '.pdf']  # MD는 이미 처리됨
    
    total_documents_loaded = 0
    total_chunks = 0
    
    # s3 폴더 처리
    s3_folder = s3_folders["s3"]
    if os.path.exists(s3_folder):
        print(f"\n📂 처리 중: {s3_folder}")
        
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
                        # 문서 로드
                        documents = doc_processor.load_document(file_path)
                        
                        if not documents:
                            print(f"   ⚠️ 문서가 비어있습니다")
                            continue
                        
                        # 기본 청킹 전략 적용
                        strategy = get_chunking_strategy('basic')
                        chunks = strategy.split_documents(documents)
                        
                        # 메타데이터 보강
                        for chunk in chunks:
                            chunk.metadata.update({
                                'source': file_path,
                                'filename': file,
                                'folder_type': 's3',
                                'processing_strategy': 'basic_chunking'
                            })
                        
                        # 벡터 DB에 저장
                        vectorstore_manager.add_documents(chunks, "basic")
                        
                        print(f"   ✅ {len(chunks)}개 청크 저장 완료 (basic 컬렉션)")
                        
                        total_documents_loaded += 1
                        total_chunks += len(chunks)
                        
                    except Exception as e:
                        print(f"   ❌ 처리 실패: {str(e)}")
    
    # 최종 통계
    try:
        counts = vectorstore_manager.get_document_count()
        print(f"\n" + "="*60)
        print("📊 최종 저장 통계:")
        print("="*60)
        print(f"   - 기본 청킹 (s3): {counts.get('basic', 0)}개")
        print(f"   - MD 최적화 청킹 (s3-chunking): {counts.get('custom', 0)}개")
        print(f"   - 전체: {counts.get('total', 0)}개")
    except Exception as e:
        print(f"⚠️ 통계 조회 실패: {e}")
    
    elapsed_time = time.time() - start_time
    print(f"\n⏱️ 총 처리 시간: {elapsed_time:.2f}초")
    print(f"\n🎉 통합 문서 로딩 완료!")
    
    return total_documents_loaded, total_chunks


def verify_image_support():
    """이미지 지원 확인"""
    print("\n🔍 이미지 지원 확인...")
    
    try:
        from models.vectorstore import DualVectorStoreManager
        from models.embeddings import EmbeddingManager
        
        embedding_manager = EmbeddingManager()
        vectorstore_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
        
        # 이미지 관련 쿼리 테스트
        test_query = "이미지"
        results = vectorstore_manager.similarity_search_with_score(test_query, "custom", k=3)
        
        image_chunks = 0
        for doc, score in results:
            if doc.metadata.get('has_images', False):
                image_chunks += 1
                print(f"\n✅ 이미지 포함 청크 발견:")
                print(f"   - 섹션: {doc.metadata.get('section', 'N/A')}")
                print(f"   - 이미지 수: {len(doc.metadata.get('images', []))}")
                for img in doc.metadata.get('images', [])[:2]:  # 처음 2개만 표시
                    print(f"   - 경로: {img['path']}")
        
        if image_chunks == 0:
            print("⚠️ 이미지 포함 청크를 찾을 수 없습니다.")
        else:
            print(f"\n✅ 총 {image_chunks}개의 이미지 포함 청크 확인")
            
    except Exception as e:
        print(f"❌ 이미지 지원 확인 실패: {e}")


if __name__ == "__main__":
    print("🎯 통합 문서 로딩 시스템")
    print("   - s3: Word/PDF 문서 (기본 청킹)")
    print("   - s3-chunking: 최적화된 MD 파일 (이미지 경로 포함)")
    print()
    
    # 문서 로딩 실행
    docs_loaded, chunks_created = load_all_documents_with_md_priority(clear_before_load=True)
    
    # 이미지 지원 확인
    verify_image_support()
    
    print("\n💡 사용 가이드:")
    print("   - 모드 1: 사내서버 vLLM + s3-기본")
    print("   - 모드 2: 사내서버 vLLM + s3-chunking (MD 최적화)")
    print("   - 모드 3: ChatGPT + s3-기본")
    print("   - 모드 4: ChatGPT + s3-chunking (MD 최적화)")
    print("\n   ➡️ s3-chunking 모드에서 이미지 경로 정보도 함께 제공됩니다.")