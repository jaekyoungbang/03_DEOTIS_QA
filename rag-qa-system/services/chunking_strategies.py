from typing import List, Dict, Any
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain.schema import Document
import nltk
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import time

# NLTK 데이터 다운로드 (필요한 경우)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

class ChunkingBenchmarker:
    """청킹 전략 벤치마킹 시스템"""
    
    def __init__(self):
        self.strategies = {
            'basic': BasicChunkingStrategy(),
            'semantic': SemanticChunkingStrategy(),
            'hybrid': HybridChunkingStrategy()
        }
        self.results = []
    
    def benchmark_strategy(self, strategy_name: str, documents: List[Document]) -> Dict:
        """특정 청킹 전략 벤치마킹"""
        if strategy_name not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        strategy = self.strategies[strategy_name]
        start_time = time.time()
        
        # 메모리 사용량 측정
        import psutil
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 청킹 실행
        chunks = strategy.split_documents(documents)
        
        end_time = time.time()
        end_memory = process.memory_info().rss / 1024 / 1024
        
        # 품질 메트릭 계산
        quality_metrics = self._calculate_quality_metrics(chunks)
        
        result = {
            'strategy': strategy_name,
            'processing_time': end_time - start_time,
            'memory_used': end_memory - start_memory,
            'total_chunks': len(chunks),
            'avg_chunk_size': np.mean([len(chunk.page_content) for chunk in chunks]),
            'std_chunk_size': np.std([len(chunk.page_content) for chunk in chunks]),
            'quality_metrics': quality_metrics,
            'timestamp': time.time()
        }
        
        self.results.append(result)
        return result
    
    def _calculate_quality_metrics(self, chunks: List[Document]) -> Dict:
        """청킹 품질 메트릭 계산"""
        if not chunks:
            return {'coherence_score': 0, 'completeness_score': 0}
        
        chunk_sizes = [len(chunk.page_content) for chunk in chunks]
        
        # 일관성 점수 (크기 분산이 낮을수록 좋음)
        size_variance = np.var(chunk_sizes)
        max_variance = np.mean(chunk_sizes) ** 2
        coherence_score = max(0, 1 - (size_variance / max_variance)) if max_variance > 0 else 1
        
        # 완성도 점수 (빈 청크나 너무 작은 청크가 적을수록 좋음)
        min_size_threshold = 100
        valid_chunks = sum(1 for size in chunk_sizes if size >= min_size_threshold)
        completeness_score = valid_chunks / len(chunks) if chunks else 0
        
        return {
            'coherence_score': coherence_score,
            'completeness_score': completeness_score,
            'avg_size': np.mean(chunk_sizes),
            'size_variance': size_variance
        }
    
    def compare_strategies(self, documents: List[Document]) -> Dict:
        """모든 전략 비교"""
        comparison_results = {}
        
        for strategy_name in self.strategies.keys():
            try:
                result = self.benchmark_strategy(strategy_name, documents)
                comparison_results[strategy_name] = result
            except Exception as e:
                comparison_results[strategy_name] = {
                    'error': str(e),
                    'strategy': strategy_name
                }
        
        # 최적 전략 선택
        best_strategy = self._select_best_strategy(comparison_results)
        
        return {
            'results': comparison_results,
            'best_strategy': best_strategy,
            'comparison_summary': self._generate_comparison_summary(comparison_results)
        }
    
    def _select_best_strategy(self, results: Dict) -> str:
        """최적 전략 선택 (종합 점수 기반)"""
        scores = {}
        
        for strategy, result in results.items():
            if 'error' in result:
                scores[strategy] = 0
                continue
            
            # 종합 점수 계산 (속도 + 품질)
            speed_score = 1 / (result['processing_time'] + 0.1)  # 빠를수록 좋음
            quality_score = (
                result['quality_metrics']['coherence_score'] + 
                result['quality_metrics']['completeness_score']
            ) / 2
            
            scores[strategy] = (speed_score * 0.3) + (quality_score * 0.7)
        
        return max(scores, key=scores.get) if scores else 'basic'
    
    def _generate_comparison_summary(self, results: Dict) -> Dict:
        """비교 요약 생성"""
        summary = {
            'fastest': None,
            'highest_quality': None,
            'most_balanced': None
        }
        
        valid_results = {k: v for k, v in results.items() if 'error' not in v}
        
        if not valid_results:
            return summary
        
        # 가장 빠른 전략
        fastest = min(valid_results.items(), 
                     key=lambda x: x[1]['processing_time'])
        summary['fastest'] = fastest[0]
        
        # 가장 높은 품질
        highest_quality = max(valid_results.items(),
                            key=lambda x: (x[1]['quality_metrics']['coherence_score'] + 
                                         x[1]['quality_metrics']['completeness_score']) / 2)
        summary['highest_quality'] = highest_quality[0]
        
        # 가장 균형잡힌 전략 (이미 계산된 best_strategy와 동일)
        summary['most_balanced'] = self._select_best_strategy(results)
        
        return summary

