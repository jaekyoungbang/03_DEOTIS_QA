import requests
import json
from typing import List, Optional
from langchain.embeddings.base import Embeddings


class OllamaEmbeddings(Embeddings):
    """Ollama BGE-M3 임베딩 클래스"""
    
    def __init__(self, model: str = "bge-m3:latest", base_url: str = "http://192.168.0.224:11434"):
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/embeddings"
    
    def test_connection(self) -> bool:
        """서버 연결 테스트"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """여러 문서 임베딩"""
        embeddings = []
        for text in texts:
            embedding = self.embed_query(text)
            embeddings.append(embedding)
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """단일 텍스트 임베딩"""
        try:
            payload = {
                "model": self.model,
                "prompt": text
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("embedding", [])
            else:
                print(f"❌ Ollama 임베딩 오류: {response.status_code}")
                return [0.0] * 1024  # BGE-M3 기본 차원
                
        except Exception as e:
            print(f"❌ Ollama 임베딩 연결 오류: {e}")
            return [0.0] * 1024  # BGE-M3 기본 차원