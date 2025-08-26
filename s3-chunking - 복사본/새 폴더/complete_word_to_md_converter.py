#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
완전한 Word to MD 변환기 - 58페이지 전체 내용 포함
"""

import sys
import json
from pathlib import Path

# 상위 디렉토리 패스 추가
current_dir = Path(__file__).parent
parent_dir = current_dir.parent / "rag-qa-system"
sys.path.append(str(parent_dir))

def load_existing_chunks(json_file_path):
    """기존 JSON 청크 파일에서 전체 내용 추출"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📄 로드된 파일: {data['source_file']}")
        print(f"   총 청크 수: {data['chunk_count']}")
        
        # 모든 청크 내용을 순서대로 합치기
        full_content = ""
        for chunk in data['chunks']:
            full_content += chunk['content'] + "\n\n"
        
        print(f"   전체 내용 길이: {len(full_content):,}자")
        return full_content, data['source_file']
        
    except Exception as e:
        print(f"❌ JSON 파일 로드 실패: {e}")
        return None, None

def convert_to_markdown(content, source_file):
    """텍스트 내용을 마크다운으로 변환"""
    
    # 파일별 제목 설정
    if "카드이용안내" in source_file:
        title = "# BC카드 카드이용안내 - 완전판"
        subtitle = "## 📋 전체 58페이지 완전 수록"
    else:
        title = "# BC카드 신용카드 업무처리 안내 - 완전판" 
        subtitle = "## 📋 업무처리 절차 및 가이드"
    
    md_content = f"""{title}

{subtitle}

---

"""
    
    # 내용을 섹션별로 분할하여 마크다운 구조 생성
    lines = content.split('\n')
    current_section = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            md_content += "\n"
            continue
            
        # 주요 섹션 헤딩 감지 및 변환
        if any(marker in line for marker in ['■', '▶', '※', '★', '●', '◆']):
            md_content += f"\n### {line}\n\n"
        # 번호 리스트 감지
        elif line.startswith(('1)', '2)', '3)', '4)', '5)', '6)', '7)', '8)', '9)')):
            md_content += f"**{line}**\n\n"
        # 영문+숫자 패턴 (예: Q:, A:, STEP)
        elif line.startswith(('Q ', 'Q:', 'A ', 'A:', 'STEP')):
            md_content += f"\n#### {line}\n\n"
        # 대괄호 제목 패턴
        elif line.startswith('[') and line.endswith(']'):
            md_content += f"\n## {line}\n\n"
        # 테이블 행 감지 (단순한 | 구분)
        elif '|' in line and line.count('|') >= 2:
            # 테이블 행으로 처리
            if not md_content.endswith('|\n'):
                md_content += "\n"
            md_content += f"{line}\n"
        else:
            # 일반 텍스트
            md_content += f"{line}\n\n"
    
    return md_content

def create_optimized_sections(md_content):
    """마크다운 내용을 최적화된 섹션으로 재구성"""
    
    sections = []
    current_section = {"title": "", "content": [], "type": "text"}
    
    lines = md_content.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # 주요 섹션 구분
        if line.startswith('###') or line.startswith('##'):
            # 이전 섹션 저장
            if current_section["content"]:
                sections.append(current_section)
            
            # 새 섹션 시작
            current_section = {
                "title": line.replace('#', '').strip(),
                "content": [],
                "type": "section"
            }
        
        # 테이블 감지
        elif '|' in line and line.count('|') >= 2:
            # 테이블 섹션으로 전환
            if current_section["type"] != "table":
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {
                    "title": current_section.get("title", "테이블"),
                    "content": [],
                    "type": "table"
                }
            current_section["content"].append(line)
        
        else:
            # 테이블에서 일반 텍스트로 전환
            if current_section["type"] == "table" and line and not line.startswith('|'):
                sections.append(current_section)
                current_section = {
                    "title": "",
                    "content": [line],
                    "type": "text"
                }
            else:
                current_section["content"].append(line)
    
    # 마지막 섹션 추가
    if current_section["content"]:
        sections.append(current_section)
    
    return sections

def main():
    """메인 실행 함수"""
    print("🔄 완전한 Word to MD 변환 시작")
    print("=" * 60)
    
    # JSON 파일 경로
    current_dir = Path(__file__).parent
    rag_dir = current_dir.parent / "rag-qa-system"
    json_files = [
        rag_dir / "data/chunked_documents/BC카드(카드이용안내)_chunks.json",
        rag_dir / "data/chunked_documents/BC카드(신용카드 업무처리 안내)_chunks.json"
    ]
    
    for json_file in json_files:
        if not json_file.exists():
            print(f"⚠️ JSON 파일을 찾을 수 없습니다: {json_file}")
            continue
            
        try:
            print(f"\n📖 처리 중: {json_file.name}")
            
            # JSON에서 전체 내용 추출
            full_content, source_file = load_existing_chunks(json_file)
            if not full_content:
                continue
            
            # 마크다운으로 변환
            print("🔄 마크다운 변환 중...")
            md_content = convert_to_markdown(full_content, source_file)
            
            # 섹션 최적화
            print("⚡ 섹션 최적화 중...")
            sections = create_optimized_sections(md_content)
            print(f"   생성된 섹션 수: {len(sections)}개")
            
            # 최적화된 MD 내용 구성
            optimized_md = md_content + "\n\n---\n\n## 📊 문서 정보\n\n"
            optimized_md += f"- **원본 파일**: {source_file}\n"
            optimized_md += f"- **전체 길이**: {len(full_content):,}자\n"
            optimized_md += f"- **생성된 섹션**: {len(sections)}개\n"
            optimized_md += f"- **변환 일시**: {json.loads(open(json_file).read())['processing_time']}\n"
            
            # MD 파일 저장
            if "카드이용안내" in source_file:
                output_file = current_dir / "BC카드_카드이용안내_완전판.md"
            else:
                output_file = current_dir / "BC카드_신용카드업무처리안내_완전판.md"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(optimized_md)
            
            print(f"✅ 완전판 MD 파일 생성: {output_file}")
            print(f"   파일 크기: {len(optimized_md):,}자")
            
        except Exception as e:
            print(f"❌ 변환 실패: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n🎉 완전한 Word to MD 변환 완료!")

if __name__ == "__main__":
    main()