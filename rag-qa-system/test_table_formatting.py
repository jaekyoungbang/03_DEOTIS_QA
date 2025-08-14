#!/usr/bin/env python3
"""
표 포맷팅 테스트
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain

def test_table_formatting():
    """표 형식 답변 테스트"""
    
    print("🔧 RAG 시스템 초기화 중...")
    rag_chain = RAGChain()
    
    # 테스트 질문들
    questions = [
        "장기카드대출이란?",
        "장기카드대출 상품 정보를 표로 정리해줘",
        "BC바로카드 장기대출의 특징을 정리해서 보여줘"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'='*80}")
        print(f"🎯 질문 {i}: {question}")
        print('='*80)
        
        try:
            response = rag_chain.query(question)
            
            print("🤖 답변:")
            print(response.get('answer', '답변을 생성할 수 없습니다.'))
            
            # 소스 문서 정보
            if response.get('source_documents'):
                print(f"\n📄 참고 문서 ({len(response['source_documents'])}개):")
                for j, doc in enumerate(response['source_documents'][:3], 1):
                    source = doc.get('metadata', {}).get('filename') or doc.get('metadata', {}).get('title', 'Unknown')
                    print(f"  {j}. {source}")
            
        except Exception as e:
            print(f"❌ 오류: {e}")
        
        print("\n" + "="*80)

if __name__ == "__main__":
    test_table_formatting()