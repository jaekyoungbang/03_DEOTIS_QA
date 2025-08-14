from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import time

app = Flask(__name__)
CORS(app)

# Mock AI responses for testing
MOCK_RESPONSES = {
    "장기카드대출": {
        "answer": """## 🏦 장기카드대출 (카드론) 안내

**장기카드대출**은 **카드론**과 같은 의미로, BC카드 회원이 장기간에 걸쳐 자금을 이용할 수 있는 대출 상품입니다.

### 📋 상품 정보

| 구분 | 내용 |
|------|------|
| 이용대상 | BC카드 우량 고객 |
| 이용한도 | 최대 5,000만원 |
| 이용기간 | 최대 60개월 |
| 금리 | 연 8.9% ~ 17.9% |
| 상환방법 | 원리금균등분할상환 |

### 📝 신청 방법
1. ✅ BC카드 홈페이지 또는 모바일앱 접속
2. ✅ 본인인증 및 로그인
3. ✅ 대출 신청서 작성
4. ✅ 심사 진행 (1~2일 소요)
5. ✅ 승인 시 계좌 입금

### ⚠️ 주의사항
- 과도한 대출은 개인신용평점 하락의 원인이 될 수 있습니다
- 연체 시 연체이자가 부과됩니다""",
        "similarity_search": {
            "query": "장기카드대출",
            "total_results": 3,
            "top_matches": [
                {
                    "rank": 1,
                    "similarity_score": 0.95,
                    "similarity_percentage": 95,
                    "content_preview": "BC카드 장기카드대출(카드론)은 회원이 장기간에 걸쳐 자금을 이용할 수 있는 신용대출 상품입니다...",
                    "document_title": "BC카드 대출상품 가이드",
                    "metadata": {"source": "bc_card_loans.pdf", "page": 15}
                },
                {
                    "rank": 2,
                    "similarity_score": 0.87,
                    "similarity_percentage": 87,
                    "content_preview": "카드론 이용 시 최대 5,000만원까지 한도 설정이 가능하며, 최대 60개월까지 분할상환...",
                    "document_title": "대출 이용약관",
                    "metadata": {"source": "loan_terms.pdf", "page": 8}
                },
                {
                    "rank": 3,
                    "similarity_score": 0.82,
                    "similarity_percentage": 82,
                    "content_preview": "장기 신용대출 상품의 금리는 개인신용평점 및 소득에 따라 차등 적용됩니다...",
                    "document_title": "금리 안내서",
                    "metadata": {"source": "interest_rates.pdf", "page": 3}
                }
            ]
        }
    },
    "단기카드대출": {
        "answer": """## 💳 단기카드대출 (현금서비스) 안내

**단기카드대출**은 **현금서비스**와 같은 의미로, BC카드 회원이 단기간 현금이 필요할 때 이용하는 서비스입니다.

### 📋 상품 정보

| 구분 | 내용 |
|------|------|
| 이용대상 | BC카드 보유 고객 |
| 이용한도 | 카드 현금서비스 한도 내 |
| 이용기간 | 다음 결제일까지 |
| 금리 | 연 15.9% ~ 19.9% |
| 이용방법 | ATM, 인터넷, 모바일 |

### 📝 이용 방법
1. ✅ ATM에서 현금서비스 이용
2. ✅ BC카드 앱에서 계좌이체
3. ✅ 인터넷뱅킹 연계 서비스
4. ✅ 전화 신청 (1588-4000)

### 💰 수수료 및 이자
- **이용수수료**: 이용금액의 1% (최소 1,000원)
- **이자**: 일할계산 (이용일부터 결제일까지)

### ⚠️ 주의사항
- 단기 자금 용도로만 사용하시기 바랍니다
- 연체 시 추가 수수료가 발생합니다""",
        "similarity_search": {
            "query": "단기카드대출",
            "total_results": 3,
            "top_matches": [
                {
                    "rank": 1,
                    "similarity_score": 0.93,
                    "similarity_percentage": 93,
                    "content_preview": "단기카드대출(현금서비스)은 BC카드 회원이 ATM이나 모바일을 통해 즉시 현금을 이용할 수 있는...",
                    "document_title": "BC카드 현금서비스 가이드",
                    "metadata": {"source": "cash_service.pdf", "page": 5}
                },
                {
                    "rank": 2,
                    "similarity_score": 0.89,
                    "similarity_percentage": 89,
                    "content_preview": "현금서비스 이용 시 이용수수료 1%와 일할 이자가 부과되며, 다음 결제일에 일시상환...",
                    "document_title": "수수료 안내",
                    "metadata": {"source": "fees_guide.pdf", "page": 12}
                },
                {
                    "rank": 3,
                    "similarity_score": 0.85,
                    "similarity_percentage": 85,
                    "content_preview": "ATM 이용 시간은 은행별로 다르며, 24시간 이용 가능한 ATM에서 현금서비스를...",
                    "document_title": "이용 안내서",
                    "metadata": {"source": "usage_guide.pdf", "page": 7}
                }
            ]
        }
    }
}

@app.route('/')
def index():
    return '<h1>🤖 BC Card AI Assistant</h1><p><a href="/deotisrag">AI Assistant 시작하기</a></p>'

@app.route('/deotisrag')
def deotis_index():
    try:
        return render_template('modern_index.html')
    except Exception as e:
        return f'<h1>Template Error: {str(e)}</h1>'

@app.route('/api/rag/chat', methods=['POST'])
def rag_chat():
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        use_memory = data.get('use_memory', False)
        llm_model = data.get('llm_model', 'gpt-4o-mini')
        
        if not question:
            return jsonify({"error": "질문을 입력해주세요."}), 400
        
        # Simulate processing delay
        time.sleep(1)
        
        # Check for mock responses
        response = None
        for key in MOCK_RESPONSES:
            if key in question:
                response = MOCK_RESPONSES[key].copy()
                response['_from_cache'] = False
                response['model_used'] = llm_model
                break
        
        if not response:
            # Generic response for other questions
            response = {
                "answer": f"""## 🤖 AI 응답

**질문**: {question}

죄송합니다. 현재 **데모 모드**로 운영 중이어서 제한된 답변만 제공됩니다.

### 📝 이용 가능한 질문들:
- ✅ **장기카드대출**에 대한 문의
- ✅ **단기카드대출**에 대한 문의  
- ✅ **카드 할부 수수료**에 대한 문의
- ✅ **신용공여기간**에 대한 문의

### 🔧 전체 기능 이용하기:
1. OpenAI API 키 설정
2. 벡터 데이터베이스 구축
3. 문서 업로드 및 인덱싱

*현재는 UI 및 레이아웃 테스트 버전입니다.*""",
                "similarity_search": {
                    "query": question,
                    "total_results": 0,
                    "top_matches": []
                },
                "_from_cache": False,
                "model_used": llm_model
            }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "error": f"서버 오류가 발생했습니다: {str(e)}"
        }), 500

@app.route('/api/chat/clear-memory', methods=['POST'])
def clear_memory():
    return jsonify({"status": "success", "message": "메모리가 초기화되었습니다."})

@app.route('/api/rag/vectordb/info')
def vectordb_info():
    return jsonify({
        "total_documents": 0,
        "status": "demo_mode",
        "message": "데모 모드 - 벡터DB 없음"
    })

@app.route('/api/document/list')
def document_list():
    return jsonify({
        "has_documents": False,
        "total_chunks": 0,
        "documents": []
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "message": "서버가 정상 작동 중입니다."})

if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')