class BasicChunkingStrategy:
    """기본 청킹 전략 - 문자 기반"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """문서를 청크로 분할"""
        return self.splitter.split_documents(documents)

class SemanticChunkingStrategy:
    """의미 기반 청킹 전략"""
    
    def __init__(self, min_chunk_size: int = 500, max_chunk_size: int = 1500):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        try:
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception:
            # 모델 로드 실패 시 기본 전략으로 대체
            self.sentence_model = None
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """의미 기반으로 문서 분할"""
        if not self.sentence_model:
            # 모델이 없으면 기본 전략 사용
            basic_strategy = BasicChunkingStrategy()
            return basic_strategy.split_documents(documents)
        
        all_chunks = []
        
        for doc in documents:
            chunks = self._split_document_semantically(doc)
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def _split_document_semantically(self, document: Document) -> List[Document]:
        """단일 문서를 의미 기반으로 분할"""
        text = document.page_content
        
        # 문장 단위로 분할
        sentences = nltk.sent_tokenize(text)
        
        if len(sentences) <= 1:
            return [document]
        
        # 문장 임베딩 생성
        try:
            embeddings = self.sentence_model.encode(sentences)
        except Exception:
            # 임베딩 생성 실패 시 기본 분할
            basic_strategy = BasicChunkingStrategy()
            return basic_strategy.split_documents([document])
        
        # 의미적 유사도 기반 그루핑
        chunks = self._group_sentences_by_similarity(
            sentences, embeddings, document.metadata
        )
        
        return chunks
    
    def _group_sentences_by_similarity(self, sentences: List[str], 
                                     embeddings: np.ndarray, 
                                     metadata: Dict) -> List[Document]:
        """유사도 기반 문장 그루핑"""
        chunks = []
        current_chunk = []
        current_size = 0
        
        for i, sentence in enumerate(sentences):
            sentence_size = len(sentence)
            
            # 현재 청크에 추가할지 판단
            if (current_size + sentence_size <= self.max_chunk_size and 
                current_size >= self.min_chunk_size):
                
                # 유사도 확인 (현재 청크의 마지막 문장과)
                if current_chunk and i > 0:
                    similarity = cosine_similarity(
                        embeddings[i].reshape(1, -1),
                        embeddings[i-1].reshape(1, -1)
                    )[0][0]
                    
                    # 유사도가 낮으면 새 청크 시작
                    if similarity < 0.5:
                        if current_chunk:
                            chunk_text = " ".join(current_chunk)
                            chunks.append(Document(
                                page_content=chunk_text,
                                metadata=metadata.copy()
                            ))
                        current_chunk = [sentence]
                        current_size = sentence_size
                        continue
            
            current_chunk.append(sentence)
            current_size += sentence_size
            
            # 최대 크기 초과 시 청크 완성
            if current_size >= self.max_chunk_size:
                chunk_text = " ".join(current_chunk)
                chunks.append(Document(
                    page_content=chunk_text,
                    metadata=metadata.copy()
                ))
                current_chunk = []
                current_size = 0
        
        # 마지막 청크 처리
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(Document(
                    page_content=chunk_text,
                    metadata=metadata.copy()
                ))
        
        return chunks if chunks else [Document(
            page_content=" ".join(sentences),
            metadata=metadata.copy()
        )]

class HybridChunkingStrategy:
    """하이브리드 청킹 전략 - 기본 + 의미 기반"""
    
    def __init__(self):
        self.basic_strategy = BasicChunkingStrategy(chunk_size=800, chunk_overlap=150)
        self.semantic_strategy = SemanticChunkingStrategy(min_chunk_size=400, max_chunk_size=1200)
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """하이브리드 방식으로 문서 분할"""
        # 먼저 기본 전략으로 분할
        basic_chunks = self.basic_strategy.split_documents(documents)
        
        # 큰 청크들은 의미 기반으로 재분할
        final_chunks = []
        
        for chunk in basic_chunks:
            if len(chunk.page_content) > 1200:
                # 큰 청크는 의미 기반으로 재분할
                semantic_chunks = self.semantic_strategy._split_document_semantically(chunk)
                final_chunks.extend(semantic_chunks)
            else:
                final_chunks.append(chunk)
        
        return final_chunks

# 전역 벤치마커 인스턴스
chunking_benchmarker = ChunkingBenchmarker()

def get_chunking_strategy(strategy_name: str = 'basic'):
    """청킹 전략 팩토리 함수"""
    strategies = {
        'basic': BasicChunkingStrategy(),
        'semantic': SemanticChunkingStrategy(),
        'hybrid': HybridChunkingStrategy()
    }
    
    return strategies.get(strategy_name, strategies['basic'])

def benchmark_chunking_strategies(documents: List[Document]) -> Dict:
    """청킹 전략 벤치마킹 수행"""
    return chunking_benchmarker.compare_strategies(documents)