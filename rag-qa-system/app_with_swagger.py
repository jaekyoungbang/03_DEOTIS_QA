from flask import Flask, render_template
from flask_restx import Api
from flask_cors import CORS
import os
from config import Config
from routes.chat import chat_bp
from routes.document import document_bp
from routes.api import api as api_namespace
from routes.admin_api import api as admin_namespace
from routes.settings import settings_bp

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Initialize Flask-RESTX
api = Api(
    app,
    version='1.0',
    title='🤖 RAG QA System API',
    description='''
    ## LangChain과 ChromaDB를 활용한 문서 기반 질의응답 시스템
    
    ### 주요 기능:
    - 📄 문서 업로드 및 처리 (PDF, DOCX, TXT, MD)
    - 🤖 AI 기반 질의응답 (GPT-4o-mini, GPT-4.1-mini)
    - 🔍 벡터 검색을 통한 관련 문서 찾기
    - ⚙️ 실시간 설정 변경 (청킹, 임베딩)
    - 🔐 관리자 설정 (캐시 타입, 청크 전략)
    
    ### 사용 방법:
    1. 문서 업로드 또는 S3 폴더 로드
    2. 질문 입력
    3. AI 답변 확인
    ''',
    doc='/swagger/',
    prefix='/api'
)

# Add namespaces
api.add_namespace(api_namespace, path='/rag')
api.add_namespace(admin_namespace, path='/admin')

# Register original blueprints (for backward compatibility)
app.register_blueprint(chat_bp, url_prefix='/api/chat')
app.register_blueprint(document_bp, url_prefix='/api/document')
app.register_blueprint(settings_bp, url_prefix='/api/settings')

@app.route('/')
def index():
    return render_template('compact_index.html')

@app.route('/deotisrag')  
def deotis_index():
    return render_template('modern_index.html')

@app.route('/enhanced')
def enhanced_index():
    return render_template('enhanced_index.html')

@app.route('/health')
def health():
    return {"status": "healthy", "message": "RAG QA System is running"}

@app.route('/api-docs')
def api_docs():
    return render_template('api_docs.html')

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
    
    app.run(debug=Config.DEBUG, port=5001, host='0.0.0.0')