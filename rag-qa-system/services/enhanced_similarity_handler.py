"""
향상된 유사도 기반 응답 처리기
- Redis 캐시 통합
- MySQL 인기질문 관리
- 50% 미만 시 인기질문 버튼 표시
"""

from typing import List, Dict, Tuple, Optional, Any
from langchain.schema import Document
from .redis_cache_manager import RedisCacheManager  
from .popular_question_manager import PopularQuestionManager
from .application_initializer import get_application_initializer
from .enhanced_logger import get_enhanced_logger
import logging
import time

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger()

class EnhancedSimilarityHandler:
    """향상된 유사도 기반 응답 처리"""
    
    def __init__(self, threshold: float = 0.75):
        """초기화"""
        self.threshold = threshold
        self.personalized_threshold = 0.65  # 개인화 쿼리용 임계값
        self.low_similarity_threshold = 0.50  # 인기질문 표시 기준
        
        # 캐시와 인기질문 매니저 초기화
        initializer = get_application_initializer()
        self.redis_manager, self.popular_manager = initializer.get_managers()
        
        # 기본 추천 질문 (Redis/MySQL 연결 실패시 사용)
        self.fallback_questions = {
            "card": [
                "BC카드 발급 절차가 궁금합니다",
                "BC카드 회원은행별 안내를 알려주세요", 
                "BC카드 신청 자격 조건이 무엇인가요?"
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
    
    def process_question(
        self, 
        question: str, 
        vectorstore_search_func,
        chunking_type: str = "basic"
    ) -> Dict:
        """질문 전체 처리 (캐시 확인 → 검색 → 결과 처리)"""
        
        start_time = time.time()
        enhanced_logger.question_flow(question, "START", {})
        
        # 1. Redis 캐시 확인
        enhanced_logger.question_flow(question, "CACHE_CHECK", {})
        cached_result = self._check_cache(question)
        
        if cached_result:
            duration = time.time() - start_time
            enhanced_logger.question_flow(question, "CACHE_CHECK", {"hit": True})
            enhanced_logger.search_operation(
                question, cached_result['max_similarity'], 
                "Redis Cache", cached=True, duration=duration
            )
            enhanced_logger.question_flow(question, "END", {"cached": True})
            return cached_result
        
        enhanced_logger.question_flow(question, "CACHE_CHECK", {"hit": False})
        
        # 2. 벡터 검색 수행
        search_start = time.time()
        search_results = vectorstore_search_func(question)
        search_duration = time.time() - search_start
        
        max_similarity = search_results[0][1] if search_results else 0.0
        enhanced_logger.question_flow(question, "VECTOR_SEARCH", {"similarity": max_similarity})
        enhanced_logger.search_operation(
            question, max_similarity, chunking_type, 
            cached=False, duration=search_duration
        )
        
        # 3. 검색 결과 처리
        processed_result = self.process_search_results(
            search_results, question, chunking_type
        )
        
        enhanced_logger.question_flow(question, "RESPONSE_TYPE", {
            "type": processed_result["response_type"],
            "threshold_met": processed_result["threshold_met"],
            "show_popular_buttons": processed_result.get("show_popular_buttons", False)
        })
        
        # 4. 캐싱 및 인기질문 처리
        caching_info = self._handle_caching_and_popularity(question, processed_result)
        
        total_duration = time.time() - start_time
        enhanced_logger.question_flow(question, "END", {
            "cached": caching_info.get("cached", False),
            "popular_saved": caching_info.get("popular_saved", False)
        })
        
        enhanced_logger.performance_metrics("QUESTION_PROCESSING", {
            "total_time": total_duration,
            "search_time": search_duration,
            "cache_check_time": search_start - start_time,
            "processing_time": total_duration - search_duration - (search_start - start_time),
            "similarity_score": max_similarity
        })
        
        return processed_result
    
    def _check_cache(self, question: str) -> Optional[Dict]:
        """Redis 캐시 확인"""
        if not self.redis_manager or not self.redis_manager.is_connected():
            return None
        
        try:
            cached_data = self.redis_manager.get_cached_result(question)
            if cached_data:
                # 캐시된 데이터를 응답 형식으로 변환
                return {
                    "response_type": "cached",
                    "should_answer": True,
                    "context": cached_data['result'].get('context', ''),
                    "similarity_info": cached_data['result'].get('similarity_info', []),
                    "max_similarity": cached_data['similarity_score'],
                    "threshold_met": True,
                    "cached": True,
                    "cache_timestamp": cached_data['cached_at']
                }
        except Exception as e:
            logger.error(f"캐시 확인 오류: {e}")
        
        return None
    
    def process_search_results(
        self, 
        search_results: List[Tuple[Document, float]], 
        question: str,
        chunking_type: str = "basic"
    ) -> Dict:
        """검색 결과를 유사도 기반으로 처리"""
        
        # 최고 유사도 확인
        max_similarity = search_results[0][1] if search_results else 0.0
        
        # 질문 카테고리 분류
        category = self._categorize_question(question)
        
        # 개인화 쿼리인지 확인하여 임계값 조정
        is_personalized = category == "personal" or any(name in question for name in ["김명정", "이영희", "박철수"])
        effective_threshold = self.personalized_threshold if is_personalized else self.threshold
        
        logger.info(f"🎯 [EnhancedHandler] 카테고리: {category}, 개인화: {is_personalized}")
        logger.info(f"📊 [EnhancedHandler] 최고유사도: {max_similarity:.2%}, 임계값: {effective_threshold:.2%}")
        
        # 유사도 임계값 체크
        if max_similarity >= effective_threshold:
            # 정상 응답 처리 (70% 이상이면 캐시 대상)
            result = {
                "response_type": "normal",
                "should_answer": True,
                "context": self._build_context(search_results, chunking_type),
                "similarity_info": self._format_similarity_info(search_results),
                "max_similarity": max_similarity,
                "threshold_met": True,
                "cached": False
            }
            return result
            
        elif max_similarity >= self.low_similarity_threshold:
            # 중간 유사도 - 일반 추천 질문
            return {
                "response_type": "medium_similarity",
                "should_answer": False,
                "suggested_questions": self._get_suggested_questions(category, question),
                "similarity_info": self._format_similarity_info(search_results),
                "max_similarity": max_similarity,
                "threshold_met": False,
                "message": f"관련 정보를 찾았지만 정확하지 않을 수 있습니다 (유사도: {max_similarity*100:.1f}%)."
            }
        else:
            # 낮은 유사도 (50% 미만) - 인기질문 버튼 표시
            popular_questions = self._get_popular_questions()
            return {
                "response_type": "low_similarity", 
                "should_answer": False,
                "suggested_questions": self._get_suggested_questions(category, question),
                "popular_questions": popular_questions,  # 버튼용 인기질문
                "similarity_info": self._format_similarity_info(search_results),
                "max_similarity": max_similarity,
                "threshold_met": False,
                "message": f"질문과 관련된 정보를 찾지 못했습니다 (유사도: {max_similarity*100:.1f}%).",
                "show_popular_buttons": True
            }
    
    def _handle_caching_and_popularity(self, question: str, result: Dict) -> Dict:
        """캐싱 및 인기질문 처리"""
        max_similarity = result.get('max_similarity', 0.0)
        info = {"cached": False, "popular_saved": False}
        
        # 1. 70% 이상이면 Redis 캐싱
        if max_similarity >= 0.70 and self.redis_manager:
            try:
                cache_success = self.redis_manager.cache_result(
                    question, result, max_similarity
                )
                info["cached"] = cache_success
            except Exception as e:
                enhanced_logger.redis_operation("CACHE_ERROR", question, error=str(e))
        
        # 2. 검색 횟수 확인 후 5회 이상이면 MySQL 저장
        if self.redis_manager and self.popular_manager:
            try:
                search_count = self.redis_manager.get_search_count(question)
                if search_count >= 5:
                    category = self._categorize_question(question)
                    popular_success = self.popular_manager.add_popular_question(
                        question, search_count, max_similarity, category
                    )
                    info["popular_saved"] = popular_success
            except Exception as e:
                enhanced_logger.mysql_operation("POPULAR_ERROR", question, error=str(e))
        
        return info
    
    def _get_popular_questions(self) -> List[str]:
        """50% 미만 시 표시할 인기질문 3개 (버튼용)"""
        if self.popular_manager and self.popular_manager.is_connected():
            try:
                return self.popular_manager.get_top_3_popular_questions()
            except Exception as e:
                logger.error(f"인기질문 조회 오류: {e}")
        
        # 폴백: 기본 추천 질문
        return self.fallback_questions["card"][:3]
    
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
                context += f"[유사도: {score:.1%}] {content}\\n\\n"
            else:
                # 텍스트만
                context += f"[유사도: {score:.1%}] {content}\\n\\n"
        
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
        base_questions = self.fallback_questions.get(category, self.fallback_questions["general"])
        
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
        elif result.get("show_popular_buttons", False):
            # 50% 미만 - 인기질문 버튼 표시
            response = f"{result['message']}\\n\\n"
            response += "다음 중에서 궁금한 내용을 선택해주세요:\\n\\n"
            
            for i, question in enumerate(result.get('popular_questions', []), 1):
                response += f"🔘 {question}\\n"
            
            return response
        else:
            # 중간 유사도 - 일반 추천질문
            response = f"{result['message']}\\n\\n"
            response += "아래와 같은 질문들은 어떠신가요?\\n\\n"
            
            for i, question in enumerate(result['suggested_questions'], 1):
                response += f"{i}. {question}\\n"
            
            return response