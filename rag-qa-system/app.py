import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from config import Config
from routes.chat import chat_bp
from routes.chat_local import chat_local_bp
from routes.card_analysis import card_analysis_bp
# document_bp는 나중에 import

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# 정적 파일 경로 추가 (s3-chunking 이미지용)
import os
s3_chunking_static_path = os.path.join(os.path.dirname(__file__), 's3-chunking')
print(f"📁 정적 파일 경로 설정: {s3_chunking_static_path}")

# 정적 파일 라우트 추가
@app.route('/static-images/<path:filename>')
def serve_static_images(filename):
    """정적 이미지 파일 서빙 (추가 방법)"""
    return send_from_directory(s3_chunking_static_path, filename)

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
    2. /api/card-analysis/demo - 카드 분석 데모
    3. /swagger/ - API 문서 확인
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
app.register_blueprint(card_analysis_bp, url_prefix='/api/card-analysis')

# document_bp는 나중에 지연 등록
def register_document_bp():
    """Document Blueprint 지연 등록"""
    try:
        from routes.document import document_bp
        app.register_blueprint(document_bp, url_prefix='/api/document')
        print("✅ Document Blueprint 등록 완료")
    except Exception as e:
        print(f"⚠️ Document Blueprint 등록 실패: {e}")
        print("💡 Document 관련 API는 사용할 수 없지만 다른 기능은 정상 작동합니다.")

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
        print("📁 D:\\99_DEOTIS_QA_SYSTEM\\03_DEOTIS_QA\\rag-qa-system\\s3 (Word 파일)")
        print("📁 D:\\99_DEOTIS_QA_SYSTEM\\03_DEOTIS_QA\\rag-qa-system\\s3-chunking (MD 파일)")
        print("📁 D:\\99_DEOTIS_QA_SYSTEM\\03_DEOTIS_QA\\rag-qa-system\\s3-common (공통 파일 - 개인정보)")
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

@app.route('/images/<path:filename>')
def serve_s3_chunking_image(filename):
    """s3-chunking 폴더의 이미지 파일 서빙"""
    try:
        # s3-chunking 폴더 경로 (rag-qa-system 내부)
        current_dir = os.path.dirname(os.path.abspath(__file__))  # rag-qa-system 폴더
        s3_chunking_path = os.path.join(current_dir, 's3-chunking')
        
        # 파일 경로 확인 로그
        print(f"🔍 이미지 요청: {filename}")
        print(f"📁 s3-chunking 경로: {s3_chunking_path}")
        
        # 실제 파일 존재 여부 확인
        full_path = os.path.join(s3_chunking_path, filename)
        print(f"📄 전체 경로: {full_path}")
        print(f"🔍 파일 존재: {os.path.exists(full_path)}")
        
        # 보안을 위해 파일명 검증
        if '..' in filename or filename.startswith('/'):
            return jsonify({'error': 'Invalid filename'}), 400
            
        # Aspose.Words로 생성된 이미지 파일만 허용
        if not filename.startswith('Aspose.Words.'):
            print(f"❌ 권한 없는 파일 접근: {filename}")
            return jsonify({'error': 'Unauthorized file access'}), 403
        
        # 이미지 파일 확장자 확인
        allowed_extensions = {'.gif', '.png', '.jpg', '.jpeg'}
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in allowed_extensions:
            print(f"❌ 허용되지 않은 파일 확장자: {file_ext}")
            return jsonify({'error': 'Invalid file type'}), 403
            
        print(f"✅ 이미지 서빙: {filename}")
        
        # 파일이 실제로 존재하는지 다시 확인
        if not os.path.exists(full_path):
            print(f"❌ 파일 없음: {full_path}")
            return jsonify({'error': f'File not found: {filename}'}), 404
        
        try:
            response = send_from_directory(s3_chunking_path, filename)
            
            # CORS 헤더 및 캐시 헤더 추가
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
            response.headers.add('Cache-Control', 'public, max-age=300')
            
            print(f"📤 파일 전송 성공: {filename}")
            return response
        except Exception as send_error:
            print(f"❌ 파일 전송 오류: {send_error}")
            return jsonify({'error': f'File send error: {str(send_error)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Image not found: {str(e)}'}), 404

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
    
    # 문서 자동 로드
    initialize_documents()
    
    # Document Blueprint 지연 등록 (벡터DB 초기화 후)
    register_document_bp()
    
    print("🚀 BC Card RAG QA System 시작")
    print(f"📱 메인 앱: http://localhost:{Config.PORT}/deotisrag")
    print(f"📖 API 문서: http://localhost:{Config.PORT}/swagger/")
    
    app.run(debug=False, host='0.0.0.0', port=Config.PORT)