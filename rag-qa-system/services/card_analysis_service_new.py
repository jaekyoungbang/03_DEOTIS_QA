import os
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from models.dual_vectorstore import DualVectorStoreManager
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

class DynamicCardAnalysisService:
    """동적 카드 분석 서비스 - txt파일 + 벡터DB 차집합 방식"""
    
    def __init__(self, vectorstore_manager=None):
        if vectorstore_manager:
            # 기존 벡터DB 매니저 재사용 (chat.py에서 전달받은 경우)
            self.vectorstore_manager = vectorstore_manager
            print(f"🔄 [DynamicCardAnalysisService] 기존 벡터DB 매니저 재사용")
        else:
            # 새로운 벡터DB 매니저 생성 (독립 실행 시)
            self.embedding_manager = EmbeddingManager()
            self.vectorstore_manager = DualVectorStoreManager(self.embedding_manager.get_embeddings())
            print(f"🆕 [DynamicCardAnalysisService] 새로운 벡터DB 매니저 생성")
        
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.s3_common_path = os.path.join(current_dir, 's3-common')
        
    def analyze_customer_cards(self, customer_name: str, chunking_type: str = "custom") -> CustomerCardAnalysis:
        """
        고객의 카드 발급 현황을 동적으로 분석
        
        Args:
            customer_name: 고객명 (예: "김명정")
            chunking_type: "basic" (s3, 텍스트만) 또는 "custom" (s3-chunking, 이미지포함)
        """
        print(f"🔍 [{customer_name}] 동적 카드 분석 시작 (청킹: {chunking_type})")
        
        # 1. txt 파일에서 보유 카드 읽기
        owned_cards = self._read_owned_cards_from_txt(customer_name)
        print(f"📄 txt 파일에서 보유 카드 {len(owned_cards)}장 읽음")
        
        if chunking_type == "basic":
            # s3 기본: 텍스트만, 이미지 없음 - 하지만 카드 목록은 제공
            print(f"📝 s3 기본 모드: 이미지 없이 텍스트만 처리")
            
            # 벡터DB에서 카드 목록만 가져오기 (이미지 제외)
            all_available_cards, _ = self._extract_cards_from_vectordb("custom")  # custom에서 카드 목록만 가져오기
            print(f"📋 s3 기본: {len(all_available_cards)}개 카드 목록 확인")
            
            # 차집합 계산 (전체 - 보유 = 미보유)
            owned_card_names = {card.name for card in owned_cards}
            available_cards = []
            recommended_cards = []
            
            for card_name in all_available_cards:
                if card_name not in owned_card_names:
                    card_info = CardInfo(
                        name=card_name,
                        bank=card_name.replace('카드', ''),
                        status="발급가능",
                        image_path=None  # s3 기본에서는 이미지 없음
                    )
                    
                    # 모든 카드를 발급 가능으로 분류 (BC카드 특별 분류 제거)
                    available_cards.append(card_info)
                    print(f"  📋 s3기본 발급가능: {card_name} (이미지 없음)")
            
        else:
            # s3-chunking: 벡터DB에서 전체 카드 목록 + 이미지 정보 추출
            all_available_cards, card_images = self._extract_cards_from_vectordb(chunking_type)
            print(f"🗃️ 벡터DB에서 전체 카드 {len(all_available_cards)}장 + 이미지 {len(card_images)}개 추출")
            
            # 차집합 계산 (전체 - 보유 = 미보유)
            owned_card_names = {card.name for card in owned_cards}
            available_cards = []
            recommended_cards = []
            
            for card_name in all_available_cards:
                if card_name not in owned_card_names:
                    # 이미지 매핑
                    image_path = self._find_card_image(card_name, card_images)
                    
                    card_info = CardInfo(
                        name=card_name,
                        bank=card_name.replace('카드', ''),
                        status="발급가능",
                        image_path=image_path
                    )
                    
                    # 모든 카드를 발급 가능으로 분류 (BC카드 특별 분류 제거)
                    available_cards.append(card_info)
                    print(f"  📋 발급가능카드 추가: {card_name} (이미지: {image_path or '없음'})")
            
            # 보유 카드에 이미지 추가 (s3-chunking만)
            for card in owned_cards:
                if not card.image_path:
                    card.image_path = self._find_card_image(card.name, card_images)
        
        print(f"✅ 분석 완료: 보유 {len(owned_cards)}, 가능 {len(available_cards)}, 추천 {len(recommended_cards)}")
        
        return CustomerCardAnalysis(
            customer_name=customer_name,
            owned_cards=owned_cards,
            available_cards=available_cards,
            recommended_cards=recommended_cards,
            total_summary={
                "owned": len(owned_cards),
                "available": len(available_cards),
                "recommended": len(recommended_cards)
            }
        )
    
    def _read_owned_cards_from_txt(self, customer_name: str) -> List[CardInfo]:
        """txt 파일에서 보유 카드 정보 읽기"""
        customer_file_path = os.path.join(self.s3_common_path, f"{customer_name}_personal.txt")
        if not os.path.exists(customer_file_path):
            customer_file_path = os.path.join(self.s3_common_path, "kim_pesonal.txt")
        
        owned_cards = []
        if os.path.exists(customer_file_path):
            try:
                with open(customer_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if '보유 카드 현황' in content:
                    owned_section = content.split('보유 카드 현황')[1]
                    if '미보유 카드' in owned_section or '## 고객 특이사항' in owned_section:
                        for delimiter in ['미보유 카드', '## 고객 특이사항']:
                            if delimiter in owned_section:
                                owned_section = owned_section.split(delimiter)[0]
                                break
                    
                    # 카드 정보 동적 파싱
                    lines = owned_section.split('\n')
                    card_patterns = {
                        '우리카드': ('우리카드', '우리은행'),
                        '하나카드': ('하나카드', '하나은행'), 
                        '농협카드': ('NH농협카드', '농협은행'),
                        'NH농협카드': ('NH농협카드', '농협은행'),
                        '신한카드': ('신한카드', '신한은행'),
                        'KB국민카드': ('KB국민카드', 'KB국민은행'),
                        '국민카드': ('KB국민카드', 'KB국민은행')
                    }
                    
                    for line in lines:
                        # 번호나 하이픈이 있는 라인에서 카드명 찾기
                        if any(marker in line for marker in ['1.', '2.', '3.', '4.', '5.', '-']):
                            for pattern, (card_name, bank_name) in card_patterns.items():
                                if pattern in line:
                                    owned_cards.append(CardInfo(
                                        name=card_name,
                                        bank=bank_name,
                                        status="보유중",
                                        benefits=["신용카드"],
                                        issue_date=self._extract_issue_date(line)
                                    ))
                                    break
                            
            except Exception as e:
                print(f"❌ txt 파일 읽기 오류: {e}")
        
        return owned_cards
    
    def _extract_cards_from_vectordb(self, chunking_type: str) -> Tuple[List[str], Dict[str, str]]:
        """벡터DB에서 전체 카드 목록과 이미지 정보 추출"""
        try:
            # 카드 목록 검색 (일반적인 쿼리 사용)
            search_queries = [
                "회원은행별 카드발급안내",
                "BC카드 발급 회원은행 카드사",
                "카드발급 절차 회원은행"
            ]
            
            all_cards = set()
            card_images = {}
            
            # 1. 카드명 추출
            for query in search_queries:
                results = self.vectorstore_manager.similarity_search_with_score(query, chunking_type, k=10)
                
                for doc, score in results:
                    content = doc.page_content
                    
                    # 카드명 패턴 추출
                    card_patterns = [
                        r'우리카드', r'하나카드', r'NH농협카드', r'농협카드',
                        r'SC제일은행', r'IBK기업은행', r'KB국민카드', r'국민카드',
                        r'DGB대구은행', r'BNK부산은행', r'BNK경남은행',
                        r'씨티은행', r'신한카드', r'BC바로카드', r'BC카드',
                        r'롯데카드', r'삼성카드', r'현대카드'
                    ]
                    
                    for pattern in card_patterns:
                        if re.search(pattern, content):
                            all_cards.add(pattern.replace(r'', ''))
            
            # 2. 이미지 정보 추출 (s3-chunking인 경우만, ChromaDB 직접 접근)
            if chunking_type == "custom":
                card_images = self._extract_card_images_directly()
                
                # 실제 MD 파일에 있는 카드만 사용 (이미지가 있는 카드만)
                print(f"  📋 벡터DB 텍스트 검색: {len(all_cards)}개 카드")
                print(f"  📋 MD 파일 이미지: {len(card_images)}개 카드")
                
                # 이미지가 있는 카드만 최종 목록에 포함
                available_image_cards = set(card_images.keys())
                all_cards = available_image_cards  # MD 파일 기준으로 대체
                print(f"  ✅ 최종 사용: {len(all_cards)}개 카드 (이미지 기준)")
                                
            return list(all_cards), card_images
            
        except Exception as e:
            print(f"❌ 벡터DB 검색 오류: {e}")
            return [], {}
    
    def _extract_card_images_directly(self) -> Dict[str, str]:
        """ChromaDB에서 직접 카드 이미지 추출"""
        try:
            import chromadb
            client = chromadb.PersistentClient(path='/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/rag-qa-system/data/vectordb')
            
            # 컬렉션 존재 확인
            collections = client.list_collections()
            collection_names = [col.name for col in collections]
            
            if 'custom_chunks' not in collection_names:
                print(f"  ⚠️ custom_chunks 컬렉션이 존재하지 않음 (사용 가능: {collection_names})")
                return {}
            
            collection = client.get_collection('custom_chunks')
            
            # 모든 문서 가져오기
            all_docs = collection.get(include=['documents'])
            card_images = {}
            
            # 카드 이미지 특정 번호가 포함된 청크 찾기
            for i, doc in enumerate(all_docs['documents']):
                if any(num in doc for num in ['014.gif', '016.gif', '017.gif', '018.gif', '019.gif']):
                    print(f"  🎯 카드 이미지 청크 발견 (인덱스: {i})")
                    
                    # 관대한 패턴으로 이미지 추출
                    image_matches = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', doc)
                    for alt_text, img_path in image_matches:
                        # 카드 관련 이미지만 필터링
                        if (any(card in alt_text for card in ['카드', '은행']) or 
                            any(num in img_path for num in ['014', '016', '017', '018', '019', '020', '021', '022', '023', '024', '025'])):
                            normalized_name = self._normalize_card_name(alt_text)
                            if normalized_name:
                                card_images[normalized_name] = img_path
                                print(f"    → {normalized_name}: {img_path}")
            
            print(f"  ✅ 총 {len(card_images)}개 카드 이미지 추출 완료")
            return card_images
            
        except Exception as e:
            print(f"❌ 직접 이미지 추출 오류: {e}")
            return {}
    
    def _normalize_card_name(self, alt_text: str) -> Optional[str]:
        """이미지 alt 텍스트에서 카드명 추출 및 정규화"""
        card_mappings = {
            # MD 파일의 정확한 alt 텍스트 기준으로 매핑
            '우리카드': '우리카드',
            'Standard Chartered SC제일은행': 'SC제일은행',  # MD 파일의 정확한 텍스트
            '하나카드': '하나카드', 
            'NH농협카드': 'NH농협카드',
            '농협카드': 'NH농협카드',
            'IBK기업은행': 'IBK기업은행',
            'KB국민카드': 'KB국민카드',
            '국민카드': 'KB국민카드',
            'DGB대구은행': 'DGB대구은행',
            'BNK부산은행': 'BNK부산은행',
            'BNK경남은행': 'BNK경남은행',
            'citi은행': '씨티은행',  # MD 파일의 정확한 텍스트
            '씨티은행': '씨티은행',
            '신한카드': '신한카드',
            'BC 바로카드': 'BC바로카드'  # MD 파일에는 공백 포함
        }
        
        for key, value in card_mappings.items():
            if key in alt_text:
                return value
        return None
    
    def _find_card_image(self, card_name: str, card_images: Dict[str, str]) -> Optional[str]:
        """카드명에 해당하는 이미지 경로 찾기"""
        # 1. 직접 매칭
        if card_name in card_images:
            return card_images[card_name]
        
        # 2. 특별한 매칭 규칙 적용 
        special_mappings = {
            'BC카드': None,  # BC카드는 MD 파일에 이미지가 없음
            'BC바로카드': 'BC바로카드',  # MD에서는 'BC 바로카드'
            'SC제일은행': 'SC제일은행',  # MD에서는 'Standard Chartered SC제일은행'
            '씨티은행': '씨티은행',      # MD에서는 'citi은행'
            # '국민카드': 'KB국민카드'   # 중복 방지를 위해 제거 - KB국민카드가 우선
        }
        
        if card_name in special_mappings:
            mapped_name = special_mappings[card_name]
            if mapped_name and mapped_name in card_images:
                return card_images[mapped_name]
            elif mapped_name is None:
                return None  # 해당 카드는 이미지가 없음
        
        # 3. 부분 매칭 (키워드 기반)
        for image_card_name, image_path in card_images.items():
            if card_name in image_card_name or image_card_name in card_name:
                return image_path
        
        # 4. 더 관대한 매칭
        if '바로카드' in card_name:
            for image_card_name, image_path in card_images.items():
                if 'BC' in image_card_name and '바로' in image_card_name:
                    return image_path
                    
        return None
    
    def _extract_issue_date(self, line: str) -> Optional[str]:
        """라인에서 발급일 추출"""
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        match = re.search(date_pattern, line)
        return match.group() if match else None
    
    def format_analysis_response(self, analysis: CustomerCardAnalysis) -> str:
        """분석 결과를 텍스트로 포맷팅"""
        response = f"## {analysis.customer_name} 고객 카드 분석 결과\n\n"
        
        # 보유 카드
        response += "### 현재 보유 중인 카드\n"
        if analysis.owned_cards:
            for card in analysis.owned_cards:
                response += f"- ✅ {card.name}"
                if card.issue_date:
                    response += f" (발급일: {card.issue_date})"
                response += f" - {card.status}\n"
        else:
            response += "- 보유하신 카드가 없습니다.\n"
        
        # 추천 카드
        response += "\n### 발급 추천 카드\n"
        if analysis.recommended_cards:
            for card in analysis.recommended_cards:
                response += f"- ⭐ {card.name}"
                if card.recommendation_reason:
                    response += f" - {card.recommendation_reason}"
                response += "\n"
        
        # 발급 가능 카드
        response += "\n### 발급 가능한 카드\n"
        if analysis.available_cards:
            for card in analysis.available_cards:
                response += f"- 🆕 {card.name} - {card.status}\n"
        
        return response