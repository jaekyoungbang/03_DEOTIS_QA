#!/usr/bin/env python3
"""
다중 모델 앙상블 시스템 - 여러 LLM을 조합하여 최고 성능 달성
"""

import asyncio
import time
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain.schema import Document
import numpy as np
import json
import hashlib

@dataclass
class ModelResponse:
    """모델 응답 결과"""
    model_name: str
    response_text: str
    confidence_score: float
    processing_time: float
    token_count: int
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class EnsembleResult:
    """앙상블 최종 결과"""
    final_answer: str
    confidence_score: float
    contributing_models: List[str]
    model_responses: List[ModelResponse]
    ensemble_method: str
    processing_time: float
    quality_metrics: Dict[str, float]

class ModelQualityEvaluator:
    """모델 품질 평가기"""
    
    def __init__(self):
        self.quality_metrics = {
            "completeness": 0.3,      # 답변 완성도
            "relevance": 0.25,        # 관련성
            "coherence": 0.2,         # 일관성
            "specificity": 0.15,      # 구체성
            "accuracy": 0.1           # 정확성 (팩트 체크)
        }
        
        # 한국어 특화 품질 지표
        self.korean_quality_patterns = {
            "formal_language": r"습니다|입니다|드립니다|하겠습니다",
            "question_markers": r"\?|\？|물어|문의|알려주|안내",
            "professional_terms": r"발급|신청|절차|안내|서비스|고객|회원",
            "structured_content": r"\d+\.|•|※|◈|★|▶|①|②|③",
            "complete_sentences": r"[.!?][\s]*[가-힣A-Z]"
        }
    
    def evaluate_response_quality(self, response: str, query: str, context: str) -> Dict[str, float]:
        """응답 품질을 다각도로 평가"""
        metrics = {}
        
        # 1. 완성도 평가 (길이, 구조, 마무리)
        completeness = self._evaluate_completeness(response)
        metrics["completeness"] = completeness
        
        # 2. 관련성 평가 (쿼리-답변 매칭)
        relevance = self._evaluate_relevance(response, query)
        metrics["relevance"] = relevance
        
        # 3. 일관성 평가 (내용 일치, 모순 없음)
        coherence = self._evaluate_coherence(response, context)
        metrics["coherence"] = coherence
        
        # 4. 구체성 평가 (구체적 정보, 실용성)
        specificity = self._evaluate_specificity(response)
        metrics["specificity"] = specificity
        
        # 5. 정확성 평가 (팩트 체크, 논리성)
        accuracy = self._evaluate_accuracy(response, context)
        metrics["accuracy"] = accuracy
        
        # 종합 점수 계산
        total_score = sum(
            metrics[metric] * weight 
            for metric, weight in self.quality_metrics.items()
        )
        metrics["total_quality"] = total_score
        
        return metrics
    
    def _evaluate_completeness(self, response: str) -> float:
        """완성도 평가"""
        import re
        
        score = 0.0
        
        # 길이 적절성 (너무 짧거나 길지 않음)
        length = len(response)
        if 100 <= length <= 2000:
            score += 0.3
        elif 50 <= length < 100 or 2000 < length <= 3000:
            score += 0.2
        elif length >= 50:
            score += 0.1
        
        # 문장 완성도
        complete_sentences = len(re.findall(self.korean_quality_patterns["complete_sentences"], response))
        if complete_sentences >= 3:
            score += 0.25
        elif complete_sentences >= 1:
            score += 0.15
        
        # 구조화된 내용
        if re.search(self.korean_quality_patterns["structured_content"], response):
            score += 0.2
        
        # 정중한 마무리
        if re.search(self.korean_quality_patterns["formal_language"], response):
            score += 0.15
        
        # 답변 마무리 적절성
        if response.rstrip().endswith(('.', '습니다', '입니다', '드립니다', '하겠습니다')):
            score += 0.1
        
        return min(score, 1.0)
    
    def _evaluate_relevance(self, response: str, query: str) -> float:
        """관련성 평가"""
        import re
        
        query_words = set(re.findall(r'[가-힣]{2,}', query.lower()))
        response_words = set(re.findall(r'[가-힣]{2,}', response.lower()))
        
        if not query_words:
            return 0.5
        
        # 키워드 매칭률
        matched_keywords = query_words.intersection(response_words)
        keyword_match_rate = len(matched_keywords) / len(query_words)
        
        # 질문 형태 응답 적절성
        question_in_query = bool(re.search(self.korean_quality_patterns["question_markers"], query))
        professional_in_response = bool(re.search(self.korean_quality_patterns["professional_terms"], response))
        
        relevance_score = keyword_match_rate * 0.7
        if question_in_query and professional_in_response:
            relevance_score += 0.3
        elif professional_in_response:
            relevance_score += 0.15
        
        return min(relevance_score, 1.0)
    
    def _evaluate_coherence(self, response: str, context: str) -> float:
        """일관성 평가"""
        import re
        
        # 문맥 일치성
        context_words = set(re.findall(r'[가-힣]{2,}', context.lower()))
        response_words = set(re.findall(r'[가-힣]{2,}', response.lower()))
        
        context_consistency = 0.5
        if context_words:
            common_words = context_words.intersection(response_words)
            context_consistency = min(len(common_words) / len(context_words) * 2, 1.0)
        
        # 논리적 구조
        logical_structure = 0.0
        if "1." in response or "첫째" in response or "먼저" in response:
            logical_structure += 0.3
        if "2." in response or "둘째" in response or "다음" in response:
            logical_structure += 0.2
        if "따라서" in response or "결론적으로" in response or "마지막으로" in response:
            logical_structure += 0.2
        
        # 모순 감지 (간단한 패턴)
        contradiction_penalty = 0.0
        if "불가능합니다" in response and "가능합니다" in response:
            contradiction_penalty = 0.2
        if "없습니다" in response and "있습니다" in response:
            contradiction_penalty = 0.1
        
        coherence_score = (context_consistency * 0.6 + logical_structure * 0.4) - contradiction_penalty
        return max(coherence_score, 0.0)
    
    def _evaluate_specificity(self, response: str) -> float:
        """구체성 평가"""
        import re
        
        score = 0.0
        
        # 구체적 숫자, 날짜, 시간
        specific_info = len(re.findall(r'\d+', response))
        if specific_info >= 5:
            score += 0.3
        elif specific_info >= 2:
            score += 0.2
        elif specific_info >= 1:
            score += 0.1
        
        # 전문 용어 사용
        professional_terms = len(re.findall(self.korean_quality_patterns["professional_terms"], response))
        if professional_terms >= 3:
            score += 0.25
        elif professional_terms >= 1:
            score += 0.15
        
        # 구체적 절차, 방법 제시
        procedure_indicators = ["방법", "절차", "단계", "과정", "준비", "필요", "구비"]
        procedure_count = sum(1 for indicator in procedure_indicators if indicator in response)
        if procedure_count >= 3:
            score += 0.25
        elif procedure_count >= 1:
            score += 0.15
        
        # 연락처, 주소 등 실용 정보
        practical_info = bool(re.search(r'\d{4}-\d{4}|\d{3}-\d{4}|www\.|http', response))
        if practical_info:
            score += 0.2
        
        return min(score, 1.0)
    
    def _evaluate_accuracy(self, response: str, context: str) -> float:
        """정확성 평가"""
        # 기본 정확성 점수 (맥락과의 일치도 기반)
        accuracy_score = 0.7  # 기본점수
        
        # 맥락에서 확인 가능한 정보와 일치하는지 확인
        if "1588-4000" in context and "1588-4000" in response:
            accuracy_score += 0.1
        if "BC카드" in context and "BC카드" in response:
            accuracy_score += 0.1
        
        # 논리적 오류 감지
        if "동시에 불가능" in response or "모순" in response:
            accuracy_score -= 0.2
        
        return min(max(accuracy_score, 0.0), 1.0)

