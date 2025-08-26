import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from config import Config
from routes.multi_benchmark import multi_benchmark_bp
from routes.admin_restored import admin_restored_bp

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
    - 🤖 4가지 벤치마킹 모드 (local/chatgpt × basic/custom)
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
ns_multi = api.namespace('multi', description='멀티 벤치마킹 시스템')
ns_admin = api.namespace('admin', description='관리자 기능')

# Register blueprints - 핵심 기능만
app.register_blueprint(multi_benchmark_bp, url_prefix='/api/multi')
app.register_blueprint(admin_restored_bp, url_prefix='/api/admin')

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

@ns_multi.route('/system-status')
class SystemStatus(Resource):
    def get(self):
        """시스템 상태 확인"""
        try:
            return {
                "status": "online",
                "message": "RAG QA 시스템이 정상 작동 중입니다",
                "endpoints": {
                    "main_app": "/deotisrag",
                    "api_docs": "/swagger/",
                    "multi_benchmark": "/api/multi/multi-query-stream"
                }
            }
        except Exception as e:
            return {"error": str(e)}, 500

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
        
        from load_documents_new import load_s3_documents, clear_all_data
        from models.vectorstore import DualVectorStoreManager
        from models.embeddings import EmbeddingManager
        
        if auto_clear_on_startup:
            print("\n" + "="*60)
            print("🗑️ 자동 초기화 모드: 시작 시 모든 데이터를 삭제합니다...")
            print("="*60)
            clear_all_data()
            print("✅ 모든 데이터 삭제 완료!")
            print("="*60 + "\n")
        
        # 벡터 스토어 확인
        embedding_manager = EmbeddingManager()
        vectorstore_manager = DualVectorStoreManager()
        
        # 이미 문서가 로드되어 있는지 확인
        try:
            doc_count = vectorstore_manager.get_document_count()
        except:
            doc_count = 0
        
        if doc_count == 0:
            print("\n" + "="*60)
            print("📚 문서가 없습니다. S3에서 문서를 자동으로 로드합니다...")
            print("="*60)
            
            # 자동 로딩 시도
            try:
                documents_loaded, total_chunks = load_s3_documents(clear_before_load=False)
                
                if documents_loaded > 0 and total_chunks > 0:
                    print(f"\n✅ 문서 로드 완료!")
                    print(f"   - 로드된 문서: {documents_loaded}개")
                    print(f"   - 생성된 청크: {total_chunks}개")
                    print("="*60 + "\n")
                else:
                    print(f"\n⚠️ 문서 로딩 실패: 문서 0개, 청크 0개")
                    print("   수동으로 /deotisrag에서 문서를 로드해주세요.")
                    print("="*60 + "\n")
            except Exception as load_error:
                print(f"\n❌ 문서 로딩 중 오류: {str(load_error)}")
                print("   DOCX 파일 처리에 문제가 있을 수 있습니다.")
                print("   /deotisrag에서 수동으로 문서를 로드해주세요.")
                print("="*60 + "\n")
        else:
            print(f"\n✅ 기존 문서가 이미 로드되어 있습니다. (총 {doc_count}개 청크)")
            
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