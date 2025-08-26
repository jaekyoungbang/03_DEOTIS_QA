from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from models.llm import LLMManager
from models.embeddings import EmbeddingManager
from models.vectorstore import VectorStoreManager
from models.dual_vectorstore import DualVectorStoreManager, get_dual_vectorstore
from utils.error_handler import detect_error_type, format_error_response
from services.cache_factory import CacheFactory
# from services.query_analyzer import QueryAnalyzer
# from services.reranker import SearchReranker
import time
import sqlite3
import os
from datetime import datetime
from typing import List

class RAGChain:
    def __init__(self):
        self.llm_manager = LLMManager()
        self.embedding_manager = EmbeddingManager()
        self.vectorstore_manager = VectorStoreManager(
            self.embedding_manager.get_embeddings()
        )
        # 이중 벡터스토어 매니저 추가
        self.dual_vectorstore_manager = get_dual_vectorstore()
        # Expose vectorstore for external access
        self.vectorstore = self.vectorstore_manager
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        self.qa_chain = None
        self.cache_manager = CacheFactory.get_cache_manager()  # Use cache factory
        # self.query_analyzer = QueryAnalyzer()  # 질문 분석기
        # self.reranker = SearchReranker()  # 재순위 시스템
        self.stats_db_path = "./data/search_stats.db"
        self.initialize_stats_db()
        self.initialize_chain()
    
    def initialize_stats_db(self):
        """검색 통계 데이터베이스 초기화"""
        os.makedirs(os.path.dirname(self.stats_db_path), exist_ok=True)
        
        with sqlite3.connect(self.stats_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    query_time REAL NOT NULL,
                    cache_hit BOOLEAN NOT NULL,
                    cache_time REAL,
                    total_time REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS global_stats (
                    id INTEGER PRIMARY KEY,
                    total_searches INTEGER DEFAULT 0,
                    total_cache_hits INTEGER DEFAULT 0,
                    avg_query_time REAL DEFAULT 0.0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Initialize global stats if empty
            cursor.execute('SELECT COUNT(*) FROM global_stats')
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO global_stats (id, total_searches, total_cache_hits, avg_query_time)
                    VALUES (1, 0, 0, 0.0)
                ''')
            
            conn.commit()
    
    def update_search_stats(self, question, query_time, cache_hit, cache_time=None, total_time=None):
        """검색 통계 업데이트"""
        try:
            with sqlite3.connect(self.stats_db_path) as conn:
                cursor = conn.cursor()
                
                # Insert individual search record
                cursor.execute('''
                    INSERT INTO search_stats (question, query_time, cache_hit, cache_time, total_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (question, query_time, cache_hit, cache_time, total_time or query_time))
                
                # Update global stats
                cursor.execute('''
                    UPDATE global_stats SET 
                        total_searches = total_searches + 1,
                        total_cache_hits = total_cache_hits + ?,
                        avg_query_time = (
                            SELECT AVG(query_time) FROM search_stats 
                            WHERE cache_hit = 0
                        ),
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = 1
                ''', (1 if cache_hit else 0,))
                
                conn.commit()
        except Exception as e:
            print(f"⚠️ 검색 통계 업데이트 오류: {e}")
    
    def get_search_stats(self):
        """검색 통계 조회"""
        try:
            with sqlite3.connect(self.stats_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT total_searches, total_cache_hits, avg_query_time, last_updated
                    FROM global_stats WHERE id = 1
                ''')
                result = cursor.fetchone()
                
                if result:
                    total_searches, total_cache_hits, avg_query_time, last_updated = result
                    cache_hit_rate = (total_cache_hits / total_searches * 100) if total_searches > 0 else 0
                    
                    return {
                        "total_searches": total_searches,
                        "total_cache_hits": total_cache_hits,
                        "cache_hit_rate": round(cache_hit_rate, 1),
                        "avg_query_time": round(avg_query_time or 0, 3),
                        "last_updated": last_updated
                    }
                
        except Exception as e:
            print(f"⚠️ 검색 통계 조회 오류: {e}")
            
        return {
            "total_searches": 0,
            "total_cache_hits": 0,
            "cache_hit_rate": 0.0,
            "avg_query_time": 0.0,
            "last_updated": None
        }
    
    def initialize_chain(self):
        """Initialize the RAG chain"""
        # Custom prompt template
        prompt_template = """당신은 문서 기반 질문 답변 시스템입니다.
        주어진 문서 내용을 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 제공하세요.

        ## 핵심 원칙
        1. **정확성 우선**: 문서에 명시된 내용만을 바탕으로 답변
        2. **형식 일치**: 원본 문서의 형식(특히 표)을 최대한 유사하게 유지
        3. **깔끔한 구성**: 체계적이고 가독성 있는 답변 구조

        ## 답변 형식 규칙

        ### 표 형식 데이터 처리
        - 문서의 표 형식 데이터는 **반드시** markdown 표로 정확히 재현
        - 원본 표의 열 구성, 정렬, 구조를 최대한 유사하게 유지
        - 표 제목이나 설명이 있다면 표 위에 명시

        ## 답변 구조
        1. **핵심 답변**: 질문에 대한 직접적인 답 (표 형식이라면 표로)
        2. **출처 명확성**: 어떤 문서의 어떤 부분에서 정보를 얻었는지 자세히 언급

        ## 작성 스타일
        - 간결하고 명확한 한국어 사용
        - 불필요한 답변은 생략
        - 핵심 정보를 앞쪽에 배치
        - 목록이나 단계별 설명 시 적절한 번호나 불릿 포인트 활용

        ## 중첩된 내용
        - 내용중에 중첩된 내용은 1개로 통합 출력 

         ## 외부 검색 불가 
        - 현재 벡터DB에서 가져온 데이터만을 가지고 화면 설계 필요 
        - 외부 검색을 통한 데이터 조회 불가 

        
        컨텍스트: {context}
        
        질문: {question}
        
        답변:"""
        
        self.prompt_template = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # Create retrieval QA chain with improved retrieval
        # Use dual_vectorstore_manager with basic collection as default
        try:
            basic_retriever = self.dual_vectorstore_manager.get_retriever("basic", k=20)
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm_manager.get_llm(),
                chain_type="stuff",
                retriever=basic_retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": self.prompt_template}
            )
        except Exception as e:
            print(f"⚠️ Dual vectorstore not available, falling back to single vectorstore: {e}")
            # Fallback to single vectorstore
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm_manager.get_llm(),
                chain_type="stuff",
                retriever=self.vectorstore_manager.get_retriever(k=20),
                return_source_documents=True,
                chain_type_kwargs={"prompt": self.prompt_template}
            )
    
    def search_with_strategy(self, question, search_mode="basic", k=5):  # Reduced k for optimization
        """청킹 전략별 문서 검색"""
        try:
            if search_mode == "dual":
                # 이중 검색: 기본 + 커스텀
                results = self.dual_vectorstore_manager.dual_search(question, k)
                documents = [doc for doc, score in results]
                return documents
            elif search_mode == "custom":
                # 커스텀 청킹만 검색
                return self.dual_vectorstore_manager.similarity_search(question, "custom", k)
            else:
                # 기본 청킹만 검색 (기존 방식)
                return self.vectorstore_manager.similarity_search(question, k)
        except Exception as e:
            print(f"⚠️ 전략별 검색 오류: {e}")
            # 폴백: 기본 검색
            return self.vectorstore_manager.similarity_search(question, k)
    
    def get_conversational_chain(self):
        """Create a conversational retrieval chain with memory"""
        return ConversationalRetrievalChain.from_llm(
            llm=self.llm_manager.get_llm(),
            retriever=self.vectorstore_manager.get_retriever(k=5),
            memory=self.memory,
            return_source_documents=True,
            verbose=True
        )
    
    def query(self, question, use_memory=False, llm_model=None, use_cache=True, search_mode="basic"):
        """Query the RAG system with caching support and performance tracking"""
        start_time = time.time()
        cache_start_time = None
        cache_end_time = None
        query_start_time = None
        query_end_time = None
        
        try:
            # Check if vectorstore has documents before querying
            try:
                doc_count_info = self.dual_vectorstore_manager.get_document_count()
                doc_count = doc_count_info.get('total', 0)
            except Exception:
                # Fallback to single vectorstore
                doc_count = self.vectorstore_manager.get_document_count()
            
            if doc_count == 0:
                from utils.error_handler import ErrorCodes, format_error_response
                error_response = format_error_response(ErrorCodes.VDB_NO_COLLECTION)
                return {
                    "error": True,
                    "error_code": error_response["error_code"],
                    "title": error_response["title"],
                    "message": error_response["message"],
                    "solution": error_response["solution"],
                    "answer": f"❌ {error_response['title']}: {error_response['message']}"
                }
            
            # Check cache first (only for non-memory queries)
            cache_hit = False
            if use_cache and not use_memory:
                cache_start_time = time.time()
                cached_response = self.cache_manager.get(question, llm_model)
                cache_end_time = time.time()
                if cached_response:
                    # Add cache indicator and timing info
                    cache_time = cache_end_time - cache_start_time
                    total_time = time.time() - start_time
                    cache_hit = True
                    
                    # Get global search statistics
                    global_stats = self.get_search_stats()
                    current_search_number = global_stats["total_searches"] + 1
                    
                    # Update statistics
                    self.update_search_stats(question, 0.0, cache_hit, cache_time, total_time)
                    
                    # Add enhanced performance info to cached response
                    # 원본 캐시된 응답의 성능 정보 보존
                    original_performance = cached_response.get('performance', {})
                    cached_response.update({
                        '_from_cache': True,
                        'performance': {
                            'cache_hit': True,
                            'cache_lookup_time_ms': round(cache_time * 1000, 2),
                            'rag_search_time_ms': original_performance.get('rag_search_time_ms', 0),  # 원본 RAG 시간
                            'llm_response_time_ms': original_performance.get('llm_response_time_ms', 0),  # 원본 LLM 시간
                            'total_time_ms': round(total_time * 1000, 2),  # 현재 캐시 조회 포함 시간
                            'original_total_time_ms': original_performance.get('total_time_ms', 0),  # 원본 총 처리 시간
                            'timestamp': datetime.now().isoformat()
                        },
                        'system_info': {
                            'llm_model': llm_model or "gpt-4o-mini",
                            'embedding_model': "text-embedding-3-small",
                            'vector_db': "ChromaDB",
                            'cache_system': "Hybrid (Redis + SQLite)"
                        },
                        'search_metadata': {
                            'current_search_number': current_search_number,
                            'total_searches_today': global_stats["total_searches"],
                            'cache_hit_rate': round((global_stats["total_cache_hits"] + 1) / current_search_number * 100, 1),
                            'avg_query_time_ms': round(global_stats["avg_query_time"] * 1000, 2),
                            'documents_searched': 0,  # No search needed
                            'vector_db_size': doc_count
                        }
                    })
                    return cached_response
            
            # Start actual query timing
            query_start_time = time.time()
            
            # 질문 분석 (DEOTIS처럼)
            try:
                query_analysis = self.query_analyzer.analyze_query(question)
                analyzed_keywords = query_analysis.get('keywords', [])
                print(f"[질문 분석] 키워드: {analyzed_keywords}")
            except:
                analyzed_keywords = []
            
            # Get similarity search results with scores first using strategy (increased k for better recall)
            if search_mode == "dual":
                similarity_results = self.dual_vectorstore_manager.dual_search(question, k=20)
                documents = [doc for doc, score in similarity_results]
            elif search_mode == "custom":
                documents = self.dual_vectorstore_manager.similarity_search(question, "custom", k=20)
                similarity_results = [(doc, 0.0) for doc in documents]  # 점수 정보가 없는 경우 기본값
            else:
                # basic 검색 모드에서도 dual_vectorstore_manager 사용
                similarity_results = self.dual_vectorstore_manager.similarity_search_with_score(question, "basic", k=20)
                documents = [doc for doc, score in similarity_results]
                
            # 키워드 정확 매칭 부스팅: 질문에 포함된 키워드가 문서에 직접 포함된 경우 점수 상승
            boosted_results = []
            for doc, score in similarity_results:
                boost_factor = 1.0
                
                # 정확한 키워드 매칭 부스팅
                if question in doc.page_content:
                    boost_factor = 1.5  # 50% 부스트
                elif any(word in doc.page_content for word in question.split() if len(word) > 2):
                    boost_factor = 1.2  # 20% 부스트
                    
                boosted_score = min(score * boost_factor, 1.0)  # 최대 1.0으로 제한
                boosted_results.append((doc, boosted_score))
            
            # 부스트된 점수로 재정렬
            boosted_results.sort(key=lambda x: x[1], reverse=True)
            
            # DEOTIS처럼 AI 재순위 적용
            try:
                similarity_results = self.reranker.rerank_results(question, boosted_results, strategy="hybrid")
                print(f"[재순위] 적용 완료")
            except:
                similarity_results = boosted_results
                
            documents = [doc for doc, score in similarity_results]
            
            # Create optimized context from retrieved documents (chunking optimization)
            # Instead of concatenating all documents, use only the most relevant ones
            # and limit the total context length to reduce LLM input size
            max_context_length = 8000  # Further increased for better content inclusion
            context, used_documents = self._create_optimized_context_with_docs(documents, max_context_length)
            
            if use_memory:
                chain = self.get_conversational_chain()
                result = chain({"question": question})
            else:
                # 수동으로 LLM 호출하여 검색 모드 반영
                if search_mode != "basic":
                    # 커스텀 검색 모드의 경우 직접 LLM 호출
                    llm = self.llm_manager.get_llm(model_name=llm_model)
                    prompt = self.prompt_template.format(context=context, question=question)
                    answer = llm.invoke(prompt)
                    result = {
                        "result": answer,
                        "source_documents": documents
                    }
                else:
                    result = self.qa_chain({"query": question})
            
            query_end_time = time.time()
            query_time = query_end_time - query_start_time
            total_time = time.time() - start_time
            cache_time = (cache_end_time - cache_start_time) if cache_start_time else 0
            
            # Get global search statistics
            global_stats = self.get_search_stats()
            current_search_number = global_stats["total_searches"] + 1
            
            # 최고 유사도 확인 및 임계값 체크
            max_similarity = similarity_results[0][1] if similarity_results else 0
            similarity_threshold_met = max_similarity >= 0.8  # 80% 기준
            
            # Format response with similarity scores and enhanced performance info
            response = {
                "answer": result.get("result") or result.get("answer"),
                "source_documents": [],
                "similarity_search": {
                    "query": question,
                    "total_results": len(similarity_results),
                    "top_matches": [],
                    "max_similarity": max_similarity,
                    "similarity_threshold_met": similarity_threshold_met
                },
                "suggested_questions": [],  # 낮은 유사도시 추천 질문
                "performance": {
                    "cache_hit": False,
                    "cache_lookup_time_ms": round(cache_time * 1000, 2) if cache_time > 0 else 0,
                    "rag_search_time_ms": round(query_time * 1000, 2),
                    "llm_response_time_ms": round(query_time * 1000, 2),  # Same as RAG for now
                    "total_time_ms": round(total_time * 1000, 2),
                    "timestamp": datetime.now().isoformat()
                },
                "system_info": {
                    "llm_model": llm_model or "gpt-4o-mini",
                    "embedding_model": "text-embedding-3-small",
                    "vector_db": "ChromaDB",
                    "cache_system": "Hybrid (Redis + SQLite)"
                },
                "search_metadata": {
                    "current_search_number": current_search_number,
                    "total_searches_today": global_stats["total_searches"],
                    "cache_hit_rate": global_stats["cache_hit_rate"],
                    "avg_query_time_ms": round(global_stats["avg_query_time"] * 1000, 2),
                    "documents_searched": len(similarity_results),
                    "vector_db_size": doc_count
                },
                "chunking_type": search_mode  # Add chunking_type to response
            }
            
            # Add source documents if available
            if "source_documents" in result:
                for doc in result["source_documents"]:
                    response["source_documents"].append({
                        "content": doc.page_content[:500],  # Limit content length
                        "metadata": doc.metadata
                    })
            
            # Add similarity search results with scores - ONLY show documents that were actually used by LLM
            # This ensures consistency between what the LLM sees and what the user sees
            used_similarity_results = []
            for doc in used_documents:
                # Find the corresponding score from original similarity_results
                for orig_doc, score in similarity_results:
                    if doc.page_content == orig_doc.page_content:
                        used_similarity_results.append((doc, score))
                        break
                else:
                    # If not found in similarity_results, assign a default score
                    used_similarity_results.append((doc, 0.5))
            
            for i, (doc, score) in enumerate(used_similarity_results[:3], 1):  # Top 3 results that were actually used
                # 전체 내용 표시 (2000자로 더 증가)
                content_full = doc.page_content
                if len(content_full) > 2000:
                    content_preview = content_full[:2000] + "..."
                else:
                    content_preview = content_full
                    
                similarity_info = {
                    "rank": i,
                    "similarity_score": round(score, 4),
                    "similarity_percentage": round(score * 100, 2),
                    "content_preview": content_preview,
                    "metadata": doc.metadata,
                    "document_source": doc.metadata.get("source", "Unknown"),
                    "document_title": doc.metadata.get("title", doc.metadata.get("filename", "Unknown"))
                }
                response["similarity_search"]["top_matches"].append(similarity_info)
            
            # 유사도 임계값 미달시 답변 수정 및 추천 질문 생성
            # ChatGPT 모델은 80% 미만시에만 적용 (로컬LLM은 자체 로직 사용)
            if not similarity_threshold_met and 'gpt' in llm_model.lower():
                # 낮은 유사도시 답변을 안내 메시지로 변경
                response["answer"] = f"죄송합니다. 질문과 정확히 일치하는 정보를 찾지 못했습니다 (최고 유사도: {max_similarity*100:.1f}%).\n\n아래와 같은 질문들은 어떠신가요?"
                
                # 추천 질문 생성 (상위 3개 검색 결과 기반)
                suggested_questions = self._generate_suggested_questions(similarity_results[:3], question)
                response["suggested_questions"] = suggested_questions
            
            # Cache the response (only for non-memory queries)
            if use_cache and not use_memory:
                self.cache_manager.set(question, response, llm_model)
            
            # Update search statistics
            self.update_search_stats(question, query_time, cache_hit, cache_time, total_time)
            
            response['_from_cache'] = False
            return response
        except Exception as e:
            # Import locally to avoid scope issues
            from utils.error_handler import detect_error_type, format_error_response
            
            # Detect error type and return user-friendly message
            error_code = detect_error_type(str(e))
            error_response = format_error_response(error_code, str(e))
            
            # Return formatted error with user-friendly message
            return {
                "error": True,
                "error_code": error_response["error_code"],
                "title": error_response["title"],
                "message": error_response["message"],
                "solution": error_response["solution"],
                "answer": f"❌ {error_response['title']}: {error_response['message']}"
            }
    
    def _create_optimized_context(self, documents: List, max_length: int) -> str:
        """Create optimized context by selecting most relevant content within length limit"""
        context, _ = self._create_optimized_context_with_docs(documents, max_length)
        return context
    
    def _create_optimized_context_with_docs(self, documents: List, max_length: int) -> tuple:
        """Create optimized context and return both context string and used documents"""
        if not documents:
            return "", []
        
        context_parts = []
        used_documents = []
        current_length = 0
        
        # Sort documents by relevance (assume first documents are most relevant)
        # Use only the most relevant chunks and truncate if necessary
        for doc in documents:
            doc_content = doc.page_content
            
            # Skip very short or empty documents
            if len(doc_content.strip()) < 50:
                continue
            
            # If adding this document would exceed the limit
            if current_length + len(doc_content) > max_length:
                # Calculate how much space is left
                remaining_space = max_length - current_length
                
                if remaining_space > 200:  # Only add if there's meaningful space left
                    # Truncate the document content to fit
                    truncated_content = doc_content[:remaining_space-3] + "..."
                    context_parts.append(truncated_content)
                    
                    # Create a copy of the document with truncated content for consistency
                    from langchain.schema import Document
                    truncated_doc = Document(
                        page_content=truncated_content,
                        metadata=doc.metadata.copy()
                    )
                    used_documents.append(truncated_doc)
                break
            else:
                # Add the full document
                context_parts.append(doc_content)
                used_documents.append(doc)
                current_length += len(doc_content)
        
        # Join with double newlines for clear separation
        optimized_context = "\n\n".join(context_parts)
        
        # Log optimization info for debugging
        print(f"[CHUNKING OPTIMIZATION] Original docs: {len(documents)}, Used docs: {len(context_parts)}, "
              f"Context length: {len(optimized_context)} chars (limit: {max_length})")
        
        return optimized_context, used_documents
    
    def _generate_suggested_questions(self, similarity_results, original_question):
        """유사도가 낮을 때 추천 질문 생성"""
        suggestions = []
        
        for doc, score in similarity_results:
            content = doc.page_content[:200]
            
            # 문서 내용 기반 추천 질문 생성
            if 'BC카드' in content or '신용카드' in content:
                if '할부' in content:
                    suggestions.append("BC카드 할부 이용 방법이 궁금하시나요?")
                elif '일시불' in content:
                    suggestions.append("신용카드 일시불 결제 장점이 궁금하시나요?")
                elif '대출' in content or '현금서비스' in content:
                    suggestions.append("BC카드 대출 서비스에 대해 알고 싶으신가요?")
                elif '수수료' in content:
                    suggestions.append("BC카드 수수료 체계에 대해 문의하시나요?")
                elif '포인트' in content:
                    suggestions.append("BC카드 포인트 적립 혜택이 궁금하시나요?")
                else:
                    suggestions.append("BC카드 일반적인 이용 방법이 궁금하시나요?")
        
        # 중복 제거 후 최대 3개 반환
        unique_suggestions = list(dict.fromkeys(suggestions))[:3]
        
        # 기본 추천 질문이 없으면 일반적인 질문 추가
        if len(unique_suggestions) < 3:
            default_suggestions = [
                "BC카드 신용카드 종류에 대해 알고 싶으신가요?",
                "BC카드 부가 서비스에 대해 문의하시나요?",
                "BC카드 고객센터 연락처를 원하시나요?"
            ]
            for default in default_suggestions:
                if default not in unique_suggestions and len(unique_suggestions) < 3:
                    unique_suggestions.append(default)
        
        return unique_suggestions

    def clear_memory(self):
        """Clear conversation memory"""
        self.memory.clear()