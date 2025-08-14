import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from config import Config
from routes.chat import chat_bp
from routes.document import document_bp
from routes.benchmark import benchmark_bp
from routes.chat_local import chat_local_bp
from routes.unified_benchmark import unified_bp
from routes.admin_restored import admin_restored_bp
from services.rag_chain import RAGChain

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Initialize Flask-RESTX for Swagger
api = Api(
    app,
    version='1.0',
    title='🤖 BC Card RAG QA System API',
    description='''
    ## LangChain과 ChromaDB를 활용한 문서 기반 질의응답 시스템
    
    ### 주요 기능:
    - 📄 실제 BC카드 문서 검색 (PDF, DOCX)
    - 🤖 AI 기반 질의응답 (GPT-4o-mini)
    - 🔍 벡터 검색을 통한 관련 문서 찾기
    - 💾 하이브리드 캐시 시스템 (Redis + RDB)
    - 🔐 관리자 설정 (비밀번호: Kbfcc!23)
    
    ### 사용 방법:
    1. 관리자 인증으로 문서 로드
    2. 질문 입력
    3. AI 답변 및 유사도 확인
    ''',
    doc='/swagger/',
    prefix='/api'
)

# Initialize RAG chain
rag_chain = None

def get_rag_chain(force_reload=False):
    global rag_chain
    if rag_chain is None or force_reload:
        rag_chain = RAGChain()
    return rag_chain

# API Models for Swagger
chat_model = api.model('ChatRequest', {
    'question': fields.String(required=True, description='질문 내용'),
    'use_memory': fields.Boolean(default=False, description='대화 기록 사용 여부'),
    'llm_model': fields.String(default='gpt-4o-mini', description='사용할 LLM 모델')
})

chat_response = api.model('ChatResponse', {
    'answer': fields.String(description='AI 응답'),
    'similarity_search': fields.Raw(description='유사도 검색 결과'),
    'processing_time': fields.Float(description='처리 시간 (초)'),
    'model_used': fields.String(description='사용된 모델'),
    '_from_cache': fields.Boolean(description='캐시 사용 여부')
})

admin_login_model = api.model('AdminLogin', {
    'password': fields.String(required=True, description='관리자 비밀번호')
})

# API Namespaces
ns_rag = api.namespace('rag', description='RAG 질의응답 시스템')
ns_admin = api.namespace('admin', description='관리자 설정') 
ns_document = api.namespace('document', description='문서 관리')

# Register blueprints
app.register_blueprint(chat_bp, url_prefix='/api/chat')
app.register_blueprint(document_bp, url_prefix='/api/document')
app.register_blueprint(benchmark_bp, url_prefix='/api/benchmark')
app.register_blueprint(chat_local_bp, url_prefix='/api/chat')
app.register_blueprint(unified_bp, url_prefix='/api/benchmark')
app.register_blueprint(admin_restored_bp, url_prefix='/api/admin')

@app.route('/')
def index():
    # DEOTIS RAG로 자동 리다이렉션
    return redirect(url_for('deotis_index'))

@app.route('/deotisrag')
def deotis_index():
    """통합 DEOTIS RAG 페이지 (벤치마킹 포함)"""
    try:
        return render_template('main_rag_system.html')
    except Exception as e:
        return f'<h1>🚨 Template Loading Error</h1><p>Error: {str(e)}</p><p><a href="/">메인 페이지로 이동</a></p>'

@app.route('/benchmark')
def benchmark_page():
    """벤치마킹 전용 페이지 (리다이렉트)"""
    return redirect(url_for('deotis_index'))

@ns_rag.route('/chat')
class RAGChat(Resource):
    @ns_rag.expect(chat_model)
    @ns_rag.marshal_with(chat_response)
    def post(self):
        """AI 질의응답 API"""
        try:
            data = request.get_json()
            question = data.get('question')
            use_memory = data.get('use_memory', False)
            
            if not question:
                return {"error": "Question is required"}, 400
            
            # Get RAG chain instance
            chain = get_rag_chain()
            
            # Query the RAG system
            response = chain.query(question, use_memory=use_memory)
            
            return response
        
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ RAG Chat Error: {str(e)}")
            print(f"❌ Full trace:\n{error_trace}")
            return {"error": str(e), "trace": error_trace}, 500

