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
        """청킹 타입별 점수 포함 유사도 검색 - BGE-M3 최적화된 유사도 계산"""
        vectorstore = self._get_vectorstore_by_type(chunking_type)
        
        # ChromaDB의 similarity_search_with_score 사용 (거리값 반환)
        results = vectorstore.similarity_search_with_score(query, k=k)
        
        # BGE-M3 임베딩에 최적화된 거리-유사도 변환
        converted_results = []
        for doc, distance in results:
            # BGE-M3는 cosine distance를 사용하므로 0~2 범위의 값이 나옴
            # 더 정교한 유사도 계산 적용
            if distance <= 2.0:
                # Cosine distance -> similarity 변환
                # cosine similarity = 1 - cosine distance
                base_similarity = max(0, min(1, 1 - distance))
                
                # BGE-M3 특성을 고려한 스케일링
                # 0.3 이하: 매우 높은 유사도 (0.85~1.0)
                # 0.3~0.6: 높은 유사도 (0.7~0.85)  
                # 0.6~0.9: 중간 유사도 (0.5~0.7)
                # 0.9~1.2: 낮은 유사도 (0.3~0.5)
                # 1.2+: 매우 낮은 유사도 (0.0~0.3)
                
                if distance <= 0.3:
                    # 매우 높은 유사도: 85-100%
                    similarity = 0.85 + (0.3 - distance) / 0.3 * 0.15
                elif distance <= 0.6:
                    # 높은 유사도: 70-85%
                    similarity = 0.70 + (0.6 - distance) / 0.3 * 0.15
                elif distance <= 0.9:
                    # 중간 유사도: 50-70%
                    similarity = 0.50 + (0.9 - distance) / 0.3 * 0.20
                elif distance <= 1.2:
                    # 낮은 유사도: 30-50%
                    similarity = 0.30 + (1.2 - distance) / 0.3 * 0.20
                else:
                    # 매우 낮은 유사도: 0-30%
                    similarity = max(0, 0.30 - (distance - 1.2) / 0.8 * 0.30)
                    
            else:
                # L2 distance인 경우 (BGE-M3에서는 드물지만 예외처리)
                import math
                similarity = math.exp(-distance / 2048.0)  # 1024차원 * 2 스케일
            
            # 시맨틱 관련도 보정 (선택적)
            try:
                from services.enhanced_query_processor import EnhancedQueryProcessor
                processor = EnhancedQueryProcessor()
                semantic_bonus = processor.calculate_semantic_relevance(query, doc.page_content[:500])
                # 시맨틱 보너스를 최대 10% 추가
                similarity = min(1.0, similarity + semantic_bonus * 0.1)
            except:
                pass  # 에러 발생시 기본 유사도만 사용
                
            converted_results.append((doc, similarity))
        
        return converted_results
    
    def dual_search(self, query, k=5):
        """기본/커스텀 두 벡터스토어에서 동시 검색 - 강화된 개인화 및 시맨틱 검색"""
        try:
            # 질의 확장 처리
            from services.enhanced_query_processor import EnhancedQueryProcessor
            processor = EnhancedQueryProcessor()
            
            # 개인화 쿼리 및 카드 관련 쿼리 감지
            intents = processor.extract_intent_keywords(query)
            is_personalized = bool(intents["person"])
            is_card_query = bool(intents["card_type"]) or any(keyword in query for keyword in ["카드", "발급", "회원은행"])
            
            print(f"🔍 [DualSearch] 개인화: {is_personalized}, 카드관련: {is_card_query}")
            print(f"🎯 [DualSearch] 의도분석: {intents}")
            
            all_results = []
            
            if is_personalized and is_card_query:
                # 개인화된 카드 쿼리: 가장 정교한 검색
                print(f"💳 [DualSearch] 개인화 카드 쿼리 처리")
                
                # 1. 원본 쿼리로 기본/커스텀 검색
                basic_results = self.similarity_search_with_score(query, "basic", k*2)
                custom_results = self.similarity_search_with_score(query, "custom", k*2)
                
                for doc, score in basic_results:
                    doc.metadata['search_source'] = 'basic_personalized'
                    # 개인명이 포함된 문서에 가점
                    person_bonus = 0.1 if any(person in doc.page_content for person in intents["person"]) else 0
                    all_results.append((doc, min(1.0, score + person_bonus)))
                
                for doc, score in custom_results:
                    doc.metadata['search_source'] = 'custom_personalized'
                    person_bonus = 0.1 if any(person in doc.page_content for person in intents["person"]) else 0
                    all_results.append((doc, min(1.0, score + person_bonus)))
                
                # 2. 확장된 개인화 쿼리들로 추가 검색
                expanded_queries = processor.build_hybrid_search_queries(query)
                for query_info in expanded_queries[1:4]:  # 상위 3개 확장 쿼리
                    try:
                        exp_basic = self.similarity_search_with_score(query_info["query"], "basic", 2)
                        for doc, score in exp_basic:
                            doc.metadata['search_source'] = f'basic_expanded_{query_info["type"]}'
                            weighted_score = score * query_info["weight"]
                            all_results.append((doc, weighted_score))
                    except:
                        continue
                
                # 3. 특정 은행/카드사 관련 문서 부스팅
                for bank in intents.get("bank", []):
                    try:
                        bank_query = f"{bank} 카드 발급 안내"
                        bank_results = self.similarity_search_with_score(bank_query, "basic", 3)
                        for doc, score in bank_results:
                            doc.metadata['search_source'] = f'basic_bank_{bank}'
                            all_results.append((doc, score * 0.95))  # 약간의 가중치
                    except:
                        continue
                        
                # 상위 20개 반환 (개인화에서는 더 많은 컨텍스트 필요)
                all_results.sort(key=lambda x: x[1], reverse=True)
                unique_results = self._remove_duplicates(all_results)
                return unique_results[:20]
                
            elif is_card_query:
                # 일반 카드 쿼리: 기존 강화 로직
                print(f"🏦 [DualSearch] 일반 카드 쿼리 처리")
                extended_keywords = [
                    f"{query} 발급절차",
                    f"{query} 신청방법", 
                    "회원은행별 카드발급안내",
                    "카드 발급 절차 안내",
                    "신청 준비서류",
                    "카드 심사 과정"
                ]
                
                # 기본/커스텀 검색
                basic_results = self.similarity_search_with_score(query, "basic", k)
                custom_results = self.similarity_search_with_score(query, "custom", k)
                
                for doc, score in basic_results:
                    doc.metadata['search_source'] = 'basic_chunking'
                    all_results.append((doc, score))
                
                for doc, score in custom_results:
                    doc.metadata['search_source'] = 'custom_chunking' 
                    all_results.append((doc, score))
                
                # 확장 키워드 검색
                for keyword in extended_keywords[:3]:
                    try:
                        extended_basic = self.similarity_search_with_score(keyword, "basic", 2)
                        for doc, score in extended_basic:
                            doc.metadata['search_source'] = 'basic_chunking_extended'
                            all_results.append((doc, score * 0.9))
                    except:
                        continue
                
                all_results.sort(key=lambda x: x[1], reverse=True)
                unique_results = self._remove_duplicates(all_results)
                return unique_results[:15]
            
            else:
                # 일반 쿼리의 경우 기존 방식
                print(f"📄 [DualSearch] 일반 쿼리 처리")
                basic_results = self.similarity_search_with_score(query, "basic", k//2 + 1)
                custom_results = self.similarity_search_with_score(query, "custom", k//2 + 1)
                
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
                unique_results = self._remove_duplicates(all_results)
                return unique_results[:k]
            
        except Exception as e:
            print(f"⚠️ 이중 검색 오류: {e}")
            import traceback
            print(f"🔍 상세 오류: {traceback.format_exc()}")
            # 폴백: 기본 검색만 수행
            return self.similarity_search_with_score(query, "basic", k)
    
    def _remove_duplicates(self, results):
        """중복 문서 제거 - 내용 기반"""
        unique_results = []
        seen_content = set()
        
        for doc, score in results:
            # 첫 200자로 중복 체크 (더 정확한 중복 감지)
            content_hash = hash(doc.page_content[:200])
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append((doc, score))
        
        return unique_results
    
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