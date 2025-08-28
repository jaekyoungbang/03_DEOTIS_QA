import json
import re
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from models.vectorstore import DualVectorStoreManager
from models.embeddings import EmbeddingManager

@dataclass
class CardInfo:
    name: str
    bank: str
    status: str  # "보유중", "발급가능", "발급추천"
    image_path: Optional[str] = None
    benefits: List[str] = None
    issue_date: Optional[str] = None
    recommendation_reason: Optional[str] = None

@dataclass
class CustomerCardAnalysis:
    customer_name: str
    owned_cards: List[CardInfo]
    available_cards: List[CardInfo]
    recommended_cards: List[CardInfo]
    total_summary: Dict[str, int]

class CardAnalysisService:
    def __init__(self):
        self.embedding_manager = EmbeddingManager()
        self.vectorstore_manager = DualVectorStoreManager(self.embedding_manager.get_embeddings())
        # s3-common 폴더 경로 (rag-qa-system 내부) - 개인정보 파일 위치
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # rag-qa-system 폴더
        self.s3_common_path = os.path.join(current_dir, 's3-common')
        
        # 하드코딩 제거: 벡터DB 검색 결과에서만 이미지 정보 추출
    
    def analyze_customer_cards(self, customer_name: str) -> CustomerCardAnalysis:
        """고객의 카드 발급 현황을 분석합니다."""
        try:
            # RAG를 통해 고객 정보 검색 - custom 컬렉션에서 더 많은 결과 가져오기
            queries = [
                f"{customer_name} 회원 카드 발급 현황",
                f"{customer_name} 보유 카드",
                f"{customer_name} 추천 카드",
                f"{customer_name} 발급 가능"
            ]
            
            search_results = []
            for query in queries:
                results = self.vectorstore_manager.similarity_search(query, "custom", k=15)
                search_results.extend(results)
            
            # 중복 제거
            seen_content = set()
            unique_results = []
            for result in search_results:
                content_hash = hash(result.page_content)
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    unique_results.append(result)
            search_results = unique_results
            
            # 먼저 직접 파일 읽기 시도
            owned_cards, available_cards, recommended_cards = self._read_customer_file_directly(customer_name)
            
            # 직접 읽기에서 데이터를 찾지 못했으면 RAG 검색 결과 사용
            if not owned_cards and not available_cards and not recommended_cards:
                owned_cards, available_cards, recommended_cards = self._parse_card_info(search_results, customer_name)
            
            # 요약 정보 계산
            total_summary = {
                "보유카드": len(owned_cards),
                "발급가능": len(available_cards),
                "발급추천": len(recommended_cards),
                "총옵션": len(owned_cards) + len(available_cards) + len(recommended_cards)
            }
            
            return CustomerCardAnalysis(
                customer_name=customer_name,
                owned_cards=owned_cards,
                available_cards=available_cards,
                recommended_cards=recommended_cards,
                total_summary=total_summary
            )
            
        except Exception as e:
            print(f"❌ 카드 분석 오류: {e}")
            return self._get_empty_analysis(customer_name)
    
    def _parse_card_info(self, search_results: List, customer_name: str) -> Tuple[List[CardInfo], List[CardInfo], List[CardInfo]]:
        """검색 결과에서 카드 정보를 파싱합니다."""
        owned_cards = []
        available_cards = []
        recommended_cards = []
        
        for result in search_results:
            content = result.page_content
            
            # 보유 카드 추출 - 수정된 정규식
            owned_matches = re.findall(r'### \d+\.\s*(.+?)\s*\(보유중\)', content, re.IGNORECASE)
            for match in owned_matches:
                card_name = match.strip()
                owned_cards.append(CardInfo(
                    name=card_name,
                    bank=card_name,
                    status="보유중",
                    image_path=self._extract_image_from_content(content, card_name),
                    benefits=self._extract_benefits(content, card_name)
                ))
            
            # 발급 추천 카드 추출
            recommended_matches = re.findall(r'### \d+\.\s*(.+?)\s*\(발급 추천\)', content, re.IGNORECASE)
            for match in recommended_matches:
                card_name = match.strip()
                recommended_cards.append(CardInfo(
                    name=card_name,
                    bank=card_name,
                    status="발급추천",
                    image_path=self._extract_image_from_content(content, card_name),
                    recommendation_reason=self._extract_recommendation_reason(content, card_name)
                ))
            
            # 발급 가능 카드 추출
            available_matches = re.findall(r'### \d+\.\s*(.+?)\s*\(발급 가능\)', content, re.IGNORECASE)
            for match in available_matches:
                card_name = match.strip()
                available_cards.append(CardInfo(
                    name=card_name,
                    bank=card_name,
                    status="발급가능",
                    image_path=self._extract_image_from_content(content, card_name)
                ))
        
        return owned_cards, available_cards, recommended_cards
    
    def _extract_image_from_content(self, content: str, card_name: str) -> Optional[str]:
        """벡터DB 검색 결과에서 이미지 경로를 추출합니다."""
        import re
        # 마크다운 이미지 패턴 찾기: ![alt](image_path)
        image_pattern = r'!\[.*?\]\(([^)]+)\)'
        matches = re.findall(image_pattern, content)
        
        # 카드명과 관련된 이미지 찾기
        for image_path in matches:
            # GIF 확장자를 JPG로 치환
            if image_path.endswith('.gif'):
                image_path = image_path.replace('.gif', '-0000.jpg')
            
            if any(keyword in image_path.lower() or keyword in content.lower() 
                   for keyword in [card_name.lower().replace('카드', ''), 'card', 'logo']):
                return image_path
        
        # 첫 번째 이미지 반환 (없으면 None)
        if matches:
            first_image = matches[0]
            if first_image.endswith('.gif'):
                first_image = first_image.replace('.gif', '-0000.jpg')
            return first_image
        return None
    
    def _extract_benefits(self, content: str, card_name: str) -> List[str]:
        """카드별 혜택을 추출합니다."""
        benefits = []
        lines = content.split('\n')
        found_card = False
        
        for line in lines:
            if card_name in line and '보유중' in line:
                found_card = True
                continue
            if found_card and line.strip().startswith('- **혜택**:'):
                benefit = line.strip().replace('- **혜택**: ', '')
                benefits.append(benefit)
                break
            if found_card and line.startswith('###'):
                break
                
        return benefits
    
    def _extract_issue_date(self, line: str) -> str:
        """발급일 추출"""
        import re
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        match = re.search(date_pattern, line)
        return match.group() if match else None
    
    def _read_customer_file_directly(self, customer_name: str) -> Tuple[List[CardInfo], List[CardInfo], List[CardInfo]]:
        """고객 파일을 직접 읽어 카드 정보 추출 (s3-common 폴더에서)"""
        customer_file_path = os.path.join(self.s3_common_path, f"{customer_name}_personal.txt")
        if not os.path.exists(customer_file_path):
            # 다른 파일명 시도
            customer_file_path = os.path.join(self.s3_common_path, "kim_pesonal.txt")
        
        owned_cards = []
        available_cards = []
        recommended_cards = []
        
        if os.path.exists(customer_file_path):
            print(f"📄 {customer_name} 고객 파일 발견: {customer_file_path}")
            try:
                with open(customer_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"📄 파일 내용 읽기 완료: {len(content)}자")
                    
                    # 보유 카드 추출
                    if '보유 카드 현황' in content:
                        owned_section = content.split('보유 카드 현황')[1]
                        if '미보유 카드' in owned_section:
                            owned_section = owned_section.split('미보유 카드')[0]
                        
                        # 카드 이름 추출
                        for line in owned_section.split('\n'):
                            if '우리카드' in line and ('1.' in line or '-' in line):
                                owned_cards.append(CardInfo(
                                    name="우리카드",
                                    bank="우리은행",
                                    status="보유중",
                                    image_path=None,  # 하드코딩 제거: 벡터DB에서만 이미지 가져오기
                                    benefits=["신용카드"],
                                    issue_date=self._extract_issue_date(line)
                                ))
                            elif '하나카드' in line and ('2.' in line or '-' in line):
                                owned_cards.append(CardInfo(
                                    name="하나카드",
                                    bank="하나은행",
                                    status="보유중",
                                    image_path=None,  # 하드코딩 제거: 벡터DB에서만 이미지 가져오기
                                    benefits=["신용카드"],
                                    issue_date=self._extract_issue_date(line)
                                ))
                            elif '농협카드' in line and ('3.' in line or '-' in line):
                                owned_cards.append(CardInfo(
                                    name="NH농협카드",
                                    bank="농협은행",
                                    status="보유중",
                                    image_path=None,  # 하드코딩 제거: 벡터DB에서만 이미지 가져오기
                                    benefits=["신용카드"],
                                    issue_date=self._extract_issue_date(line)
                                ))
                    
                    # 미보유 카드 추출
                    if '미보유 카드' in content:
                        unavailable_section = content.split('미보유 카드')[1]
                        if '고객 특이사항' in unavailable_section:
                            unavailable_section = unavailable_section.split('고객 특이사항')[0]
                        
                        # 미보유 카드를 밟급 가능 또는 추천으로 분류
                        unavailable_cards = [
                            "BC카드", "신한카드", "국민카드", "롯데카드", 
                            "삼성카드", "현대카드", "씨티카드"
                        ]
                        
                        for i, card_name in enumerate(unavailable_cards):
                            if card_name in unavailable_section or card_name.replace('카드', '') in unavailable_section:
                                # 첫 4개는 추천, 나머지는 발급가능으로 분류
                                if i < 4:
                                    recommended_cards.append(CardInfo(
                                        name=card_name,
                                        bank=card_name.replace('카드', ''),
                                        status="발급추천",
                                        image_path=None,  # 하드코딩 제거: 벡터DB에서만 이미지 가져오기
                                        recommendation_reason="VIP 등급 고객 우대 혜택"
                                    ))
                                else:
                                    available_cards.append(CardInfo(
                                        name=card_name,
                                        bank=card_name.replace('카드', ''),
                                        status="발급가능",
                                        image_path=None  # 하드코딩 제거: 벡터DB에서만 이미지 가져오기,
                                    ))
                        
                        print(f"📊 분석 완료: 보유 {len(owned_cards)}, 추천 {len(recommended_cards)}, 가능 {len(available_cards)}")
                        
            except Exception as e:
                print(f"❌ 파일 읽기 오류: {e}")
        else:
            print(f"⚠️ 고객 파일을 찾을 수 없음: {customer_file_path}")
        
        return owned_cards, available_cards, recommended_cards
    
    def _extract_recommendation_reason(self, content: str, card_name: str) -> str:
        """추천 사유를 추출합니다."""
        lines = content.split('\n')
        found_card = False
        
        for line in lines:
            if card_name in line and ('발급 추천' in line or '추천' in line):
                found_card = True
                continue
            if found_card and line.strip().startswith('- **추천 이유**:'):
                return line.strip().replace('- **추천 이유**: ', '')
            if found_card and line.startswith('###'):
                break
                
        return ""
    
    def _get_empty_analysis(self, customer_name: str) -> CustomerCardAnalysis:
        """빈 분석 결과를 반환합니다."""
        return CustomerCardAnalysis(
            customer_name=customer_name,
            owned_cards=[],
            available_cards=[],
            recommended_cards=[],
            total_summary={"보유카드": 0, "발급가능": 0, "발급추천": 0, "총옵션": 0}
        )
    
    def format_analysis_response(self, analysis: CustomerCardAnalysis) -> str:
        """분석 결과를 포맷팅된 텍스트로 변환합니다."""
        response = f"## {analysis.customer_name} 회원 카드 발급 현황 분석\n\n"
        
        # 보유 카드
        if analysis.owned_cards:
            response += f"### ✅ 현재 보유 카드 ({len(analysis.owned_cards)}장)\n\n"
            for i, card in enumerate(analysis.owned_cards, 1):
                # 벡터DB에서 추출된 이미지만 사용
                if card.image_path:
                    response += f"![{card.name} 로고]({card.image_path})\n"
                response += f"**{i}. {card.name}** - ✅ 보유중\n"
                if card.benefits:
                    response += f"- 혜택: {', '.join(card.benefits)}\n"
                response += "\n"
        
        # 발급 추천 카드
        if analysis.recommended_cards:
            response += f"### 🌟 발급 추천 카드 ({len(analysis.recommended_cards)}장)\n\n"
            for i, card in enumerate(analysis.recommended_cards, 1):
                # 벡터DB에서 추출된 이미지만 사용
                if card.image_path:
                    response += f"![{card.name} 로고]({card.image_path})\n"
                response += f"**{i}. {card.name}** - ⭐ 발급 추천\n"
                if card.recommendation_reason:
                    response += f"- 추천 이유: {card.recommendation_reason}\n"
                response += "\n"
        
        # 발급 가능 카드
        if analysis.available_cards:
            response += f"### 🆕 발급 가능 카드 ({len(analysis.available_cards)}장)\n\n"
            for i, card in enumerate(analysis.available_cards, 1):
                # 벡터DB에서 추출된 이미지만 사용
                if card.image_path:
                    response += f"![{card.name} 로고]({card.image_path})\n"
                response += f"**{i}. {card.name}** - 📋 발급 가능\n"
                response += "\n"
        
        # BC카드 발급 절차는 벡터DB 검색 결과에 포함된 경우만 표시
        
        # 요약
        response += "### 📊 현황 요약\n\n"
        response += f"- **보유 카드**: {analysis.total_summary['보유카드']}장\n"
        response += f"- **발급 추천**: {analysis.total_summary['발급추천']}장\n"
        response += f"- **발급 가능**: {analysis.total_summary['발급가능']}장\n"
        response += f"- **총 옵션**: {analysis.total_summary['총옵션']}장\n\n"
        
        if not analysis.owned_cards and not analysis.available_cards and not analysis.recommended_cards:
            response += "⚠️ 해당 고객의 카드 발급 정보를 찾을 수 없습니다. 정확한 고객명을 확인해주세요.\n"
        
        return response
    
    def get_card_recommendations(self, customer_name: str, limit: int = 3) -> List[CardInfo]:
        """고객에게 추천할 카드 목록을 반환합니다."""
        analysis = self.analyze_customer_cards(customer_name)
        
        # 발급 추천 카드를 우선으로 하고, 발급 가능 카드를 추가
        recommendations = analysis.recommended_cards[:limit]
        
        if len(recommendations) < limit:
            remaining = limit - len(recommendations)
            recommendations.extend(analysis.available_cards[:remaining])
        
        return recommendations