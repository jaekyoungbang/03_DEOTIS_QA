"""
고급 청킹 전략 모음
- 의미론적 청킹 (Semantic Chunking)
- 질문 유형별 맞춤 청킹
- 중요도 기반 청킹
- 하이브리드 청킹 전략
"""

import re
import json
from typing import List, Dict, Tuple, Optional, Set
from langchain.schema import Document
from dataclasses import dataclass
import hashlib
from collections import Counter

@dataclass
class ChunkQuality:
    """청크 품질 평가"""
    completeness: float  # 완성도 (문장 완전성)
    coherence: float     # 일관성 (주제 일관성)
    information_density: float  # 정보 밀도
    importance_score: float     # 중요도 점수
    overall_score: float        # 전체 점수

class AdvancedChunkingStrategies:
    """고급 청킹 전략 클래스"""
    
    def __init__(self, base_chunk_size: int = 1500, overlap_ratio: float = 0.15):
        self.base_chunk_size = base_chunk_size
        self.overlap_ratio = overlap_ratio
        
        # 핵심 키워드 (가중치 포함)
        self.important_keywords = {
            # 개인화 관련 (최고 가중치)
            '김명정': 5.0, '보유카드': 4.5, '발급가능': 4.5, '현재보유': 4.5,
            '신규발급': 4.0, '추가발급': 4.0, '고객': 2.5, '개인': 2.0,
            
            # 카드 발급 관련 (높은 가중치)
            '카드발급': 3.5, '신청': 3.0, '절차': 3.0, '구비서류': 2.5,
            'BC카드': 3.5, '회원은행': 2.5, '발급기준': 3.0,
            
            # 카드 상태 관련
            '보유중': 4.0, '소지': 3.5, '이용중': 3.5, '신규': 3.0,
            '기존': 2.5, '현재': 2.5,
            
            # 고객 서비스 관련
            '민원': 2.0, '접수': 2.0, '상담': 1.5, '고객센터': 2.0,
            '문의': 1.5, '처리': 1.5,
            
            # 금융 용어
            '연회비': 2.0, '이용한도': 2.0, '결제': 1.8, '대출': 1.8,
            '신용': 1.8, '할부': 1.5, '포인트': 1.5,
            
            # 이미지 관련
            '이미지': 1.5, 'gif': 1.5, '그림': 1.5,
            
            # 프로세스 관련
            '단계': 2.0, 'STEP': 2.0, '방법': 1.8, '안내': 1.8
        }
        
        # 질문 유형별 키워드 패턴
        self.question_patterns = {
            'personal_card_status': ['김명정', '보유카드', '현재보유', '보유중', '발급가능', '신규발급', '추가발급'],
            'card_application': ['발급', '신청', '카드', '어떻게', '방법'],
            'customer_service': ['민원', '문의', '상담', '연락처', '고객센터'],
            'fees_costs': ['연회비', '수수료', '비용', '얼마', '요금'],
            'procedures': ['절차', '단계', '과정', '순서', 'STEP'],
            'personal_info': ['김명정', '고객', '개인', '내', '나'],
            'card_features': ['혜택', '서비스', '기능', '특징', '포인트'],
            'eligibility': ['자격', '조건', '기준', '대상', '가능'],
            'card_ownership': ['소지', '이용중', '기존카드', '현재카드', '보유현황']
        }
    
    def semantic_chunking(self, content: str, metadata: Dict) -> List[Document]:
        """의미론적 청킹 - 문맥과 의미 단위로 분할"""
        documents = []
        
        # 1. 문서를 의미 단위로 분할
        semantic_sections = self._extract_semantic_sections(content)
        
        # 2. 각 섹션의 중요도 계산
        for idx, section in enumerate(semantic_sections):
            importance_score = self._calculate_importance_score(section['content'])
            
            # 중요도에 따른 청크 크기 조정
            adjusted_chunk_size = self._adjust_chunk_size_by_importance(
                self.base_chunk_size, importance_score
            )
            
            # 3. 적응적 청킹 적용
            chunks = self._adaptive_chunking(section['content'], adjusted_chunk_size)
            
            for chunk_idx, chunk_content in enumerate(chunks):
                quality = self._evaluate_chunk_quality(chunk_content)
                
                doc = Document(
                    page_content=chunk_content,
                    metadata={
                        **metadata,
                        'chunking_strategy': 'semantic',
                        'section_title': section['title'],
                        'section_type': section['type'],
                        'importance_score': importance_score,
                        'chunk_quality': quality.overall_score,
                        'chunk_completeness': quality.completeness,
                        'information_density': quality.information_density,
                        'semantic_section_id': idx,
                        'chunk_in_section_id': chunk_idx,
                        'adjusted_chunk_size': adjusted_chunk_size
                    }
                )
                documents.append(doc)
        
        return documents
    
    def question_aware_chunking(self, content: str, metadata: Dict) -> List[Document]:
        """질문 유형 인식 청킹 - 자주 묻는 질문 패턴에 최적화"""
        documents = []
        
        # 1. 문서 내 질문 유형 식별
        detected_patterns = self._detect_question_patterns(content)
        
        # 2. 패턴별 특화 청킹
        sections = self._split_by_question_patterns(content, detected_patterns)
        
        for idx, section in enumerate(sections):
            pattern_type = section['pattern_type']
            
            # 질문 유형별 청킹 전략 적용
            chunks = self._apply_pattern_specific_chunking(
                section['content'], pattern_type
            )
            
            for chunk_idx, chunk_content in enumerate(chunks):
                doc = Document(
                    page_content=chunk_content,
                    metadata={
                        **metadata,
                        'chunking_strategy': 'question_aware',
                        'pattern_type': pattern_type,
                        'pattern_confidence': section['confidence'],
                        'section_id': idx,
                        'chunk_id': chunk_idx,
                        'optimized_for_questions': True,
                        'question_keywords': section['keywords']
                    }
                )
                documents.append(doc)
        
        return documents
    
    def hierarchical_chunking(self, content: str, metadata: Dict) -> List[Document]:
        """계층적 청킹 - 문서 구조를 활용한 다층 청킹"""
        documents = []
        
        # 1. 문서 계층 구조 분석
        hierarchy = self._analyze_document_hierarchy(content)
        
        # 2. 각 계층별로 다른 청킹 전략 적용
        for level, sections in hierarchy.items():
            for section in sections:
                # 계층 레벨별 청크 크기 조정
                level_chunk_size = self._get_level_chunk_size(level)
                
                chunks = self._hierarchical_split(
                    section['content'], level_chunk_size, level
                )
                
                for chunk_idx, chunk_content in enumerate(chunks):
                    doc = Document(
                        page_content=chunk_content,
                        metadata={
                            **metadata,
                            'chunking_strategy': 'hierarchical',
                            'hierarchy_level': level,
                            'section_path': section['path'],
                            'parent_section': section.get('parent', ''),
                            'child_sections': section.get('children', []),
                            'level_chunk_size': level_chunk_size,
                            'hierarchical_index': f"{level}-{section['id']}-{chunk_idx}"
                        }
                    )
                    documents.append(doc)
        
        return documents
    
    def hybrid_chunking(self, content: str, metadata: Dict) -> List[Document]:
        """하이브리드 청킹 - 여러 전략을 조합"""
        # 모든 전략 적용
        semantic_docs = self.semantic_chunking(content, metadata)
        question_aware_docs = self.question_aware_chunking(content, metadata)
        hierarchical_docs = self.hierarchical_chunking(content, metadata)
        
        # 중복 제거 및 최적 조합
        combined_docs = self._combine_and_deduplicate([
            semantic_docs, question_aware_docs, hierarchical_docs
        ])
        
        # 최종 품질 평가 및 필터링
        quality_filtered_docs = self._filter_by_quality(combined_docs)
        
        return quality_filtered_docs
    
    def _extract_semantic_sections(self, content: str) -> List[Dict]:
        """의미 단위 섹션 추출"""
        sections = []
        
        # 헤더 기반 분할
        header_pattern = r'^(#{1,6})\s+(.+)$'
        lines = content.split('\n')
        current_section = {'title': 'Introduction', 'content': '', 'type': 'intro', 'level': 0}
        
        for line in lines:
            header_match = re.match(header_pattern, line)
            if header_match:
                # 이전 섹션 저장
                if current_section['content'].strip():
                    sections.append(current_section)
                
                # 새 섹션 시작
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                section_type = self._classify_section_type(title)
                
                current_section = {
                    'title': title,
                    'content': line + '\n',
                    'type': section_type,
                    'level': level
                }
            else:
                current_section['content'] += line + '\n'
        
        # 마지막 섹션 추가
        if current_section['content'].strip():
            sections.append(current_section)
        
        return sections
    
    def _classify_section_type(self, title: str) -> str:
        """섹션 제목을 기반으로 타입 분류"""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['발급', '신청', '절차']):
            return 'procedure'
        elif any(word in title_lower for word in ['문의', '민원', '상담']):
            return 'customer_service'
        elif any(word in title_lower for word in ['연회비', '수수료', '비용']):
            return 'fees'
        elif any(word in title_lower for word in ['안내', '설명', '개요']):
            return 'information'
        elif any(word in title_lower for word in ['이미지', '그림', '도표']):
            return 'visual'
        else:
            return 'general'
    
    def _calculate_importance_score(self, content: str) -> float:
        """내용의 중요도 점수 계산"""
        score = 0.0
        content_lower = content.lower()
        
        # 키워드 기반 점수
        for keyword, weight in self.important_keywords.items():
            count = content_lower.count(keyword.lower())
            score += count * weight
        
        # 구조적 특징 점수
        if '단계' in content or 'STEP' in content or '절차' in content:
            score += 2.0  # 절차적 정보는 중요
        
        if '![' in content:  # 이미지 포함
            score += 1.5
        
        if '|' in content and '-' in content:  # 테이블 포함
            score += 1.0
        
        # 길이 기반 정규화
        normalized_score = score / max(len(content.split()), 1) * 100
        
        return min(normalized_score, 10.0)  # 최대 10점으로 제한
    
    def _adjust_chunk_size_by_importance(self, base_size: int, importance: float) -> int:
        """중요도에 따른 청크 크기 조정"""
        if importance >= 7.0:  # 매우 중요
            return int(base_size * 0.7)  # 작게 나누어 정밀하게
        elif importance >= 4.0:  # 중요
            return base_size
        else:  # 일반
            return int(base_size * 1.3)  # 크게 나누어 효율성 높임
    
    def _adaptive_chunking(self, content: str, target_size: int) -> List[str]:
        """적응적 청킹 - 문장과 단락 경계 고려"""
        chunks = []
        
        # 문장 단위로 분할
        sentences = re.split(r'[.!?]\s+', content)
        current_chunk = ""
        
        for sentence in sentences:
            # 문장을 추가했을 때 크기 확인
            test_chunk = current_chunk + sentence + '. '
            
            if len(test_chunk) <= target_size:
                current_chunk = test_chunk
            else:
                # 현재 청크 저장
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                # 새 청크 시작
                current_chunk = sentence + '. '
        
        # 마지막 청크 추가
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _detect_question_patterns(self, content: str) -> Dict[str, float]:
        """질문 패턴 감지"""
        detected = {}
        content_lower = content.lower()
        
        for pattern_name, keywords in self.question_patterns.items():
            matches = sum(1 for keyword in keywords if keyword in content_lower)
            confidence = matches / len(keywords)
            
            if confidence > 0.3:  # 30% 이상 매치시 패턴으로 인식
                detected[pattern_name] = confidence
        
        return detected
    
    def _split_by_question_patterns(self, content: str, patterns: Dict) -> List[Dict]:
        """패턴별 섹션 분할"""
        sections = []
        
        # 가장 강한 패턴으로 전체 분류
        if patterns:
            best_pattern = max(patterns.items(), key=lambda x: x[1])
            sections.append({
                'content': content,
                'pattern_type': best_pattern[0],
                'confidence': best_pattern[1],
                'keywords': self.question_patterns[best_pattern[0]]
            })
        else:
            sections.append({
                'content': content,
                'pattern_type': 'general',
                'confidence': 0.0,
                'keywords': []
            })
        
        return sections
    
    def _apply_pattern_specific_chunking(self, content: str, pattern_type: str) -> List[str]:
        """패턴별 특화 청킹"""
        if pattern_type == 'personal_card_status':
            # 개인 카드 상태는 개인화 정보를 우선하여 세밀하게
            return self._personal_card_chunking(content)
        elif pattern_type == 'procedures':
            # 절차형은 단계별로 세밀하게
            return self._step_based_chunking(content)
        elif pattern_type == 'customer_service':
            # 고객서비스는 문의별로
            return self._service_based_chunking(content)
        elif pattern_type == 'fees_costs':
            # 비용정보는 항목별로
            return self._item_based_chunking(content)
        elif pattern_type == 'card_ownership':
            # 카드 보유 현황은 카드별로 분리
            return self._ownership_based_chunking(content)
        else:
            # 기본 청킹
            return self._adaptive_chunking(content, self.base_chunk_size)
    
    def _step_based_chunking(self, content: str) -> List[str]:
        """단계 기반 청킹"""
        # 단계 표시자로 분할
        step_pattern = r'(단계\s*\d+|STEP\s*\d+|\d+\.\s|\d+\))'
        chunks = re.split(step_pattern, content)
        
        result = []
        current_chunk = ""
        
        for i, chunk in enumerate(chunks):
            if re.match(step_pattern, chunk):
                if current_chunk:
                    result.append(current_chunk.strip())
                current_chunk = chunk
            else:
                current_chunk += chunk
        
        if current_chunk:
            result.append(current_chunk.strip())
        
        return [c for c in result if c.strip()]
    
    def _service_based_chunking(self, content: str) -> List[str]:
        """서비스 기반 청킹"""
        # 연락처, 방법별로 분할
        service_markers = ['전화', '팩스', 'FAX', '인터넷', '방문', '우편']
        
        chunks = [content]  # 기본적으로는 전체 유지
        for marker in service_markers:
            new_chunks = []
            for chunk in chunks:
                parts = chunk.split(marker)
                if len(parts) > 1:
                    for i, part in enumerate(parts):
                        if i > 0:
                            part = marker + part
                        new_chunks.append(part)
                else:
                    new_chunks.append(chunk)
            chunks = new_chunks
        
        return [c.strip() for c in chunks if c.strip()]
    
    def _item_based_chunking(self, content: str) -> List[str]:
        """항목 기반 청킹"""
        # 리스트 항목별로 분할
        item_pattern = r'(?:^|\n)(?:[\-\*\+]|\d+\.|\w+\.)\s+'
        chunks = re.split(item_pattern, content)
        return [c.strip() for c in chunks if c.strip()]
    
    def _personal_card_chunking(self, content: str) -> List[str]:
        """개인 카드 상태 기반 청킹 - 보유/발급가능 구분"""
        chunks = []
        
        # 보유 카드와 발급 가능 카드를 명확히 구분
        card_sections = {
            'current': [],  # 현재 보유
            'available': [],  # 발급 가능
            'general': []   # 일반 정보
        }
        
        lines = content.split('\n')
        current_section = 'general'
        current_content = []
        
        for line in lines:
            line_lower = line.lower()
            
            # 보유 카드 섹션 감지
            if any(keyword in line_lower for keyword in ['현재 보유', '보유 중인', '소지', '이용중']):
                if current_content:
                    card_sections[current_section].extend(current_content)
                current_section = 'current'
                current_content = [line]
                
            # 발급 가능 카드 섹션 감지  
            elif any(keyword in line_lower for keyword in ['발급 가능', '신규 발급', '추가 발급', '신청 가능']):
                if current_content:
                    card_sections[current_section].extend(current_content)
                current_section = 'available'
                current_content = [line]
                
            else:
                current_content.append(line)
        
        # 마지막 섹션 저장
        if current_content:
            card_sections[current_section].extend(current_content)
        
        # 각 섹션별로 청크 생성
        for section_type, lines in card_sections.items():
            if lines:
                section_content = '\n'.join(lines)
                if section_content.strip():
                    # 섹션 타입에 따라 청크 크기 조정
                    chunk_size = int(self.base_chunk_size * 0.6) if section_type in ['current', 'available'] else self.base_chunk_size
                    section_chunks = self._adaptive_chunking(section_content, chunk_size)
                    chunks.extend(section_chunks)
        
        return chunks if chunks else [content]
    
    def _ownership_based_chunking(self, content: str) -> List[str]:
        """카드 보유 현황 기반 청킹"""
        # 카드 브랜드별로 분할
        card_brands = ['BC카드', 'bc카드', '비씨카드', '우리카드', '하나카드', 'NH농협카드', '현대카드', '신한카드']
        
        chunks = []
        current_chunk = ""
        
        lines = content.split('\n')
        for line in lines:
            # 새로운 카드 브랜드 시작 감지
            if any(brand in line for brand in card_brands) and current_chunk.strip():
                chunks.append(current_chunk.strip())
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'
        
        # 마지막 청크 추가
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [content]
    
    def _analyze_document_hierarchy(self, content: str) -> Dict:
        """문서 계층 구조 분석"""
        hierarchy = {1: [], 2: [], 3: [], 4: []}
        
        lines = content.split('\n')
        current_sections = {1: None, 2: None, 3: None, 4: None}
        section_id = 0
        
        for line in lines:
            header_match = re.match(r'^(#{1,4})\s+(.+)$', line)
            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2)
                
                # 상위 레벨 섹션 정보 가져오기
                parent_path = []
                for i in range(1, level):
                    if current_sections[i]:
                        parent_path.append(current_sections[i]['title'])
                
                section_info = {
                    'id': section_id,
                    'title': title,
                    'content': line + '\n',
                    'path': ' > '.join(parent_path + [title]),
                    'parent': current_sections[level-1]['title'] if level > 1 and current_sections[level-1] else '',
                    'children': []
                }
                
                hierarchy[level].append(section_info)
                current_sections[level] = section_info
                
                # 하위 레벨 초기화
                for i in range(level + 1, 5):
                    current_sections[i] = None
                
                section_id += 1
            else:
                # 현재 활성 섹션에 내용 추가
                for level in range(4, 0, -1):
                    if current_sections[level]:
                        current_sections[level]['content'] += line + '\n'
                        break
        
        return hierarchy
    
    def _get_level_chunk_size(self, level: int) -> int:
        """레벨별 청크 크기 결정"""
        size_map = {
            1: int(self.base_chunk_size * 1.5),  # 대제목: 더 큰 청크
            2: self.base_chunk_size,              # 중제목: 기본 크기
            3: int(self.base_chunk_size * 0.8),   # 소제목: 작은 청크
            4: int(self.base_chunk_size * 0.6)    # 세부항목: 더 작은 청크
        }
        return size_map.get(level, self.base_chunk_size)
    
    def _hierarchical_split(self, content: str, chunk_size: int, level: int) -> List[str]:
        """계층별 분할"""
        if level <= 2:
            # 상위 레벨은 단락 단위로
            paragraphs = content.split('\n\n')
            return self._combine_paragraphs(paragraphs, chunk_size)
        else:
            # 하위 레벨은 문장 단위로
            return self._adaptive_chunking(content, chunk_size)
    
    def _combine_paragraphs(self, paragraphs: List[str], target_size: int) -> List[str]:
        """단락 조합"""
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            test_chunk = current_chunk + '\n\n' + para if current_chunk else para
            
            if len(test_chunk) <= target_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _evaluate_chunk_quality(self, content: str) -> ChunkQuality:
        """청크 품질 평가"""
        # 완성도 평가 (문장 완전성)
        sentence_endings = content.count('.') + content.count('!') + content.count('?')
        sentences = len(re.split(r'[.!?]', content))
        completeness = sentence_endings / max(sentences, 1)
        
        # 일관성 평가 (주제 일관성 - 키워드 분산도)
        words = content.lower().split()
        word_freq = Counter(words)
        coherence = len([w for w, c in word_freq.items() if c > 1]) / max(len(word_freq), 1)
        
        # 정보 밀도 (중요 키워드 밀도)
        important_words = sum(1 for word in words if word in [k.lower() for k in self.important_keywords])
        information_density = important_words / max(len(words), 1)
        
        # 중요도 점수
        importance_score = self._calculate_importance_score(content) / 10.0
        
        # 전체 점수
        overall_score = (completeness * 0.3 + coherence * 0.2 + 
                        information_density * 0.3 + importance_score * 0.2)
        
        return ChunkQuality(
            completeness=completeness,
            coherence=coherence,
            information_density=information_density,
            importance_score=importance_score,
            overall_score=overall_score
        )
    
    def _combine_and_deduplicate(self, doc_lists: List[List[Document]]) -> List[Document]:
        """문서 조합 및 중복 제거"""
        all_docs = []
        seen_contents = set()
        
        for doc_list in doc_lists:
            for doc in doc_list:
                # 내용 해시로 중복 확인
                content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
                if content_hash not in seen_contents:
                    seen_contents.add(content_hash)
                    all_docs.append(doc)
        
        return all_docs
    
    def _filter_by_quality(self, documents: List[Document], min_quality: float = 0.3) -> List[Document]:
        """품질 기준으로 문서 필터링"""
        filtered = []
        
        for doc in documents:
            quality_score = doc.metadata.get('chunk_quality', 0.0)
            if quality_score >= min_quality:
                filtered.append(doc)
        
        return filtered