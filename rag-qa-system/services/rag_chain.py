from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from models.llm import LLMManager
from models.embeddings import EmbeddingManager
from models.vectorstore import VectorStoreManager
from utils.error_handler import detect_error_type, format_error_response
from services.cache_factory import CacheFactory
import time
import sqlite3
import os
from datetime import datetime

class RAGChain:
    def __init__(self):
        self.llm_manager = LLMManager()
        self.embedding_manager = EmbeddingManager()
        self.vectorstore_manager = VectorStoreManager(
            self.embedding_manager.get_embeddings()
        )
        # Expose vectorstore for external access
        self.vectorstore = self.vectorstore_manager
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        self.qa_chain = None
        self.cache_manager = CacheFactory.get_cache_manager()  # Use cache factory
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
        prompt_template = """당신은 BC카드 관련 질문에 답변하는 전문 AI 어시스턴트입니다. 
        아래 제공된 컨텍스트를 활용하여 질문에 답변해주세요.
        
        중요 지침:
        1. 제공된 컨텍스트에서 직접적으로 관련된 정보를 찾아 답변하세요.
        2. 단기카드대출은 현금서비스와 같은 의미입니다.
        3. 장기카드대출은 카드론과 같은 의미입니다.
        4. 답변은 다음과 같이 구조화하여 작성하세요:
           - 상품 개요를 간단히 설명
           - 상품 정보는 반드시 마크다운 표 형식으로 정리
           - 신청 방법은 단계별로 번호를 매겨 설명
           - 중요 주의사항이 있으면 마지막에 추가
        5. 마크다운 표 형식 예시:
           | 구분 | 내용 |
           |------|------|
           | 이용대상 | BC바로카드 우량 고객 |
           | 이용한도 | 최대 5,000만원 |
        6. 체크리스트 형식: - ✅ 항목명
        7. 정보가 부족한 경우에만 "제공된 정보가 부족합니다"라고 말하세요.
        
        컨텍스트: {context}
        
        질문: {question}
        
        답변:"""
        
        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # Create retrieval QA chain with improved retrieval
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm_manager.get_llm(),
            chain_type="stuff",
            retriever=self.vectorstore_manager.get_retriever(k=8),  # 더 많은 문서 검색
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )
    
    def get_conversational_chain(self):
        """Create a conversational retrieval chain with memory"""
        return ConversationalRetrievalChain.from_llm(
            llm=self.llm_manager.get_llm(),
            retriever=self.vectorstore_manager.get_retriever(k=5),
            memory=self.memory,
            return_source_documents=True,
            verbose=True
        )
    
    def query(self, question, use_memory=False, llm_model=None, use_cache=True):
        """Query the RAG system with caching support and performance tracking"""
        start_time = time.time()
        cache_start_time = None
        cache_end_time = None
        query_start_time = None
        query_end_time = None
        
        try:
            # Check if vectorstore has documents before querying
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
            
            # Get similarity search results with scores first
            similarity_results = self.vectorstore_manager.similarity_search_with_score(question, k=8)
            
            if use_memory:
                chain = self.get_conversational_chain()
                result = chain({"question": question})
            else:
                result = self.qa_chain({"query": question})
            
            query_end_time = time.time()
            query_time = query_end_time - query_start_time
            total_time = time.time() - start_time
            cache_time = (cache_end_time - cache_start_time) if cache_start_time else 0
            
            # Get global search statistics
            global_stats = self.get_search_stats()
            current_search_number = global_stats["total_searches"] + 1
            
            # Format response with similarity scores and enhanced performance info
            response = {
                "answer": result.get("result") or result.get("answer"),
                "source_documents": [],
                "similarity_search": {
                    "query": question,
                    "total_results": len(similarity_results),
                    "top_matches": []
                },
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
                }
            }
            
            # Add source documents if available
            if "source_documents" in result:
                for doc in result["source_documents"]:
                    response["source_documents"].append({
                        "content": doc.page_content[:500],  # Limit content length
                        "metadata": doc.metadata
                    })
            
            # Add similarity search results with scores
            for i, (doc, score) in enumerate(similarity_results[:3], 1):  # Top 3 results
                similarity_info = {
                    "rank": i,
                    "similarity_score": round(score, 4),
                    "similarity_percentage": round(score * 100, 2),
                    "content_preview": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "metadata": doc.metadata,
                    "document_source": doc.metadata.get("source", "Unknown"),
                    "document_title": doc.metadata.get("title", doc.metadata.get("filename", "Unknown"))
                }
                response["similarity_search"]["top_matches"].append(similarity_info)
            
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
    
    def clear_memory(self):
        """Clear conversation memory"""
        self.memory.clear()