"""
강화된 질의 처리기 - 유사도 향상을 위한 질의 확장 및 시맨틱 검색
"""

from typing import List, Dict, Tuple, Optional
import re
from langchain.schema import Document

class EnhancedQueryProcessor:
    """질의 확장 및 시맨틱 검색 강화"""
    
    def __init__(self):
        # 동의어/유의어 사전
        self.synonyms = {
            # 카드 관련
            "카드": ["신용카드", "체크카드", "카드", "결제카드"],
            "발급": ["신청", "개설", "만들기", "가입", "등록"],
            "안내": ["정보", "설명", "가이드", "방법", "절차"],
            "회원": ["고객", "사용자", "회원"],
            "은행": ["금융기관", "은행", "카드사"],
            
            # BC카드 특화
            "BC카드": ["BC", "비씨카드", "비시카드", "BC카드"],
            "회원은행": ["제휴은행", "발급은행", "카드발급은행", "회원은행"],
            
            # 개인화 관련
            "보유": ["소지", "가지고있는", "현재갖고있는", "이미있는"],
            "추천": ["제안", "권장", "안내", "추천"],
            "적합": ["맞는", "적절한", "좋은", "알맞은"],
            
            # 절차 관련  
            "절차": ["과정", "단계", "방법", "순서"],
            "서류": ["문서", "준비물", "필요한것", "구비서류"],
            "신청": ["접수", "등록", "가입", "발급신청"]
        }
        
        # 카드사별 매핑
        self.bank_mappings = {
            "우리": ["우리은행", "우리카드", "WB"],
            "하나": ["하나은행", "하나카드", "하나금융"],
            "농협": ["NH농협", "농협은행", "NH", "농협카드"],
            "KB": ["KB국민", "국민은행", "국민카드", "KB카드"],
            "신한": ["신한은행", "신한카드", "신한금융"],
            "SC": ["SC제일", "SC제일은행", "스탠차드"],
            "IBK": ["IBK기업", "기업은행", "IBK카드"],
            "DGB": ["DGB대구", "대구은행", "DGB카드"],
            "BNK": ["BNK부산", "부산은행", "BNK카드", "BNK경남", "경남은행"],
            "씨티": ["citi", "씨티은행", "씨티카드", "시티"]
        }
        
        # 개인명 패턴
        self.name_patterns = [
            r"([가-힣]{2,4})\s*(?:고객|회원|님|씨)?",
            r"([가-힣]{2,4})\s*(?:인데|이고|입니다)"
        ]
    
    def expand_query(self, original_query: str) -> List[str]:
        """질의 확장 - 동의어, 유의어, 관련 키워드 추가"""
        expanded_queries = [original_query]
        
        # 1. 동의어 확장
        for word, synonyms in self.synonyms.items():
            if word in original_query:
                for synonym in synonyms[:2]:  # 최대 2개까지
                    expanded_query = original_query.replace(word, synonym)
                    if expanded_query not in expanded_queries:
                        expanded_queries.append(expanded_query)
        
        # 2. 카드사 확장
        for bank, variations in self.bank_mappings.items():
            for variation in variations:
                if variation in original_query:
                    for alt_variation in variations[:2]:
                        expanded_query = original_query.replace(variation, alt_variation)
                        if expanded_query not in expanded_queries:
                            expanded_queries.append(expanded_query)
        
        # 3. 개인화 쿼리 확장
        expanded_queries.extend(self._expand_personalized_query(original_query))
        
        # 4. 카테고리별 확장
        if self._is_card_issuance_query(original_query):
            expanded_queries.extend(self._expand_card_issuance_query(original_query))
        
        return expanded_queries[:8]  # 최대 8개로 제한
    
    def _expand_personalized_query(self, query: str) -> List[str]:
        """개인화 쿼리 확장"""
        expanded = []
        
        # 이름 추출
        for pattern in self.name_patterns:
            matches = re.findall(pattern, query)
            for name in matches:
                # 개인화 관련 키워드 조합
                personal_variations = [
                    f"{name} 고객 카드 발급 안내",
                    f"{name} 보유카드 확인 추천카드",
                    f"{name} 회원은행별 카드발급",
                    f"{name} 맞춤 카드 추천"
                ]
                expanded.extend(personal_variations)
        
        return expanded
    
    def _expand_card_issuance_query(self, query: str) -> List[str]:
        """카드 발급 관련 쿼리 확장"""
        expanded = []
        
        if "BC카드" in query or "카드" in query:
            card_variations = [
                "BC카드 발급절차 신청방법",
                "카드발급 준비서류 신청자격",
                "회원은행별 카드발급안내",
                "카드 승인률 높이는 방법",
                "카드발급 심사기준 조건",
                "BC카드 온라인 신청방법"
            ]
            expanded.extend(card_variations)
        
        return expanded
    
    def _is_card_issuance_query(self, query: str) -> bool:
        """카드 발급 관련 쿼리인지 확인"""
        card_keywords = ["카드", "발급", "신청", "BC카드", "회원은행"]
        return any(keyword in query for keyword in card_keywords)
    
    def extract_intent_keywords(self, query: str) -> Dict[str, List[str]]:
        """질의에서 의도 키워드 추출"""
        intents = {
            "person": [],
            "bank": [],
            "action": [],
            "card_type": []
        }
        
        # 인명 추출
        for pattern in self.name_patterns:
            matches = re.findall(pattern, query)
            intents["person"].extend(matches)
        
        # 은행 추출
        for bank, variations in self.bank_mappings.items():
            for variation in variations:
                if variation in query:
                    intents["bank"].append(bank)
        
        # 행동 키워드
        action_keywords = ["발급", "신청", "안내", "추천", "확인", "조회"]
        for action in action_keywords:
            if action in query:
                intents["action"].append(action)
        
        # 카드 타입
        card_types = ["신용카드", "체크카드", "BC카드", "카드"]
        for card_type in card_types:
            if card_type in query:
                intents["card_type"].append(card_type)
        
        return intents
    
    def build_hybrid_search_queries(self, original_query: str) -> List[Dict[str, str]]:
        """하이브리드 검색을 위한 다양한 쿼리 생성"""
        queries = []
        
        # 1. 원본 쿼리
        queries.append({
            "query": original_query,
            "type": "original",
            "weight": 1.0
        })
        
        # 2. 확장된 쿼리들
        expanded = self.expand_query(original_query)
        for i, exp_query in enumerate(expanded[1:], 1):
            queries.append({
                "query": exp_query,
                "type": "expanded",
                "weight": 0.8 - (i * 0.1)  # 점진적으로 가중치 감소
            })
        
        # 3. 의도 기반 쿼리
        intents = self.extract_intent_keywords(original_query)
        if intents["person"] and intents["action"]:
            intent_query = f"{' '.join(intents['person'])} {' '.join(intents['action'])} {' '.join(intents['card_type'])}"
            queries.append({
                "query": intent_query,
                "type": "intent_based",
                "weight": 0.9
            })
        
        return queries
    
    def calculate_semantic_relevance(self, query: str, document_content: str) -> float:
        """시맨틱 관련도 계산 (간단한 키워드 기반)"""
        # 실제로는 더 정교한 시맨틱 분석이 필요
        query_keywords = set(re.findall(r'[가-힣]{2,}', query))
        doc_keywords = set(re.findall(r'[가-힣]{2,}', document_content))
        
        if not query_keywords:
            return 0.0
        
        # Jaccard 유사도 계산
        intersection = query_keywords.intersection(doc_keywords)
        union = query_keywords.union(doc_keywords)
        
        jaccard_sim = len(intersection) / len(union) if union else 0.0
        
        # 중요 키워드 가중치 적용
        important_keywords = ["BC카드", "카드발급", "회원은행", "신청", "절차"]
        important_matches = sum(1 for keyword in important_keywords if keyword in document_content)
        
        # 최종 점수 = Jaccard * 0.7 + 중요키워드매칭 * 0.3
        final_score = jaccard_sim * 0.7 + (important_matches / len(important_keywords)) * 0.3
        
        return min(final_score, 1.0)