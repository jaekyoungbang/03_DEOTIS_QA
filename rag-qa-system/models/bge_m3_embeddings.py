"""
BGE-M3 한국어 특화 임베딩 모델
"""
from typing import List
import torch
from FlagEmbedding import BGEM3FlagModel

class BGEM3Embeddings:
    """BGE-M3 임베딩 모델 래퍼"""
    
    def __init__(self, model_name: str = "BAAI/bge-m3", use_fp16: bool = True):
        self.model = BGEM3FlagModel(model_name, use_fp16=use_fp16)
        self.dimension = 1024
        
    def embed_query(self, text: str) -> List[float]:
        """단일 텍스트 임베딩"""
        # BGE-M3는 dense, sparse, colbert 벡터를 모두 반환
        embeddings = self.model.encode([text])['dense_vecs']
        return embeddings[0].tolist()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """여러 문서 임베딩"""
        embeddings = self.model.encode(texts)['dense_vecs']
        return embeddings.tolist()
    
    def encode_with_instruction(self, text: str, instruction: str = "query") -> List[float]:
        """지시문과 함께 임베딩 (검색 쿼리 최적화)"""
        if instruction == "query":
            # 검색 쿼리용 특수 프롬프트
            text = f"Represent this sentence for searching relevant passages: {text}"
        embeddings = self.model.encode([text])['dense_vecs']
        return embeddings[0].tolist()