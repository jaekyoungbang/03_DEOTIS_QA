#!/usr/bin/env python3
"""
포맷이 개선된 장기카드대출 정보를 추가
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.document_processor import DocumentProcessor
from models.embeddings import EmbeddingManager
from models.vectorstore import VectorStoreManager

def add_formatted_content():
    """포맷이 개선된 장기카드대출 정보 추가"""
    
    # 초기화
    doc_processor = DocumentProcessor()
    embedding_manager = EmbeddingManager()
    vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
    
    # 표 형식의 장기카드대출 정보
    formatted_content = """
## 장기카드대출(카드론) 상품 안내

BC바로카드 우량 회원을 위한 **서류 없이 간편하게 신청 가능한 대출 상품**입니다.

### 📋 상품 정보

| 구분 | 내용 |
|------|------|
| **이용대상** | BC바로카드 우량 고객 |
| **이용한도** | 최대 5,000만원 |
| **약정기간** | 최대 60개월 이내 선택 |
| **상환방법** | 원리금 균등분할상환, 원금 균등분할상환 |
| **수수료율** | 개인 신용도/기여도에 따라 차등 적용 |
| **취급수수료** | 없음 |
| **연체이자율** | 약정 이자율 + 최고 3% |
| **필요서류** | 없음 |

### 📱 신청 방법

1. **페이북APP** 실행
2. **'전체'** 메뉴 선택
3. **'대출'** 카테고리 이동
4. **'장기카드대출(카드론)'** 선택
5. **신청 절차** 진행

### ✨ 상품 특징

- ✅ **서류 없이** 간편 신청
- ✅ **중도상환수수료** 없음  
- ✅ **취급수수료** 없음
- ✅ **최대 5천만원** 한도
- ✅ **최대 60개월** 약정 가능

### ⚠️ 주의사항

- 상환능력에 비해 대출금이 과도할 경우 개인신용평점이 하락할 수 있습니다
- 일정기간 원리금 연체 시 모든 원리금을 변제할 의무가 발생할 수 있습니다
- 본인의 수수료율은 페이북에서 확인 가능합니다
"""
    
    print("📄 포맷이 개선된 장기카드대출 정보를 벡터DB에 추가 중...")
    
    # 메타데이터
    metadata = {
        "source": "formatted_guide",
        "title": "장기카드대출(카드론) 완전 가이드",
        "category": "대출상품",
        "format": "structured",
        "keywords": "장기카드대출,카드론,BC바로카드,페이북APP,5000만원,60개월,신청방법"
    }
    
    # 텍스트를 청크로 분할하여 추가
    chunks = doc_processor.process_text(formatted_content, metadata)
    vectorstore_manager.add_documents(chunks)
    
    print(f"✅ 성공: {len(chunks)}개 청크 추가됨")
    print(f"📊 전체 벡터DB 문서 수: {vectorstore_manager.get_document_count()}개")
    
    return len(chunks)

if __name__ == "__main__":
    try:
        add_formatted_content()
        print("\n🎉 포맷 개선된 장기카드대출 정보 추가 완료!")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")