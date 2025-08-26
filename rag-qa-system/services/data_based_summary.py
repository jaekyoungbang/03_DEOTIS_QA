from typing import List, Dict, Any, Optional
import time
from services.rag_chain import RAGChain

class DataBasedSummaryRAG(RAGChain):
    """데이터 기반 요약 모드 - 검색된 데이터만 활용"""
    
    def __init__(self):
        super().__init__()
        self.summary_mode = True
    
    def summarize_from_data(self, question: str, max_documents: int = 10) -> Dict[str, Any]:
        """검색된 데이터만을 기반으로 요약 생성"""
        start_time = time.time()
        
        try:
            # 1. 관련 문서 검색 (더 많은 문서 검색)
            search_results = self.vectorstore_manager.similarity_search_with_score(
                question, k=max_documents
            )
            
            if not search_results:
                return {
                    'summary': '관련 데이터를 찾을 수 없습니다.',
                    'source_count': 0,
                    'processing_time': time.time() - start_time,
                    'mode': 'data_only_summary',
                    'warning': '검색된 데이터가 없어 요약을 생성할 수 없습니다.'
                }
            
            # 2. 검색된 데이터 분석 및 그룹핑
            grouped_data = self._group_similar_content(search_results)
            
            # 3. 데이터 기반으로만 요약 생성
            summary_data = self._generate_data_summary(grouped_data, question)
            
            # 4. 응답 구성
            response = {
                'summary': summary_data['summary_text'],
                'data_sources': summary_data['sources'],
                'content_groups': summary_data['groups'],
                'source_count': len(search_results),
                'unique_sources': len(set([doc.metadata.get('source', '알 수 없음') 
                                         for doc, _ in search_results])),
                'processing_time': time.time() - start_time,
                'mode': 'data_only_summary',
                'similarity_range': {
                    'highest': search_results[0][1] if search_results else 0,
                    'lowest': search_results[-1][1] if search_results else 0
                },
                'data_disclaimer': '이 요약은 오직 검색된 문서 데이터만을 바탕으로 작성되었습니다.'
            }
            
            return response
            
        except Exception as e:
            return {
                'error': str(e),
                'summary': '요약 생성 중 오류가 발생했습니다.',
                'mode': 'data_only_summary'
            }
    
    def _group_similar_content(self, search_results: List[tuple]) -> List[Dict[str, Any]]:
        """유사한 내용끼리 그룹핑"""
        groups = []
        processed_indices = set()
        
        for i, (doc1, score1) in enumerate(search_results):
            if i in processed_indices:
                continue
                
            # 새 그룹 시작
            current_group = {
                'main_content': doc1.page_content,
                'main_source': doc1.metadata,
                'main_similarity': score1,
                'related_contents': [],
                'keywords': self._extract_content_keywords(doc1.page_content)
            }
            
            processed_indices.add(i)
            
            # 유사한 내용 찾기
            for j, (doc2, score2) in enumerate(search_results[i+1:], i+1):
                if j in processed_indices:
                    continue
                
                # 키워드 중복도로 유사성 판단
                similarity_ratio = self._calculate_content_similarity(
                    doc1.page_content, doc2.page_content
                )
                
                if similarity_ratio > 0.3:  # 30% 이상 유사하면 같은 그룹
                    current_group['related_contents'].append({
                        'content': doc2.page_content,
                        'source': doc2.metadata,
                        'similarity': score2,
                        'content_similarity': similarity_ratio
                    })
                    processed_indices.add(j)
            
            groups.append(current_group)
        
        # 중요도순 정렬 (메인 유사도 기준)
        groups.sort(key=lambda x: x['main_similarity'], reverse=True)
        
        return groups[:5]  # 상위 5개 그룹만
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """두 문서 내용 간의 유사도 계산 (간단한 키워드 기반)"""
        # 키워드 추출
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        # 공통 단어 비율
        common_words = words1.intersection(words2)
        total_words = words1.union(words2)
        
        if len(total_words) == 0:
            return 0.0
        
        return len(common_words) / len(total_words)
    
    def _extract_content_keywords(self, content: str) -> List[str]:
        """내용에서 주요 키워드 추출"""
        # 불용어 목록
        stopwords = {
            '있습니다', '됩니다', '입니다', '하여', '경우', '때문에', 
            '관련', '대해', '에서', '으로', '를', '을', '의', '이', '가',
            '은', '는', '에', '와', '과', '도', '만', '부터', '까지'
        }
        
        words = content.split()
        keywords = []
        
        for word in words:
            # 정리
            cleaned = word.strip('.,!?()[]{}":;')
            
            # 조건 확인
            if (len(cleaned) > 1 and 
                cleaned not in stopwords and 
                not cleaned.isdigit()):
                keywords.append(cleaned)
        
        # 빈도순 정렬 (간단한 구현)
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, freq in sorted_keywords[:10]]  # 상위 10개
    
    def _generate_data_summary(self, grouped_data: List[Dict], question: str) -> Dict[str, Any]:
        """그룹화된 데이터를 기반으로 요약 생성"""
        
        # 각 그룹별 핵심 내용 추출
        group_summaries = []
        all_sources = []
        
        for i, group in enumerate(grouped_data):
            main_content = group['main_content']
            keywords = group['keywords']
            
            # 그룹 요약 생성 (데이터만 활용)
            group_summary = self._create_group_summary(group, question)
            
            group_summaries.append({
                'group_index': i + 1,
                'summary': group_summary,
                'key_points': self._extract_key_points(main_content),
                'source_info': {
                    'main_source': group['main_source'].get('source', '알 수 없음'),
                    'similarity': group['main_similarity'],
                    'related_count': len(group['related_contents'])
                },
                'keywords': keywords[:5]  # 상위 5개 키워드
            })
            
            # 소스 정보 수집
            all_sources.append(group['main_source'])
            for related in group['related_contents']:
                all_sources.append(related['source'])
        
        # 전체 요약문 생성
        overall_summary = self._create_overall_summary(group_summaries, question)
        
        return {
            'summary_text': overall_summary,
            'groups': group_summaries,
            'sources': all_sources
        }
    
    def _create_group_summary(self, group: Dict, question: str) -> str:
        """각 그룹별 요약 생성 (데이터만 활용)"""
        main_content = group['main_content']
        keywords = group['keywords']
        
        # 질문과 관련된 핵심 문장 추출
        sentences = main_content.split('.')
        relevant_sentences = []
        
        question_keywords = set(question.split())
        
        for sentence in sentences[:10]:  # 처음 10개 문장만 분석
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
                
            # 질문 키워드나 그룹 키워드가 포함된 문장 우선
            sentence_words = set(sentence.split())
            
            if (question_keywords.intersection(sentence_words) or
                set(keywords[:3]).intersection(sentence_words)):
                relevant_sentences.append(sentence)
        
        # 관련 문장이 없으면 처음 3문장 사용
        if not relevant_sentences:
            relevant_sentences = [s.strip() for s in sentences[:3] if len(s.strip()) > 10]
        
        # 요약문 구성 (데이터만 활용)
        summary_parts = relevant_sentences[:3]  # 최대 3개 문장
        
        if group['related_contents']:
            summary_parts.append(f"(관련 문서 {len(group['related_contents'])}개에서 유사한 내용 확인)")
        
        return ' '.join(summary_parts)
    
    def _extract_key_points(self, content: str) -> List[str]:
        """문서에서 핵심 포인트 추출"""
        sentences = content.split('.')
        key_points = []
        
        # 특정 패턴을 포함한 문장을 핵심 포인트로 추출
        key_patterns = ['중요', '필수', '반드시', '주의', '참고', '단계', '방법', '절차']
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
                
            # 핵심 패턴 포함 여부 확인
            if any(pattern in sentence for pattern in key_patterns):
                key_points.append(sentence)
                
            # 숫자로 시작하는 문장 (순서나 단계)
            if sentence and sentence[0].isdigit():
                key_points.append(sentence)
        
        return key_points[:5]  # 최대 5개
    
    def _create_overall_summary(self, group_summaries: List[Dict], question: str) -> str:
        """전체 요약문 생성"""
        
        if not group_summaries:
            return "검색된 데이터가 없습니다."
        
        # 데이터 기반 요약 시작
        summary_parts = [
            f"검색된 {len(group_summaries)}개 그룹의 데이터를 기반으로 요약드립니다:"
        ]
        
        # 각 그룹별 핵심 내용
        for i, group in enumerate(group_summaries[:3], 1):  # 상위 3개 그룹만
            source_name = group['source_info']['main_source'].split('/')[-1] if '/' in group['source_info']['main_source'] else group['source_info']['main_source']
            similarity_percent = f"{group['source_info']['similarity']*100:.1f}%"
            
            group_text = f"{i}. {group['summary']} (출처: {source_name}, 유사도: {similarity_percent})"
            summary_parts.append(group_text)
        
        # 추가 정보가 있는 경우
        if len(group_summaries) > 3:
            summary_parts.append(f"외 {len(group_summaries)-3}개 관련 문서에서 추가 정보를 확인했습니다.")
        
        # 공통 키워드 추출
        all_keywords = []
        for group in group_summaries:
            all_keywords.extend(group['keywords'])
        
        # 빈도 계산
        keyword_freq = {}
        for keyword in all_keywords:
            keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
        
        common_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:3]
        
        if common_keywords:
            keyword_text = ', '.join([kw for kw, freq in common_keywords])
            summary_parts.append(f"주요 키워드: {keyword_text}")
        
        return '\n\n'.join(summary_parts)