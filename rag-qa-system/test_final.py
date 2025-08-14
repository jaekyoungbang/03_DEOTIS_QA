#!/usr/bin/env python3
"""
최종 테스트 - 장기카드대출 신청경로 확인
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain

def test_longterm_loan_questions():
    """장기카드대출 관련 질문 테스트"""
    
    # RAG 체인 초기화
    print("🔧 RAG 시스템 초기화 중...")
    rag_chain = RAGChain()
    
    # 테스트 질문들
    questions = [
        "장기 카드 대출 신청경로 알려줘",
        "장기카드대출 이용방법은?",
        "카드론 신청하는 방법",
        "페이북APP에서 장기카드대출 어떻게 신청해?",
        "BC바로카드 장기대출 한도는 얼마야?"
    ]
    
    print("\n" + "="*80)
    print("🎯 장기카드대출 관련 질문 테스트")
    print("="*80)
    
    for i, question in enumerate(questions, 1):
        print(f"\n[질문 {i}] {question}")
        print("-"*70)
        
        try:
            # RAG 질문 수행
            response = rag_chain.query(question)
            
            print("🤖 답변:")
            print(response.get('answer', '답변을 생성할 수 없습니다.'))
            
            # 소스 문서 정보
            if response.get('source_documents'):
                print("\n📄 참고 문서:")
                for j, doc in enumerate(response['source_documents'][:3], 1):
                    source = doc.get('metadata', {}).get('filename') or doc.get('metadata', {}).get('title', 'Unknown')
                    print(f"  {j}. {source}")
            
        except Exception as e:
            print(f"❌ 오류: {e}")
        
        print("\n" + "="*70)

if __name__ == "__main__":
    test_longterm_loan_questions()