class ModelManager:
    """모델 관리자"""
    
    def __init__(self):
        self.models = {
            "gpt-4o-mini": {
                "type": "openai",
                "weight": 1.0,
                "strengths": ["general", "korean", "logical"],
                "max_tokens": 4000,
                "temperature": 0.1
            },
            "gpt-4o": {
                "type": "openai", 
                "weight": 1.2,
                "strengths": ["complex", "detailed", "professional"],
                "max_tokens": 4000,
                "temperature": 0.1
            },
            "local_kanana8b": {
                "type": "local",
                "weight": 0.8,
                "strengths": ["fast", "local", "korean"],
                "max_tokens": 2000,
                "temperature": 0.2
            }
        }
        
        self.quality_evaluator = ModelQualityEvaluator()
        self.logger = logging.getLogger(__name__)
    
    async def get_model_response(self, model_name: str, prompt: str, context: str) -> ModelResponse:
        """단일 모델에서 응답 생성"""
        start_time = time.time()
        
        try:
            model_config = self.models[model_name]
            
            if model_config["type"] == "openai":
                response_text = await self._call_openai_model(model_name, prompt, model_config)
            elif model_config["type"] == "local":
                response_text = await self._call_local_model(model_name, prompt, model_config)
            else:
                raise ValueError(f"Unknown model type: {model_config['type']}")
            
            processing_time = time.time() - start_time
            
            # 응답 품질 평가
            quality_metrics = self.quality_evaluator.evaluate_response_quality(
                response_text, prompt, context
            )
            
            return ModelResponse(
                model_name=model_name,
                response_text=response_text,
                confidence_score=quality_metrics["total_quality"],
                processing_time=processing_time,
                token_count=len(response_text.split()),
                metadata={"quality_metrics": quality_metrics}
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Model {model_name} error: {e}")
            
            return ModelResponse(
                model_name=model_name,
                response_text="",
                confidence_score=0.0,
                processing_time=processing_time,
                token_count=0,
                error_message=str(e)
            )
    
    async def _call_openai_model(self, model_name: str, prompt: str, config: Dict) -> str:
        """OpenAI 모델 호출"""
        import os
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=config["max_tokens"],
            temperature=config["temperature"]
        )
        
        return response.choices[0].message.content
    
    async def _call_local_model(self, model_name: str, prompt: str, config: Dict) -> str:
        """로컬 모델 호출"""
        from models.llm import LLMManager
        
        llm_manager = LLMManager()
        llm = llm_manager.get_vllm_llm()
        
        # 비동기 처리를 위해 ThreadPoolExecutor 사용
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, llm.invoke, prompt)
        
        if hasattr(response, 'content'):
            return response.content
        return str(response)

