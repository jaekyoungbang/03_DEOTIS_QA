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
            persist_directory=self.persist_directory
        )
        
        # 커스텀 청킹용 벡터스토어  
        self.custom_vectorstore = Chroma(
            collection_name=self.custom_collection_name,
            embedding_function=self.embedding_function,
            persist_directory=self.persist_directory
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
                similarity = math.exp(-distance / 1000.0)  # BGE-M3 1024차원에 맞는 스케일 조정
            else:
                # cosine distance인 경우: similarity = 1 - distance  
                similarity = max(0, 1 - distance)
            converted_results.append((doc, similarity))
        
        return converted_results
    
    def dual_search(self, query, k=5):
        """기본/커스텀 두 벡터스토어에서 동시 검색 - 강화된 카드 분석"""
        try:
            # 카드 발급 관련 쿼리인지 확인
            card_keywords = ["카드", "발급", "회원", "은행", "카드발급", "김명정"]
            is_card_query = any(keyword in query for keyword in card_keywords)
            
            if is_card_query:
                # 카드 관련 쿼리의 경우 더 많은 결과 검색 및 상세 키워드 추가
                extended_keywords = [
                    f"{query} 발급절차",
                    f"{query} 신청방법",
                    f"{query} 심사과정", 
                    "회원은행별 카드발급안내",
                    "카드 발급 절차",
                    "신청 준비",
                    "심사 과정",
                    "카드 발급"
                ]
                
                all_results = []
                
                # 1. 기본 검색
                basic_results = self.similarity_search_with_score(query, "basic", k)
                for doc, score in basic_results:
                    doc.metadata['search_source'] = 'basic_chunking'
                    all_results.append((doc, score))
                
                # 2. 커스텀 검색
                custom_results = self.similarity_search_with_score(query, "custom", k)
                for doc, score in custom_results:
                    doc.metadata['search_source'] = 'custom_chunking' 
                    all_results.append((doc, score))
                
                # 3. 확장된 키워드로 추가 검색 (basic에서 상세 정보)
                for keyword in extended_keywords[:3]:  # 상위 3개만 검색
                    try:
                        extended_basic = self.similarity_search_with_score(keyword, "basic", 3)
                        for doc, score in extended_basic:
                            doc.metadata['search_source'] = 'basic_chunking_extended'
                            # 중복 문서 제거를 위해 내용 비교
                            doc_content = doc.page_content[:100]  # 첫 100자로 중복 체크
                            if not any(existing_doc.page_content[:100] == doc_content for existing_doc, _ in all_results):
                                all_results.append((doc, score * 0.9))  # 약간 낮은 점수 부여
                    except:
                        continue
                
                # 점수순 정렬 후 상위 15개 반환 (더 많은 컨텍스트)
                all_results.sort(key=lambda x: x[1], reverse=True)
                return all_results[:15]
            
            else:
                # 일반 쿼리의 경우 기존 방식
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
    
    def enhanced_card_search(self, query, k=5):
        """카드 관련 쿼리에 최적화된 검색 - 이미지 포함 문서 우선"""
        try:
            # 다양한 카드 발급 관련 키워드로 검색
            search_terms = [
                query,
                "카드발급절차",
                "회원은행별 카드발급안내", 
                "신청 준비 서류",
                "심사 과정",
                "발급 팁",
                "승인률 높이는 방법"
            ]
            
            all_results = []
            
            # 각 검색어로 basic 컨렉션에서 검색
            for term in search_terms:
                try:
                    results = self.similarity_search_with_score(term, "basic", 3)
                    for doc, score in results:
                        doc.metadata['search_source'] = 'basic_enhanced'
                        # 이미지 포함 문서 우선 처리
                        if '![' in doc.page_content or '.gif' in doc.page_content or '.png' in doc.page_content:
                            score = score * 1.2  # 이미지 포함 문서 가점 부여
                            doc.metadata['has_image'] = True
                        all_results.append((doc, score))
                except:
                    continue
            
            # custom 컨렉션에서도 검색
            custom_results = self.similarity_search_with_score(query, "custom", k)
            for doc, score in custom_results:
                doc.metadata['search_source'] = 'custom_chunking'
                all_results.append((doc, score))
            
            # 중복 제거 및 점수순 정렬
            unique_results = []
            seen_content = set()
            
            for doc, score in all_results:
                content_hash = hash(doc.page_content[:200])  # 첫 200자로 중복 체크
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    unique_results.append((doc, score))
            
            # 점수순 정렬 후 상위 k*2 반환 (더 많은 컨텍스트)
            unique_results.sort(key=lambda x: x[1], reverse=True)
            return unique_results[:k*2]
            
        except Exception as e:
            print(f"⚠️ 강화된 카드 검색 오류: {e}")
            return self.dual_search(query, k)
    
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