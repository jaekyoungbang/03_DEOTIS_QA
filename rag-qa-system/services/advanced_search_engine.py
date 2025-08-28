#!/usr/bin/env python3
"""
고급 검색 엔진 - 상업화 QA 시스템을 위한 정교한 검색 알고리즘
"""

import re
import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from langchain.schema import Document
import time
from collections import defaultdict, Counter
import math
import logging

@dataclass
class SearchResult:
    """고급 검색 결과"""
    document: Document
    relevance_score: float
    search_strategy: str
    matched_keywords: List[str]
    semantic_score: float
    keyword_score: float
    context_score: float
    final_rank: int

class SemanticAnalyzer:
    """의미적 분석기"""
    
    def __init__(self):
        self.semantic_patterns = {
            # 카드 관련 의미군
            "card_issuance": ["발급", "신청", "개설", "만들기", "등록", "가입"],
            "card_management": ["관리", "이용", "사용", "결제", "승인"],
            "card_benefits": ["혜택", "적립", "할인", "포인트", "마일리지", "캐시백"],
            "card_types": ["신용카드", "체크카드", "기업카드", "개인카드"],
            
            # 고객 서비스 의미군
            "customer_service": ["상담", "문의", "도움", "지원", "안내"],
            "contact_info": ["연락처", "전화번호", "고객센터", "상담센터"],
            
            # 절차 관련 의미군
            "procedures": ["절차", "과정", "단계", "방법", "순서"],
            "requirements": ["조건", "자격", "요구사항", "기준"],
            "documents": ["서류", "문서", "준비물", "구비서류"],
            
            # 금융 기관 의미군
            "banks": ["은행", "금융기관", "카드사", "회원은행"],
            "specific_banks": ["우리", "하나", "농협", "KB", "신한", "IBK", "DGB", "BNK", "씨티"]
        }
        
        # 동의어 확장
        self.synonyms = {
            "발급": ["신청", "개설", "만들기", "가입"],
            "카드": ["신용카드", "체크카드", "결제카드"],
            "은행": ["금융기관", "카드사", "회원은행"],
            "안내": ["정보", "가이드", "설명", "도움말"],
            "절차": ["과정", "방법", "단계", "순서"],
            "조건": ["자격", "요구사항", "기준", "요건"]
        }
    
    def analyze_query_semantics(self, query: str) -> Dict[str, float]:
        """쿼리의 의미적 특성 분석"""
        semantic_scores = {}
        query_lower = query.lower()
        
        for category, keywords in self.semantic_patterns.items():
            # 직접 매칭 점수
            direct_matches = sum(1 for keyword in keywords if keyword in query_lower)
            direct_score = direct_matches / len(keywords)
            
            # 동의어 매칭 점수
            synonym_score = 0
            for keyword in keywords:
                if keyword in self.synonyms:
                    synonym_matches = sum(1 for syn in self.synonyms[keyword] if syn in query_lower)
                    synonym_score += synonym_matches / len(self.synonyms[keyword])
            
            # 최종 점수 (직접 매칭 70% + 동의어 매칭 30%)
            semantic_scores[category] = (direct_score * 0.7) + (synonym_score * 0.3)
        
        return semantic_scores
    
    def calculate_semantic_similarity(self, query: str, document: str) -> float:
        """쿼리와 문서 간 의미적 유사도 계산"""
        query_semantics = self.analyze_query_semantics(query)
        doc_semantics = self.analyze_query_semantics(document)
        
        # 벡터 내적으로 유사도 계산
        similarity = 0.0
        total_weight = 0.0
        
        for category in query_semantics:
            if category in doc_semantics:
                weight = max(query_semantics[category], doc_semantics[category])
                similarity += query_semantics[category] * doc_semantics[category] * weight
                total_weight += weight
        
        return similarity / max(total_weight, 0.01)

