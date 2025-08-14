#!/usr/bin/env python3
"""
장기카드대출 상세 정보를 벡터DB에 추가
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.document_processor import DocumentProcessor
from models.embeddings import EmbeddingManager
from models.vectorstore import VectorStoreManager

def add_longterm_loan_content():
    """장기카드대출 상세 정보 추가"""
    
    # 초기화
    doc_processor = DocumentProcessor()
    embedding_manager = EmbeddingManager()
    vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
    
    # 장기카드대출 상세 정보
    longterm_content = """1-5) 장기카드대출(카드론)이란?

BC바로카드 우량 회원이 서류없이 언제든 간편하게 신청할 수 있고 중도상환수수료 및 취급수수료가 없는 대출성 상품입니다.

이용대상: BC바로카드 우량 고객

이용한도: 최대 5000만원

약정기간: 대출 약정시에 최대 60개월 이내에서 회원이 선택

상환방법: 원리금 균등분할상환, 원금 균등분할상환

수수료율: 회원 본인의 신용도 및 기여도에 따라 차등 적용되며 본인의 수수료율은 페이북에서 조회 시 확인가능함

취급수수료: 없음

연체이자율: 약정 이자율+최고3%(법정 최고금리 이내)

필요서류: 없음

신청경로: 페이북APP > 전체 > 대출 > 장기카드대출(카드론)

장기카드대출 신청방법:
1. 페이북APP 실행
2. '전체' 메뉴 선택  
3. '대출' 카테고리 이동
4. '장기카드대출(카드론)' 선택
5. 신청 절차 진행

장기카드대출 특징:
- BC바로카드 우량회원 대상
- 서류 없이 간편 신청 가능
- 중도상환수수료 없음
- 취급수수료 없음
- 최대 5천만원까지 이용 가능
- 최대 60개월까지 약정 기간 선택 가능
- 개인 신용도에 따른 차등 수수료율 적용

※ 상환능력에 비해 대출금이 과도할 경우 귀하의 개인신용평점이 하락할 수 있습니다.
※ 일정기간 원리금을 연체할 경우 모든 원리금을 변제할 의무가 발생할 수 있습니다."""
    
    print("📄 장기카드대출 상세 정보를 벡터DB에 추가 중...")
    
    # 메타데이터
    metadata = {
        "source": "manual_input",
        "title": "장기카드대출(카드론) 상세 안내",
        "category": "대출상품",
        "keywords": "장기카드대출,카드론,BC바로카드,페이북APP,5000만원,60개월"
    }
    
    # 텍스트를 청크로 분할하여 추가
    chunks = doc_processor.process_text(longterm_content, metadata)
    vectorstore_manager.add_documents(chunks)
    
    print(f"✅ 성공: {len(chunks)}개 청크 추가됨")
    print(f"📊 전체 벡터DB 문서 수: {vectorstore_manager.get_document_count()}개")
    
    return len(chunks)

if __name__ == "__main__":
    try:
        add_longterm_loan_content()
        print("\n🎉 장기카드대출 정보 추가 완료!")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")