class EnsembleStrategy:
    """앙상블 전략 클래스"""
    
    @staticmethod
    def weighted_voting(responses: List[ModelResponse], weights: Dict[str, float]) -> EnsembleResult:
        """가중 투표 앙상블"""
        if not responses:
            return EnsembleResult(
                final_answer="응답을 생성할 수 없습니다.",
                confidence_score=0.0,
                contributing_models=[],
                model_responses=[],
                ensemble_method="weighted_voting",
                processing_time=0.0,
                quality_metrics={}
            )
        
        # 오류 응답 필터링
        valid_responses = [r for r in responses if not r.error_message and r.response_text]
        
        if not valid_responses:
            return EnsembleResult(
                final_answer="모든 모델에서 오류가 발생했습니다.",
                confidence_score=0.0,
                contributing_models=[r.model_name for r in responses],
                model_responses=responses,
                ensemble_method="weighted_voting",
                processing_time=sum(r.processing_time for r in responses),
                quality_metrics={"error_count": len(responses)}
            )
        
        # 가중 점수 계산
        weighted_scores = []
        for response in valid_responses:
            weight = weights.get(response.model_name, 1.0)
            weighted_score = response.confidence_score * weight
            weighted_scores.append((response, weighted_score))
        
        # 최고 점수 응답 선택
        weighted_scores.sort(key=lambda x: x[1], reverse=True)
        best_response = weighted_scores[0][0]
        
        # 품질 메트릭 계산
        quality_metrics = {
            "max_confidence": max(r.confidence_score for r in valid_responses),
            "avg_confidence": sum(r.confidence_score for r in valid_responses) / len(valid_responses),
            "response_count": len(valid_responses),
            "total_models": len(responses)
        }
        
        return EnsembleResult(
            final_answer=best_response.response_text,
            confidence_score=best_response.confidence_score,
            contributing_models=[r.model_name for r in valid_responses],
            model_responses=responses,
            ensemble_method="weighted_voting",
            processing_time=sum(r.processing_time for r in responses),
            quality_metrics=quality_metrics
        )
    
    @staticmethod
    def consensus_based(responses: List[ModelResponse], similarity_threshold: float = 0.7) -> EnsembleResult:
        """합의 기반 앙상블"""
        valid_responses = [r for r in responses if not r.error_message and r.response_text]
        
        if len(valid_responses) < 2:
            return EnsembleStrategy.weighted_voting(responses, {})
        
        # 응답 간 유사도 계산 (간단한 키워드 기반)
        def calculate_similarity(text1: str, text2: str) -> float:
            import re
            words1 = set(re.findall(r'[가-힣]{2,}', text1.lower()))
            words2 = set(re.findall(r'[가-힣]{2,}', text2.lower()))
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            return len(intersection) / len(union)
        
        # 합의 그룹 찾기
        consensus_groups = []
        used_responses = set()
        
        for i, response in enumerate(valid_responses):
            if i in used_responses:
                continue
            
            group = [response]
            used_responses.add(i)
            
            for j, other_response in enumerate(valid_responses[i+1:], i+1):
                if j in used_responses:
                    continue
                
                similarity = calculate_similarity(response.response_text, other_response.response_text)
                if similarity >= similarity_threshold:
                    group.append(other_response)
                    used_responses.add(j)
            
            consensus_groups.append(group)
        
        # 가장 큰 합의 그룹 선택
        if consensus_groups:
            largest_group = max(consensus_groups, key=len)
            best_in_group = max(largest_group, key=lambda r: r.confidence_score)
            
            quality_metrics = {
                "consensus_size": len(largest_group),
                "total_groups": len(consensus_groups),
                "consensus_ratio": len(largest_group) / len(valid_responses)
            }
            
            return EnsembleResult(
                final_answer=best_in_group.response_text,
                confidence_score=best_in_group.confidence_score * (len(largest_group) / len(valid_responses)),
                contributing_models=[r.model_name for r in largest_group],
                model_responses=responses,
                ensemble_method="consensus_based",
                processing_time=sum(r.processing_time for r in responses),
                quality_metrics=quality_metrics
            )
        
        # 합의 없음 - 최고 품질 응답 선택
        return EnsembleStrategy.weighted_voting(responses, {})
    
    @staticmethod
    def adaptive_ensemble(responses: List[ModelResponse], query: str) -> EnsembleResult:
        """적응형 앙상블 - 쿼리 특성에 따라 전략 선택"""
        # 쿼리 복잡도 분석
        is_complex = len(query) > 50 or "절차" in query or "방법" in query
        is_personal = "김명정" in query or "고객" in query
        
        if is_complex:
            # 복잡한 쿼리 - 합의 기반
            return EnsembleStrategy.consensus_based(responses, similarity_threshold=0.6)
        elif is_personal:
            # 개인화 쿼리 - 높은 가중치
            weights = {"gpt-4o": 1.5, "gpt-4o-mini": 1.2, "local_kanana8b": 1.0}
            return EnsembleStrategy.weighted_voting(responses, weights)
        else:
            # 일반 쿼리 - 기본 가중 투표
            weights = {"gpt-4o": 1.0, "gpt-4o-mini": 1.0, "local_kanana8b": 0.8}
            return EnsembleStrategy.weighted_voting(responses, weights)

