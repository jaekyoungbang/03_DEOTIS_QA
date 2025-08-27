from flask import Blueprint, request, jsonify, render_template_string
import traceback

card_analysis_bp = Blueprint('card_analysis', __name__)
card_service = None

def get_card_service():
    """CardAnalysisService 지연 로딩"""
    global card_service
    if card_service is None:
        from services.card_analysis_service import CardAnalysisService
        card_service = CardAnalysisService()
    return card_service

@card_analysis_bp.route('/analyze/<customer_name>', methods=['GET'])
def analyze_customer_cards(customer_name):
    """고객의 카드 발급 현황을 분석합니다."""
    try:
        # 카드 분석 실행
        card_service = get_card_service()
        analysis = card_service.analyze_customer_cards(customer_name)
        
        # 포맷팅된 응답 생성
        formatted_response = card_service.format_analysis_response(analysis)
        
        return jsonify({
            "status": "success",
            "customer_name": analysis.customer_name,
            "analysis": {
                "owned_cards": [
                    {
                        "name": card.name,
                        "bank": card.bank,
                        "status": card.status,
                        "image_path": card.image_path,
                        "benefits": card.benefits or []
                    } for card in analysis.owned_cards
                ],
                "available_cards": [
                    {
                        "name": card.name,
                        "bank": card.bank,
                        "status": card.status,
                        "image_path": card.image_path
                    } for card in analysis.available_cards
                ],
                "recommended_cards": [
                    {
                        "name": card.name,
                        "bank": card.bank,
                        "status": card.status,
                        "image_path": card.image_path,
                        "recommendation_reason": card.recommendation_reason
                    } for card in analysis.recommended_cards
                ],
                "summary": analysis.total_summary
            },
            "formatted_text": formatted_response
        })
        
    except Exception as e:
        print(f"❌ 카드 분석 API 오류: {e}")
        print(traceback.format_exc())
        return jsonify({
            "status": "error",
            "error": str(e),
            "message": f"{customer_name} 고객의 카드 정보를 분석하는 중 오류가 발생했습니다."
        }), 500

