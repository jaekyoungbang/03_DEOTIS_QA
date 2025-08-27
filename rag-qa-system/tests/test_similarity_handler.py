"""
유사도 핸들러 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.similarity_response_handler import SimilarityResponseHandler
from langchain.schema import Document

def test_similarity_handler():
    """유사도 핸들러 테스트"""
    
    handler = SimilarityResponseHandler(threshold=0.8)
    
    # 테스트 케이스 1: 높은 유사도 (80% 이상)
    print("=== 테스트 1: 높은 유사도 (85%) ===")
    high_similarity_results = [
        (Document(page_content="BC카드 발급 절차는 회원은행 방문이 필요합니다.", metadata={"source": "s3"}), 0.85),
        (Document(page_content="BC카드는 여러 회원은행에서 발급 가능합니다.", metadata={"source": "s3"}), 0.75),
        (Document(page_content="신분증과 소득증빙서류가 필요합니다.", metadata={"source": "s3"}), 0.65)
    ]
    
    result1 = handler.process_search_results(
        high_similarity_results, 
        "BC카드 발급 절차를 알려주세요",
        "basic"
    )
    
    print(f"응답 타입: {result1['response_type']}")
    print(f"정상 답변 여부: {result1['should_answer']}")
    print(f"최고 유사도: {result1['max_similarity']:.1%}")
    print(f"임계값 충족: {result1['threshold_met']}")
    print()
    
    # 테스트 케이스 2: 낮은 유사도 (80% 미만)
    print("=== 테스트 2: 낮은 유사도 (65%) ===")
    low_similarity_results = [
        (Document(page_content="BC카드는 다양한 혜택을 제공합니다.", metadata={"source": "s3"}), 0.65),
        (Document(page_content="회원은행별로 상품이 다릅니다.", metadata={"source": "s3"}), 0.55),
        (Document(page_content="연회비는 카드별로 상이합니다.", metadata={"source": "s3"}), 0.45)
    ]
    
    result2 = handler.process_search_results(
        low_similarity_results,
        "김철수 고객의 카드 추천해주세요",
        "basic"
    )
    
    print(f"응답 타입: {result2['response_type']}")
    print(f"정상 답변 여부: {result2['should_answer']}")
    print(f"최고 유사도: {result2['max_similarity']:.1%}")
    print(f"임계값 충족: {result2['threshold_met']}")
    print(f"메시지: {result2['message']}")
    print("\n추천 질문:")
    for i, q in enumerate(result2['suggested_questions'], 1):
        print(f"  {i}. {q}")
    print()
    
    # 테스트 케이스 3: 포맷된 응답
    print("=== 테스트 3: 포맷된 응답 (낮은 유사도) ===")
    formatted = handler.format_response_with_threshold(result2)
    print(formatted)
    
    # 테스트 케이스 4: 개인화 질문
    print("\n=== 테스트 4: 개인화 질문 (낮은 유사도) ===")
    personal_results = [
        (Document(page_content="김명정 고객님의 정보입니다.", metadata={"source": "s3-common"}), 0.72),
        (Document(page_content="보유 카드: 우리카드, 하나카드", metadata={"source": "s3-common"}), 0.68),
    ]
    
    result4 = handler.process_search_results(
        personal_results,
        "김명정 고객의 미보유 카드를 추천해주세요",
        "custom"
    )
    
    print(f"카테고리: personal")
    print(f"최고 유사도: {result4['max_similarity']:.1%}")
    print("\n추천 질문 (개인화):")
    for i, q in enumerate(result4['suggested_questions'], 1):
        print(f"  {i}. {q}")

if __name__ == "__main__":
    test_similarity_handler()