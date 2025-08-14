from flask_restx import Namespace, Resource, fields
from flask import request
from services.rag_chain import RAGChain
from services.document_processor import DocumentProcessor
from models.embeddings import EmbeddingManager
from models.vectorstore import VectorStoreManager
from utils.error_handler import detect_error_type, format_error_response
import os
import uuid

# Create namespaces
api = Namespace('rag', description='RAG QA System API - 문서 기반 질의응답 시스템')

# Models for request/response
chat_model = api.model('ChatRequest', {
    'question': fields.String(required=True, description='질문 내용'),
    'use_memory': fields.Boolean(default=False, description='대화 기록 사용 여부'),
    'llm_model': fields.String(default='gpt-4o-mini', description='사용할 LLM 모델')
})

chat_response = api.model('ChatResponse', {
    'answer': fields.String(description='답변 내용'),
    'source_documents': fields.List(fields.Raw, description='참고 문서'),
    'model_used': fields.String(description='사용된 모델')
})

upload_text_model = api.model('UploadTextRequest', {
    'text': fields.String(required=True, description='텍스트 내용'),
    'title': fields.String(default='Untitled', description='문서 제목')
})

settings_model = api.model('SettingsRequest', {
    'chunk_size': fields.Integer(default=1000, description='청크 크기'),
    'chunk_overlap': fields.Integer(default=200, description='청크 겹침'),
    'embedding_model': fields.String(default='text-embedding-3-small', description='임베딩 모델')
})

# Initialize components (will be updated with dynamic selection)
rag_chain = None

def get_rag_chain(model_name='gpt-4o-mini'):
    # Always create a fresh RAG chain to ensure latest vectorstore state
    return RAGChain()

@api.route('/chat')
class Chat(Resource):
    @api.doc('chat_query')
    @api.expect(chat_model)
    @api.marshal_with(chat_response)
    def post(self):
        """질문에 대한 답변 생성"""
        try:
            data = request.get_json()
            question = data.get('question')
            use_memory = data.get('use_memory', False)
            llm_model = data.get('llm_model', 'gpt-4o-mini')
            
            if not question:
                return {'error': 'Question is required'}, 400
            
            # Get RAG chain instance
            chain = get_rag_chain(llm_model)
            
            # Query the RAG system with cache support
            response = chain.query(question, use_memory=use_memory, llm_model=llm_model)
            response['model_used'] = llm_model
            
            return response
        
        except Exception as e:
            error_code = detect_error_type(str(e))
            error_response = format_error_response(error_code, str(e))
            return error_response, 500

@api.route('/documents/upload-text')
class UploadText(Resource):
    @api.doc('upload_text')
    @api.expect(upload_text_model)
    def post(self):
        """텍스트 직접 업로드"""
        try:
            data = request.get_json()
            text = data.get('text')
            title = data.get('title', 'Untitled')
            
            if not text:
                return {'error': 'Text is required'}, 400
            
            # Process text
            doc_processor = DocumentProcessor()
            embedding_manager = EmbeddingManager()
            vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
            
            metadata = {
                "title": title,
                "source": "direct_input",
                "upload_id": str(hash(text))
            }
            
            chunks = doc_processor.process_text(text, metadata)
            vectorstore_manager.add_documents(chunks)
            
            return {
                "message": "Text processed successfully",
                "title": title,
                "chunks_created": len(chunks),
                "total_documents": vectorstore_manager.get_document_count()
            }
        
        except Exception as e:
            error_code = detect_error_type(str(e))
            error_response = format_error_response(error_code, str(e))
            return error_response, 500

@api.route('/documents/load-s3')
class LoadS3Documents(Resource):
    @api.doc('load_s3_documents')
    def post(self):
        """S3 폴더의 문서들을 자동으로 로드"""
        try:
            from load_documents import load_s3_documents
            documents_loaded, total_chunks = load_s3_documents()
            
            return {
                "message": "S3 documents loaded successfully",
                "documents_loaded": documents_loaded,
                "total_chunks": total_chunks
            }
        
        except Exception as e:
            error_code = detect_error_type(str(e))
            error_response = format_error_response(error_code, str(e))
            return error_response, 500

