"""
검색 결과 재순위 시스템
AI 기반으로 검색 결과의 관련성을 재평가
"""
from typing import List, Tuple
from langchain.schema import Document
import numpy as np

class SearchReranker:
    """검색 결과 재순위"""
    
    def __init__(self):
        self.boost_keywords = {
            '민원': 1.5,
            '접수': 1.3,
            '방법': 1.2,
            '안내': 1.2,
            'BC카드': 1.1
        }
    
    def rerank_results(self, 
                      query: str, 
                      results: List[Tuple[Document, float]],
                      strategy: str = "hybrid") -> List[Tuple[Document, float]]:
        """검색 결과 재순위"""
        
        if strategy == "keyword_boost":
            return self._keyword_boost_rerank(query, results)
        elif strategy == "semantic":
            return self._semantic_rerank(query, results)
        else:  # hybrid
            keyword_results = self._keyword_boost_rerank(query, results)
            return self._combine_rankings(results, keyword_results)
    
    def _keyword_boost_rerank(self, query: str, results: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
        """키워드 기반 부스팅"""
        reranked = []
        
        for doc, score in results:
            boost = 1.0
            content = doc.page_content.lower()
            query_lower = query.lower()
            
            # 정확한 매칭 부스트
            if query_lower in content:
                boost *= 1.5
            
            # 키워드별 부스트
            for keyword, boost_factor in self.boost_keywords.items():
                if keyword in query_lower and keyword in content:
                    boost *= boost_factor
            
            # 제목 매칭 부스트
            if doc.metadata.get('title'):
                if query_lower in doc.metadata['title'].lower():
                    boost *= 2.0
            
            new_score = min(score * boost, 1.0)
            reranked.append((doc, new_score))
        
        # 점수 기준 재정렬
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked
    
    def _semantic_rerank(self, query: str, results: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
        """의미 기반 재순위 (간소화 버전)"""
        # 질문 유형에 따른 가중치
        if '방법' in query or '절차' in query:
            # 단계별 설명이 있는 문서 우선
            reranked = []
            for doc, score in results:
                if any(marker in doc.page_content for marker in ['1.', '2.', '①', '②', '단계']):
                    reranked.append((doc, score * 1.3))
                else:
                    reranked.append((doc, score))
            return sorted(reranked, key=lambda x: x[1], reverse=True)
        
        return results
    
    def _combine_rankings(self, original: List, reranked: List) -> List[Tuple[Document, float]]:
        """원본과 재순위 결과 결합"""
        # 간단한 평균 방식
        combined = {}
        
        for i, (doc, score) in enumerate(original):
            combined[doc.page_content[:100]] = score * 0.6  # 원본 60%
        
        for i, (doc, score) in enumerate(reranked):
            key = doc.page_content[:100]
            if key in combined:
                combined[key] += score * 0.4  # 재순위 40%
            else:
                combined[key] = score * 0.4
        
        # 결과 재구성
        final_results = []
        for (doc, _) in original:
            key = doc.page_content[:100]
            if key in combined:
                final_results.append((doc, combined[key]))
        
        return sorted(final_results, key=lambda x: x[1], reverse=True)