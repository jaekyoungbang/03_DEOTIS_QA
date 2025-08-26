"""
질문 사전 분석 및 최적화
GPT-4를 사용하여 사용자 질문을 분석하고 개선
"""
from typing import Dict, List
from models.llm import LLMManager

class QueryAnalyzer:
    """질문 분석 및 개선"""
    
    def __init__(self):
        self.llm_manager = LLMManager()
        
    def analyze_query(self, query: str) -> Dict:
        """질문을 분석하고 개선된 버전 제공"""
        
        analysis_prompt = f"""
        사용자 질문을 분석하고 개선해주세요.
        
        원본 질문: {query}
        
        다음 항목들을 분석해주세요:
        1. 질문의 의도
        2. 핵심 키워드
        3. 예상 답변 유형
        4. 개선된 검색어 (2-3개)
        
        JSON 형식으로 응답해주세요.
        """
        
        # GPT-4로 분석
        llm = self.llm_manager.get_llm('gpt-4')
        response = llm.invoke(analysis_prompt)
        
        # 기본 분석 (폴백)
        keywords = self._extract_keywords(query)
        
        return {
            "original_query": query,
            "keywords": keywords,
            "intent": self._detect_intent(query),
            "enhanced_queries": self._generate_enhanced_queries(query, keywords)
        }
    
    def _extract_keywords(self, query: str) -> List[str]:
        """핵심 키워드 추출"""
        # 불용어 제거
        stopwords = ['은', '는', '이', '가', '을', '를', '의', '에', '와', '과']
        words = query.split()
        keywords = [w for w in words if w not in stopwords and len(w) > 1]
        return keywords
    
    def _detect_intent(self, query: str) -> str:
        """질문 의도 파악"""
        if any(word in query for word in ['방법', '절차', '어떻게']):
            return "how_to"
        elif any(word in query for word in ['무엇', '뭐', '정의']):
            return "definition"
        elif any(word in query for word in ['왜', '이유', '원인']):
            return "reason"
        else:
            return "general"
    
    def _generate_enhanced_queries(self, query: str, keywords: List[str]) -> List[str]:
        """개선된 검색어 생성"""
        enhanced = [query]  # 원본 포함
        
        # 키워드 조합
        if len(keywords) >= 2:
            enhanced.append(" ".join(keywords[:2]))
            
        # 의도별 변형
        if '방법' in query:
            enhanced.append(query.replace('방법', '절차'))
        
        return enhanced[:3]  # 최대 3개