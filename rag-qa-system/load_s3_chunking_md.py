#!/usr/bin/env python3
"""
s3-chunking 전용 MD 파일 로더
최적화된 청킹으로 MD 파일들을 처리하고 이미지 경로 정보도 보존
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import hashlib

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.embeddings import EmbeddingManager
from models.vectorstore import DualVectorStoreManager
from services.advanced_chunking_strategies import AdvancedChunkingStrategies
from langchain.schema import Document


class OptimizedMarkdownChunker:
    """최적화된 마크다운 청킹 클래스 - 고급 청킹 전략 포함"""
    
    def __init__(self, chunk_size_limit: int = 1500, chunk_overlap: int = 250, preserve_images: bool = True, use_advanced_chunking: bool = True):
        self.chunk_size_limit = chunk_size_limit
        self.chunk_overlap = chunk_overlap
        self.preserve_images = preserve_images
        self.use_advanced_chunking = use_advanced_chunking
        self.image_pattern = re.compile(r'!\[.*?\]\((.*?)\)')
        
        # 고급 청킹 전략 초기화
        if use_advanced_chunking:
            self.advanced_chunker = AdvancedChunkingStrategies(
                base_chunk_size=chunk_size_limit,
                overlap_ratio=chunk_overlap / chunk_size_limit
            )
        
    def chunk_markdown_file(self, file_path: str, chunking_strategy: str = "hybrid") -> List[Document]:
        """MD 파일을 청킹하여 Document 객체 리스트로 반환"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            filename = os.path.basename(file_path)
            
            # 고급 청킹 사용 여부에 따라 처리 방식 선택
            if self.use_advanced_chunking and hasattr(self, 'advanced_chunker'):
                documents = self._apply_advanced_chunking(content, file_path, filename, chunking_strategy)
            else:
                # 기존 방식 사용
                sections = self._split_by_sections(content)
                documents = self._create_overlapped_documents(sections, file_path, filename)
            
            return documents
            
        except Exception as e:
            print(f"❌ MD 파일 청킹 실패 ({file_path}): {e}")
            return []
    
    def _apply_advanced_chunking(self, content: str, file_path: str, filename: str, chunking_strategy: str) -> List[Document]:
        """고급 청킹 전략 적용"""
        base_metadata = {
            'source': file_path,
            'filename': filename,
            'folder_type': 's3-chunking',
            'file_type': 'markdown',
            'processing_strategy': f'advanced_{chunking_strategy}_chunking'
        }
        
        # 전략별 청킹 적용
        if chunking_strategy == "semantic":
            return self.advanced_chunker.semantic_chunking(content, base_metadata)
        elif chunking_strategy == "question_aware":
            return self.advanced_chunker.question_aware_chunking(content, base_metadata)
        elif chunking_strategy == "hierarchical":
            return self.advanced_chunker.hierarchical_chunking(content, base_metadata)
        elif chunking_strategy == "hybrid":
            return self.advanced_chunker.hybrid_chunking(content, base_metadata)
        else:
            # 기본적으로 하이브리드 방식 사용
            return self.advanced_chunker.hybrid_chunking(content, base_metadata)
    
    def _extract_images(self, content: str) -> List[Dict[str, str]]:
        """텍스트에서 이미지 경로 추출"""
        images = []
        for match in self.image_pattern.finditer(content):
            image_path = match.group(1)
            # GIF 확장자를 JPG로 치환
            if image_path.endswith('.gif'):
                image_path = image_path.replace('.gif', '-0000.jpg')
            
            images.append({
                'path': image_path,
                'full_tag': match.group(0)
            })
        return images
    
    def _create_overlapped_documents(self, sections: List[Dict], file_path: str, filename: str) -> List[Document]:
        """중첩 기능을 포함한 문서 생성"""
        documents = []
        
        for idx, section in enumerate(sections):
            # 현재 섹션의 기본 문서
            current_content = section['content']
            images = self._extract_images(current_content)
            
            # 기본 문서 생성
            doc = Document(
                page_content=current_content,
                metadata={
                    'source': file_path,
                    'filename': filename,
                    'section': section['title'],
                    'chunk_id': str(idx),
                    'chunk_type': section['type'],
                    'images_count': len(images),
                    'has_images': len(images) > 0,
                    'folder_type': 's3-chunking',
                    'file_type': 'markdown',
                    'processing_strategy': 'optimized_md_chunking_with_overlap',
                    'is_overlap': False
                }
            )
            documents.append(doc)
            
            # 중첩 문서 생성 (다음 섹션과)
            if idx < len(sections) - 1 and len(current_content) > self.chunk_overlap:
                next_section = sections[idx + 1]
                
                # 현재 섹션의 마지막 부분 + 다음 섹션의 시작 부분
                current_end = current_content[-self.chunk_overlap:]
                next_start = next_section['content'][:self.chunk_overlap]
                
                # 섹션 헤더 보존
                overlap_content = f"## {section['title']}\n...\n{current_end}\n\n## {next_section['title']}\n{next_start}"
                
                overlap_images = self._extract_images(overlap_content)
                
                overlap_doc = Document(
                    page_content=overlap_content,
                    metadata={
                        'source': file_path,
                        'filename': filename,
                        'section': f"{section['title']} → {next_section['title']}",
                        'chunk_id': f"{idx}_overlap_{idx+1}",
                        'chunk_type': 'overlap',
                        'images_count': len(overlap_images),
                        'has_images': len(overlap_images) > 0,
                        'folder_type': 's3-chunking',
                        'file_type': 'markdown',
                        'processing_strategy': 'optimized_md_chunking_with_overlap',
                        'is_overlap': True
                    }
                )
                documents.append(overlap_doc)
        
        return documents
    
    def _split_by_sections(self, content: str) -> List[Dict]:
        """마크다운을 섹션별로 분할"""
        sections = []
        lines = content.split('\n')
        
        current_section = {"title": "", "content": "", "type": "text"}
        in_table = False
        table_buffer = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 주요 섹션 헤딩 감지
            if re.match(r'^#{1,3}\s+', line_stripped):
                # 이전 섹션 저장
                if current_section['content'].strip():
                    sections.append(current_section)
                
                # 새 섹션 시작
                current_section = {
                    "title": line_stripped.replace('#', '').strip(),
                    "content": line + '\n',
                    "type": "section"
                }
            
            # 테이블 감지 및 처리
            elif '|' in line and line.count('|') >= 2:
                if not in_table:
                    # 테이블 시작 - 현재 섹션 저장
                    if current_section['content'].strip() and not re.match(r'^#{1,3}\s+', current_section['content'].strip()):
                        sections.append(current_section)
                    
                    # 테이블 버퍼 시작
                    table_buffer = [line]
                    in_table = True
                else:
                    table_buffer.append(line)
            
            # 테이블 종료 감지
            elif in_table and (line_stripped == "" or not '|' in line):
                if table_buffer:
                    # 테이블을 별도 섹션으로 저장
                    table_content = '\n'.join(table_buffer)
                    table_section = {
                        "title": current_section.get("title", "테이블"),
                        "content": table_content,
                        "type": "table"
                    }
                    sections.append(table_section)
                    table_buffer = []
                
                in_table = False
                
                # 새 섹션 시작
                if line_stripped:
                    current_section = {
                        "title": current_section.get("title", ""),
                        "content": line + '\n',
                        "type": "text"
                    }
            
            else:
                if not in_table:
                    current_section['content'] += line + '\n'
                    
                    # 청크 크기 제한 확인
                    if len(current_section['content']) > self.chunk_size_limit:
                        sections.append(current_section)
                        current_section = {
                            "title": current_section.get("title", ""),
                            "content": "",
                            "type": "text"
                        }
        
        # 마지막 섹션 처리
        if in_table and table_buffer:
            table_content = '\n'.join(table_buffer)
            sections.append({
                "title": current_section.get("title", "테이블"),
                "content": table_content,
                "type": "table"
            })
        
        if current_section['content'].strip():
            sections.append(current_section)
        
        return sections


