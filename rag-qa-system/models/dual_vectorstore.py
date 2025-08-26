import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from config import Config
import os

class DualVectorStoreManager:
    """이중 벡터스토어 관리자 - 기본 청킹과 커스텀 청킹 분리"""
    
    def __init__(self, embedding_function):
        self.embedding_function = embedding_function
        self.basic_vectorstore = None
        self.custom_vectorstore = None
        self.persist_directory = Config.CHROMA_PERSIST_DIRECTORY
        
        # 별도 컬렉션명 설정
        self.basic_collection_name = "basic_chunks"
        self.custom_collection_name = "custom_chunks"
        
        self.initialize_vectorstores()
    
    def initialize_vectorstores(self):
        """기본/커스텀 벡터스토어 초기화"""
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # 기본 청킹용 벡터스토어
        self.basic_vectorstore = Chroma(
            collection_name=self.basic_collection_name,
            embedding_function=self.embedding_function,
            persist_directory=self.persist_directory,
            collection_metadata={"hnsw:space": "cosine", "chunking_type": "basic"}
        )
        
        # 커스텀 청킹용 벡터스토어  
        self.custom_vectorstore = Chroma(
            collection_name=self.custom_collection_name,
            embedding_function=self.embedding_function,
            persist_directory=self.persist_directory,
            collection_metadata={"hnsw:space": "cosine", "chunking_type": "custom"}
        )
    
    def add_documents(self, documents, chunking_type="basic", ids=None):
        """청킹 타입에 따라 적절한 벡터스토어에 문서 추가"""
        vectorstore = self._get_vectorstore_by_type(chunking_type)
        
        if ids:
            vectorstore.add_documents(documents=documents, ids=ids)
        else:
            vectorstore.add_documents(documents=documents)
        
        vectorstore.persist()
        return True
    
    def similarity_search(self, query, chunking_type="basic", k=5):
        """청킹 타입별 유사도 검색"""
        vectorstore = self._get_vectorstore_by_type(chunking_type)
        return vectorstore.similarity_search(query, k=k)
    
    def similarity_search_with_score(self, query, chunking_type="basic", k=5):
        """청킹 타입별 점수 포함 유사도 검색"""
        vectorstore = self._get_vectorstore_by_type(chunking_type)
        return vectorstore.similarity_search_with_relevance_scores(query, k=k)
    
    def dual_search(self, query, k=5):
        """기본/커스텀 두 벡터스토어에서 동시 검색"""
        try:
            basic_results = self.similarity_search_with_score(query, "basic", k//2 + 1)
            custom_results = self.similarity_search_with_score(query, "custom", k//2 + 1)
            
            # 결과 합치기 및 점수순 정렬
            all_results = []
            
            # 기본 청킹 결과 추가
            for doc, score in basic_results:
                doc.metadata['search_source'] = 'basic_chunking'
                all_results.append((doc, score))
            
            # 커스텀 청킹 결과 추가
            for doc, score in custom_results:
                doc.metadata['search_source'] = 'custom_chunking' 
                all_results.append((doc, score))
            
            # 점수순 정렬 후 상위 k개 반환
            all_results.sort(key=lambda x: x[1], reverse=True)
            return all_results[:k]
            
        except Exception as e:
            print(f"⚠️ 이중 검색 오류: {e}")
            # 폴백: 기본 검색만 수행
            return self.similarity_search_with_score(query, "basic", k)
    
    def _get_vectorstore_by_type(self, chunking_type):
        """청킹 타입에 따른 벡터스토어 반환"""
        if chunking_type == "custom" or chunking_type == "custom_delimiter":
            return self.custom_vectorstore
        else:
            return self.basic_vectorstore
    
    def get_document_count(self, chunking_type=None):
        """문서 수 조회"""
        if chunking_type == "basic":
            try:
                return self.basic_vectorstore._collection.count()
            except:
                return 0
        elif chunking_type == "custom":
            try:
                return self.custom_vectorstore._collection.count()
            except:
                return 0
        else:
            # 전체 문서 수
            try:
                basic_count = self.basic_vectorstore._collection.count()
                custom_count = self.custom_vectorstore._collection.count()
                return {"basic": basic_count, "custom": custom_count, "total": basic_count + custom_count}
            except:
                return {"basic": 0, "custom": 0, "total": 0}
    
    def clear_vectorstore(self, chunking_type="all"):
        """벡터스토어 삭제"""
        if chunking_type == "all" or chunking_type == "basic":
            try:
                self.basic_vectorstore.delete_collection()
            except:
                pass
                
        if chunking_type == "all" or chunking_type == "custom":
            try:
                self.custom_vectorstore.delete_collection()
            except:
                pass
        
        # 재초기화
        self.initialize_vectorstores()
        
        # 캐시 삭제
        try:
            from services.hybrid_cache_manager import HybridCacheManager
            cache_manager = HybridCacheManager()
            result = cache_manager.clear_all()
            print(f"🗑️ 벡터DB 초기화와 함께 캐시 삭제됨")
        except Exception as e:
            print(f"⚠️ 캐시 삭제 중 오류: {e}")
    
    def get_retriever(self, chunking_type="basic", k=5):
        """청킹 타입별 리트리버 반환"""
        vectorstore = self._get_vectorstore_by_type(chunking_type)
        return vectorstore.as_retriever(search_kwargs={"k": k})

# 전역 이중 벡터스토어 인스턴스
_dual_vectorstore_instance = None

def get_dual_vectorstore():
    """전역 이중 벡터스토어 인스턴스 반환"""
    global _dual_vectorstore_instance
    if _dual_vectorstore_instance is None:
        from models.embeddings import EmbeddingManager
        embedding_manager = EmbeddingManager()
        _dual_vectorstore_instance = DualVectorStoreManager(embedding_manager.get_embeddings())
    return _dual_vectorstore_instance

def reset_dual_vectorstore():
    """이중 벡터스토어 인스턴스 리셋"""
    global _dual_vectorstore_instance
    _dual_vectorstore_instance = None