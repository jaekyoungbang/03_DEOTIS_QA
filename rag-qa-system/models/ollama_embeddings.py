"""
vLLM + Ollama 원격 서버 임베딩 모델 (BGE-M3)
"""
import requests
import numpy as np
from typing import List
import os

class OllamaEmbeddings:
    """Ollama 임베딩 모델을 LangChain 스타일로 래핑"""
    
    def __init__(self, 
                 model: str = "bge-m3:latest", 
                 base_url: str = None):
        self.model = model
        # vLLM에서는 LLM용 8701, 임베딩용은 Ollama 11434 사용
        self.base_url = base_url or os.getenv('OLLAMA_BASE_URL', 'http://192.168.0.224:11434')
        self.dimension = self._get_dimension()
        print(f"✅ BGE-M3 임베딩 초기화: {self.model} @ {self.base_url}")
    
    def _get_dimension(self) -> int:
        """모델별 임베딩 차원 반환"""
        dimensions = {
            "bge-m3:latest": 1024,         # BGE-M3
            "nomic-embed-text": 768,       # Nomic AI
            "mxbai-embed-large": 1024,     # Mixedbread AI
            "all-minilm": 384,             # Sentence Transformers
        }
        return dimensions.get(self.model, 1024)
    
    def embed_query(self, text: str) -> List[float]:
        """단일 텍스트를 임베딩"""
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()["embedding"]
            else:
                raise Exception(f"Ollama 임베딩 실패: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Ollama 임베딩 오류: {e}")
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """여러 문서를 임베딩"""
        embeddings = []
        for i, text in enumerate(texts):
            try:
                embedding = self.embed_query(text)
                embeddings.append(embedding)
                if (i + 1) % 10 == 0:
                    print(f"   임베딩 진행: {i + 1}/{len(texts)}")
            except Exception as e:
                print(f"❌ 문서 {i} 임베딩 실패: {e}")
                # 실패시 제로 벡터로 대체
                embeddings.append([0.0] * self.dimension)
        return embeddings
    
    def test_connection(self) -> bool:
        """연결 테스트"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                if self.model in model_names:
                    print(f"✅ BGE-M3 모델 확인됨: {self.model}")
                    return True
                else:
                    print(f"❌ BGE-M3 모델을 찾을 수 없음. 사용 가능한 모델: {model_names}")
                    return False
        except Exception as e:
            print(f"❌ BGE-M3 Ollama 서버 연결 실패: {e}")
            return False