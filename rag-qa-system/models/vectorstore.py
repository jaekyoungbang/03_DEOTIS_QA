import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from config import Config
import os

class VectorStoreManager:
    def __init__(self, embedding_function):
        self.embedding_function = embedding_function
        self.vectorstore = None
        self.collection_name = Config.CHROMA_COLLECTION_NAME
        self.persist_directory = Config.CHROMA_PERSIST_DIRECTORY
        self.initialize_vectorstore()
    
    def initialize_vectorstore(self):
        """Initialize ChromaDB vector store"""
        # Create persist directory if it doesn't exist
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize ChromaDB with persistent storage
        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embedding_function,
            persist_directory=self.persist_directory,
            collection_metadata={"hnsw:space": "cosine"}
        )
    
    def add_documents(self, documents, ids=None):
        """Add documents to the vector store"""
        if ids:
            self.vectorstore.add_documents(documents=documents, ids=ids)
        else:
            self.vectorstore.add_documents(documents=documents)
        # Persist changes
        self.vectorstore.persist()
        return True
    
    def similarity_search(self, query, k=5):
        """Perform similarity search"""
        return self.vectorstore.similarity_search(query, k=k)
    
    def similarity_search_with_score(self, query, k=5):
        """Perform similarity search with relevance scores"""
        return self.vectorstore.similarity_search_with_relevance_scores(query, k=k)
    
    def delete_collection(self, clear_cache=True):
        """Delete the entire collection and reinitialize"""
        try:
            self.vectorstore.delete_collection()
        except Exception:
            pass  # Collection might not exist
        
        # Clear all caches when vector DB is reset
        if clear_cache:
            try:
                from services.hybrid_cache_manager import HybridCacheManager
                cache_manager = HybridCacheManager()
                result = cache_manager.clear_all()
                print(f"🗑️ 벡터DB 초기화와 함께 캐시 삭제됨: Redis {result['redis_cleared']}개, RDB {result['popular_cleared']}개")
            except Exception as e:
                print(f"⚠️ 캐시 삭제 중 오류: {e}")
        
        # Reinitialize after deletion
        self.initialize_vectorstore()
    
    def get_retriever(self, k=5):
        """Get a retriever interface for the vector store"""
        return self.vectorstore.as_retriever(
            search_kwargs={"k": k}
        )
    
    def get_document_count(self):
        """Get the number of documents in the vector store"""
        try:
            return self.vectorstore._collection.count()
        except Exception:
            # If collection doesn't exist, return 0
            return 0

# 전역 벡터스토어 인스턴스
_vectorstore_instance = None

def get_vectorstore():
    """전역 벡터스토어 인스턴스 반환"""
    global _vectorstore_instance
    if _vectorstore_instance is None:
        from models.embeddings import EmbeddingManager
        embedding_manager = EmbeddingManager()
        _vectorstore_instance = VectorStoreManager(embedding_manager.get_embeddings())
    return _vectorstore_instance.vectorstore

def reset_vectorstore():
    """벡터스토어 인스턴스 리셋"""
    global _vectorstore_instance
    _vectorstore_instance = None