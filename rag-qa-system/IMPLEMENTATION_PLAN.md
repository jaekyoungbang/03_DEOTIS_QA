# RAG QA 시스템 구현 계획

## 1. 즉시 구현 가능한 개선사항

### 1.1 config.py 확장
```python
# config.py
import os
from typing import Dict, Any

class Config:
    # 기본 설정
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    UPLOAD_FOLDER = 'data/documents'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # LLM 설정
    LLM_MODELS = {
        'gpt-4-turbo': {
            'api_type': 'openai',
            'model_name': 'gpt-4-turbo-preview',
            'temperature': 0,  # 창의성 0으로 고정
            'max_tokens': 2000,
            'system_prompt': """당신은 정확한 정보를 제공하는 전문가입니다. 
                             주어진 문서를 기반으로만 답변하고, 추측하지 마세요."""
        },
        'gpt-3.5-turbo': {
            'api_type': 'openai',
            'model_name': 'gpt-3.5-turbo',
            'temperature': 0,
            'max_tokens': 1500,
            'system_prompt': """You are a helpful assistant that provides accurate information 
                             based on the given documents."""
        },
        'llama3-local': {
            'api_type': 'local',
            'model_path': './models/llama3-8b',
            'temperature': 0,
            'max_tokens': 2000,
            'system_prompt': """You are a precise information retrieval system."""
        }
    }
    
    # 임베딩 모델 설정
    EMBEDDING_MODELS = {
        'openai': {
            'model_name': 'text-embedding-ada-002',
            'dimension': 1536
        },
        'sentence-transformers': {
            'model_name': 'sentence-transformers/all-MiniLM-L6-v2',
            'dimension': 384
        }
    }
    
    # 청킹 전략
    CHUNKING_STRATEGIES = {
        'basic': {
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'separator': '\n'
        },
        'semantic': {
            'method': 'sentence_based',
            'min_chunk_size': 500,
            'max_chunk_size': 1500
        }
    }
    
    # 시스템 정보
    SYSTEM_INFO = {
        'python_version': '3.9+',
        'port': 5000,
        'current_llm': 'gpt-3.5-turbo',
        'current_embedding': 'openai',
        'current_chunking': 'basic'
    }
```

### 1.2 벤치마킹 모듈
```python
# benchmarking.py
import time
import psutil
from typing import Dict, List, Any
import json
from datetime import datetime

class BenchmarkManager:
    def __init__(self):
        self.results = []
        
    def benchmark_llm(self, llm_model: str, test_queries: List[str]) -> Dict:
        """LLM 성능 벤치마킹"""
        results = {
            'model': llm_model,
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'avg_response_time': 0,
                'total_tokens': 0,
                'accuracy_score': 0,
                'memory_usage': 0
            }
        }
        
        # 실제 테스트 로직 구현
        return results
    
    def benchmark_chunking(self, strategy: str, documents: List[str]) -> Dict:
        """청킹 전략 벤치마킹"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # 청킹 수행
        chunks = []  # 실제 청킹 로직
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        return {
            'strategy': strategy,
            'processing_time': end_time - start_time,
            'memory_used': end_memory - start_memory,
            'total_chunks': len(chunks),
            'avg_chunk_size': sum(len(c) for c in chunks) / len(chunks) if chunks else 0
        }
    
    def save_results(self, filepath: str = 'benchmark_results.json'):
        """벤치마킹 결과 저장"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
```

