#!/usr/bin/env python3
"""
포맷 개선된 답변 테스트
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain

def test_formatted_response():
    """포맷 개선된 답변 테스트"""
    
    print("🔧 RAG 시스템 초기화 중...")
    rag_chain = RAGChain()
    
    # 테스트 질문
    question = "장기카드대출이란?"
    
    print(f"\n🎯 질문: {question}")
    print("="*80)
    
    try:
        response = rag_chain.query(question)
        
        print("🤖 답변:")
        print(response.get('answer', '답변을 생성할 수 없습니다.'))
        
        # 소스 문서 정보
        if response.get('source_documents'):
            print("\n📄 참고 문서:")
            for i, doc in enumerate(response['source_documents'][:3], 1):
                source = doc.get('metadata', {}).get('filename') or doc.get('metadata', {}).get('title', 'Unknown')
                print(f"  {i}. {source}")
        
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    test_formatted_response()