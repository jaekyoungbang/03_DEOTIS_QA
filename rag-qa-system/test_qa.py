#!/usr/bin/env python3
"""
QA 시스템 테스트 스크립트 - 이중 벡터스토어 포함
"""

import os
import sys

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain

def test_qa_system():
    """QA 시스템 테스트"""
    
    print("🔧 QA 시스템 테스트 시작...")
    
    # RAG 체인 초기화
    rag_chain = RAGChain()
    
    # 테스트 질문들
    test_questions = [
        "BC카드 신용카드 발급 절차를 알려주세요",
        "카드 결제 한도는 어떻게 설정하나요?",
        "BC카드 고객센터 연락처를 알려주세요",
        "해외에서 카드를 사용할 때 주의사항은 무엇인가요?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*80}")
        print(f"질문 {i}: {question}")
        print("="*80)
        
        try:
            # QA 실행 (이중 벡터스토어 검색 모드 사용)
            result = rag_chain.query(question, search_mode="dual")
            
            print(f"📝 답변:")
            print(result['answer'])
            
            # 메타데이터 출력 (있는 경우)
            if 'metadata' in result:
                metadata = result['metadata']
                print(f"\n📊 메타데이터:")
                print(f"- 캐시 히트: {'예' if metadata.get('cache_hit', False) else '아니오'}")
                print(f"- 응답 시간: {metadata.get('total_time', 0):.2f}초")
                if 'sources' in metadata:
                    print(f"- 참조 문서 수: {len(metadata['sources'])}개")
                    
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_qa_system()