### 1.3 개선된 RAG Chain
```python
# services/enhanced_rag_chain.py
from typing import List, Dict, Tuple
import numpy as np

class EnhancedRAGChain:
    def __init__(self, llm, vectorstore, config):
        self.llm = llm
        self.vectorstore = vectorstore
        self.config = config
        
    def process_query(self, query: str, top_k: int = 3) -> Dict:
        """개선된 질의 처리"""
        
        # 1. 질문 벡터화 (LLM으로 의도 파악 포함)
        enhanced_query = self._enhance_query(query)
        
        # 2. 벡터 DB에서 유사 문서 검색
        results = self.vectorstore.similarity_search_with_score(
            enhanced_query, 
            k=top_k * 2  # 더 많이 검색해서 필터링
        )
        
        # 3. 유사도 기반 그룹핑
        grouped_results = self._group_by_similarity(results)
        
        # 4. 각 그룹에 대한 답변 생성
        answers = []
        for i, group in enumerate(grouped_results[:3]):
            answer = self._generate_answer(query, group['documents'])
            answers.append({
                'rank': i + 1,
                'similarity': group['avg_similarity'],
                'answer': answer,
                'sources': [doc.metadata for doc in group['documents']]
            })
        
        # 5. 답변 요약 및 정리
        final_response = self._format_response(answers)
        
        return final_response
    
    def _enhance_query(self, query: str) -> str:
        """LLM을 사용한 질문 개선"""
        prompt = f"""다음 질문의 핵심 키워드와 의도를 파악하여 검색에 최적화된 쿼리로 변환하세요.
        
        원본 질문: {query}
        
        검색 쿼리:"""
        
        enhanced = self.llm.predict(prompt)
        return enhanced
    
    def _group_by_similarity(self, results: List[Tuple]) -> List[Dict]:
        """유사도 기반 결과 그룹핑"""
        if not results:
            return []
            
        # 유사도 임계값 설정 (0.05 차이 이내는 같은 그룹)
        threshold = 0.05
        groups = []
        current_group = {'documents': [results[0][0]], 
                        'similarities': [results[0][1]]}
        
        for doc, similarity in results[1:]:
            if abs(similarity - current_group['similarities'][0]) <= threshold:
                current_group['documents'].append(doc)
                current_group['similarities'].append(similarity)
            else:
                current_group['avg_similarity'] = np.mean(current_group['similarities'])
                groups.append(current_group)
                current_group = {'documents': [doc], 'similarities': [similarity]}
        
        current_group['avg_similarity'] = np.mean(current_group['similarities'])
        groups.append(current_group)
        
        return groups
    
    def _format_response(self, answers: List[Dict]) -> Dict:
        """다중 답변 포맷팅"""
        if len(answers) == 1:
            return {
                'type': 'single',
                'answer': answers[0]['answer'],
                'sources': answers[0]['sources']
            }
        else:
            formatted = "찾은 답변들:\n\n"
            for ans in answers:
                formatted += f"{ans['rank']}. [유사도: {ans['similarity']:.2f}]\n"
                formatted += f"{ans['answer']}\n\n"
            
            formatted += "이 중에서 원하시는 답변이 있으신가요?"
            
            return {
                'type': 'multiple',
                'answer': formatted,
                'detailed_answers': answers
            }
```

### 1.4 시스템 정보 API
```python
# routes/system.py
from flask import Blueprint, jsonify
from config import Config
import sys
import pkg_resources

system_bp = Blueprint('system', __name__)

@system_bp.route('/api/system/info', methods=['GET'])
def get_system_info():
    """시스템 정보 반환"""
    
    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    
    info = {
        'python_version': sys.version,
        'port': Config.SYSTEM_INFO['port'],
        'current_settings': {
            'llm_model': Config.SYSTEM_INFO['current_llm'],
            'embedding_model': Config.SYSTEM_INFO['current_embedding'],
            'chunking_strategy': Config.SYSTEM_INFO['current_chunking']
        },
        'available_models': {
            'llm': list(Config.LLM_MODELS.keys()),
            'embedding': list(Config.EMBEDDING_MODELS.keys())
        },
        'key_dependencies': {
            'langchain': installed_packages.get('langchain', 'Not installed'),
            'chromadb': installed_packages.get('chromadb', 'Not installed'),
            'openai': installed_packages.get('openai', 'Not installed')
        }
    }
    
    return jsonify(info)

@system_bp.route('/api/system/benchmark', methods=['GET'])
def get_benchmark_results():
    """최신 벤치마킹 결과 반환"""
    try:
        with open('benchmark_results.json', 'r') as f:
            results = json.load(f)
        return jsonify(results)
    except FileNotFoundError:
        return jsonify({'error': 'No benchmark results available'}), 404
```

## 2. Redis 없이 실행하는 방법

현재 시스템은 Redis가 필수가 아닙니다. 다음과 같이 실행할 수 있습니다:

```bash
# 1. 가상환경 활성화
source venv_new/bin/activate  # Linux/Mac
# 또는
venv_windows\Scripts\activate  # Windows

# 2. 환경변수 설정 확인
export OPENAI_API_KEY="your-api-key"

# 3. 애플리케이션 실행
python app.py
```

## 3. 추가 개선 사항

### 3.1 캐싱 (Redis 없이)
```python
# services/cache.py
import json
import os
from datetime import datetime, timedelta

class SimpleFileCache:
    def __init__(self, cache_dir='data/cache'):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
    def get(self, key: str):
        filepath = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                if datetime.fromisoformat(data['expires']) > datetime.now():
                    return data['value']
        return None
        
    def set(self, key: str, value: Any, ttl: int = 3600):
        filepath = os.path.join(self.cache_dir, f"{key}.json")
        data = {
            'value': value,
            'expires': (datetime.now() + timedelta(seconds=ttl)).isoformat()
        }
        with open(filepath, 'w') as f:
            json.dump(data, f)
```

### 3.2 자연어 질문 처리 예시
```python
# 질문 예시 및 처리
sample_questions = [
    "이 문서에서 가장 중요한 내용은 무엇인가요?",
    "BC카드 신용카드 발급 절차를 설명해주세요",
    "연체 시 벌금은 얼마인가요?",
    "카드 분실 시 어떻게 해야 하나요?"
]

# 각 질문은 다음과 같이 처리됨:
# 1. 자연어 -> 벡터화
# 2. 유사 문서 검색
# 3. 답변 생성 (temperature=0)
# 4. 소스 표시와 함께 반환
```

이제 시스템을 실행할 준비가 되었습니다!