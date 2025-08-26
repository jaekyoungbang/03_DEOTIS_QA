import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from config import Config
from routes.chat import chat_bp
from routes.chat_local import chat_local_bp
from routes.document import document_bp

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
    - 📄 BC카드 문서 검색 및 질의응답
    - 🤖 2가지 모드 (사내서버 vLLM × basic/custom)
    - ⚡ 실시간 스트리밍 응답
    - 🔍 vLLM + kanana8b 로컬 모델 지원
    
    ### 사용 방법:
    1. /deotisrag - 메인 RAG 시스템 접속
    2. /swagger/ - API 문서 확인
    ''',
    doc='/swagger/',
    prefix='/api'
)

# API Namespaces
ns_api = api.namespace('api', description='기본 API')
ns_chat = api.namespace('chat', description='채팅 시스템')

# Register blueprints - 핵심 기능만
app.register_blueprint(chat_bp, url_prefix='/api/chat')
app.register_blueprint(chat_local_bp, url_prefix='/api/chat')
app.register_blueprint(document_bp, url_prefix='/api/document')

@app.route('/')
def index():
    """메인 페이지 - Swagger로 리다이렉션"""
    return redirect('/swagger/')

@app.route('/deotisrag')
def deotis_index():
    """DEOTIS RAG 메인 페이지"""
    try:
        return render_template('main_rag_system.html')
    except Exception as e:
        return f'''
        <h1>🚨 Template Loading Error</h1>
        <p>Error: {str(e)}</p>
        <p><a href="/swagger/">Swagger API 문서로 이동</a></p>
        '''

@ns_api.route('/system-status')
class SystemStatus(Resource):
    def get(self):
        """시스템 상태 확인"""
        try:
            return {
                "status": "online",
                "message": "RAG QA 시스템이 정상 작동 중입니다",
                "endpoints": {
                    "main_app": "/deotisrag",
                    "api_docs": "/swagger/"
                }
            }
        except Exception as e:
            return {"error": str(e)}, 500

@app.route('/api/system-status')
def system_status():
    """시스템 상태 확인 API"""
    try:
        return jsonify({
            "status": "success",
            "system_status": {
                "server": "online",
                "vectordb": {
                    "available": True,
                    "doc_count": 0
                },
                "documents": {
                    "available": True
                }
            },
            "message": "시스템 정상 작동 중"
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/admin/clear-all', methods=['DELETE'])
def clear_all():
    """모든 데이터 삭제"""
    try:
        # 벡터DB 삭제
        import shutil
        import os
        vectordb_path = Config.CHROMA_PERSIST_DIRECTORY
        if os.path.exists(vectordb_path):
            shutil.rmtree(vectordb_path)
            print(f"✅ 벡터DB 삭제 완료: {vectordb_path}")
        
        return jsonify({
            "status": "success",
            "message": "모든 데이터가 삭제되었습니다."
        })
    except Exception as e:
        print(f"❌ 데이터 삭제 오류: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/admin/reload-documents', methods=['POST'])
def reload_documents():
    """문서 재로드"""
    try:
        # S3 폴더에서 문서 로드
        from load_documents import load_s3_documents
        
        # 기존 벡터DB 삭제
        import shutil
        import os
        vectordb_path = Config.CHROMA_PERSIST_DIRECTORY
        if os.path.exists(vectordb_path):
            shutil.rmtree(vectordb_path)
            print(f"✅ 기존 벡터DB 삭제: {vectordb_path}")
        
        # 새로 생성
        os.makedirs(vectordb_path, exist_ok=True)
        
        # 문서 로드
        documents_loaded, total_chunks = load_s3_documents(clear_before_load=False)
        
        return jsonify({
            "status": "success",
            "message": "문서가 성공적으로 로드되었습니다.",
            "documents_loaded": documents_loaded,
            "total_chunks": total_chunks
        })
        
    except Exception as e:
        print(f"❌ 문서 로드 오류: {e}")
        return jsonify({
            "status": "error", 
            "error": str(e),
            "message": "문서 로드 중 오류가 발생했습니다."
        }), 500

@app.route('/health')
def health():
    """헬스 체크"""
    return jsonify({
        "status": "healthy", 
        "message": "BC Card RAG QA System is running",
        "version": "1.0"
    })

def initialize_documents():
    """애플리케이션 시작 시 문서 자동 로드"""
    try:
        # 환경 변수로 자동 초기화 옵션 확인
        auto_clear_on_startup = os.environ.get('RAG_AUTO_CLEAR_ON_STARTUP', 'false').lower() == 'true'
        
        from load_documents import load_s3_documents
        from models.vectorstore import DualVectorStoreManager
        from models.embeddings import EmbeddingManager
        
        if auto_clear_on_startup:
            print("\n" + "="*60)
            print("🗑️ 자동 초기화 모드: 시작 시 모든 데이터를 삭제합니다...")
            print("="*60)
            # 벡터DB 삭제
            import shutil
            vectordb_path = Config.CHROMA_PERSIST_DIRECTORY
            if os.path.exists(vectordb_path):
                shutil.rmtree(vectordb_path)
                print(f"✅ 벡터DB 삭제 완료: {vectordb_path}")
            print("="*60 + "\n")
        
        # 벡터 스토어 확인
        embedding_manager = EmbeddingManager()
        vectorstore_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
        
        # 항상 문서를 로드 (매번 최신 상태 유지)
        print("\n" + "="*60)
        print("🚀 S3 폴더에서 문서를 로드합니다...")
        print("📁 D:\\99_DEOTIS_QA_SYSTEM\\03_DEOTIS_QA\\s3 (Word 파일)")
        print("📁 D:\\99_DEOTIS_QA_SYSTEM\\03_DEOTIS_QA\\s3-chunking (MD 파일)")
        print("="*60)
        
        # 자동 로딩 실행 (항상 clear_before_load=True)
        try:
            documents_loaded, total_chunks = load_s3_documents(clear_before_load=True)
            
            if documents_loaded > 0 and total_chunks > 0:
                print(f"\n✅ 문서 로드 완료!")
                print(f"   - 로드된 문서: {documents_loaded}개")
                print(f"   - 생성된 청크: {total_chunks}개")
                print("="*60 + "\n")
            else:
                print(f"\n⚠️ 문서 로딩 실패: 문서 0개, 청크 0개")
                print("   S3 폴더를 확인해주세요.")
                print("="*60 + "\n")
        except Exception as load_error:
            print(f"\n❌ 문서 로딩 중 오류: {str(load_error)}")
            print("   S3 폴더의 파일들을 확인해주세요.")
            print("="*60 + "\n")
            
    except Exception as e:
        print(f"\n⚠️ 문서 자동 로드 초기화 오류: {str(e)}")
        print("   애플리케이션은 정상적으로 시작되지만, 문서가 로드되지 않았습니다.")
        print("   /deotisrag에서 수동으로 문서를 로드할 수 있습니다.")
        print("="*60 + "\n")

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
    
    # 문서 자동 로드
    initialize_documents()
    
    print("🚀 BC Card RAG QA System 시작")
    print(f"📱 메인 앱: http://localhost:{Config.PORT}/deotisrag")
    print(f"📖 API 문서: http://localhost:{Config.PORT}/swagger/")
    
    app.run(debug=False, host='0.0.0.0', port=Config.PORT)