@api.route('/documents/list')
class ListDocuments(Resource):
    @api.doc('list_documents')
    def get(self):
        """업로드된 문서 목록 조회"""
        try:
            embedding_manager = EmbeddingManager()
            vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
            
            # Get vector DB status
            total_chunks = vectorstore_manager.get_document_count()
            has_documents = total_chunks > 0
            
            # List files in upload folder
            from config import Config
            files = []
            if os.path.exists(Config.UPLOAD_FOLDER):
                for filename in os.listdir(Config.UPLOAD_FOLDER):
                    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                    if os.path.isfile(file_path):
                        files.append({
                            "filename": filename,
                            "size": os.path.getsize(file_path),
                            "modified": os.path.getmtime(file_path)
                        })
            
            # Check S3 folder status
            s3_folder = "/mnt/d/03_DEOTIS_QA/s3"
            s3_files = []
            if os.path.exists(s3_folder):
                for filename in os.listdir(s3_folder):
                    if filename.endswith(('.pdf', '.docx', '.txt', '.md')):
                        s3_files.append({
                            "filename": filename,
                            "source": "S3"
                        })
            
            return {
                "files": files,
                "s3_files": s3_files,
                "total_chunks": total_chunks,
                "has_documents": has_documents,
                "status": "loaded" if has_documents else "empty"
            }
        
        except Exception as e:
            error_code = detect_error_type(str(e))
            error_response = format_error_response(error_code, str(e))
            return error_response, 500

@api.route('/settings')
class Settings(Resource):
    @api.doc('update_settings')
    @api.expect(settings_model)
    def post(self):
        """시스템 설정 업데이트"""
        try:
            data = request.get_json()
            
            # Update configuration (would need to implement config update mechanism)
            return {
                "message": "Settings updated successfully",
                "settings": data
            }
        
        except Exception as e:
            error_code = detect_error_type(str(e))
            error_response = format_error_response(error_code, str(e))
            return error_response, 500

@api.route('/vectordb/info')
class VectorDBInfo(Resource):
    @api.doc('vectordb_info')
    def get(self):
        """벡터DB 정보 조회"""
        try:
            embedding_manager = EmbeddingManager()
            vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
            
            return {
                "total_documents": vectorstore_manager.get_document_count(),
                "embedding_model": "text-embedding-3-small",
                "vector_db_type": "ChromaDB"
            }
        
        except Exception as e:
            error_code = detect_error_type(str(e))
            error_response = format_error_response(error_code, str(e))
            return error_response, 500

@api.route('/vectordb/clear')
class ClearVectorDB(Resource):
    @api.doc('clear_vectordb')
    def delete(self):
        """벡터DB 전체 삭제 후 문서 자동 재로드"""
        try:
            embedding_manager = EmbeddingManager()
            vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
            
            # 벡터 DB 삭제 및 초기화
            vectorstore_manager.delete_collection()
            vectorstore_manager.initialize_vectorstore()
            
            # 문서 자동 재로드
            try:
                from load_documents import load_s3_documents
                documents_loaded, total_chunks = load_s3_documents()
                
                return {
                    "message": "Vector database cleared and documents reloaded successfully",
                    "documents_loaded": documents_loaded,
                    "total_chunks": total_chunks,
                    "status": "completed"
                }
            except Exception as reload_error:
                # 벡터 DB는 초기화되었지만 문서 재로드 실패
                return {
                    "message": "Vector database cleared but document reload failed",
                    "error": str(reload_error),
                    "documents_loaded": 0,
                    "total_chunks": 0,
                    "status": "partial_success"
                }, 200
        
        except Exception as e:
            error_code = detect_error_type(str(e))
            error_response = format_error_response(error_code, str(e))
            return error_response, 500

@api.route('/cache/stats')
class CacheStats(Resource):
    @api.doc('cache_stats')
    def get(self):
        """캐시 통계 조회"""
        try:
            from services.cache_manager import CacheManager
            cache = CacheManager()
            stats = cache.get_stats()
            return stats
        except Exception as e:
            return {'error': str(e)}, 500

@api.route('/cache/clear')
class ClearCache(Resource):
    @api.doc('clear_cache')
    def delete(self):
        """캐시 전체 삭제"""
        try:
            from services.cache_manager import CacheManager
            cache = CacheManager()
            deleted = cache.clear_all()
            return {'message': f'Cleared {deleted} cache entries'}
        except Exception as e:
            return {'error': str(e)}, 500

@api.route('/cache/popular')
class PopularQueries(Resource):
    @api.doc('popular_queries')
    def get(self):
        """인기 검색어 조회"""
        try:
            from services.cache_manager import CacheManager
            cache = CacheManager()
            popular = cache.get_popular_queries(limit=10)
            return {'popular_queries': popular}
        except Exception as e:
            return {'error': str(e)}, 500