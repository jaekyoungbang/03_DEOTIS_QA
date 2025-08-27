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
        
        # ChromaDB 강력한 호환성 해결
        try:
            # 먼저 완전히 깨끗한 환경에서 시작
            if os.path.exists(self.persist_directory):
                import shutil
                shutil.rmtree(self.persist_directory, ignore_errors=True)
                print(f"🗑️ 기존 ChromaDB 완전 삭제")
            
            # 새 디렉토리 생성
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # ChromaDB 초기화 (가장 기본적인 설정으로)
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embedding_function,
                persist_directory=self.persist_directory
            )
            print(f"✅ ChromaDB 새로 생성 완료: {self.collection_name}")
        except Exception as e:
            print(f"⚠️ ChromaDB 초기화 오류: {e}")
            # 기존 벡터DB 완전 삭제 후 재생성
            try:
                if os.path.exists(self.persist_directory):
                    import shutil
                    import time
                    # Windows 파일 잠금 해제를 위해 잠시 대기
                    time.sleep(1)
                    
                    # 강제 삭제 시도 (Windows 호환)
                    try:
                        shutil.rmtree(self.persist_directory, ignore_errors=True)
                        time.sleep(0.5)  # 삭제 완료 대기
                        print(f"🗑️ 기존 벡터DB 완전 삭제: {self.persist_directory}")
                    except Exception as delete_err:
                        # 삭제 실패시 고유한 디렉토리명 사용
                        print(f"⚠️ 삭제 실패, 새 디렉토리 사용: {delete_err}")
                        self.persist_directory = f"./data/vectordb_{int(time.time())}"
                        print(f"📁 새 디렉토리: {self.persist_directory}")
                
                # 새 디렉토리 생성
                os.makedirs(self.persist_directory, exist_ok=True)
                print(f"📁 새 벡터DB 디렉토리 생성")
                
                # 다시 시도 (메타데이터 없이)
                self.vectorstore = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embedding_function,
                    persist_directory=self.persist_directory
                )
                print("✅ ChromaDB 재생성 완료")
                
            except Exception as retry_error:
                print(f"❌ ChromaDB 재생성 실패: {retry_error}")
                # 최후의 수단: 고유한 컬렉션명 사용
                self.collection_name = f"{self.collection_name}_{uuid.uuid4().hex[:8]}"
                self.vectorstore = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embedding_function,
                    persist_directory=self.persist_directory
                )
                print(f"✅ 고유 컬렉션명으로 생성: {self.collection_name}")
    
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
        """Perform similarity search with distance scores (0=perfect match, higher=less similar)"""
        # ChromaDB의 similarity_search_with_score는 거리값(낮을수록 유사)을 반환
        # similarity_search_with_relevance_scores는 음수값을 반환하므로 사용하지 않음
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        
        # 거리를 유사도로 변환 (0~1 사이, 1에 가까울수록 유사)
        converted_results = []
        for doc, distance in results:
            # ChromaDB가 L2 distance를 반환하는 경우를 처리
            # L2 distance가 큰 값(>2)이면 L2 거리, 작은 값이면 cosine distance로 가정
            if distance > 2:
                # L2 거리를 유사도로 변환: exp(-distance/scale)로 더 부드러운 변환
                import math
                similarity = math.exp(-distance / 100.0)  # 스케일 조정으로 더 의미있는 범위
            else:
                # cosine distance인 경우: similarity = 1 - distance  
                similarity = max(0, 1 - distance)
            converted_results.append((doc, similarity))
        
        return converted_results
    
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
        """기본/커스텀 벡터스토어 초기화 - 완전 새로 시작"""
        # ChromaDB 완전 새로 시작 (호환성 보장)
        if os.path.exists(self.persist_directory):
            import shutil
            shutil.rmtree(self.persist_directory, ignore_errors=True)
            print(f"🗑️ 기존 DualVectorStore 완전 삭제")
        
        # 새 디렉토리 생성
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # 기본 청킹용 벡터스토어 (완전 새로 생성)
        try:
            self.basic_vectorstore = Chroma(
                collection_name=self.basic_collection_name,
                embedding_function=self.embedding_function,
                persist_directory=self.persist_directory
            )
            print(f"✅ Basic 벡터스토어 새로 생성: {self.basic_collection_name}")
        except Exception as e:
            print(f"❌ Basic 벡터스토어 생성 실패: {e}")
            raise e
        
        # 커스텀 청킹용 벡터스토어 (완전 새로 생성)  
        try:
            self.custom_vectorstore = Chroma(
                collection_name=self.custom_collection_name,
                embedding_function=self.embedding_function,
                persist_directory=self.persist_directory
            )
            print(f"✅ Custom 벡터스토어 새로 생성: {self.custom_collection_name}")
        except Exception as e:
            print(f"❌ Custom 벡터스토어 생성 실패: {e}")
            raise e
    
    def _reset_vectorstore(self, store_type):
        """벡터스토어 재설정 - Windows 호환"""
        import uuid
        
        try:
            # 기존 벡터DB 완전 삭제 (Windows 호환)
            if os.path.exists(self.persist_directory):
                import shutil
                import time
                time.sleep(1)  # Windows 파일 잠금 해제 대기
                
                try:
                    shutil.rmtree(self.persist_directory, ignore_errors=True)
                    time.sleep(0.5)
                    print(f"🗑️ 기존 벡터DB 완전 삭제: {self.persist_directory}")
                except Exception as delete_err:
                    print(f"⚠️ 삭제 실패, 새 디렉토리 사용: {delete_err}")
                    self.persist_directory = f"./data/vectordb_{int(time.time())}"
            
            # 새 디렉토리 생성
            os.makedirs(self.persist_directory, exist_ok=True)
            print(f"📁 새 벡터DB 디렉토리 생성")
        except Exception as e:
            print(f"⚠️ 디렉토리 처리 오류: {e}")
            # 고유한 컬렉션명으로 처리
            if store_type == "basic":
                self.basic_collection_name = f"{self.basic_collection_name}_{uuid.uuid4().hex[:8]}"
            elif store_type == "custom":
                self.custom_collection_name = f"{self.custom_collection_name}_{uuid.uuid4().hex[:8]}"
        
        if store_type == "basic":
            self.basic_vectorstore = Chroma(
                collection_name=self.basic_collection_name,
                embedding_function=self.embedding_function,
                persist_directory=self.persist_directory
            )
        elif store_type == "custom":
            self.custom_vectorstore = Chroma(
                collection_name=self.custom_collection_name,
                embedding_function=self.embedding_function,
                persist_directory=self.persist_directory
            )
        print(f"✅ {store_type} 벡터스토어 재생성 완료")
    
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
        """청킹 타입별 점수 포함 유사도 검색 - 거리를 유사도로 변환"""
        vectorstore = self._get_vectorstore_by_type(chunking_type)
        
        # ChromaDB의 similarity_search_with_score 사용 (거리값 반환)
        results = vectorstore.similarity_search_with_score(query, k=k)
        
        # 거리를 유사도로 변환 (0~1 사이, 1에 가까울수록 유사)
        converted_results = []
        for doc, distance in results:
            # ChromaDB가 L2 distance를 반환하는 경우를 처리
            # L2 distance가 큰 값(>2)이면 L2 거리, 작은 값이면 cosine distance로 가정
            if distance > 2:
                # L2 거리를 유사도로 변환: exp(-distance/scale)로 더 부드러운 변환
                import math
                similarity = math.exp(-distance / 100.0)  # 스케일 조정으로 더 의미있는 범위
            else:
                # cosine distance인 경우: similarity = 1 - distance  
                similarity = max(0, 1 - distance)
            converted_results.append((doc, similarity))
        
        return converted_results
    
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

# 전역 벡터스토어 인스턴스
_vectorstore_instance = None
_dual_vectorstore_instance = None

def get_vectorstore():
    """전역 벡터스토어 인스턴스 반환 (기존 호환성)"""
    global _vectorstore_instance
    if _vectorstore_instance is None:
        from models.embeddings import EmbeddingManager
        embedding_manager = EmbeddingManager()
        _vectorstore_instance = VectorStoreManager(embedding_manager.get_embeddings())
    return _vectorstore_instance.vectorstore

def get_dual_vectorstore():
    """전역 DualVectorStoreManager 인스턴스 반환"""
    global _dual_vectorstore_instance
    if _dual_vectorstore_instance is None:
        from models.embeddings import EmbeddingManager
        embedding_manager = EmbeddingManager()
        _dual_vectorstore_instance = DualVectorStoreManager(embedding_manager.get_embeddings())
    return _dual_vectorstore_instance

def reset_vectorstore():
    """벡터스토어 인스턴스 리셋"""
    global _vectorstore_instance
    _vectorstore_instance = None