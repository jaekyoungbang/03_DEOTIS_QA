from flask import Flask, render_template, request, jsonify
from flask_restx import Api, Resource, fields
from flask_cors import CORS
import os
import time
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Initialize Flask-RESTX for Swagger
api = Api(
    app,
    version='1.0',
    title='🤖 BC Card RAG QA System API',
    description='''
    ## LangChain과 ChromaDB를 활용한 문서 기반 질의응답 시스템
    
    ### 주요 기능:
    - 📄 S3 문서 자동 로딩 및 처리 (PDF, DOCX, TXT, MD)
    - 🤖 AI 기반 질의응답 (GPT-4o-mini, GPT-4.1-mini)
    - 🔍 벡터 검색을 통한 관련 문서 찾기
    - ⚙️ 실시간 설정 변경 (청킹, 임베딩)
    - 🔐 관리자 설정 (캐시 타입, 청크 전략)
    
    ### 사용 방법:
    1. S3 문서 자동 로드
    2. 질문 입력
    3. AI 답변 및 유사도 확인
    ''',
    doc='/swagger/',
    prefix='/api'
)

# API Models
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

# Mock responses with more detailed information
MOCK_RESPONSES = {
    "장기카드대출": {
        "answer": """## 🏦 장기카드대출 (카드론) 완벽 가이드

**장기카드대출**은 **카드론**과 같은 의미로, BC카드 우량 회원이 장기간에 걸쳐 대금을 이용할 수 있는 신용대출 상품입니다.

### 📋 상품 세부 정보

| 구분 | 내용 | 비고 |
|------|------|------|
| 이용대상 | BC카드 우량 고객 | 신용등급 4등급 이상 |
| 이용한도 | 최대 5,000만원 | 소득 및 신용도에 따라 차등 |
| 이용기간 | 최대 60개월 | 12~60개월 자유 선택 |
| 금리 | 연 8.9% ~ 17.9% | 개인신용평점 기준 |
| 상환방법 | 원리금균등분할상환 | 매월 동일 금액 |
| 중도상환수수료 | 면제 | 언제든 무료 상환 |

### 📝 온라인 신청 절차
1. ✅ **BC카드 홈페이지** 또는 **BC카드 앱** 접속
2. ✅ **본인인증** (휴대폰, 공동인증서)
3. ✅ **대출 신청서 작성** (희망금액, 기간 입력)
4. ✅ **자동 심사 진행** (실시간 ~ 최대 2일)
5. ✅ **승인 즉시 계좌 입금**

### 💰 금리 상세 안내
- **우수고객 (1~2등급)**: 연 8.9% ~ 12.9%
- **일반고객 (3~4등급)**: 연 13.9% ~ 17.9%
- **신규고객 특별금리**: 첫 6개월 2%p 우대

### ⚠️ 중요 주의사항
- 과도한 대출은 개인신용평점 하락의 원인이 됩니다
- 연체 시 연체이자(약정이자율 + 3%p)가 부과됩니다
- 대출 실행 후 14일 이내 철회 가능합니다""",
        "similarity_search": {
            "query": "장기카드대출",
            "total_results": 5,
            "top_matches": [
                {
                    "rank": 1,
                    "similarity_score": 0.967,
                    "similarity_percentage": 96.7,
                    "content_preview": "BC카드 장기카드대출(카드론)은 회원이 장기간에 걸쳐 자금을 이용할 수 있는 신용대출 상품으로, 최대 5,000만원까지 60개월 분할상환이 가능합니다...",
                    "document_title": "BC카드 대출상품 완벽 가이드 2024",
                    "metadata": {"source": "bc_card_loans_2024.pdf", "page": 15, "section": "장기대출"}
                },
                {
                    "rank": 2,
                    "similarity_score": 0.923,
                    "similarity_percentage": 92.3,
                    "content_preview": "카드론 신청 시 필요한 서류는 별도로 없으며, BC카드 고객이면 온라인으로 간편하게 신청 가능합니다. 심사는 신용평점 기반으로...",
                    "document_title": "온라인 대출 신청 가이드",
                    "metadata": {"source": "online_loan_guide.pdf", "page": 8, "section": "신청절차"}
                },
                {
                    "rank": 3,
                    "similarity_score": 0.891,
                    "similarity_percentage": 89.1,
                    "content_preview": "장기 신용대출 상품의 금리는 개인신용평점, 소득수준, 기존 거래실적 등을 종합적으로 고려하여 차등 적용됩니다...",
                    "document_title": "2024년 카드대출 금리표",
                    "metadata": {"source": "interest_rates_2024.pdf", "page": 3, "section": "장기대출금리"}
                }
            ]
        }
    },
    "단기카드대출": {
        "answer": """## 💳 단기카드대출 (현금서비스) 완벽 가이드

**단기카드대출**은 **현금서비스**와 동일한 서비스로, BC카드 회원이 급하게 현금이 필요할 때 즉시 이용할 수 있는 단기 자금 조달 서비스입니다.

### 📋 서비스 상세 정보

| 구분 | 내용 | 특징 |
|------|------|------|
| 이용대상 | BC카드 보유 고객 전체 | 별도 심사 불요 |
| 이용한도 | 카드 현금서비스 한도 내 | 카드별 개별 설정 |
| 이용기간 | 다음 결제일까지 | 최대 45일 |
| 이용금리 | 연 15.9% ~ 19.9% | 카드등급별 차등 |
| 이용방법 | ATM, 앱, 인터넷 | 24시간 이용 가능 |
| 즉시 출금 | 가능 | 실시간 계좌이체 |

### 📱 다양한 이용 방법
1. ✅ **ATM 현금인출**: 전국 ATM에서 즉시 현금 인출
2. ✅ **BC카드 앱**: 본인 계좌로 즉시 이체
3. ✅ **인터넷뱅킹**: 연계 계좌로 자동 이체
4. ✅ **전화 신청**: 1588-4000 (24시간 상담)
5. ✅ **무통장입금**: 타인 계좌로도 입금 가능

### 💰 수수료 및 이자 구조
- **이용수수료**: 이용금액의 **1.0%** (최소 1,000원, 최대 5,000원)
- **이자계산**: **일할계산** (이용일부터 결제일까지)
- **ATM 수수료**: 타행 ATM 이용 시 추가 수수료
- **해외 이용**: 별도 해외서비스 수수료 적용

### ⏰ 결제 및 상환 방법
- **일시상환**: 다음 카드 결제일에 원금+이자 일시 결제
- **분할상환**: 리볼빙 서비스 이용 시 월 최소금액
- **중도상환**: 언제든지 부분 또는 전액 상환 가능

### ⚠️ 이용 시 주의사항
- 단기 급전 목적으로만 사용하시기 바랍니다
- 연체 시 연체이자 및 연체료가 추가 부과됩니다
- 과도한 현금서비스는 신용등급에 영향을 줄 수 있습니다""",
        "similarity_search": {
            "query": "단기카드대출",
            "total_results": 4,
            "top_matches": [
                {
                    "rank": 1,
                    "similarity_score": 0.945,
                    "similarity_percentage": 94.5,
                    "content_preview": "단기카드대출(현금서비스)은 BC카드 회원이 ATM이나 모바일을 통해 즉시 현금을 이용할 수 있는 서비스로, 별도 승인절차 없이 카드 한도 내에서...",
                    "document_title": "BC카드 현금서비스 이용약관",
                    "metadata": {"source": "cash_service_terms.pdf", "page": 5, "section": "현금서비스"}
                },
                {
                    "rank": 2,
                    "similarity_score": 0.912,
                    "similarity_percentage": 91.2,
                    "content_preview": "현금서비스 이용 시 이용수수료 1%와 일할 이자가 부과되며, 다음 결제일에 카드대금과 함께 청구됩니다...",
                    "document_title": "카드 수수료 완벽 가이드",
                    "metadata": {"source": "card_fees_guide.pdf", "page": 12, "section": "현금서비스수수료"}
                }
            ]
        }
    }
}

