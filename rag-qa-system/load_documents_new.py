#!/usr/bin/env python3
"""
개선된 문서 로딩 시스템
- s3 폴더: 기본 청킹 (BasicChunkingStrategy)
- s3-chunking 폴더: /$$/ 구분자 청킹 (CustomDelimiterChunkingStrategy)
"""

import os
import sys
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.document_processor import DocumentProcessor
from services.chunking_strategies import get_chunking_strategy
from models.embeddings import EmbeddingManager
from models.vectorstore import DualVectorStoreManager
from config import Config

def clear_all_data():
    """모든 벡터 DB 데이터 삭제"""
    try:
        print("🗑️ 모든 데이터 삭제 중...")
        vector_manager = DualVectorStoreManager()
        vector_manager.clear_all_collections()
        print("✅ 모든 데이터 삭제 완료")
        return True
    except Exception as e:
        print(f"❌ 데이터 삭제 실패: {e}")
        return False

def load_s3_documents(clear_before_load=True):
    """S3 폴더와 S3-chunking 폴더의 문서를 분리하여 벡터 DB에 저장"""
    
    print("🚀 개선된 문서 로딩 시스템 시작...")
    
    # S3 폴더들 경로 - 환경별 자동 감지
    import platform
    if platform.system() == "Windows" or os.name == "nt":
        # Windows CMD 환경
        s3_folders = {
            "s3": r"D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\s3",
            "s3-chunking": r"D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\s3-chunking"
        }
        print("🪟 Windows 환경에서 실행 중")
    else:
        # WSL/Linux 환경
        s3_folders = {
            "s3": "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3",
            "s3-chunking": "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3-chunking"
        }
        print("🐧 WSL/Linux 환경에서 실행 중")
    
    # 컴포넌트 초기화
    print("🔧 시스템 초기화 중...")
    doc_processor = DocumentProcessor()
    embedding_manager = EmbeddingManager()
    vectorstore_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
    
    # 기존 데이터 삭제 (옵션)
    if clear_before_load:
        print("🗑️ 기존 벡터 DB 데이터 삭제 중...")
        try:
            from models.vectorstore import reset_vectorstore
            reset_vectorstore()
            print("✅ 기존 데이터 삭제 완료")
        except Exception as e:
            print(f"⚠️ 기존 데이터 삭제 실패: {e}")
    
    # 지원되는 파일 확장자
    supported_extensions = ['.txt', '.docx', '.pdf', '.md']
    
    # 각 폴더별 파일 찾기
    total_documents_loaded = 0
    total_chunks = 0
    
    # 전역 중복 제거를 위한 컬렉션별 중복 체크
    global_seen_content = {
        'basic': set(),
        'custom': set()
    }
    
    # 전체 시스템에서 절대 중복 제거 (컬렉션 무관)
    global_absolute_content = set()
    
    for folder_type, s3_folder in s3_folders.items():
        print(f"\n📂 폴더 처리 중: {s3_folder} ({folder_type})")
        
        if not os.path.exists(s3_folder):
            print(f"⚠️ 폴더가 존재하지 않습니다: {s3_folder}")
            continue
        
        folder_documents_loaded = 0
        folder_chunks = 0
        
        for root, dirs, files in os.walk(s3_folder):
            for file in files:
                file_path = os.path.join(root, file)
                file_extension = os.path.splitext(file)[1].lower()
                
                # 임시 파일 제외
                if file.startswith('~$') or file.startswith('.'):
                    print(f"   ⏭️ 임시 파일 건너뛰기: {file}")
                    continue
                
                # s3-chunking 폴더는 MD 파일만 처리
                if folder_type == "s3-chunking" and file_extension != '.md':
                    continue
                
                # s3-chunking 폴더는 특정 MD 파일만 처리 (완전판, 최적화 파일)
                if folder_type == "s3-chunking" and file_extension == '.md':
                    if not ('완전판' in file or '최적화' in file):
                        print(f"   ⏭️ s3-chunking: 대상 외 MD 파일 건너뛰기: {file}")
                        continue
                
                if file_extension in supported_extensions:
                    print(f"\n📄 처리 중: {file}")
                    
                    try:
                        # 문서 로드
                        documents = doc_processor.load_document(file_path)
                        
                        if not documents:
                            print(f"   ⚠️ 문서가 비어있습니다: {file}")
                            continue
                        
                        # 청킹 전략 선택
                        if folder_type == "s3":
                            # s3 폴더: 기본 청킹 (개선된 버전)
                            strategy = get_chunking_strategy('basic')
                            collection_name = "basic"
                            print(f"   🔧 기본 청킹 적용")
                        else:
                            # s3-chunking 폴더: /$$/ 구분자 청킹
                            strategy = get_chunking_strategy('custom_delimiter')
                            collection_name = "custom"
                            print(f"   🔧 /$$/ 구분자 청킹 적용")
                        
                        # 청킹 수행
                        chunks = strategy.split_documents(documents)
                        
                        # 메타데이터 보강
                        for chunk in chunks:
                            chunk.metadata.update({
                                'source': file_path,
                                'filename': file,
                                'folder_type': folder_type,
                                'processing_timestamp': os.path.getmtime(file_path)
                            })
                        
                        # 중복 청크 제거 - 전역 및 로컬 중복 체크
                        unique_chunks = []
                        seen_content = set()
                        
                        for chunk in chunks:
                            content_hash = hash(chunk.page_content.strip())
                            
                            # 로컬 파일 내 중복 체크
                            if content_hash in seen_content:
                                continue
                            
                            # 절대 중복 체크 (전체 시스템에서 유일)
                            if content_hash in global_absolute_content:
                                print(f"   🚫 절대 중복 제거: {repr(chunk.page_content[:50])}...")
                                continue
                                
                            # 컬렉션별 중복 체크
                            if content_hash in global_seen_content[collection_name]:
                                print(f"   🔄 컬렉션 중복 제거: {repr(chunk.page_content[:50])}...")
                                continue
                            
                            # 중복이 아니면 추가
                            seen_content.add(content_hash)
                            global_seen_content[collection_name].add(content_hash)
                            global_absolute_content.add(content_hash)
                            unique_chunks.append(chunk)
                        
                        # 중복 제거 결과 출력
                        if len(chunks) != len(unique_chunks):
                            print(f"   🔄 중복 제거: {len(chunks)}개 → {len(unique_chunks)}개")
                        
                        # 벡터 저장소에 추가
                        vectorstore_manager.add_documents(unique_chunks, collection_name)
                        
                        print(f"   ✅ {len(unique_chunks)}개 청크 저장 완료 ({collection_name} 컬렉션)")
                        
                        folder_documents_loaded += 1
                        folder_chunks += len(unique_chunks)
                        
                        # 특정 키워드 분석 (신용카드알뜰이용법 등)
                        problematic_chunks = 0
                        smart_usage_chunks = 0
                        
                        for chunk in chunks:
                            content = chunk.page_content
                            if "회원제 업소" in content and "신용카드알뜰이용법" in content:
                                problematic_chunks += 1
                            if "신용카드알뜰이용법" in content:
                                smart_usage_chunks += 1
                        
                        if problematic_chunks > 0:
                            print(f"   ⚠️ 경고: {problematic_chunks}개 청크에서 섹션 혼재 발견")
                        if smart_usage_chunks > 0:
                            print(f"   📊 '신용카드알뜰이용법' 포함 청크: {smart_usage_chunks}개")
                            
                    except Exception as e:
                        print(f"   ❌ 처리 실패: {str(e)}")
        
        print(f"\n📊 {folder_type} 폴더 처리 완료:")
        print(f"   - 처리된 문서: {folder_documents_loaded}개")
        print(f"   - 생성된 청크: {folder_chunks}개")
        
        total_documents_loaded += folder_documents_loaded
        total_chunks += folder_chunks
    
    # 최종 통계
    try:
        counts = vectorstore_manager.get_document_count()
        print(f"\n📈 최종 저장 통계:")
        print(f"   - 기본 청킹 (s3): {counts.get('basic', 0)}개")
        print(f"   - 커스텀 청킹 (s3-chunking): {counts.get('custom', 0)}개")
        print(f"   - 전체: {counts.get('total', 0)}개")
    except Exception as e:
        print(f"⚠️ 통계 조회 실패: {e}")
    
    # 중복 제거 통계
    print(f"\n🔄 전역 중복 제거 통계:")
    print(f"   - 기본 청킹 고유 콘텐츠: {len(global_seen_content['basic'])}개")
    print(f"   - 커스텀 청킹 고유 콘텐츠: {len(global_seen_content['custom'])}개")
    print(f"   - 전체 절대 고유 콘텐츠: {len(global_absolute_content)}개")
    print(f"   - 컬렉션별 합계: {len(global_seen_content['basic']) + len(global_seen_content['custom'])}개")
    
    print(f"\n🎉 문서 로딩 완료!")
    print(f"   - 총 처리된 문서: {total_documents_loaded}개")
    print(f"   - 총 생성된 청크: {total_chunks}개")
    print(f"   - 중복 제거 후 절대 고유 청크: {len(global_absolute_content)}개")
    
    return total_documents_loaded, total_chunks

if __name__ == "__main__":
    # 문서 로딩 실행
    docs_loaded, chunks_created = load_s3_documents(clear_before_load=True)