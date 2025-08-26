#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
최적화된 청킹 로더 - s3-chunking 전용
MD 파일을 세분화된 청킹으로 처리하여 벡터 DB에 저장
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path

# 상위 디렉토리를 Python 패스에 추가
current_dir = Path(__file__).parent
parent_dir = current_dir.parent / "rag-qa-system"
sys.path.append(str(parent_dir))

from models.vectorstore import DualVectorStoreManager
from models.embeddings import EmbeddingManager

class OptimizedChunker:
    """최적화된 청킹 전략 클래스"""
    
    def __init__(self):
        self.chunk_patterns = [
            # 주요 섹션 구분자
            r'^#{1,3}\s+.*$',  # # ## ### 헤딩
            r'^---+$',         # 가로선 구분자
            r'^\|.*\|$',       # 테이블 행
            r'^\*\*.*\*\*$',   # 볼드 제목
            r'^\d+[.)]',       # 번호 리스트
            r'^\s*[-*]\s+',    # 불렛 리스트
        ]
    
    def chunk_markdown_content(self, content: str, source_file: str = "optimized.md") -> list:
        """MD 내용을 최적화된 청킹으로 분할"""
        chunks = []
        lines = content.split('\n')
        
        current_chunk = []
        current_section = ""
        chunk_id = 0
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 주요 섹션 헤딩 감지 (# ## ###)
            if re.match(r'^#{1,3}\s+', line):
                # 이전 청크 저장
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk).strip()
                    if chunk_text:
                        chunks.append({
                            'content': chunk_text,
                            'metadata': {
                                'chunk_id': chunk_id,
                                'section': current_section,
                                'source_file': source_file,
                                'chunk_type': 'section',
                                'length': len(chunk_text)
                            }
                        })
                        chunk_id += 1
                
                # 새로운 섹션 시작
                current_section = line.replace('#', '').strip()
                current_chunk = [line]
            
            # 테이블 감지 및 처리
            elif re.match(r'^\|.*\|', line):
                table_chunk = self._extract_table(lines, i)
                if table_chunk['content']:
                    table_chunk['metadata'].update({
                        'chunk_id': chunk_id,
                        'section': current_section,
                        'source_file': source_file,
                        'chunk_type': 'table'
                    })
                    chunks.append(table_chunk)
                    chunk_id += 1
                    
                # 테이블 끝까지 인덱스 이동
                i = table_chunk['end_index']
                continue
            
            # 가로선 구분자 (---)
            elif re.match(r'^---+$', line):
                # 이전 청크 저장
                if current_chunk and len(current_chunk) > 1:  # 헤딩만 있는 경우 제외
                    chunk_text = '\n'.join(current_chunk).strip()
                    if chunk_text:
                        chunks.append({
                            'content': chunk_text,
                            'metadata': {
                                'chunk_id': chunk_id,
                                'section': current_section,
                                'source_file': source_file,
                                'chunk_type': 'section',
                                'length': len(chunk_text)
                            }
                        })
                        chunk_id += 1
                current_chunk = []
            
            # 일반 텍스트
            else:
                current_chunk.append(line)
                
                # 청크 크기 제한 (2000자)
                if len('\n'.join(current_chunk)) > 2000:
                    chunk_text = '\n'.join(current_chunk).strip()
                    if chunk_text:
                        chunks.append({
                            'content': chunk_text,
                            'metadata': {
                                'chunk_id': chunk_id,
                                'section': current_section,
                                'source_file': source_file,
                                'chunk_type': 'content',
                                'length': len(chunk_text)
                            }
                        })
                        chunk_id += 1
                    current_chunk = []
            
            i += 1
        
        # 마지막 청크 처리
        if current_chunk:
            chunk_text = '\n'.join(current_chunk).strip()
            if chunk_text:
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        'chunk_id': chunk_id,
                        'section': current_section,
                        'source_file': source_file,
                        'chunk_type': 'content',
                        'length': len(chunk_text)
                    }
                })
        
        return chunks
    
    def _extract_table(self, lines: list, start_index: int) -> dict:
        """테이블 전체를 하나의 청크로 추출"""
        table_lines = []
        i = start_index
        
        # 테이블 헤더 및 구분자 찾기
        while i < len(lines) and (re.match(r'^\|.*\|', lines[i]) or re.match(r'^[-:|]+$', lines[i])):
            table_lines.append(lines[i])
            i += 1
        
        # 테이블 데이터 계속 읽기
        while i < len(lines) and re.match(r'^\|.*\|', lines[i]):
            table_lines.append(lines[i])
            i += 1
        
        table_content = '\n'.join(table_lines).strip()
        
        return {
            'content': table_content,
            'metadata': {
                'chunk_type': 'table',
                'length': len(table_content),
                'table_rows': len([line for line in table_lines if '|' in line])
            },
            'end_index': i - 1
        }

