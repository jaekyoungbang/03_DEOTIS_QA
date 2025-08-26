#!/usr/bin/env python3
"""
Chunking 전략 확인 스크립트
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.chunking_strategies import get_chunking_strategy
from services.document_processor import DocumentProcessor
from langchain.schema import Document

def check_chunking_strategies():
    print("✂️ Chunking 전략 확인")
    print("=" * 60)
    
    # 사용 가능한 청킹 전략 목록
    strategies = [
        'basic',           # 기본 청킹 (1000자/200중첩)
        'semantic',        # 의미 기반 청킹
        'hybrid',          # 하이브리드 청킹
        'custom_delimiter' # 커스텀 구분자 (/$$/)
    ]
    
    print("📋 사용 가능한 청킹 전략:")
    for idx, strategy in enumerate(strategies, 1):
        print(f"   {idx}. {strategy}")
    
    # 테스트 문서 생성
    test_text = """제1장 연회비 안내

BC카드의 연회비는 카드 종류에 따라 다르게 책정됩니다. 
기본 카드의 경우 연회비는 10,000원이며, 프리미엄 카드는 50,000원입니다.

/$$/ 

제2장 연회비 면제 조건

연회비는 다음과 같은 조건을 충족할 경우 면제됩니다:
1. 전월 실적 30만원 이상
2. 연간 이용 금액 300만원 이상
3. 신규 가입 첫 해 면제

/$$/ 

제3장 특별 혜택

프리미엄 카드 회원에게는 다음과 같은 혜택이 제공됩니다:
- 공항 라운지 무료 이용 (연 12회)
- 호텔 투숙 시 20% 할인
- 해외 이용 시 수수료 면제

이상으로 BC카드 연회비 안내를 마칩니다."""
    
    test_doc = Document(page_content=test_text, metadata={"source": "test_document.txt"})
    
    print(f"\n📄 테스트 문서 (길이: {len(test_text)}자)")
    print("-" * 40)
    print(test_text[:200] + "..." if len(test_text) > 200 else test_text)
    print("-" * 40)
    
    # 각 전략별로 청킹 테스트
    for strategy_name in strategies:
        try:
            print(f"\n\n🔹 {strategy_name.upper()} 전략 테스트:")
            print("=" * 50)
            
            strategy = get_chunking_strategy(strategy_name)
            chunks = strategy.split_documents([test_doc])
            
            print(f"📊 청킹 결과:")
            print(f"   - 청크 개수: {len(chunks)}")
            print(f"   - 평균 청크 크기: {sum(len(c.page_content) for c in chunks) / len(chunks) if chunks else 0:.1f}자")
            
            # 각 청크 내용 표시
            for idx, chunk in enumerate(chunks, 1):
                print(f"\n   청크 #{idx}:")
                print(f"   - 크기: {len(chunk.page_content)}자")
                print(f"   - 메타데이터: {chunk.metadata}")
                print(f"   - 내용:")
                print("   " + "-" * 35)
                # 청크 내용을 들여쓰기해서 표시
                content_lines = chunk.page_content.split('\n')
                for line in content_lines[:5]:  # 처음 5줄만 표시
                    print(f"   {line}")
                if len(content_lines) > 5:
                    print(f"   ... ({len(content_lines)-5} more lines)")
                print("   " + "-" * 35)
                
        except Exception as e:
            print(f"❌ {strategy_name} 전략 테스트 실패: {e}")
    
    # 실제 문서에서 청킹 확인
    print("\n\n" + "=" * 60)
    print("📁 실제 문서의 청킹 확인")
    
    doc_processor = DocumentProcessor()
    
    # 샘플 파일 경로 (실제 파일로 변경 필요)
    sample_files = [
        "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3-chunking/sample.txt",
        "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3-chunking/sample.pdf",
    ]
    
    for file_path in sample_files:
        if os.path.exists(file_path):
            print(f"\n📄 파일: {os.path.basename(file_path)}")
            try:
                # 청킹 전략 자동 감지
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()[:500]  # 처음 500자만 확인
                    
                detected_strategy = doc_processor._detect_chunking_strategy(content)
                print(f"   - 감지된 전략: {detected_strategy}")
                
                if '/$$/' in content:
                    print(f"   - 커스텀 구분자(/$$/) 발견!")
                    
            except Exception as e:
                print(f"   - 파일 읽기 실패: {e}")

if __name__ == "__main__":
    check_chunking_strategies()