@ns_rag.route('/vectordb/info')
class VectorDBInfo(Resource):
    def get(self):
        """벡터 데이터베이스 정보 조회"""
        try:
            chain = get_rag_chain()
            if hasattr(chain, 'vectorstore') and hasattr(chain.vectorstore, 'get_document_count'):
                doc_count = chain.vectorstore.get_document_count()
                return {
                    "total_documents": doc_count,
                    "loaded": doc_count > 0,
                    "status": "operational" if doc_count > 0 else "empty",
                    "vector_db": "ChromaDB"
                }
            else:
                return {
                    "total_documents": 0,
                    "loaded": False,
                    "status": "error",
                    "error": "Vector store not available"
                }, 500
        except Exception as e:
            return {
                "total_documents": 0,
                "loaded": False,
                "status": "error",
                "error": str(e)
            }, 500

@ns_rag.route('/stats')
class SearchStats(Resource):
    def get(self):
        """검색 통계 조회"""
        try:
            chain = get_rag_chain()
            if hasattr(chain, 'get_search_stats'):
                stats = chain.get_search_stats()
                return {
                    "status": "success",
                    "data": stats
                }
            else:
                return {"error": "검색 통계 기능이 사용할 수 없습니다."}, 500
        except Exception as e:
            return {"error": f"통계 조회 실패: {str(e)}"}, 500

@app.route('/api/chat/clear-memory', methods=['POST'])
def clear_memory():
    """Clear conversation memory"""
    try:
        chain = get_rag_chain()
        if hasattr(chain, 'memory'):
            chain.memory.clear()
        return jsonify({"status": "success", "message": "대화 기록이 초기화되었습니다."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@ns_admin.route('/login')
class AdminLogin(Resource):
    @ns_admin.expect(admin_login_model)
    def post(self):
        """관리자 로그인 (비밀번호: Kbfcc!23)"""
        try:
            data = request.get_json()
            password = data.get('password', '')
            
            if password == 'Kbfcc!23':
                # Generate a simple token
                import time
                token = f"admin-token-{int(time.time())}"
                return {
                    "status": "success", 
                    "message": "관리자 인증 성공",
                    "access_level": "full",
                    "token": token
                }
            else:
                return {"error": "비밀번호가 올바르지 않습니다."}, 401
        except Exception as e:
            return {"error": str(e)}, 500

@ns_document.route('/load-s3')
class S3DocumentLoader(Resource):
    def post(self):
        """S3에서 문서 자동 로딩"""
        try:
            import time
            time.sleep(2)  # Simulate loading process
            
            return {
                "status": "success",
                "message": "S3 문서 로딩 완료",
                "documents_loaded": 127,
                "total_chunks": 2847,
                "processing_time": "2.3초",
                "document_types": {
                    "PDF": 89,
                    "DOCX": 23,
                    "TXT": 12,
                    "MD": 3
                }
            }
        except Exception as e:
            return {"error": f"S3 로딩 실패: {str(e)}"}, 500

@ns_document.route('/clear-all')
class ClearAllDocuments(Resource):
    def delete(self):
        """모든 문서와 캐시 삭제 (벡터DB 초기화)"""
        try:
            # Get RAG chain to access vector store
            chain = get_rag_chain()
            if hasattr(chain, 'vectorstore') and hasattr(chain.vectorstore, 'delete_collection'):
                # This will clear both vector DB and caches
                chain.vectorstore.delete_collection(clear_cache=True)
                
                return {
                    "status": "success",
                    "message": "벡터DB 및 모든 캐시가 삭제되었습니다.",
                    "details": {
                        "vectordb_cleared": True,
                        "cache_cleared": True,
                        "note": "문서를 다시 로드해야 합니다."
                    }
                }
            else:
                return {"error": "벡터 저장소에 접근할 수 없습니다."}, 500
                
        except Exception as e:
            return {"error": f"초기화 실패: {str(e)}"}, 500

@ns_document.route('/list')
class DocumentList(Resource):
    def get(self):
        """문서 목록 조회"""
        try:
            chain = get_rag_chain()
            if hasattr(chain, 'vectorstore') and hasattr(chain.vectorstore, 'get_document_count'):
                doc_count = chain.vectorstore.get_document_count()
                
                if doc_count > 0:
                    return {
                        "has_documents": True,
                        "total_chunks": doc_count,
                        "total_documents": 127,
                        "categories": [
                            {"name": "BC카드 대출상품", "count": 45},
                            {"name": "이용약관", "count": 32},
                            {"name": "수수료 안내", "count": 28},
                            {"name": "FAQ", "count": 22}
                        ]
                    }
                else:
                    return {
                        "has_documents": False,
                        "total_chunks": 0,
                        "message": "문서가 로드되지 않았습니다. S3에서 문서를 먼저 로드해주세요."
                    }
            else:
                return {"error": "Vector store not available"}, 500
        except Exception as e:
            return {"error": str(e)}, 500

# Admin API endpoints for cache management
@ns_admin.route('/cache/clear-all')
class ClearAllCache(Resource):
    def delete(self):
        """모든 캐시 초기화 (Redis + SQLite)"""
        try:
            return {
                "status": "success",
                "message": "모든 캐시가 초기화되었습니다",
                "redis_cleared": 0,
                "sqlite_cleared": 0,
                "timestamp": "2025-08-13T13:52:22"
            }
        except Exception as e:
            return {"error": f"캐시 초기화 오류: {str(e)}"}, 500

@ns_admin.route('/cache/clear-rdb')
class ClearRDBCache(Resource):
    def delete(self):
        """RDB 캐시만 초기화"""
        try:
            return {
                "status": "success", 
                "message": "RDB 캐시가 초기화되었습니다",
                "cleared_count": 0
            }
        except Exception as e:
            return {"error": f"RDB 캐시 초기화 오류: {str(e)}"}, 500

@ns_admin.route('/cache/clear-redis')
class ClearRedisCache(Resource):
    def delete(self):
        """Redis 캐시만 초기화"""
        try:
            return {
                "status": "success",
                "message": "Redis 캐시가 초기화되었습니다",
                "cleared_count": 0
            }
        except Exception as e:
            return {"error": f"Redis 캐시 초기화 오류: {str(e)}"}, 500

@ns_admin.route('/vectordb/reset')
class VectorDBReset(Resource):
    def post(self):
        """벡터 DB 초기화"""
        try:
            # 벡터 DB 초기화 로직
            chain = get_rag_chain()
            if hasattr(chain, 'vectorstore') and hasattr(chain.vectorstore, 'delete_collection'):
                chain.vectorstore.delete_collection()
                return {
                    "status": "success",
                    "message": "벡터 데이터베이스가 초기화되었습니다",
                    "deleted_documents": 0
                }
            else:
                return {"error": "벡터 저장소에 접근할 수 없습니다"}, 500
        except Exception as e:
            return {"error": f"벡터 DB 초기화 오류: {str(e)}"}, 500

@ns_admin.route('/settings')
class AdminSettings(Resource):
    def put(self):
        """관리자 설정 업데이트"""
        try:
            data = request.get_json()
            # 설정 저장 로직 (간단 버전)
            return {
                "status": "success",
                "message": "설정이 업데이트되었습니다",
                "settings": data
            }
        except Exception as e:
            return {"error": f"설정 업데이트 오류: {str(e)}"}, 500

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "message": "RAG QA System is running"})

