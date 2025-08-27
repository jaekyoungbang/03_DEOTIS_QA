import re
import os
from typing import Dict, List, Tuple, Optional

class CardManager:
    """카드 이미지 관리 및 사용자 보유 카드 비교 클래스"""
    
    def __init__(self, s3_chunking_path: str = '/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3-chunking'):
        self.s3_chunking_path = s3_chunking_path
        self.card_image_pattern = r'!\[([^\]]*)\]\((Aspose\.Words\.[^)]+\.gif)\)'
        
    def extract_card_images_from_md(self, md_file_path: str) -> List[Dict[str, str]]:
        """MD 파일에서 카드 이미지 정보 추출"""
        try:
            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 마크다운 이미지 패턴 매칭
            matches = re.findall(self.card_image_pattern, content)
            
            card_images = []
            for alt_text, image_path in matches:
                # 이미지 파일이 실제로 존재하는지 확인
                full_image_path = os.path.join(self.s3_chunking_path, image_path)
                if os.path.exists(full_image_path):
                    card_info = {
                        'alt_text': alt_text.strip(),
                        'image_path': image_path,
                        'card_name': self._extract_card_name(alt_text),
                        'full_path': full_image_path
                    }
                    card_images.append(card_info)
                    print(f"✅ 카드 발견: {alt_text} -> {image_path}")
                else:
                    print(f"❌ 이미지 파일 없음: {image_path}")
            
            return card_images
            
        except Exception as e:
            print(f"MD 파일 파싱 오류: {e}")
            return []
    
    def _extract_card_name(self, alt_text: str) -> str:
        """alt 텍스트에서 카드명 추출"""
        if not alt_text:
            return ''
            
        # 카드명 패턴 매칭
        card_patterns = {
            '우리카드': ['우리카드', 'woori'],
            '하나카드': ['하나카드', 'hana'], 
            '농협카드': ['NH농협카드', '농협', 'NH'],
            'SC제일은행': ['Standard Chartered', 'SC제일은행', 'SC'],
            '기업은행': ['IBK기업은행', 'IBK', '기업은행'],
            '국민카드': ['KB국민카드', 'KB', '국민'],
            '대구은행': ['DGB대구은행', 'DGB', '대구'],
            '부산은행': ['BNK부산은행', 'BNK부산', '부산'],
            '경남은행': ['BNK경남은행', 'BNK경남', '경남'],
            '씨티은행': ['citi은행', 'citi', 'Citi'],
            '신한카드': ['신한카드', 'shinhan', 'Shinhan'],
            'BC카드': ['BC 바로카드', 'BC', 'bc', '바로카드']
        }
        
        for card_name, patterns in card_patterns.items():
            if any(pattern in alt_text for pattern in patterns):
                return card_name
                
        return alt_text  # 매칭되지 않으면 원본 반환
    
    def load_user_profile(self, user_name: str) -> Dict[str, List[str]]:
        """사용자 프로필에서 보유 카드 정보 로드"""
        try:
            profile_path = os.path.join(self.s3_chunking_path, f'{user_name}_개인정보.txt')
            if not os.path.exists(profile_path):
                print(f"❌ 사용자 프로필 파일 없음: {profile_path}")
                return {'owned': [], 'not_owned': []}
            
            with open(profile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 보유 카드 추출 (간단한 패턴 매칭)
            owned_cards = []
            lines = content.split('\n')
            
            in_owned_section = False
            for line in lines:
                line = line.strip()
                if '보유 카드' in line:
                    in_owned_section = True
                    continue
                elif '미보유 카드' in line:
                    in_owned_section = False
                    continue
                    
                if in_owned_section and line:
                    # "1. 우리카드" 형태에서 카드명 추출
                    if any(char.isdigit() for char in line[:3]):  # 숫자가 포함된 경우
                        card_name = re.sub(r'^\d+\.\s*', '', line)  # 번호 제거
                        if card_name and '발급일' not in card_name and '카드종류' not in card_name and '상태' not in card_name:
                            owned_cards.append(card_name.strip())
            
            print(f"📋 {user_name} 보유 카드: {owned_cards}")
            return {'owned': owned_cards}
            
        except Exception as e:
            print(f"사용자 프로필 로드 오류: {e}")
            return {'owned': []}
    
    def classify_cards_by_ownership(self, card_images: List[Dict], user_owned_cards: List[str]) -> Dict[str, List[Dict]]:
        """카드를 보유/미보유로 분류"""
        owned = []
        not_owned = []
        
        for card_info in card_images:
            card_name = card_info['card_name']
            alt_text = card_info['alt_text']
            
            # 보유 카드 여부 확인 (더 유연한 매칭)
            is_owned = False
            for owned_card in user_owned_cards:
                if (owned_card in card_name or 
                    owned_card in alt_text or
                    card_name in owned_card or
                    self._is_similar_card_name(owned_card, card_name)):
                    is_owned = True
                    break
            
            if is_owned:
                card_info['status'] = 'owned'
                owned.append(card_info)
                print(f"✅ 보유 카드: {card_name} ({alt_text})")
            else:
                card_info['status'] = 'not_owned'
                not_owned.append(card_info)
                print(f"⭐ 미보유 카드: {card_name} ({alt_text})")
        
        return {
            'owned': owned,
            'not_owned': not_owned,
            'total': len(card_images)
        }
    
    def _is_similar_card_name(self, user_card: str, extracted_card: str) -> bool:
        """카드명 유사성 검사"""
        # 간단한 유사성 검사 로직
        user_card_lower = user_card.lower()
        extracted_card_lower = extracted_card.lower()
        
        # 키워드 기반 매칭
        keyword_matches = {
            '우리': ['woori', '우리'],
            '하나': ['hana', '하나'],
            '농협': ['nh', '농협'],
            '국민': ['kb', '국민'],
            '신한': ['shinhan', '신한'],
            '기업': ['ibk', '기업'],
            '씨티': ['citi', '씨티']
        }
        
        for keyword, variants in keyword_matches.items():
            if keyword in user_card_lower:
                if any(variant in extracted_card_lower for variant in variants):
                    return True
        
        return False
    
    def generate_card_summary_html(self, classified_cards: Dict, user_name: str) -> str:
        """카드 분류 결과를 HTML로 생성"""
        owned = classified_cards['owned']
        not_owned = classified_cards['not_owned']
        
        html = f"""
## 📋 {user_name} 고객 카드 현황

### ✅ 현재 보유 카드 ({len(owned)}장)
"""
        
        for card in owned:
            html += f"""
![{card['alt_text']}]({card['image_path']})
**{card['alt_text']}** - ✅ 보유중

"""
        
        html += f"""
### ⭐ 추가 발급 가능 카드 ({len(not_owned)}장)
"""
        
        for card in not_owned:
            html += f"""
![{card['alt_text']}]({card['image_path']})  
**{card['alt_text']}** - ⭐ 발급 추천

"""
        
        html += f"""
---
**총 {classified_cards['total']}개 카드** | 보유: {len(owned)}장 | 미보유: {len(not_owned)}장
"""
        
        return html

def process_user_card_query(user_name: str, md_file_path: str) -> str:
    """사용자 카드 질의 처리 메인 함수"""
    card_manager = CardManager()
    
    # 1. MD 파일에서 카드 이미지 추출
    card_images = card_manager.extract_card_images_from_md(md_file_path)
    print(f"🔍 총 {len(card_images)}개 카드 이미지 발견")
    
    # 2. 사용자 보유 카드 정보 로드
    user_profile = card_manager.load_user_profile(user_name)
    owned_cards = user_profile['owned']
    
    # 3. 카드 분류
    classified_cards = card_manager.classify_cards_by_ownership(card_images, owned_cards)
    
    # 4. HTML 결과 생성
    result_html = card_manager.generate_card_summary_html(classified_cards, user_name)
    
    return result_html