class OptimizedChunkingLoader:
    """최적화된 청킹 로더"""
    
    def __init__(self):
        self.chunker = OptimizedChunker()
        self.embedding_manager = EmbeddingManager()
        self.vectorstore_manager = DualVectorStoreManager()
        
        print("🚀 최적화된 청킹 로더 초기화 완료")
        print(f"   - 임베딩: {self.embedding_manager.model_name}")
        print(f"   - 벡터 DB: DualVectorStoreManager")
    
    def load_markdown_file(self, md_file_path: str) -> dict:
        """MD 파일을 로드하고 청킹 처리"""
        try:
            print(f"\n📖 MD 파일 로드 중: {md_file_path}")
            
            with open(md_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            filename = os.path.basename(md_file_path)
            chunks = self.chunker.chunk_markdown_content(content, filename)
            
            print(f"✅ 청킹 완료: {len(chunks)}개 청크 생성")
            
            # 청크 정보 출력
            for i, chunk in enumerate(chunks):
                metadata = chunk['metadata']
                print(f"   청크 {i}: [{metadata['chunk_type']}] {metadata['section'][:30]}... ({metadata['length']}자)")
            
            return {
                'source_file': filename,
                'total_chunks': len(chunks),
                'chunks': chunks,
                'processing_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ MD 파일 로드 실패: {str(e)}")
            raise
    
    def store_to_vectordb(self, chunk_data: dict) -> bool:
        """청크 데이터를 벡터 DB에 저장"""
        try:
            print(f"\n💾 벡터 DB 저장 시작: {chunk_data['source_file']}")
            
            documents = []
            metadatas = []
            
            for chunk in chunk_data['chunks']:
                documents.append(chunk['content'])
                
                metadata = chunk['metadata'].copy()
                metadata.update({
                    'chunking_strategy': 'optimized_markdown',
                    'processing_time': chunk_data['processing_time'],
                    'file_type': 'markdown'
                })
                metadatas.append(metadata)
            
            # custom 컬렉션에 저장 (s3-chunking용)
            collection_name = "custom"
            
            # 기존 동일 파일 삭제
            self._clear_existing_file_chunks(chunk_data['source_file'], collection_name)
            
            # 벡터 임베딩 생성
            print("🔄 임베딩 벡터 생성 중...")
            embeddings = self.embedding_manager.embed_documents(documents)
            
            # 벡터 DB에 저장
            print("📝 벡터 DB 저장 중...")
            success = self.vectorstore_manager.add_documents_to_collection(
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
                collection_name=collection_name
            )
            
            if success:
                print(f"✅ 벡터 DB 저장 완료: {len(documents)}개 청크")
                return True
            else:
                print("❌ 벡터 DB 저장 실패")
                return False
                
        except Exception as e:
            print(f"❌ 벡터 DB 저장 중 오류: {str(e)}")
            return False
    
    def _clear_existing_file_chunks(self, filename: str, collection_name: str):
        """기존 파일의 청크들 삭제"""
        try:
            print(f"🗑️ 기존 파일 청크 삭제 중: {filename}")
            # 여기에 기존 파일 삭제 로직 구현 (선택사항)
            # self.vectorstore_manager.delete_by_metadata({"source_file": filename}, collection_name)
            pass
        except Exception as e:
            print(f"⚠️ 기존 파일 청크 삭제 중 오류: {str(e)}")
    
    def save_chunk_analysis(self, chunk_data: dict, output_path: str):
        """청킹 분석 결과 저장"""
        try:
            analysis = {
                'source_file': chunk_data['source_file'],
                'total_chunks': chunk_data['total_chunks'],
                'processing_time': chunk_data['processing_time'],
                'chunk_summary': [],
                'chunk_statistics': {}
            }
            
            # 청크별 요약
            chunk_types = {}
            total_length = 0
            
            for chunk in chunk_data['chunks']:
                metadata = chunk['metadata']
                chunk_type = metadata['chunk_type']
                chunk_length = metadata['length']
                
                analysis['chunk_summary'].append({
                    'chunk_id': metadata['chunk_id'],
                    'section': metadata['section'],
                    'type': chunk_type,
                    'length': chunk_length,
                    'preview': chunk['content'][:100] + '...' if len(chunk['content']) > 100 else chunk['content']
                })
                
                # 통계
                chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
                total_length += chunk_length
            
            analysis['chunk_statistics'] = {
                'chunk_types': chunk_types,
                'average_length': total_length // len(chunk_data['chunks']) if chunk_data['chunks'] else 0,
                'total_length': total_length
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)
            
            print(f"📊 청킹 분석 결과 저장: {output_path}")
            
        except Exception as e:
            print(f"❌ 청킹 분석 결과 저장 실패: {str(e)}")

def main():
    """메인 실행 함수"""
    print("🎯 최적화된 청킹 로더 시작")
    print("=" * 60)
    
    # 파일 경로 설정
    current_dir = Path(__file__).parent
    md_file = current_dir / "BC카드_카드이용안내_최적화.md"
    output_dir = current_dir / "optimized_chunks"
    output_dir.mkdir(exist_ok=True)
    
    if not md_file.exists():
        print(f"❌ MD 파일을 찾을 수 없습니다: {md_file}")
        return
    
    try:
        # 로더 초기화
        loader = OptimizedChunkingLoader()
        
        # MD 파일 로드 및 청킹
        chunk_data = loader.load_markdown_file(str(md_file))
        
        # 청킹 분석 결과 저장
        analysis_file = output_dir / "chunk_analysis.json"
        loader.save_chunk_analysis(chunk_data, str(analysis_file))
        
        # 벡터 DB에 저장
        success = loader.store_to_vectordb(chunk_data)
        
        if success:
            print(f"\n🎉 최적화된 청킹 처리 완료!")
            print(f"   - 총 청크 수: {chunk_data['total_chunks']}개")
            print(f"   - 분석 결과: {analysis_file}")
            print(f"   - 벡터 DB: custom 컬렉션에 저장됨")
        else:
            print(f"\n❌ 벡터 DB 저장 실패")
            
    except Exception as e:
        print(f"\n💥 처리 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()