class S3ChunkingMDLoader:
    """s3-chunking 폴더의 MD 파일 전용 로더 - 고급 청킹 전략 포함"""
    
    def __init__(self, use_advanced_chunking: bool = True, default_chunking_strategy: str = "hybrid"):
        # 고급 청킹 전략을 포함한 청킹 설정
        self.chunker = OptimizedMarkdownChunker(
            chunk_size_limit=1500, 
            chunk_overlap=250,
            use_advanced_chunking=use_advanced_chunking
        )
        self.default_chunking_strategy = default_chunking_strategy
        self.embedding_manager = EmbeddingManager()
        self.vectorstore_manager = DualVectorStoreManager(self.embedding_manager.get_embeddings())
        
    def load_s3_chunking_md_files(self, clear_before_load: bool = False, chunking_strategy: str = None):
        """s3-chunking 폴더의 MD 파일들을 로드하고 고급 청킹 전략 적용"""
        
        strategy = chunking_strategy or self.default_chunking_strategy
        
        print("🚀 s3-chunking MD 파일 로딩 시작...")
        print(f"📋 청킹 전략: {strategy}")
        print("=" * 60)
        
        # 폴더 경로 설정
        import platform
        if platform.system() == "Windows" or os.name == "nt":
            s3_chunking_path = r"D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\s3-chunking"
        else:
            s3_chunking_path = "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3-chunking"
        
        print(f"📂 대상 폴더: {s3_chunking_path}")
        
        # 기존 custom 컬렉션 데이터 삭제 (옵션)
        if clear_before_load:
            print("🗑️ 기존 custom 컬렉션 데이터 삭제 중...")
            try:
                # custom 컬렉션만 삭제
                self.vectorstore_manager.clear_collection("custom")
                print("✅ custom 컬렉션 초기화 완료")
            except Exception as e:
                print(f"⚠️ 컬렉션 초기화 실패: {e}")
        
        # MD 파일 찾기 - 모든 MD 파일 포함
        md_files = []
        if os.path.exists(s3_chunking_path):
            for file in os.listdir(s3_chunking_path):
                if file.endswith('.md'):
                    md_files.append(os.path.join(s3_chunking_path, file))
        
        if not md_files:
            print("⚠️ 처리할 MD 파일이 없습니다.")
            return
        
        print(f"\n📋 발견된 MD 파일: {len(md_files)}개")
        for md_file in md_files:
            print(f"   - {os.path.basename(md_file)}")
        
        # 전체 청크 저장용
        all_documents = []
        total_chunks = 0
        files_processed = 0
        
        # 각 MD 파일 처리
        for md_file in md_files:
            print(f"\n📄 처리 중: {os.path.basename(md_file)}")
            
            try:
                # MD 파일 청킹 (선택된 전략 적용)
                documents = self.chunker.chunk_markdown_file(md_file, strategy)
                
                if not documents:
                    print("   ⚠️ 문서가 비어있습니다.")
                    continue
                
                # 통계 정보 수집
                chunk_types = {}
                chunk_strategies = {}
                image_chunks = 0
                table_chunks = 0
                quality_scores = []
                importance_scores = []
                
                for doc in documents:
                    chunk_type = doc.metadata.get('chunk_type', 'text')
                    chunk_strategy = doc.metadata.get('chunking_strategy', 'legacy')
                    
                    chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
                    chunk_strategies[chunk_strategy] = chunk_strategies.get(chunk_strategy, 0) + 1
                    
                    if doc.metadata.get('has_images', False):
                        image_chunks += 1
                    if chunk_type == 'table':
                        table_chunks += 1
                    
                    # 고급 청킹 메트릭
                    if 'chunk_quality' in doc.metadata:
                        quality_scores.append(doc.metadata['chunk_quality'])
                    if 'importance_score' in doc.metadata:
                        importance_scores.append(doc.metadata['importance_score'])
                
                print(f"   ✅ {len(documents)}개 청크 생성")
                print(f"      - 청킹 전략: {chunk_strategies}")
                print(f"      - 청크 타입: {chunk_types}")
                print(f"      - 이미지 포함: {image_chunks}개")
                print(f"      - 테이블: {table_chunks}개")
                
                # 품질 메트릭 표시
                if quality_scores:
                    avg_quality = sum(quality_scores) / len(quality_scores)
                    print(f"      - 평균 품질 점수: {avg_quality:.3f}")
                if importance_scores:
                    avg_importance = sum(importance_scores) / len(importance_scores)
                    print(f"      - 평균 중요도 점수: {avg_importance:.3f}")
                
                # 중요 테이블 확인
                for doc in documents:
                    if "결제일별 신용공여기간" in doc.page_content:
                        print(f"      🌟 결제일별 신용공여기간 테이블 발견!")
                    if "장애유형별 본인확인" in doc.page_content:
                        print(f"      🌟 장애유형별 본인확인 테이블 발견!")
                
                all_documents.extend(documents)
                files_processed += 1
                total_chunks += len(documents)
                
            except Exception as e:
                print(f"   ❌ 처리 실패: {e}")
                import traceback
                traceback.print_exc()
        
        # 벡터 DB에 저장
        if all_documents:
            print(f"\n💾 벡터 DB 저장 시작...")
            print(f"   - 총 문서 수: {files_processed}개")
            print(f"   - 총 청크 수: {total_chunks}개")
            
            try:
                # custom 컬렉션에 저장
                self.vectorstore_manager.add_documents(all_documents, "custom")
                
                print(f"\n✅ 벡터 DB 저장 완료!")
                print(f"   - 컬렉션: custom")
                print(f"   - 저장된 청크: {len(all_documents)}개")
                
                # 저장 결과 검증
                self._verify_storage()
                
            except Exception as e:
                print(f"❌ 벡터 DB 저장 실패: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n🎉 s3-chunking MD 파일 로딩 완료!")
    
    def _verify_storage(self):
        """저장된 데이터 검증"""
        try:
            print("\n🔍 저장 데이터 검증...")
            
            # 테스트 쿼리
            test_queries = [
                "결제일별 신용공여기간",
                "1일 결제일",
                "장애유형별 본인확인",
                "할부수수료율"
            ]
            
            for query in test_queries:
                results = self.vectorstore_manager.similarity_search_with_score(
                    query, "custom", k=3
                )
                
                if results:
                    print(f"\n   ✅ '{query}' 검색 결과: {len(results)}개")
                    for doc, score in results[:1]:  # 상위 1개만 표시
                        print(f"      - Score: {score:.4f}")
                        print(f"      - Content: {doc.page_content[:100]}...")
                        if doc.metadata.get('has_images'):
                            print(f"      - 이미지 포함: {doc.metadata.get('images_count', 0)}개")
                else:
                    print(f"   ⚠️ '{query}' 검색 결과 없음")
                    
        except Exception as e:
            print(f"⚠️ 검증 중 오류: {e}")


