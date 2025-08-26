from typing import List, Dict, Any
import time
from services.rag_chain import RAGChain

class SimilaritySuggestionRAG(RAGChain):
    """유사도 기반 추천 기능이 추가된 RAG 체인"""
    
    def __init__(self):
        super().__init__()
        self.similarity_threshold = 0.8  # 80% 기준
    
    def query_with_suggestions(self, question: str, use_memory: bool = False, threshold: float = None) -> Dict[str, Any]:
        """유사도 기반 추천을 포함한 쿼리"""
        start_time = time.time()
        threshold = threshold or self.similarity_threshold
        
        try:
            # 1. 기본 검색 수행
            search_results = self.vectorstore_manager.similarity_search_with_score(question, k=5)
            
            # 2. 유사도 분석
            top_similarity = search_results[0][1] if search_results else 0
            
            # 3. 기본 RAG 응답 생성
            basic_response = self.query(question, use_memory)
            
            # 4. 유사도가 80% 미만인 경우 추가 선택지 제공
            response = {
                'answer': basic_response['answer'],
                'similarity_search': basic_response['similarity_search'],
                'processing_time': basic_response['processing_time'],
                'model_used': basic_response['model_used'],
                '_from_cache': basic_response.get('_from_cache', False),
                'top_similarity': top_similarity,
                'suggestions': []
            }
            
            if top_similarity < threshold:
                response['low_confidence'] = True
                response['confidence_message'] = f"말씀하신 내용과 유사도가 {top_similarity*100:.1f}%입니다. 이런 내용이 있습니다. 말씀하신 내용이 맞을까요?"
                response['suggestions'] = self._generate_suggestions(search_results)
            else:
                response['low_confidence'] = False
            
            return response
            
        except Exception as e:
            return {
                'error': str(e),
                'answer': '죄송합니다. 처리 중 오류가 발생했습니다.',
                'suggestions': []
            }
    
    def _generate_suggestions(self, search_results: List[tuple]) -> List[Dict[str, Any]]:
        """검색 결과 기반으로 추천 선택지 생성"""
        suggestions = []
        
        # 상위 3개 결과를 선택지로 제공 (유사도 2, 3 포함)
        for i, (doc, score) in enumerate(search_results[:3]):
            # 문서 내용 요약 (첫 200자)
            content_preview = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            
            suggestion = {
                'id': f"suggestion_{i+1}",
                'title': self._extract_title(doc),
                'content_preview': content_preview,
                'similarity': score,
                'similarity_percent': f"{score*100:.1f}%",
                'metadata': doc.metadata,
                'suggested_query': self._generate_suggested_query(doc, i+1),
                'button_text': f"이건 어떠세요? ({score*100:.1f}%)"
            }
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _extract_title(self, doc) -> str:
        """문서에서 제목 추출"""
        # 메타데이터에서 제목 확인
        if 'title' in doc.metadata:
            return doc.metadata['title']
        
        if 'source' in doc.metadata:
            filename = doc.metadata['source'].split('/')[-1]
            return filename.replace('.pdf', '').replace('.docx', '')
        
        # 내용의 첫 줄을 제목으로 사용
        first_line = doc.page_content.split('\n')[0][:50]
        return first_line + "..." if len(first_line) == 50 else first_line
    
    def _generate_suggested_query(self, doc, index: int) -> str:
        """문서 기반 추천 질문 생성"""
        content = doc.page_content[:500]  # 처음 500자만 사용
        
        # 간단한 키워드 기반 질문 생성
        if '절차' in content or '방법' in content:
            return f"{self._extract_keywords(content)} 절차가 어떻게 되나요?"
        elif '요금' in content or '비용' in content or '수수료' in content:
            return f"{self._extract_keywords(content)} 요금이 얼마인가요?"
        elif '신청' in content or '등록' in content:
            return f"{self._extract_keywords(content)} 신청 방법을 알려주세요"
        else:
            return f"{self._extract_keywords(content)}에 대해 자세히 알려주세요"
    
    def _extract_keywords(self, text: str) -> str:
        """텍스트에서 주요 키워드 추출"""
        # 간단한 키워드 추출 (실제로는 NLP 라이브러리 사용 가능)
        common_words = {'입니다', '있습니다', '됩니다', '하여', '경우', '때문에', '관련', '대해', '에서'}
        
        words = text.split()[:10]  # 처음 10단어만
        keywords = []
        
        for word in words:
            cleaned = word.strip('.,!?()[]{}')
            if len(cleaned) > 1 and cleaned not in common_words:
                keywords.append(cleaned)
        
        return ' '.join(keywords[:3])  # 상위 3개 키워드
    
    def query_suggestion(self, suggestion_id: str, original_question: str) -> Dict[str, Any]:
        """추천 선택지 선택시 4곳에서 모두 재검색"""
        start_time = time.time()
        
        try:
            # 추천 ID를 기반으로 특정 문서 선택
            suggestion_index = int(suggestion_id.split('_')[1]) - 1
            
            # 1. 원본 검색 결과에서 선택된 문서 가져오기
            search_results = self.vectorstore_manager.similarity_search_with_score(original_question, k=10)
            
            if suggestion_index >= len(search_results):
                return {'error': '선택된 추천 항목을 찾을 수 없습니다.'}
            
            selected_doc = search_results[suggestion_index][0]
            selected_content = selected_doc.page_content
            
            # 2. 선택된 내용의 키워드로 새로운 쿼리 생성
            new_query = self._generate_focused_query(selected_content, original_question)
            
            # 3. 4곳에서 모두 재검색
            multi_search_results = self.multi_vectorstore_search(new_query)
            
            # 4. 선택된 문서 중심으로 답변 생성
            focused_answer = self._generate_focused_answer(selected_content, new_query)
            
            response = {
                'answer': focused_answer,
                'original_question': original_question,
                'focused_query': new_query,
                'selected_suggestion': {
                    'title': self._extract_title(selected_doc),
                    'source': selected_doc.metadata.get('source', '알 수 없음'),
                    'similarity': search_results[suggestion_index][1],
                    'content_preview': selected_content[:300] + "..."
                },
                'multi_search_results': multi_search_results,
                'processing_time': time.time() - start_time,
                'model_used': 'suggestion_focused_search'
            }
            
            return response
                
        except Exception as e:
            return {
                'error': str(e),
                'answer': '추천 검색 중 오류가 발생했습니다.'
            }
    
    def _generate_focused_query(self, content: str, original_question: str) -> str:
        """선택된 내용을 기반으로 집중된 쿼리 생성"""
        # 원본 질문의 핵심 키워드 추출
        original_keywords = set(original_question.split())
        
        # 선택된 내용에서 핵심 키워드 추출
        content_keywords = self._extract_keywords(content).split()
        
        # 공통 키워드와 내용 키워드 결합
        focused_keywords = []
        for word in content_keywords:
            if len(word) > 1:
                focused_keywords.append(word)
        
        # 새로운 집중된 질문 생성
        if focused_keywords:
            return f"{' '.join(focused_keywords[:3])}에 대해 자세히 설명해주세요"
        else:
            return original_question
    
    def _generate_focused_answer(self, content: str, query: str) -> str:
        """선택된 내용 기반으로 집중된 답변 생성"""
        try:
            focused_prompt = f"""다음 문서를 바탕으로 질문에 답변해주세요.

문서 내용:
{content}

질문: {query}

위 문서의 내용을 중심으로 정확하고 상세한 답변을 제공해주세요:"""
            
            llm = self.llm_manager.get_llm()
            answer = llm.invoke(focused_prompt)
            
            # LangChain 응답 처리
            if hasattr(answer, 'content'):
                return answer.content
            else:
                return str(answer)
            
        except Exception as e:
            return f"선택하신 문서를 바탕으로 답변을 생성하는 중 오류가 발생했습니다: {str(e)}"
    
    def multi_vectorstore_search(self, question: str) -> Dict[str, Any]:
        """4곳의 다른 벡터스토어에서 검색"""
        results = {
            'question': question,
            'searches': []
        }
        
        # 1. 기본 벡터스토어
        try:
            basic_results = self.vectorstore_manager.similarity_search_with_score(question, k=3)
            results['searches'].append({
                'source': 'basic_vectorstore',
                'source_name': '기본 벡터 검색',
                'count': len(basic_results),
                'results': [{'content': doc.page_content[:200], 'score': score, 'metadata': doc.metadata} 
                           for doc, score in basic_results]
            })
        except Exception as e:
            results['searches'].append({
                'source': 'basic_vectorstore',
                'source_name': '기본 벡터 검색',
                'count': 0,
                'error': str(e),
                'results': []
            })
        
        # 2. 이중 벡터스토어 (기본 청킹)
        try:
            if hasattr(self, 'dual_vectorstore_manager') and self.dual_vectorstore_manager:
                dual_basic_results = self.dual_vectorstore_manager.search_basic(question, k=3)
                results['searches'].append({
                    'source': 'dual_basic_chunks',
                    'source_name': '기본 청킹 검색',
                    'count': len(dual_basic_results),
                    'results': [{'content': doc.page_content[:200], 'score': score, 'metadata': doc.metadata} 
                               for doc, score in dual_basic_results]
                })
            else:
                results['searches'].append({
                    'source': 'dual_basic_chunks',
                    'source_name': '기본 청킹 검색',
                    'count': 0,
                    'results': [],
                    'note': '이중 벡터스토어가 설정되지 않음'
                })
        except Exception as e:
            results['searches'].append({
                'source': 'dual_basic_chunks',
                'source_name': '기본 청킹 검색',
                'count': 0,
                'error': str(e),
                'results': []
            })
            
        # 3. 이중 벡터스토어 (커스텀 청킹)
        try:
            if hasattr(self, 'dual_vectorstore_manager') and self.dual_vectorstore_manager:
                dual_custom_results = self.dual_vectorstore_manager.search_custom(question, k=3)
                results['searches'].append({
                    'source': 'dual_custom_chunks',
                    'source_name': '커스텀 청킹 검색',
                    'count': len(dual_custom_results),
                    'results': [{'content': doc.page_content[:200], 'score': score, 'metadata': doc.metadata} 
                               for doc, score in dual_custom_results]
                })
            else:
                results['searches'].append({
                    'source': 'dual_custom_chunks',  
                    'source_name': '커스텀 청킹 검색',
                    'count': 0,
                    'results': [],
                    'note': '이중 벡터스토어가 설정되지 않음'
                })
        except Exception as e:
            results['searches'].append({
                'source': 'dual_custom_chunks',
                'source_name': '커스텀 청킹 검색',
                'count': 0,
                'error': str(e),
                'results': []
            })
        
        # 4. 키워드 기반 검색
        try:
            keyword_results = self._keyword_based_search(question)
            results['searches'].append({
                'source': 'keyword_based',
                'source_name': '키워드 기반 검색',
                'count': len(keyword_results),
                'results': keyword_results
            })
        except Exception as e:
            results['searches'].append({
                'source': 'keyword_based',
                'source_name': '키워드 기반 검색',
                'count': 0,
                'error': str(e),
                'results': []
            })
        
        return results
    
    def _keyword_based_search(self, question: str) -> List[Dict]:
        """키워드 기반 검색 (보완적 검색)"""
        # 간단한 키워드 기반 검색 구현
        keywords = question.split()[:5]  # 처음 5개 단어를 키워드로
        
        try:
            # 전체 문서에서 키워드 매칭
            all_docs = self.vectorstore_manager.similarity_search(question, k=20)
            
            keyword_matches = []
            for doc in all_docs:
                score = 0
                matched_keywords = []
                
                for keyword in keywords:
                    if keyword.lower() in doc.page_content.lower():
                        score += 1
                        matched_keywords.append(keyword)
                
                if score > 0:
                    keyword_matches.append({
                        'content': doc.page_content[:200],
                        'score': score / len(keywords),  # 정규화된 점수
                        'metadata': doc.metadata,
                        'matched_keywords': matched_keywords,
                        'keyword_count': score
                    })
            
            # 점수순 정렬
            keyword_matches.sort(key=lambda x: x['score'], reverse=True)
            
            return keyword_matches[:3]
            
        except Exception as e:
            return [{'error': f'키워드 검색 오류: {str(e)}'}]