class KeywordAnalyzer:
    """키워드 분석기 - TF-IDF 기반"""
    
    def __init__(self):
        self.document_frequencies = {}
        self.total_documents = 0
        self.stop_words = {
            "의", "가", "이", "을", "를", "에", "는", "은", "과", "와", "도", "만", "까지", 
            "부터", "로", "으로", "에서", "한테", "께", "에게", "한", "두", "세", "네", "다섯"
        }
    
    def build_idf_scores(self, documents: List[Document]):
        """문서 집합에서 IDF 점수 구축"""
        self.total_documents = len(documents)
        word_doc_count = defaultdict(int)
        
        for doc in documents:
            words = self._extract_keywords(doc.page_content)
            unique_words = set(words)
            
            for word in unique_words:
                word_doc_count[word] += 1
        
        # IDF 계산
        for word, doc_count in word_doc_count.items():
            self.document_frequencies[word] = math.log(self.total_documents / doc_count)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출"""
        # 한글, 영문, 숫자만 추출
        words = re.findall(r'[가-힣a-zA-Z0-9]{2,}', text)
        # 불용어 제거
        return [word.lower() for word in words if word.lower() not in self.stop_words]
    
    def calculate_tf_idf_score(self, query: str, document: str) -> Tuple[float, List[str]]:
        """TF-IDF 기반 관련도 점수 계산"""
        query_keywords = self._extract_keywords(query)
        doc_keywords = self._extract_keywords(document)
        
        if not query_keywords or not doc_keywords:
            return 0.0, []
        
        # 문서 키워드 빈도 계산
        doc_word_count = Counter(doc_keywords)
        total_doc_words = len(doc_keywords)
        
        matched_keywords = []
        tf_idf_score = 0.0
        
        for query_word in query_keywords:
            if query_word in doc_word_count:
                # TF 계산
                tf = doc_word_count[query_word] / total_doc_words
                
                # IDF 계산 (문서 집합이 없으면 기본값 사용)
                idf = self.document_frequencies.get(query_word, 1.0)
                
                tf_idf_score += tf * idf
                matched_keywords.append(query_word)
        
        return tf_idf_score, matched_keywords

class ContextAnalyzer:
    """문맥 분석기 - 주변 문맥의 관련성 평가"""
    
    def __init__(self):
        self.context_window = 100  # 앞뒤 100자
        self.important_contexts = {
            "질문_응답": ["질문", "Q:", "A:", "답변", "답:", "문의"],
            "절차_설명": ["절차", "단계", "STEP", "방법", "과정"],
            "연락처_정보": ["연락처", "전화", "고객센터", "상담센터", "문의"],
            "요구사항": ["조건", "자격", "요구사항", "필요", "구비"],
            "카드_정보": ["카드명", "카드종류", "혜택", "특징", "이용방법"]
        }
    
    def analyze_context_relevance(self, query: str, document: str, match_position: int) -> float:
        """매칭 위치 주변 문맥의 관련성 분석"""
        # 매칭 위치 주변 텍스트 추출
        start_pos = max(0, match_position - self.context_window)
        end_pos = min(len(document), match_position + self.context_window)
        context = document[start_pos:end_pos]
        
        context_score = 0.0
        query_lower = query.lower()
        
        # 중요한 문맥 패턴과 매칭
        for context_type, patterns in self.important_contexts.items():
            pattern_matches = sum(1 for pattern in patterns if pattern in context.lower())
            if pattern_matches > 0:
                # 쿼리와 문맥 타입의 연관성 가중치
                if any(pattern in query_lower for pattern in patterns):
                    context_score += pattern_matches * 2.0  # 쿼리와 직접 연관된 문맥은 높은 점수
                else:
                    context_score += pattern_matches * 0.5  # 간접 연관된 문맥은 낮은 점수
        
        # 문맥 내 키워드 밀도
        query_words = query.split()
        context_words = context.split()
        
        if context_words:
            keyword_density = sum(1 for word in query_words if word in context) / len(context_words)
            context_score += keyword_density * 5.0
        
        return min(context_score, 10.0) / 10.0  # 0-1 범위로 정규화

class AdvancedSearchEngine:
    """고급 검색 엔진 - 다중 전략 통합"""
    
    def __init__(self):
        self.semantic_analyzer = SemanticAnalyzer()
        self.keyword_analyzer = KeywordAnalyzer()
        self.context_analyzer = ContextAnalyzer()
        
        # 검색 전략 가중치
        self.strategy_weights = {
            "semantic": 0.4,
            "keyword": 0.35,
            "context": 0.25
        }
        
        # 개인화 키워드 가중치 (김명정님 등)
        self.personalization_weights = {
            "김명정": 3.0,
            "보유카드": 2.5,
            "발급가능": 2.5,
            "추천카드": 2.0,
            "맞춤": 1.8
        }
        
        self.logger = logging.getLogger(__name__)
    
    def initialize_with_documents(self, documents: List[Document]):
        """문서 집합으로 검색 엔진 초기화"""
        self.logger.info(f"고급 검색 엔진 초기화: {len(documents)}개 문서")
        self.keyword_analyzer.build_idf_scores(documents)
        self.logger.info("TF-IDF 점수 구축 완료")
    
    def search(self, query: str, documents: List[Document], top_k: int = 10) -> List[SearchResult]:
        """고급 다중 전략 검색 수행"""
        start_time = time.time()
        
        if not documents:
            return []
        
        search_results = []
        
        for i, document in enumerate(documents):
            doc_content = document.page_content
            
            # 1. 의미적 유사도 계산
            semantic_score = self.semantic_analyzer.calculate_semantic_similarity(query, doc_content)
            
            # 2. TF-IDF 키워드 점수 계산
            keyword_score, matched_keywords = self.keyword_analyzer.calculate_tf_idf_score(query, doc_content)
            
            # 3. 문맥 관련성 점수 계산
            # 첫 번째 키워드 매칭 위치 찾기
            match_position = 0
            for keyword in matched_keywords:
                pos = doc_content.lower().find(keyword.lower())
                if pos != -1:
                    match_position = pos
                    break
            
            context_score = self.context_analyzer.analyze_context_relevance(query, doc_content, match_position)
            
            # 4. 개인화 가중치 적용
            personalization_bonus = 0.0
            for person_keyword, weight in self.personalization_weights.items():
                if person_keyword in query and person_keyword in doc_content:
                    personalization_bonus += weight
            
            # 5. 통합 관련도 점수 계산
            relevance_score = (
                semantic_score * self.strategy_weights["semantic"] +
                keyword_score * self.strategy_weights["keyword"] +
                context_score * self.strategy_weights["context"] +
                personalization_bonus * 0.1  # 개인화 보너스
            )
            
            search_result = SearchResult(
                document=document,
                relevance_score=relevance_score,
                search_strategy="multi_strategy",
                matched_keywords=matched_keywords,
                semantic_score=semantic_score,
                keyword_score=keyword_score,
                context_score=context_score,
                final_rank=0  # 나중에 설정
            )
            
            search_results.append(search_result)
        
        # 관련도 점수로 정렬
        search_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # 순위 설정
        for rank, result in enumerate(search_results[:top_k], 1):
            result.final_rank = rank
        
        search_time = time.time() - start_time
        self.logger.info(f"고급 검색 완료: {len(search_results)}개 결과, {search_time:.3f}초")
        
        return search_results[:top_k]
    
    def explain_search_result(self, result: SearchResult) -> Dict[str, any]:
        """검색 결과 상세 설명"""
        return {
            "final_rank": result.final_rank,
            "total_relevance_score": round(result.relevance_score, 3),
            "score_breakdown": {
                "semantic_score": round(result.semantic_score, 3),
                "keyword_score": round(result.keyword_score, 3),
                "context_score": round(result.context_score, 3)
            },
            "matched_keywords": result.matched_keywords,
            "search_strategy": result.search_strategy,
            "document_preview": result.document.page_content[:200] + "..." if len(result.document.page_content) > 200 else result.document.page_content,
            "document_metadata": result.document.metadata
        }
    
    def search_with_explanation(self, query: str, documents: List[Document], top_k: int = 10) -> Tuple[List[SearchResult], Dict[str, any]]:
        """검색 수행 및 상세 설명 제공"""
        results = self.search(query, documents, top_k)
        
        explanation = {
            "query_analysis": self.semantic_analyzer.analyze_query_semantics(query),
            "search_strategy": "advanced_multi_strategy",
            "strategy_weights": self.strategy_weights,
            "total_documents_searched": len(documents),
            "results_returned": len(results),
            "top_results_explanation": [
                self.explain_search_result(result) for result in results[:3]
            ]
        }
        
        return results, explanation

class HybridSearchEngine:
    """하이브리드 검색 엔진 - 벡터 검색 + 고급 검색 결합"""
    
    def __init__(self, vectorstore_manager=None):
        self.vectorstore_manager = vectorstore_manager
        self.advanced_engine = AdvancedSearchEngine()
        self.alpha = 0.6  # 벡터 검색 가중치
        self.beta = 0.4   # 고급 검색 가중치
    
    def hybrid_search(self, query: str, chunking_type: str = "custom", k: int = 20) -> List[Tuple[Document, float]]:
        """하이브리드 검색: 벡터 검색 + 고급 알고리즘 검색"""
        
        # 1. 벡터 검색 수행
        if self.vectorstore_manager:
            vector_results = self.vectorstore_manager.similarity_search_with_score(
                query, chunking_type, k=k
            )
        else:
            vector_results = []
        
        # 2. 고급 검색 엔진 초기화
        documents = [doc for doc, score in vector_results]
        if documents:
            self.advanced_engine.initialize_with_documents(documents)
        
        # 3. 고급 검색 수행
        advanced_results = self.advanced_engine.search(query, documents, top_k=k)
        
        # 4. 점수 정규화 및 결합
        if not vector_results or not advanced_results:
            return vector_results[:10]  # 벡터 검색만 사용
        
        # 벡터 점수 정규화 (0-1 범위)
        vector_scores = [score for doc, score in vector_results]
        if vector_scores:
            min_vector = min(vector_scores)
            max_vector = max(vector_scores)
            vector_range = max_vector - min_vector
            
            if vector_range > 0:
                normalized_vector = [(score - min_vector) / vector_range for score in vector_scores]
            else:
                normalized_vector = [1.0] * len(vector_scores)
        else:
            normalized_vector = []
        
        # 고급 검색 점수 정규화 (0-1 범위)
        advanced_scores = [result.relevance_score for result in advanced_results]
        if advanced_scores:
            min_advanced = min(advanced_scores)
            max_advanced = max(advanced_scores)
            advanced_range = max_advanced - min_advanced
            
            if advanced_range > 0:
                normalized_advanced = [(score - min_advanced) / advanced_range for score in advanced_scores]
            else:
                normalized_advanced = [1.0] * len(advanced_scores)
        else:
            normalized_advanced = []
        
        # 5. 하이브리드 점수 계산 및 결합
        combined_results = []
        doc_to_vector_score = {id(doc): norm_score for (doc, _), norm_score in zip(vector_results, normalized_vector)}
        
        for i, advanced_result in enumerate(advanced_results):
            doc = advanced_result.document
            
            # 벡터 점수 가져오기
            vector_score = doc_to_vector_score.get(id(doc), 0.0)
            advanced_score = normalized_advanced[i] if i < len(normalized_advanced) else 0.0
            
            # 하이브리드 점수 계산
            hybrid_score = (self.alpha * vector_score) + (self.beta * advanced_score)
            
            combined_results.append((doc, hybrid_score))
        
        # 하이브리드 점수로 정렬
        combined_results.sort(key=lambda x: x[1], reverse=True)
        
        logging.info(f"하이브리드 검색 완료: 벡터 {len(vector_results)}개 + 고급 {len(advanced_results)}개 → 결합 {len(combined_results)}개")
        
        return combined_results[:10]

# 전역 인스턴스
advanced_search_engine = AdvancedSearchEngine()
hybrid_search_engine = HybridSearchEngine()

def initialize_search_engines(vectorstore_manager, documents: List[Document]):
    """검색 엔진들을 문서 집합으로 초기화"""
    advanced_search_engine.initialize_with_documents(documents)
    hybrid_search_engine.vectorstore_manager = vectorstore_manager
    hybrid_search_engine.advanced_engine.initialize_with_documents(documents)
    logging.info("모든 검색 엔진 초기화 완료")

if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    # 샘플 문서
    sample_docs = [
        Document(page_content="BC카드 발급 절차: 1단계 신청서 작성, 2단계 서류 준비, 3단계 심사", metadata={"source": "test"}),
        Document(page_content="김명정 고객님의 보유카드: 우리카드, 하나카드. 추천카드: NH농협카드", metadata={"source": "test"}),
        Document(page_content="고객센터 연락처: 1588-4000. 24시간 상담 가능합니다.", metadata={"source": "test"})
    ]
    
    # 검색 엔진 테스트
    engine = AdvancedSearchEngine()
    engine.initialize_with_documents(sample_docs)
    
    query = "김명정 고객의 카드발급 안내"
    results, explanation = engine.search_with_explanation(query, sample_docs, top_k=3)
    
    print("=== 고급 검색 결과 ===")
    for result in results:
        print(f"순위 {result.final_rank}: 점수 {result.relevance_score:.3f}")
        print(f"매칭 키워드: {result.matched_keywords}")
        print(f"문서: {result.document.page_content[:100]}...")
        print("-" * 50)
    
    print("\n=== 검색 설명 ===")
    print(f"쿼리 분석: {explanation['query_analysis']}")
    print(f"검색된 문서 수: {explanation['total_documents_searched']}")