from typing import List, Dict, Tuple, Any
import numpy as np
from services.benchmarking import DualLLMBenchmarker
from models.dual_llm import DualLLMManager
from config import Config

class EnhancedRAGChain:
    """개선된 RAG 체인 - 듀얼 LLM 벤치마킹 지원"""
    
    def __init__(self, vectorstore):
        self.vectorstore = vectorstore
        self.dual_llm = DualLLMManager()
        self.benchmarker = DualLLMBenchmarker()
        self.use_benchmarking = Config.BENCHMARKING_MODE
    
    def process_query(self, query: str, top_k: int = 3) -> Dict:
        """질의 처리 - 벤치마킹 모드 지원"""
        
        # 1. 관련 문서 검색
        results = self._search_documents(query, top_k)
        
        if not results:
            return {
                'type': 'error',
                'message': '관련 문서를 찾을 수 없습니다.'
            }
        
        # 2. 유사도 기반 그룹핑
        grouped_results = self._group_by_similarity(results)
        
        # 3. 벤치마킹 모드인 경우
        if self.use_benchmarking:
            return self._process_benchmarking_mode(query, grouped_results)
        
        # 4. 일반 모드인 경우
        return self._process_normal_mode(query, grouped_results)
    
    def _search_documents(self, query: str, top_k: int) -> List[Tuple]:
        """벡터 DB에서 문서 검색"""
        try:
            # 더 많은 문서를 검색해서 필터링
            results = self.vectorstore.similarity_search_with_score(
                query, 
                k=top_k * 2
            )
            return results
        except Exception as e:
            print(f"문서 검색 오류: {e}")
            return []
    
    def _group_by_similarity(self, results: List[Tuple]) -> List[Dict]:
        """유사도 기반 결과 그룹핑"""
        if not results:
            return []
        
        # 유사도 임계값 설정 (0.05 차이 이내는 같은 그룹)
        threshold = 0.05
        groups = []
        current_group = {
            'documents': [results[0][0]], 
            'similarities': [results[0][1]]
        }
        
        for doc, similarity in results[1:]:
            if abs(similarity - current_group['similarities'][0]) <= threshold:
                current_group['documents'].append(doc)
                current_group['similarities'].append(similarity)
            else:
                current_group['avg_similarity'] = np.mean(current_group['similarities'])
                groups.append(current_group)
                current_group = {'documents': [doc], 'similarities': [similarity]}
        
        if current_group['documents']:
            current_group['avg_similarity'] = np.mean(current_group['similarities'])
            groups.append(current_group)
        
        return groups[:3]  # 상위 3개 그룹만 반환
    
    def _process_benchmarking_mode(self, query: str, grouped_results: List[Dict]) -> Dict:
        """벤치마킹 모드 처리 - 두 LLM 동시 실행"""
        
        # 첫 번째 그룹의 문서들 사용
        if not grouped_results:
            return {
                'type': 'error',
                'message': '처리할 문서가 없습니다.'
            }
        
        documents = grouped_results[0]['documents']
        avg_similarity = grouped_results[0]['avg_similarity']
        
        # 사용 가능한 모델 확인
        available_models = self.dual_llm.get_available_models()
        
        if not available_models['api'] and not available_models['local']:
            return {
                'type': 'error',
                'message': '사용 가능한 LLM이 없습니다.'
            }
        
        # 벤치마킹 실행
        try:
            api_chain = self.dual_llm.get_api_chain() if available_models['api'] else None
            local_chain = self.dual_llm.get_local_chain() if available_models['local'] else None
            
            benchmark_result = self.benchmarker.benchmark_dual_llm(
                api_chain=api_chain,
                local_chain=local_chain,
                query=query,
                relevant_docs=documents
            )
            
            # 결과 포맷팅
            response = {
                'type': 'benchmark',
                'query': query,
                'avg_similarity': avg_similarity,
                'api_result': benchmark_result.get('api', {}),
                'local_result': benchmark_result.get('local', {}),
                'comparison': benchmark_result.get('comparison', {}),
                'total_time': benchmark_result.get('total_time', 0),
                'sources': [doc.metadata for doc in documents]
            }
            
            # 다중 답변 옵션 추가 (유사도가 비슷한 다른 그룹이 있는 경우)
            if len(grouped_results) > 1:
                response['alternative_groups'] = []
                for i, group in enumerate(grouped_results[1:3], 1):
                    response['alternative_groups'].append({
                        'rank': i + 1,
                        'avg_similarity': group['avg_similarity'],
                        'document_count': len(group['documents']),
                        'sources': [doc.metadata for doc in group['documents']]
                    })
            
            return response
            
        except Exception as e:
            return {
                'type': 'error',
                'message': f'벤치마킹 실행 중 오류 발생: {str(e)}'
            }
    
    def _process_normal_mode(self, query: str, grouped_results: List[Dict]) -> Dict:
        """일반 모드 처리 - 단일 LLM 사용"""
        
        # API LLM 우선 사용
        available_models = self.dual_llm.get_available_models()
        
        if available_models['api']:
            chain = self.dual_llm.get_api_chain()
            model_info = 'API LLM'
        elif available_models['local']:
            chain = self.dual_llm.get_local_chain()
            model_info = 'Local LLM'
        else:
            return {
                'type': 'error',
                'message': '사용 가능한 LLM이 없습니다.'
            }
        
        # 답변 생성
        answers = []
        for i, group in enumerate(grouped_results):
            context = self._format_context(group['documents'])
            
            try:
                response = chain.invoke({
                    "question": query,
                    "context": context
                })
                
                answer_text = response.content if hasattr(response, 'content') else str(response)
                
                answers.append({
                    'rank': i + 1,
                    'similarity': group['avg_similarity'],
                    'answer': answer_text,
                    'sources': [doc.metadata for doc in group['documents']]
                })
            except Exception as e:
                print(f"답변 생성 오류: {e}")
                continue
        
        # 결과 포맷팅
        if not answers:
            return {
                'type': 'error',
                'message': '답변을 생성할 수 없습니다.'
            }
        
        if len(answers) == 1:
            return {
                'type': 'single',
                'answer': answers[0]['answer'],
                'sources': answers[0]['sources'],
                'model_used': model_info
            }
        else:
            return {
                'type': 'multiple',
                'answers': answers,
                'model_used': model_info
            }
    
    def _format_context(self, docs: List[Any]) -> str:
        """문서를 컨텍스트 문자열로 포맷"""
        context_parts = []
        for i, doc in enumerate(docs):
            context_parts.append(f"문서 {i+1}:\n{doc.page_content}\n")
        return "\n".join(context_parts)
    
    def get_system_info(self) -> Dict:
        """시스템 정보 반환"""
        return {
            'benchmarking_mode': self.use_benchmarking,
            'models': self.dual_llm.get_model_info(),
            'benchmark_summary': self.benchmarker.get_benchmark_summary()
        }