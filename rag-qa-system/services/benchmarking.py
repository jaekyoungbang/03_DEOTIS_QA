import time
import asyncio
from typing import Dict, List, Any, Tuple
import json
from datetime import datetime
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import os

class DualLLMBenchmarker:
    """두 개의 LLM을 동시에 실행하고 비교하는 벤치마킹 시스템"""
    
    def __init__(self):
        self.results_history = []
        self.executor = ThreadPoolExecutor(max_workers=2)
        
    def benchmark_dual_llm(self, 
                          api_chain, 
                          local_chain, 
                          query: str, 
                          relevant_docs: List[Any]) -> Dict:
        """두 LLM을 동시에 실행하고 결과를 비교"""
        
        # 시작 시간 기록
        start_time = time.time()
        
        # 동시 실행을 위한 Future 객체들
        future_to_llm = {
            self.executor.submit(self._run_llm, 'api', api_chain, query, relevant_docs): 'api',
            self.executor.submit(self._run_llm, 'local', local_chain, query, relevant_docs): 'local'
        }
        
        results = {
            'api': None,
            'local': None,
            'query': query,
            'timestamp': datetime.now().isoformat()
        }
        
        # 결과 수집
        for future in as_completed(future_to_llm):
            llm_type = future_to_llm[future]
            try:
                result = future.result()
                results[llm_type] = result
            except Exception as e:
                results[llm_type] = {
                    'error': str(e),
                    'response_time': -1
                }
        
        # 전체 실행 시간
        results['total_time'] = time.time() - start_time
        
        # 비교 메트릭 계산
        results['comparison'] = self._calculate_comparison_metrics(results)
        
        # 결과 저장
        self.results_history.append(results)
        
        return results
    
    def _run_llm(self, llm_type: str, chain, query: str, relevant_docs: List[Any]) -> Dict:
        """개별 LLM 실행 및 성능 측정"""
        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        
        try:
            # LLM 실행
            response = chain.invoke({
                "question": query,
                "context": self._format_context(relevant_docs)
            })
            
            end_time = time.time()
            end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            
            # 응답에서 텍스트 추출
            if hasattr(response, 'content'):
                answer = response.content
            elif isinstance(response, dict) and 'answer' in response:
                answer = response['answer']
            else:
                answer = str(response)
            
            # 토큰 수 추정 (대략적인 계산)
            estimated_tokens = len(answer.split()) * 1.3
            
            return {
                'answer': answer,
                'response_time': end_time - start_time,
                'memory_used': end_memory - start_memory,
                'estimated_tokens': int(estimated_tokens),
                'sources': [doc.metadata.get('source', 'Unknown') for doc in relevant_docs],
                'success': True
            }
            
        except Exception as e:
            return {
                'answer': f"오류 발생: {str(e)}",
                'response_time': time.time() - start_time,
                'memory_used': 0,
                'estimated_tokens': 0,
                'sources': [],
                'success': False,
                'error': str(e)
            }
    
    def _format_context(self, docs: List[Any]) -> str:
        """문서를 컨텍스트 문자열로 포맷"""
        context_parts = []
        for i, doc in enumerate(docs):
            context_parts.append(f"문서 {i+1}:\n{doc.page_content}\n")
        return "\n".join(context_parts)
    
    def _calculate_comparison_metrics(self, results: Dict) -> Dict:
        """두 LLM 결과 비교 메트릭 계산"""
        api_result = results.get('api', {})
        local_result = results.get('local', {})
        
        comparison = {
            'speed_difference': None,
            'faster_model': None,
            'similarity_score': None,
            'both_succeeded': False
        }
        
        # 둘 다 성공한 경우에만 비교
        if api_result and local_result and api_result.get('success') and local_result.get('success'):
            comparison['both_succeeded'] = True
            
            # 속도 비교
            api_time = api_result['response_time']
            local_time = local_result['response_time']
            
            if api_time > 0 and local_time > 0:
                comparison['speed_difference'] = abs(api_time - local_time)
                comparison['faster_model'] = 'api' if api_time < local_time else 'local'
                comparison['speed_ratio'] = min(api_time, local_time) / max(api_time, local_time)
            
            # 답변 유사도 계산 (간단한 문자열 유사도)
            similarity = self._calculate_text_similarity(
                api_result['answer'], 
                local_result['answer']
            )
            comparison['similarity_score'] = similarity
            
            # 답변 길이 비교
            comparison['length_difference'] = abs(
                len(api_result['answer']) - len(local_result['answer'])
            )
        
        return comparison
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """두 텍스트의 유사도를 계산 (0-1 사이)"""
        # 간단한 자카드 유사도 계산
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def get_benchmark_summary(self) -> Dict:
        """벤치마킹 결과 요약"""
        if not self.results_history:
            return {'message': '아직 벤치마킹 결과가 없습니다.'}
        
        # 성공한 결과만 필터링
        successful_results = [
            r for r in self.results_history 
            if r.get('comparison', {}).get('both_succeeded')
        ]
        
        if not successful_results:
            return {'message': '성공한 벤치마킹 결과가 없습니다.'}
        
        # API와 Local 성능 집계
        api_times = [r['api']['response_time'] for r in successful_results]
        local_times = [r['local']['response_time'] for r in successful_results]
        
        summary = {
            'total_benchmarks': len(self.results_history),
            'successful_benchmarks': len(successful_results),
            'api_performance': {
                'avg_response_time': np.mean(api_times),
                'min_response_time': np.min(api_times),
                'max_response_time': np.max(api_times),
                'std_response_time': np.std(api_times)
            },
            'local_performance': {
                'avg_response_time': np.mean(local_times),
                'min_response_time': np.min(local_times),
                'max_response_time': np.max(local_times),
                'std_response_time': np.std(local_times)
            },
            'comparison': {
                'api_faster_count': sum(1 for r in successful_results 
                                      if r['comparison']['faster_model'] == 'api'),
                'local_faster_count': sum(1 for r in successful_results 
                                        if r['comparison']['faster_model'] == 'local'),
                'avg_similarity': np.mean([r['comparison']['similarity_score'] 
                                         for r in successful_results])
            }
        }
        
        return summary
    
    def save_results(self, filepath: str = 'data/benchmark_results.json'):
        """벤치마킹 결과를 파일로 저장"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'results': self.results_history,
                'summary': self.get_benchmark_summary(),
                'saved_at': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
    
    def __del__(self):
        """리소스 정리"""
        self.executor.shutdown(wait=True)