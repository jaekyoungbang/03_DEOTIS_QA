"""
chat.py 유사도 임계값 처리 업데이트 코드
"""

# 1. Import 추가
from services.similarity_response_handler import SimilarityResponseHandler

# 2. 초기화 추가 (클래스 또는 함수 시작 부분)
similarity_handler = SimilarityResponseHandler(threshold=0.8)

# 3. 검색 결과 처리 부분 수정 예시
def process_with_similarity_threshold(search_results, question, chunking_type, chain, process_id):
    """유사도 임계값 기반 처리"""
    
    # 유사도 핸들러로 결과 처리
    result = similarity_handler.process_search_results(search_results, question, chunking_type)
    
    if result["threshold_met"]:
        # 80% 이상 - 정상 답변 생성
        print(f"✅ [vLLM {process_id}] 유사도 {result['max_similarity']:.1%} - 정상 답변 모드")
        
        # 기존 LLM 답변 생성 로직 사용
        context = result["context"]
        
        # LLM에 컨텍스트 전달하여 답변 생성
        # ... 기존 코드 ...
        
        return {
            "answer": generated_answer,  # LLM이 생성한 답변
            "similarity_info": result["similarity_info"],
            "threshold_met": True,
            "max_similarity": result["max_similarity"]
        }
    else:
        # 80% 미만 - 추천 질문 모드
        print(f"⚠️ [vLLM {process_id}] 유사도 {result['max_similarity']:.1%} - 추천 질문 모드")
        
        formatted_response = similarity_handler.format_response_with_threshold(result)
        
        return {
            "answer": formatted_response,
            "similarity_info": result["similarity_info"],
            "threshold_met": False,
            "max_similarity": result["max_similarity"],
            "suggested_questions": result["suggested_questions"]
        }

# 4. 실제 적용 예시 (routes/chat.py의 특정 부분 수정)
"""
예시: routes/chat.py의 1137번 라인 근처에서

# 기존 코드:
print(f"🎯 [vLLM {process_id}] 최고 유사도: {search_results[0][1]:.2%}")

# 수정 후:
max_similarity = search_results[0][1] if search_results else 0.0
print(f"🎯 [vLLM {process_id}] 최고 유사도: {max_similarity:.2%}")

# 유사도 체크 추가
if max_similarity < 0.8:
    print(f"⚠️ [vLLM {process_id}] 유사도 임계값 미달 - 추천 질문 모드 전환")
    # 추천 질문 처리 로직
"""