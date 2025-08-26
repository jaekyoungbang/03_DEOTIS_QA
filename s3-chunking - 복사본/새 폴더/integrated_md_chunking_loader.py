#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 MD 청킹 로더 - s3-chunking 전용
BC카드 2개 MD 파일을 최적화된 청킹으로 처리하여 벡터 DB에 저장
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 상위 디렉토리를 Python 패스에 추가
current_dir = Path(__file__).parent
rag_system_dir = current_dir.parent / "rag-qa-system"
sys.path.append(str(rag_system_dir))

try:
    from models.vectorstore import DualVectorStoreManager
    from models.embeddings import EmbeddingManager
except ImportError:
    print("⚠️ Import 실패: rag-qa-system 모듈들")
    print("   현재 디렉토리에서 실행해주세요: cd /mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3-chunking")

class OptimizedMarkdownChunker:
    """최적화된 마크다운 청킹 클래스"""
    
    def __init__(self, chunk_size_limit: int = 2000):
        self.chunk_size_limit = chunk_size_limit
        
    def chunk_markdown_file(self, md_file_path: str) -> Dict:
        """마크다운 파일을 읽어서 최적화된 청킹 수행"""
        try:
            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            filename = os.path.basename(md_file_path)
            chunks = self._chunk_by_sections(content, filename)
            
            return {
                'source_file': filename,
                'file_path': md_file_path,
                'total_chunks': len(chunks),
                'chunks': chunks,
                'processing_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ MD 파일 청킹 실패 ({md_file_path}): {e}")
            return None
    
    def _chunk_by_sections(self, content: str, filename: str) -> List[Dict]:
        """섹션별 청킹 수행"""
        chunks = []
        lines = content.split('\n')
        
        current_chunk_lines = []
        current_section = ""
        chunk_id = 0
        in_table = False
        table_buffer = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 주요 섹션 헤딩 감지 (##, ###)
            if re.match(r'^#{2,3}\s+', line_stripped):
                # 이전 청크 완료 처리
                if current_chunk_lines:
                    chunk = self._create_chunk(current_chunk_lines, current_section, filename, chunk_id)
                    if chunk:
                        chunks.append(chunk)
                        chunk_id += 1
                
                # 새 섹션 시작
                current_section = line_stripped.replace('#', '').strip()
                current_chunk_lines = [line]
                in_table = False
            
            # 테이블 감지
            elif re.match(r'^[\|\s]*\|.*\|[\|\s]*$', line_stripped):
                if not in_table:
                    # 테이블 시작 - 이전 내용 청크로 저장
                    if current_chunk_lines and len(current_chunk_lines) > 1:
                        chunk = self._create_chunk(current_chunk_lines, current_section, filename, chunk_id, chunk_type='section')
                        if chunk:
                            chunks.append(chunk)
                            chunk_id += 1
                    
                    # 테이블 전용 청크 시작
                    table_buffer = [line]
                    in_table = True
                else:
                    table_buffer.append(line)
            
            # 구분선 (---)
            elif re.match(r'^---+$', line_stripped):
                if in_table and table_buffer:
                    # 테이블 청크 완료
                    table_chunk = self._create_table_chunk(table_buffer, current_section, filename, chunk_id)
                    if table_chunk:
                        chunks.append(table_chunk)
                        chunk_id += 1
                    table_buffer = []
                    in_table = False
                
                # 구분선으로 섹션 구분
                if current_chunk_lines and len(current_chunk_lines) > 1:
                    chunk = self._create_chunk(current_chunk_lines, current_section, filename, chunk_id)
                    if chunk:
                        chunks.append(chunk)
                        chunk_id += 1
                
                current_chunk_lines = []
            
            else:
                if in_table:
                    # 테이블이 끝났을 가능성
                    if line_stripped == "":
                        continue  # 빈 줄은 무시
                    else:
                        # 테이블 종료
                        if table_buffer:
                            table_chunk = self._create_table_chunk(table_buffer, current_section, filename, chunk_id)
                            if table_chunk:
                                chunks.append(table_chunk)
                                chunk_id += 1
                            table_buffer = []
                        in_table = False
                        current_chunk_lines = [line]
                else:
                    current_chunk_lines.append(line)
                    
                    # 청크 크기 제한 체크
                    current_content = '\n'.join(current_chunk_lines)
                    if len(current_content) > self.chunk_size_limit:
                        chunk = self._create_chunk(current_chunk_lines, current_section, filename, chunk_id)
                        if chunk:
                            chunks.append(chunk)
                            chunk_id += 1
                        current_chunk_lines = []
        
        # 마지막 청크 처리
        if in_table and table_buffer:
            table_chunk = self._create_table_chunk(table_buffer, current_section, filename, chunk_id)
            if table_chunk:
                chunks.append(table_chunk)
                chunk_id += 1
        
        if current_chunk_lines:
            chunk = self._create_chunk(current_chunk_lines, current_section, filename, chunk_id)
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def _create_chunk(self, lines: List[str], section: str, filename: str, chunk_id: int, chunk_type: str = 'content') -> Optional[Dict]:
        """일반 청크 생성"""
        content = '\n'.join(lines).strip()
        if not content or len(content) < 50:  # 너무 짧은 청크 제외
            return None
        
        return {
            'content': content,
            'metadata': {
                'chunk_id': chunk_id,
                'section': section,
                'source_file': filename,
                'chunk_type': chunk_type,
                'length': len(content)
            }
        }
    
    def _create_table_chunk(self, table_lines: List[str], section: str, filename: str, chunk_id: int) -> Optional[Dict]:
        """테이블 전용 청크 생성"""
        content = '\n'.join(table_lines).strip()
        if not content:
            return None
        
        # 테이블 행 수 계산
        table_rows = len([line for line in table_lines if '|' in line and not re.match(r'^[\s\-\|:]+$', line.strip())])
        
        return {
            'content': content,
            'metadata': {
                'chunk_id': chunk_id,
                'section': section,
                'source_file': filename,
                'chunk_type': 'table',
                'length': len(content),
                'table_rows': table_rows,
                'is_structured_data': True
            }
        }

class IntegratedMDChunkingLoader:
    """통합 MD 청킹 로더"""
    
    def __init__(self):
        self.chunker = OptimizedMarkdownChunker()
        self.chunk_results = []
        
        # 벡터스토어 및 임베딩 매니저 초기화
        try:
            self.embedding_manager = EmbeddingManager()
            self.vectorstore_manager = DualVectorStoreManager()
            print("✅ 벡터 DB 및 임베딩 매니저 초기화 완료")
        except Exception as e:
            print(f"⚠️ 벡터 DB 초기화 실패: {e}")
            self.embedding_manager = None
            self.vectorstore_manager = None
    
    def load_all_md_files(self, md_dir: str = None) -> List[Dict]:
        """s3-chunking 폴더의 모든 완전판 MD 파일 로드"""
        if md_dir is None:
            md_dir = str(current_dir)
        
        md_files = [
            os.path.join(md_dir, "BC카드_카드이용안내_완전판.md"),
            os.path.join(md_dir, "BC카드_신용카드업무처리안내_완전판.md")
        ]
        
        print(f"🔍 MD 파일 검색 중: {md_dir}")
        
        results = []
        for md_file in md_files:
            if os.path.exists(md_file):
                print(f"📖 처리 중: {os.path.basename(md_file)}")
                result = self.chunker.chunk_markdown_file(md_file)
                if result:
                    results.append(result)
                    print(f"   ✅ {result['total_chunks']}개 청크 생성")
            else:
                print(f"⚠️ 파일 없음: {os.path.basename(md_file)}")
        
        self.chunk_results = results
        return results
    
    def store_to_vectordb(self, chunk_results: List[Dict] = None) -> bool:
        """모든 청크 데이터를 벡터 DB에 저장"""
        if not self.vectorstore_manager or not self.embedding_manager:
            print("❌ 벡터 DB 또는 임베딩 매니저가 초기화되지 않았습니다.")
            return False
        
        if chunk_results is None:
            chunk_results = self.chunk_results
        
        if not chunk_results:
            print("❌ 저장할 청크 데이터가 없습니다.")
            return False
        
        try:
            print("\n💾 벡터 DB 저장 시작")
            print("=" * 50)
            
            collection_name = "custom"  # s3-chunking 전용 컬렉션
            
            # 모든 문서와 메타데이터 수집
            all_documents = []
            all_metadatas = []
            
            for chunk_data in chunk_results:
                print(f"\n📄 처리 중: {chunk_data['source_file']}")
                
                for chunk in chunk_data['chunks']:
                    all_documents.append(chunk['content'])
                    
                    # 메타데이터 준비
                    metadata = chunk['metadata'].copy()
                    metadata.update({
                        'chunking_strategy': 'integrated_markdown_s3',
                        'processing_time': chunk_data['processing_time'],
                        'file_type': 'markdown_complete',
                        'collection_type': 's3_chunking'
                    })
                    all_metadatas.append(metadata)
            
            print(f"📊 총 청크 수: {len(all_documents)}개")
            
            # 기존 s3-chunking 데이터 삭제 (선택사항)
            # self._clear_s3_chunking_collection(collection_name)
            
            # 벡터 임베딩 생성
            print("🔄 임베딩 벡터 생성 중...")
            embeddings = self.embedding_manager.embed_documents(all_documents)
            print(f"   ✅ {len(embeddings)}개 임베딩 생성 완료")
            
            # 벡터 DB에 일괄 저장
            print("📝 벡터 DB 저장 중...")
            success = self.vectorstore_manager.add_documents_to_collection(
                documents=all_documents,
                metadatas=all_metadatas,
                embeddings=embeddings,
                collection_name=collection_name
            )
            
            if success:
                print("\n🎉 벡터 DB 저장 완료!")
                self._print_storage_summary(chunk_results)
                return True
            else:
                print("\n❌ 벡터 DB 저장 실패")
                return False
                
        except Exception as e:
            print(f"\n💥 벡터 DB 저장 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _print_storage_summary(self, chunk_results: List[Dict]):
        """저장 결과 요약 출력"""
        print("\n📊 저장 결과 요약:")
        print("-" * 40)
        
        total_chunks = 0
        for chunk_data in chunk_results:
            total_chunks += chunk_data['total_chunks']
            
            # 청크 타입별 통계
            chunk_types = {}
            for chunk in chunk_data['chunks']:
                chunk_type = chunk['metadata']['chunk_type']
                chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            
            print(f"📄 {chunk_data['source_file']}: {chunk_data['total_chunks']}개 청크")
            for chunk_type, count in chunk_types.items():
                print(f"   - {chunk_type}: {count}개")
        
        print(f"\n✨ 전체: {total_chunks}개 청크가 'custom' 컬렉션에 저장됨")
        print(f"🎯 s3-chunking 모드에서 최적화된 검색 가능")
    
    def save_processing_log(self, output_file: str = None):
        """처리 결과 로그 저장"""
        if output_file is None:
            output_file = os.path.join(current_dir, "integrated_chunking_log.json")
        
        try:
            log_data = {
                'processing_time': datetime.now().isoformat(),
                'total_files': len(self.chunk_results),
                'chunk_results': self.chunk_results,
                'summary': {
                    'total_chunks': sum(r['total_chunks'] for r in self.chunk_results),
                    'files_processed': [r['source_file'] for r in self.chunk_results],
                    'chunking_strategy': 'integrated_markdown_s3',
                    'target_collection': 'custom'
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            print(f"📄 처리 로그 저장: {output_file}")
            
        except Exception as e:
            print(f"⚠️ 로그 저장 실패: {e}")

def main():
    """메인 실행 함수"""
    print("🚀 통합 MD 청킹 로더 시작")
    print("=" * 60)
    print("📋 BC카드 완전판 MD 파일들을 s3-chunking 최적화 처리")
    print()
    
    try:
        # 로더 초기화
        loader = IntegratedMDChunkingLoader()
        
        # 모든 MD 파일 로드 및 청킹
        print("1️⃣ MD 파일 로드 및 청킹 처리...")
        chunk_results = loader.load_all_md_files()
        
        if not chunk_results:
            print("❌ 처리할 MD 파일이 없습니다.")
            return
        
        # 벡터 DB에 저장
        print("\n2️⃣ 벡터 DB 저장...")
        success = loader.store_to_vectordb()
        
        # 처리 로그 저장
        print("\n3️⃣ 처리 로그 저장...")
        loader.save_processing_log()
        
        if success:
            print("\n🎊 통합 MD 청킹 처리 완료!")
            print("\n💡 사용법:")
            print("   - 모드 2: 사내서버 vLLM + s3-chunking")
            print("   - 모드 4: ChatGPT + s3-chunking")
            print("   ➡️ 최적화된 청킹으로 더 정확한 검색 가능")
        else:
            print("\n💥 처리 중 오류가 발생했습니다.")
            
    except KeyboardInterrupt:
        print("\n\n⏸️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()