class MultiModelEnsemble:
    """다중 모델 앙상블 메인 클래스"""
    
    def __init__(self):
        self.model_manager = ModelManager()
        self.logger = logging.getLogger(__name__)
        
        # 성능 통계
        self.performance_stats = {
            "total_queries": 0,
            "successful_responses": 0,
            "average_processing_time": 0.0,
            "model_usage": defaultdict(int)
        }
    
    async def generate_ensemble_response(self, query: str, context: str, 
                                       model_selection: Optional[List[str]] = None,
                                       ensemble_strategy: str = "adaptive") -> EnsembleResult:
        """앙상블 응답 생성"""
        start_time = time.time()
        
        # 사용할 모델 선택
        if model_selection is None:
            model_selection = ["gpt-4o-mini", "local_kanana8b"]  # 기본 2개 모델
        
        # 프롬프트 구성
        prompt = f"""다음 정보를 바탕으로 질문에 답하세요:

{context}

질문: {query}

답변:"""
        
        self.logger.info(f"앙상블 시작: {len(model_selection)}개 모델 사용")
        
        # 모든 모델에서 병렬로 응답 생성
        tasks = []
        for model_name in model_selection:
            if model_name in self.model_manager.models:
                task = self.model_manager.get_model_response(model_name, prompt, context)
                tasks.append(task)
                self.performance_stats["model_usage"][model_name] += 1
        
        # 모든 응답 대기
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        valid_responses = []
        for response in responses:
            if isinstance(response, Exception):
                self.logger.error(f"Model response error: {response}")
            else:
                valid_responses.append(response)
        
        # 앙상블 전략 적용
        if ensemble_strategy == "weighted":
            result = EnsembleStrategy.weighted_voting(valid_responses, self.model_manager.models)
        elif ensemble_strategy == "consensus":
            result = EnsembleStrategy.consensus_based(valid_responses)
        else:  # adaptive
            result = EnsembleStrategy.adaptive_ensemble(valid_responses, query)
        
        # 성능 통계 업데이트
        total_time = time.time() - start_time
        self.performance_stats["total_queries"] += 1
        if result.confidence_score > 0.5:
            self.performance_stats["successful_responses"] += 1
        
        # 평균 처리 시간 업데이트
        self.performance_stats["average_processing_time"] = (
            (self.performance_stats["average_processing_time"] * (self.performance_stats["total_queries"] - 1) + total_time) /
            self.performance_stats["total_queries"]
        )
        
        self.logger.info(f"앙상블 완료: {result.ensemble_method}, 신뢰도: {result.confidence_score:.2f}, 시간: {total_time:.2f}초")
        
        return result
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        return {
            "performance_stats": dict(self.performance_stats),
            "model_configs": self.model_manager.models,
            "success_rate": (
                self.performance_stats["successful_responses"] / 
                max(self.performance_stats["total_queries"], 1)
            )
        }