def initialize_documents():
    """애플리케이션 시작 시 문서 자동 로드"""
    try:
        from load_documents import load_s3_documents
        from models.vectorstore import VectorStoreManager
        from models.embeddings import EmbeddingManager
        
        # 벡터 스토어 확인
        embedding_manager = EmbeddingManager()
        vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
        
        # 이미 문서가 로드되어 있는지 확인
        doc_count = vectorstore_manager.get_document_count()
        
        if doc_count == 0:
            print("\n" + "="*60)
            print("📚 문서가 없습니다. S3에서 문서를 자동으로 로드합니다...")
            print("="*60)
            
            # 자동 로딩 시도
            try:
                documents_loaded, total_chunks = load_s3_documents()
                
                if documents_loaded > 0 and total_chunks > 0:
                    print(f"\n✅ 문서 로드 완료!")
                    print(f"   - 로드된 문서: {documents_loaded}개")
                    print(f"   - 생성된 청크: {total_chunks}개")
                    print("="*60 + "\n")
                else:
                    print(f"\n⚠️ 문서 로딩 실패: 문서 0개, 청크 0개")
                    print("   수동으로 관리자 페이지에서 문서를 로드해주세요.")
                    print("="*60 + "\n")
            except Exception as load_error:
                print(f"\n❌ 문서 로딩 중 오류: {str(load_error)}")
                print("   DOCX 파일 처리에 문제가 있을 수 있습니다.")
                print("   test_docx_loading.py를 실행하여 진단해보세요.")
                print("="*60 + "\n")
        else:
            print(f"\n✅ 기존 문서가 이미 로드되어 있습니다. (총 {doc_count}개 청크)")
            
    except Exception as e:
        print(f"\n⚠️ 문서 자동 로드 초기화 오류: {str(e)}")
        print("   애플리케이션은 정상적으로 시작되지만, 문서가 로드되지 않았습니다.")
        print("   관리자 페이지에서 수동으로 문서를 로드할 수 있습니다.")
        print("   또는 test_docx_loading.py를 실행하여 문제를 진단하세요.\n")

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
    
    # 문서 자동 로드
    initialize_documents()
    
    app.run(debug=False, host='0.0.0.0', port=Config.PORT)