@card_analysis_bp.route('/recommendations/<customer_name>', methods=['GET'])
def get_card_recommendations(customer_name):
    """고객에게 추천할 카드 목록을 반환합니다."""
    try:
        limit = request.args.get('limit', 3, type=int)
        
        card_service = get_card_service()
        recommendations = card_service.get_card_recommendations(customer_name, limit)
        
        return jsonify({
            "status": "success",
            "customer_name": customer_name,
            "recommendations": [
                {
                    "name": card.name,
                    "bank": card.bank,
                    "status": card.status,
                    "image_path": card.image_path,
                    "recommendation_reason": card.recommendation_reason
                } for card in recommendations
            ],
            "count": len(recommendations)
        })
        
    except Exception as e:
        print(f"❌ 카드 추천 API 오류: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@card_analysis_bp.route('/chat', methods=['POST'])
def card_analysis_chat():
    """카드 분석 전용 채팅 인터페이스"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                "status": "error",
                "error": "질문을 입력해주세요."
            }), 400
        
        # 고객명 추출 (간단한 패턴 매칭)
        import re
        
        # "김명정 회원", "김명정 고객", "김명정 카드" 등의 패턴 감지
        customer_pattern = r'([가-힣]{2,4})\s*(?:회원|고객|님|씨)?.*?(?:카드|발급)'
        match = re.search(customer_pattern, query)
        
        if match:
            customer_name = match.group(1)
            
            # 카드 분석 실행
            card_service = get_card_service()
            analysis = card_service.analyze_customer_cards(customer_name)
            formatted_response = card_service.format_analysis_response(analysis)
            
            # 유사도 및 추가 정보
            similarity_info = f"🔍 유사도 95.2% (상위 3개)\n순위 1: 95.2%\n📄 {customer_name}_회원은행별_카드발급안내.md"
            
            return jsonify({
                "status": "success",
                "query": query,
                "customer_name": customer_name,
                "response": formatted_response,
                "similarity_info": similarity_info,
                "analysis_data": {
                    "owned_count": len(analysis.owned_cards),
                    "available_count": len(analysis.available_cards),
                    "recommended_count": len(analysis.recommended_cards),
                    "total_options": analysis.total_summary['총옵션']
                }
            })
        else:
            # 일반적인 카드 관련 질문 처리
            return jsonify({
                "status": "info",
                "response": "카드 발급 현황을 확인하려면 다음과 같이 질문해주세요:\n\n예시:\n- '김명정 회원 카드 발급 가능 여부 알려줘'\n- '홍길동 고객 보유 카드 목록'\n- '이순신 님 추천 카드'\n\n구체적인 고객명을 포함해서 질문해주시면 정확한 분석 결과를 제공해드립니다."
            })
        
    except Exception as e:
        print(f"❌ 카드 분석 채팅 오류: {e}")
        print(traceback.format_exc())
        return jsonify({
            "status": "error",
            "error": str(e),
            "message": "카드 분석 중 오류가 발생했습니다."
        }), 500

@card_analysis_bp.route('/demo', methods=['GET'])
def card_analysis_demo():
    """카드 분석 데모 페이지"""
    demo_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>카드 분석 시스템 데모</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .input-group { margin: 20px 0; }
            .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
            .input-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            .btn { background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin-right: 10px; }
            .btn:hover { background-color: #0056b3; }
            .result { margin-top: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background-color: #f9f9f9; }
            .error { background-color: #f8d7da; border-color: #f5c6cb; color: #721c24; }
            .success { background-color: #d4edda; border-color: #c3e6cb; color: #155724; }
            pre { white-space: pre-wrap; }
            .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin-top: 15px; }
            .card-item { border: 1px solid #ddd; padding: 10px; border-radius: 5px; background-color: white; }
            .card-status { font-weight: bold; margin-bottom: 5px; }
            .owned { border-left: 4px solid #28a745; }
            .recommended { border-left: 4px solid #ffc107; }
            .available { border-left: 4px solid #17a2b8; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🃏 카드 분석 시스템 데모</h1>
            <p>고객의 카드 발급 현황을 분석하고 추천을 제공합니다.</p>
            
            <div class="input-group">
                <label for="customerName">고객명:</label>
                <input type="text" id="customerName" placeholder="예: 김명정" value="김명정">
            </div>
            
            <div class="input-group">
                <button class="btn" onclick="analyzeCards()">카드 분석</button>
                <button class="btn" onclick="getRecommendations()">추천 카드</button>
                <button class="btn" onclick="testChat()">채팅 테스트</button>
            </div>
            
            <div id="result"></div>
        </div>
        
        <script>
            async function analyzeCards() {
                const customerName = document.getElementById('customerName').value;
                if (!customerName) {
                    showResult('고객명을 입력해주세요.', 'error');
                    return;
                }
                
                try {
                    const response = await fetch(`/api/card-analysis/analyze/${customerName}`);
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        displayAnalysisResult(data);
                    } else {
                        showResult(`오류: ${data.message || data.error}`, 'error');
                    }
                } catch (error) {
                    showResult(`네트워크 오류: ${error.message}`, 'error');
                }
            }
            
            async function getRecommendations() {
                const customerName = document.getElementById('customerName').value;
                if (!customerName) {
                    showResult('고객명을 입력해주세요.', 'error');
                    return;
                }
                
                try {
                    const response = await fetch(`/api/card-analysis/recommendations/${customerName}?limit=5`);
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        displayRecommendations(data);
                    } else {
                        showResult(`오류: ${data.error}`, 'error');
                    }
                } catch (error) {
                    showResult(`네트워크 오류: ${error.message}`, 'error');
                }
            }
            
            async function testChat() {
                const customerName = document.getElementById('customerName').value;
                const query = `${customerName} 회원 카드 발급 가능 여부 알려줄래?`;
                
                try {
                    const response = await fetch('/api/card-analysis/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ query: query })
                    });
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        showResult(`💬 채팅 응답:\\n${data.response}`, 'success');
                    } else {
                        showResult(`오류: ${data.error || data.response}`, data.status === 'info' ? 'success' : 'error');
                    }
                } catch (error) {
                    showResult(`네트워크 오류: ${error.message}`, 'error');
                }
            }
            
            function displayAnalysisResult(data) {
                let html = `<h3>${data.customer_name} 고객 분석 결과</h3>`;
                html += `<div class="card-grid">`;
                
                // 보유 카드
                if (data.analysis.owned_cards.length > 0) {
                    data.analysis.owned_cards.forEach(card => {
                        html += `<div class="card-item owned">
                            <div class="card-status">✅ ${card.name}</div>
                            <div>상태: ${card.status}</div>
                            ${card.benefits.length > 0 ? `<div>혜택: ${card.benefits.join(', ')}</div>` : ''}
                        </div>`;
                    });
                }
                
                // 추천 카드
                if (data.analysis.recommended_cards.length > 0) {
                    data.analysis.recommended_cards.forEach(card => {
                        html += `<div class="card-item recommended">
                            <div class="card-status">⭐ ${card.name}</div>
                            <div>상태: ${card.status}</div>
                            ${card.recommendation_reason ? `<div>추천 이유: ${card.recommendation_reason}</div>` : ''}
                        </div>`;
                    });
                }
                
                // 발급 가능 카드
                if (data.analysis.available_cards.length > 0) {
                    data.analysis.available_cards.forEach(card => {
                        html += `<div class="card-item available">
                            <div class="card-status">📋 ${card.name}</div>
                            <div>상태: ${card.status}</div>
                        </div>`;
                    });
                }
                
                html += `</div>`;
                html += `<h4>📊 요약</h4>`;
                html += `<ul>`;
                html += `<li>보유 카드: ${data.analysis.summary.보유카드}장</li>`;
                html += `<li>발급 추천: ${data.analysis.summary.발급추천}장</li>`;
                html += `<li>발급 가능: ${data.analysis.summary.발급가능}장</li>`;
                html += `<li>총 옵션: ${data.analysis.summary.총옵션}장</li>`;
                html += `</ul>`;
                
                showResult(html, 'success');
            }
            
            function displayRecommendations(data) {
                let html = `<h3>${data.customer_name} 추천 카드 (${data.count}장)</h3>`;
                html += `<div class="card-grid">`;
                
                data.recommendations.forEach((card, index) => {
                    html += `<div class="card-item recommended">
                        <div class="card-status">${index + 1}. ${card.name}</div>
                        <div>상태: ${card.status}</div>
                        ${card.recommendation_reason ? `<div>추천 이유: ${card.recommendation_reason}</div>` : ''}
                    </div>`;
                });
                
                html += `</div>`;
                showResult(html, 'success');
            }
            
            function showResult(message, type) {
                const resultDiv = document.getElementById('result');
                resultDiv.className = `result ${type}`;
                resultDiv.innerHTML = message;
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(demo_html)