# 전역 앙상블 인스턴스
ensemble_system = MultiModelEnsemble()

async def get_ensemble_response(query: str, context: str, 
                              model_selection: Optional[List[str]] = None,
                              ensemble_strategy: str = "adaptive") -> EnsembleResult:
    """앙상블 응답 생성 (편의 함수)"""
    return await ensemble_system.generate_ensemble_response(
        query, context, model_selection, ensemble_strategy
    )

if __name__ == "__main__":
    # 테스트 코드
    import asyncio
    logging.basicConfig(level=logging.INFO)
    
    async def test_ensemble():
        query = "BC카드 발급 절차를 알려주세요"
        context = "BC카드 발급은 1단계 신청서 작성, 2단계 서류 준비, 3단계 심사 과정을 거칩니다."
        
        result = await get_ensemble_response(query, context, ["gpt-4o-mini"], "adaptive")
        
        print("=== 앙상블 결과 ===")
        print(f"최종 답변: {result.final_answer[:200]}...")
        print(f"신뢰도: {result.confidence_score:.3f}")
        print(f"사용 모델: {result.contributing_models}")
        print(f"앙상블 방법: {result.ensemble_method}")
        print(f"처리 시간: {result.processing_time:.2f}초")
        
        for response in result.model_responses:
            print(f"\n--- {response.model_name} ---")
            print(f"신뢰도: {response.confidence_score:.3f}")
            print(f"처리 시간: {response.processing_time:.2f}초")
            if response.error_message:
                print(f"오류: {response.error_message}")
    
    # asyncio.run(test_ensemble())