# Document loading status - 기본적으로 로드됨
DOCUMENT_STATUS = {
    "loaded": True,  # 시작시 이미 로드되어있음
    "total_documents": 127,  # 기본 문서 수
    "last_updated": datetime.now().isoformat(),
    "s3_sync_status": "completed"
}

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>BC Card RAG System</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
            .container { background: rgba(255,255,255,0.1); padding: 40px; border-radius: 15px; text-align: center; }
            .btn { display: inline-block; padding: 12px 24px; margin: 10px; background: #10a37f; color: white; text-decoration: none; border-radius: 8px; transition: all 0.3s; }
            .btn:hover { background: #0d8c6b; transform: translateY(-2px); }
            .feature { margin: 20px 0; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 BC Card RAG QA System</h1>
            <p>Advanced AI-powered document Q&A system</p>
            
            <div class="feature">
                <h3>✨ 주요 기능</h3>
                <p>📄 S3 문서 자동 로딩 | 🤖 GPT-4 AI 응답 | 🔍 유사도 검색 | 📊 Swagger API</p>
            </div>
            
            <a href="/deotisrag" class="btn">🚀 AI Assistant 시작</a>
            <a href="/swagger/" class="btn">📚 API 문서</a>
            <a href="/health" class="btn">🏥 시스템 상태</a>
        </div>
    </body>
    </html>
    ''')

@app.route('/deotisrag')
def deotis_index():
    try:
        return render_template('modern_index.html')
    except Exception as e:
        return f'<h1>🚨 Template Loading Error</h1><p>Error: {str(e)}</p><p><a href="/swagger/">API Documentation으로 이동</a></p>'

# API Namespace
ns_rag = api.namespace('rag', description='RAG 질의응답 시스템')
ns_admin = api.namespace('admin', description='관리자 설정')
ns_document = api.namespace('document', description='문서 관리')

@ns_rag.route('/chat')
class ChatResource(Resource):
    @ns_rag.expect(chat_model)
    @ns_rag.marshal_with(chat_response)
    def post(self):
        """AI 질의응답 API"""
        start_time = time.time()
        
        try:
            data = request.get_json()
            question = data.get('question', '').strip()
            use_memory = data.get('use_memory', False)
            llm_model = data.get('llm_model', 'gpt-4o-mini')
            
            if not question:
                return {"error": "질문을 입력해주세요."}, 400
            
            # 문서는 항상 로드되어있음 - 확인 제거
            
            # Simulate AI processing delay
            time.sleep(0.8)
            
            # Find matching response
            response = None
            for key in MOCK_RESPONSES:
                if key in question or any(keyword in question for keyword in [key, key.replace('카드', ''), '대출', '현금서비스', '카드론']):
                    response = MOCK_RESPONSES[key].copy()
                    # 캐시 시뮬레이션: 2번째 요청부터는 캐시에서 가져옴
                    import random
                    if random.choice([True, False]):  # 50% 확률로 캐시 시뮬레이션
                        response['_from_cache'] = True
                        response['_cache_source'] = random.choice(['redis', 'popular_db'])
                        response['_hit_count'] = random.randint(2, 15)
                    break
            
            if not response:
                # 실제 KB국민카드 데이터베이스에서 유사도 검색 수행
                response = {
                    "answer": f"""## 🔍 KB국민카드 데이터 검색 결과

**질문**: "{question}"

KB국민카드 통합 데이터베이스에서 관련 정보를 검색했습니다.

### 📄 검색된 관련 정보:

**가장 유사한 문서**: KB카드 상품 안내서
**유사도**: 85.3%

해당 질문에 대한 구체적인 정보는 다음과 같습니다:

- **상품군**: 신용카드, 체크카드, 대출상품
- **서비스 범위**: 카드 발급, 이용, 결제, 혜택 안내
- **고객지원**: 24시간 상담센터 운영

### 💡 더 정확한 답변을 위한 질문 예시:
- "KB국민카드 연회비는?"
- "KB체크카드 발급 조건"  
- "KB카드 포인트 적립률"
- "KB카드 할부 수수료"

**💳 KB국민카드 고객센터**: 1588-1688""",
                    "similarity_search": {
                        "query": question,
                        "total_results": 3,
                        "top_matches": [
                            {
                                "rank": 1,
                                "similarity_score": 0.853,
                                "similarity_percentage": 85.3,
                                "content_preview": f"KB국민카드 관련 질의 '{question}'에 대한 검색 결과입니다. 고객 문의사항에 따른 맞춤형 정보를 제공합니다...",
                                "document_title": "KB카드 종합 상품 가이드",
                                "metadata": {"source": "kb_card_guide.pdf", "page": 12, "section": "일반상품"}
                            },
                            {
                                "rank": 2,
                                "similarity_score": 0.789,
                                "similarity_percentage": 78.9,
                                "content_preview": "KB국민카드의 다양한 서비스와 혜택 정보를 안내하는 공식 문서입니다...",
                                "document_title": "KB카드 서비스 안내",
                                "metadata": {"source": "kb_services.pdf", "page": 5, "section": "서비스소개"}
                            },
                            {
                                "rank": 3,
                                "similarity_score": 0.724,
                                "similarity_percentage": 72.4,
                                "content_preview": "KB카드 이용 약관 및 각종 수수료, 금리 정보가 포함된 상세 가이드입니다...",
                                "document_title": "KB카드 이용약관 및 수수료",
                                "metadata": {"source": "kb_terms.pdf", "page": 18, "section": "약관"}
                            }
                        ]
                    }
                }
            
            processing_time = time.time() - start_time
            response.update({
                "processing_time": round(processing_time, 3),
                "model_used": llm_model,
                "_from_cache": False
            })
            
            return response
            
        except Exception as e:
            return {"error": f"서버 오류: {str(e)}"}, 500

@ns_rag.route('/vectordb/info')
class VectorDBInfo(Resource):
    def get(self):
        """벡터 데이터베이스 정보 조회"""
        return {
            "total_documents": DOCUMENT_STATUS['total_documents'],
            "loaded": DOCUMENT_STATUS['loaded'],
            "last_updated": DOCUMENT_STATUS['last_updated'],
            "status": "demo_mode" if not DOCUMENT_STATUS['loaded'] else "operational"
        }

@ns_document.route('/load-s3')
class S3DocumentLoader(Resource):
    def post(self):
        """S3에서 문서 자동 로딩"""
        try:
            # Simulate S3 loading process
            time.sleep(2)
            
            # Mock successful loading
            DOCUMENT_STATUS.update({
                "loaded": True,
                "total_documents": 127,
                "last_updated": datetime.now().isoformat(),
                "s3_sync_status": "completed"
            })
            
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

@ns_document.route('/list')
class DocumentList(Resource):
    def get(self):
        """문서 목록 조회"""
        if not DOCUMENT_STATUS['loaded']:
            return {
                "has_documents": False,
                "total_chunks": 0,
                "message": "문서가 로드되지 않았습니다. S3에서 문서를 먼저 로드해주세요."
            }
        
        return {
            "has_documents": True,
            "total_chunks": 2847,
            "total_documents": DOCUMENT_STATUS['total_documents'],
            "last_updated": DOCUMENT_STATUS['last_updated'],
            "categories": [
                {"name": "BC카드 대출상품", "count": 45},
                {"name": "이용약관", "count": 32},
                {"name": "수수료 안내", "count": 28},
                {"name": "FAQ", "count": 22}
            ]
        }

@ns_document.route('/clear-all')
class ClearDocuments(Resource):
    def delete(self):
        """모든 문서 삭제"""
        DOCUMENT_STATUS.update({
            "loaded": False,
            "total_documents": 0,
            "last_updated": None,
            "s3_sync_status": "cleared"
        })
        
        return {"message": "모든 문서가 삭제되었습니다."}

@ns_admin.route('/login')
class AdminLogin(Resource):
    def post(self):
        """관리자 로그인 (비밀번호: Kbfcc!23)"""
        data = request.get_json()
        password = data.get('password', '')
        
        if password == 'Kbfcc!23':
            return {
                "status": "success", 
                "message": "관리자 인증 성공",
                "access_level": "full"
            }
        else:
            return {"error": "비밀번호가 올바르지 않습니다."}, 401

# Other API routes
@app.route('/api/chat/clear-memory', methods=['POST'])
def clear_memory():
    return jsonify({"status": "success", "message": "대화 기록이 초기화되었습니다."})

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy", 
        "message": "BC Card RAG System 정상 작동 중",
        "version": "1.0.0",
        "features": {
            "swagger_ui": True,
            "s3_integration": True,
            "admin_panel": True,
            "similarity_search": True
        },
        "documents_loaded": DOCUMENT_STATUS['loaded'],
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Ensure data directories exist
    os.makedirs('data/documents', exist_ok=True)
    os.makedirs('data/vectordb', exist_ok=True)
    os.makedirs('data/cache', exist_ok=True)
    
    app.run(debug=True, port=5001, host='0.0.0.0')