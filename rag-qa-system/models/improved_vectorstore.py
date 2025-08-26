import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from config import Config
import os
import shutil
import time

class ImprovedVectorStoreManager:
    """개선된 벡터스토어 관리자 - 완전한 삭제/재로드 지원"""
    
    def __init__(self, embedding_function):
        self.embedding_function = embedding_function
        self.vectorstore = None
        self.collection_name = Config.CHROMA_COLLECTION_NAME
        self.persist_directory = Config.CHROMA_PERSIST_DIRECTORY
        self.client = None
        self.initialize_vectorstore()
    
    def initialize_vectorstore(self):
        """ChromaDB 벡터스토어 초기화"""
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Langchain Chroma 래퍼 초기화
        self.vectorstore = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embedding_function,
            persist_directory=self.persist_directory,
            collection_metadata={"hnsw:space": "cosine"}
        )
    
    def add_documents(self, documents, ids=None):
        """문서 추가"""
        if ids:
            self.vectorstore.add_documents(documents=documents, ids=ids)
        else:
            self.vectorstore.add_documents(documents=documents)
        # 변경사항 저장
        self.vectorstore.persist()
        return True
    
    def similarity_search(self, query, k=5):
        """유사도 검색"""
        return self.vectorstore.similarity_search(query, k=k)
    
    def similarity_search_with_score(self, query, k=5):
        """점수와 함께 유사도 검색"""
        return self.vectorstore.similarity_search_with_relevance_scores(query, k=k)
    
    def delete_collection(self, clear_cache=True):
        """컬렉션 완전 삭제 - 물리적 파일까지 삭제"""
        try:
            # 1. ChromaDB 컬렉션 삭제 시도
            try:
                self.client.delete_collection(name=self.collection_name)
                print(f"✅ 컬렉션 '{self.collection_name}' 삭제됨")
            except Exception as e:
                print(f"⚠️  컬렉션 삭제 시도: {e}")
            
            # 2. 벡터스토어 객체 해제
            self.vectorstore = None
            self.client = None
            
            # 3. 잠시 대기 (파일 핸들 해제)
            time.sleep(0.5)
            
            # 4. 물리적 디렉토리 삭제
            if os.path.exists(self.persist_directory):
                try:
                    shutil.rmtree(self.persist_directory)
                    print(f"✅ 벡터DB 디렉토리 완전 삭제: {self.persist_directory}")
                except Exception as e:
                    print(f"❌ 디렉토리 삭제 실패: {e}")
                    # 대안: 파일별 삭제
                    for file in os.listdir(self.persist_directory):
                        try:
                            file_path = os.path.join(self.persist_directory, file)
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                        except Exception as fe:
                            print(f"파일 삭제 실패: {file} - {fe}")
            
            # 5. 캐시 삭제
            if clear_cache:
                try:
                    from services.hybrid_cache_manager import HybridCacheManager
                    cache_manager = HybridCacheManager()
                    result = cache_manager.clear_all()
                    print(f"🗑️ 캐시 삭제: Redis {result['redis_cleared']}개, RDB {result['popular_cleared']}개")
                except Exception as e:
                    print(f"⚠️ 캐시 삭제 중 오류: {e}")
            
            # 6. 재초기화
            print("🔄 벡터스토어 재초기화 중...")
            self.initialize_vectorstore()
            print("✅ 벡터스토어 재초기화 완료")
            
        except Exception as e:
            print(f"❌ 컬렉션 삭제 중 오류: {e}")
            # 강제 재초기화
            self.initialize_vectorstore()
    
    def get_retriever(self, k=5):
        """검색기 인터페이스 반환"""
        return self.vectorstore.as_retriever(
            search_kwargs={"k": k}
        )
    
    def get_document_count(self):
        """문서 수 확인"""
        try:
            if self.vectorstore and self.vectorstore._collection:
                return self.vectorstore._collection.count()
            return 0
        except Exception:
            return 0
    
    def clear_and_reload(self, documents):
        """완전 삭제 후 재로드 - 원자적 작업"""
        print("🔄 벡터DB 완전 초기화 및 재로드 시작...")
        
        # 1. 완전 삭제
        self.delete_collection(clear_cache=True)
        
        # 2. 새 문서 로드
        if documents:
            print(f"📄 {len(documents)}개 문서 로드 중...")
            self.add_documents(documents)
            print("✅ 문서 로드 완료")
        
        return self.get_document_count()


class DualVectorStoreManager:
    """이중 벡터스토어 관리자 - 기본/커스텀 청킹 분리 저장"""
    
    def __init__(self, embedding_function):
        self.embedding_function = embedding_function
        self.basic_manager = None
        self.custom_manager = None
        self.persist_directory = Config.CHROMA_PERSIST_DIRECTORY
        
        # 별도 디렉토리 사용
        self.basic_persist_dir = os.path.join(self.persist_directory, "basic")
        self.custom_persist_dir = os.path.join(self.persist_directory, "custom")
        
        self.initialize_managers()
    
    def initialize_managers(self):
        """기본/커스텀 매니저 초기화"""
        # 기본 청킹 매니저
        Config.CHROMA_PERSIST_DIRECTORY = self.basic_persist_dir
        Config.CHROMA_COLLECTION_NAME = "basic_chunks"
        self.basic_manager = ImprovedVectorStoreManager(self.embedding_function)
        
        # 커스텀 청킹 매니저
        Config.CHROMA_PERSIST_DIRECTORY = self.custom_persist_dir
        Config.CHROMA_COLLECTION_NAME = "custom_chunks"
        self.custom_manager = ImprovedVectorStoreManager(self.embedding_function)
        
        # 원래 설정 복원
        Config.CHROMA_PERSIST_DIRECTORY = self.persist_directory
        Config.CHROMA_COLLECTION_NAME = "rag_documents"
    
    def add_basic_documents(self, documents):
        """기본 청킹 문서 추가"""
        return self.basic_manager.add_documents(documents)
    
    def add_custom_documents(self, documents):
        """커스텀 청킹 문서 추가"""
        return self.custom_manager.add_documents(documents)
    
    def dual_search(self, query, k=5):
        """두 벡터스토어에서 동시 검색"""
        basic_results = self.basic_manager.similarity_search_with_score(query, k)
        custom_results = self.custom_manager.similarity_search_with_score(query, k)
        
        # 결과 병합 및 점수순 정렬
        all_results = []
        
        for doc, score in basic_results:
            all_results.append({
                'document': doc,
                'score': score,
                'source': 'basic',
                'metadata': doc.metadata
            })
        
        for doc, score in custom_results:
            all_results.append({
                'document': doc,
                'score': score,
                'source': 'custom',
                'metadata': doc.metadata
            })
        
        # 점수순 정렬 (높은 점수 우선)
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        # 상위 k개만 반환
        return all_results[:k]
    
    def clear_all(self):
        """모든 벡터스토어 삭제"""
        print("🗑️ 모든 벡터스토어 삭제 중...")
        self.basic_manager.delete_collection(clear_cache=False)
        self.custom_manager.delete_collection(clear_cache=False)
        
        # 캐시도 삭제
        try:
            from services.hybrid_cache_manager import HybridCacheManager
            cache_manager = HybridCacheManager()
            cache_manager.clear_all()
        except:
            pass
        
        print("✅ 모든 벡터스토어 삭제 완료")
    
    def get_stats(self):
        """통계 정보 반환"""
        return {
            'basic_count': self.basic_manager.get_document_count(),
            'custom_count': self.custom_manager.get_document_count(),
            'total_count': (
                self.basic_manager.get_document_count() + 
                self.custom_manager.get_document_count()
            )
        }