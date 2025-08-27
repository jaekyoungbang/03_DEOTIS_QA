"""
유사도 기반 응답 처리기
- 80% 이상: 정상 답변
- 80% 미만: 추천 질문 제시
"""

from typing import List, Dict, Tuple, Optional
from langchain.schema import Document

class SimilarityResponseHandler:
    """유사도 기반 응답 처리"""
    
    def __init__(self, threshold: float = 0.75):  # 80%에서 75%로 낮춤
        self.threshold = threshold
        # 개인화 쿼리는 더 낮은 임계값 적용
        self.personalized_threshold = 0.65  # 개인화 쿼리용 임계값
        self.recommended_questions = {
            "card": [
                "BC카드 발급 절차가 궁금합니다",
                "BC카드 회원은행별 안내를 알려주세요",
                "BC카드 신청 자격 조건이 무엇인가요?",
                "BC카드 발급에 필요한 서류는 무엇인가요?",
                "BC카드 연회비는 어떻게 되나요?"
            ],
            "personal": [
                "김명정 고객의 보유 카드 현황을 알려주세요",
                "김명정 고객에게 추천하는 카드는 무엇인가요?",
                "김명정 고객의 카드 이용 내역을 확인하고 싶습니다"
            ],
            "general": [
                "BC카드란 무엇인가요?",
                "BC카드의 주요 혜택을 알려주세요",
                "BC카드 고객센터 연락처가 궁금합니다"
            ]
        }
    
    def process_search_results(
        self, 
        search_results: List[Tuple[Document, float]], 
        question: str,
        chunking_type: str = "basic"
    ) -> Dict:
        """검색 결과를 유사도 기반으로 처리 - 개인화 임계값 적용"""
        
        # 최고 유사도 확인
        max_similarity = search_results[0][1] if search_results else 0.0
        
        # 질문 카테고리 분류
        category = self._categorize_question(question)
        
        # 개인화 쿼리인지 확인하여 임계값 조정
        is_personalized = category == "personal" or any(name in question for name in ["김명정", "이영희", "박철수"])
        effective_threshold = self.personalized_threshold if is_personalized else self.threshold
        
        print(f"🎯 [SimilarityHandler] 카테고리: {category}, 개인화: {is_personalized}")
        print(f"📊 [SimilarityHandler] 최고유사도: {max_similarity:.2%}, 임계값: {effective_threshold:.2%}")
        
        # 유사도 임계값 체크
        if max_similarity >= effective_threshold:
            # 정상 응답 처리
            return {
                "response_type": "normal",
                "should_answer": True,
                "context": self._build_context(search_results, chunking_type),
                "similarity_info": self._format_similarity_info(search_results),
                "max_similarity": max_similarity,
                "threshold_met": True
            }
        else:
            # 낮은 유사도 - 추천 질문 제시
            return {
                "response_type": "low_similarity",
                "should_answer": False,
                "suggested_questions": self._get_suggested_questions(category, question),
                "similarity_info": self._format_similarity_info(search_results),
                "max_similarity": max_similarity,
                "threshold_met": False,
                "message": f"죄송합니다. 질문과 정확히 일치하는 정보를 찾지 못했습니다 (최고 유사도: {max_similarity*100:.1f}%)."
            }
    
    def _categorize_question(self, question: str) -> str:
        """질문 카테고리 분류"""
        if any(name in question for name in ["김명정", "김철수", "박영희"]):
            return "personal"
        elif any(keyword in question for keyword in ["카드", "발급", "신청", "BC카드"]):
            return "card"
        else:
            return "general"
    
    def _build_context(self, search_results: List[Tuple[Document, float]], chunking_type: str) -> str:
        """컨텍스트 구성"""
        context = ""
        for doc, score in search_results[:3]:  # Top 3
            content = doc.page_content
            
            # 청킹 타입별 처리
            if chunking_type == "custom" and "![" in content:
                # 이미지 포함된 컨텍스트
                context += f"[유사도: {score:.1%}] {content}\n\n"
            else:
                # 텍스트만
                context += f"[유사도: {score:.1%}] {content}\n\n"
        
        return context.strip()
    
    def _format_similarity_info(self, search_results: List[Tuple[Document, float]]) -> List[Dict]:
        """유사도 정보 포맷팅"""
        similarity_info = []
        for i, (doc, score) in enumerate(search_results[:3], 1):
            info = {
                "rank": i,
                "score": f"{score:.1%}",
                "score_raw": score,
                "source": doc.metadata.get("source", "unknown"),
                "preview": doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
            }
            similarity_info.append(info)
        
        return similarity_info
    
    def _get_suggested_questions(self, category: str, original_question: str) -> List[str]:
        """추천 질문 생성"""
        base_questions = self.recommended_questions.get(category, self.recommended_questions["general"])
        
        # 원본 질문과 유사한 키워드를 포함한 추천 질문 우선순위 조정
        keywords = self._extract_keywords(original_question)
        scored_questions = []
        
        for question in base_questions:
            score = sum(1 for keyword in keywords if keyword in question)
            scored_questions.append((score, question))
        
        # 점수 높은 순으로 정렬
        scored_questions.sort(key=lambda x: x[0], reverse=True)
        
        return [q[1] for q in scored_questions[:5]]  # Top 5 추천
    
    def _extract_keywords(self, question: str) -> List[str]:
        """질문에서 키워드 추출"""
        # 간단한 키워드 추출 (실제로는 형태소 분석 사용 권장)
        keywords = []
        important_words = ["카드", "발급", "신청", "BC", "안내", "절차", "서류", "자격", "혜택", "연회비"]
        
        for word in important_words:
            if word in question:
                keywords.append(word)
        
        return keywords
    
    def format_response_with_threshold(self, result: Dict) -> str:
        """임계값 기반 응답 포맷팅"""
        if result["threshold_met"]:
            # 정상 응답
            return result.get("answer", "")
        else:
            # 낮은 유사도 응답
            response = f"{result['message']}\n\n"
            response += "아래와 같은 질문들은 어떠신가요?\n\n"
            
            for i, question in enumerate(result['suggested_questions'], 1):
                response += f"{i}. {question}\n"
            
            return response