def main():
    """메인 실행 함수"""
    print("🎯 고급 청킹 전략 선택:")
    print("1. semantic - 의미론적 청킹 (문맥 중심)")
    print("2. question_aware - 질문 유형별 맞춤 청킹")
    print("3. hierarchical - 계층적 문서 구조 기반 청킹")
    print("4. hybrid - 하이브리드 청킹 (추천)")
    print("5. legacy - 기존 청킹 방식")
    
    strategy_choice = input("\n전략을 선택하세요 (1-5, 기본값: 4): ").strip()
    
    strategy_map = {
        "1": "semantic",
        "2": "question_aware", 
        "3": "hierarchical",
        "4": "hybrid",
        "5": "legacy"
    }
    
    selected_strategy = strategy_map.get(strategy_choice, "hybrid")
    use_advanced = selected_strategy != "legacy"
    
    print(f"\n✅ 선택된 전략: {selected_strategy}")
    print("=" * 60)
    
    # 선택된 전략으로 로더 초기화
    loader = S3ChunkingMDLoader(
        use_advanced_chunking=use_advanced,
        default_chunking_strategy=selected_strategy
    )
    
    # clear_before_load=True로 기존 custom 컬렉션 데이터 삭제 후 로드
    loader.load_s3_chunking_md_files(
        clear_before_load=True,
        chunking_strategy=selected_strategy
    )
    
    print("\n💡 사용 방법:")
    print("   - 모드 2: 사내서버 vLLM + s3-chunking")
    print("   - 모드 4: ChatGPT + s3-chunking")
    print(f"   ➡️ {selected_strategy} 청킹으로 더 정확한 검색 가능")
    print("   ➡️ 이미지 경로 정보도 함께 전달")
    
    if selected_strategy != "legacy":
        print(f"\n🔍 {selected_strategy} 청킹 전략의 특징:")
        strategy_descriptions = {
            "semantic": "문맥과 의미 단위로 분할하여 정보의 완전성 보장",
            "question_aware": "자주 묻는 질문 패턴에 최적화된 청킹",
            "hierarchical": "문서 계층 구조를 활용한 다층 청킹",
            "hybrid": "모든 전략을 조합한 최적의 청킹 (중복 제거 포함)"
        }
        print(f"   📋 {strategy_descriptions.get(selected_strategy, '')}")


if __name__ == "__main__":
    main()