from flask import Blueprint, request, jsonify
from services.similarity_suggestions import SimilaritySuggestionRAG

suggestions_bp = Blueprint('suggestions', __name__)

# 전역 인스턴스 (메모리 효율성)
_suggestion_rag = None

def get_suggestion_rag():
    """싱글톤 패턴으로 SimilaritySuggestionRAG 인스턴스 관리"""
    global _suggestion_rag
    if _suggestion_rag is None:
        _suggestion_rag = SimilaritySuggestionRAG()
    return _suggestion_rag

@suggestions_bp.route('/query', methods=['POST'])
def query_with_suggestions():
    """유사도 기반 추천을 포함한 쿼리"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON 데이터가 필요합니다.'}), 400
        
        question = data.get('question')
        use_memory = data.get('use_memory', False)
        threshold = data.get('threshold', 0.8)
        
        if not question:
            return jsonify({'error': '질문이 필요합니다.'}), 400
        
        # 유사도 기반 추천 쿼리 실행
        rag_chain = get_suggestion_rag()
        result = rag_chain.query_with_suggestions(
            question=question,
            use_memory=use_memory,
            threshold=threshold
        )
        
        return jsonify({
            'status': 'success',
            'result': result
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@suggestions_bp.route('/select', methods=['POST'])
def select_suggestion():
    """추천 선택지 선택시 4곳에서 재검색"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON 데이터가 필요합니다.'}), 400
        
        suggestion_id = data.get('suggestion_id')
        original_question = data.get('original_question')
        
        if not suggestion_id or not original_question:
            return jsonify({'error': 'suggestion_id와 original_question이 필요합니다.'}), 400
        
        # 추천 선택지 기반 재검색
        rag_chain = get_suggestion_rag()
        result = rag_chain.query_suggestion(
            suggestion_id=suggestion_id,
            original_question=original_question
        )
        
        return jsonify({
            'status': 'success',
            'result': result
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@suggestions_bp.route('/multi-search', methods=['POST'])
def multi_vectorstore_search():
    """4곳의 벡터스토어에서 동시 검색"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON 데이터가 필요합니다.'}), 400
        
        question = data.get('question')
        
        if not question:
            return jsonify({'error': '질문이 필요합니다.'}), 400
        
        # 다중 벡터스토어 검색
        rag_chain = get_suggestion_rag()
        result = rag_chain.multi_vectorstore_search(question)
        
        return jsonify({
            'status': 'success',
            'result': result
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@suggestions_bp.route('/similarity-test', methods=['POST'])
def similarity_test():
    """유사도 임계값 테스트"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON 데이터가 필요합니다.'}), 400
        
        question = data.get('question')
        thresholds = data.get('thresholds', [0.6, 0.7, 0.8, 0.9])
        
        if not question:
            return jsonify({'error': '질문이 필요합니다.'}), 400
        
        rag_chain = get_suggestion_rag()
        results = {}
        
        # 각 임계값별로 테스트
        for threshold in thresholds:
            result = rag_chain.query_with_suggestions(
                question=question,
                threshold=threshold
            )
            
            results[f"threshold_{int(threshold*100)}"] = {
                'threshold': threshold,
                'low_confidence': result.get('low_confidence', False),
                'top_similarity': result.get('top_similarity', 0),
                'suggestion_count': len(result.get('suggestions', [])),
                'confidence_message': result.get('confidence_message', '')
            }
        
        return jsonify({
            'status': 'success',
            'question': question,
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@suggestions_bp.route('/health', methods=['GET'])
def health_check():
    """건강상태 체크"""
    try:
        rag_chain = get_suggestion_rag()
        
        # 벡터스토어 문서 수 확인
        doc_count = rag_chain.vectorstore_manager.get_document_count()
        
        return jsonify({
            'status': 'healthy',
            'service': 'similarity_suggestions',
            'document_count': doc_count,
            'similarity_threshold': rag_chain.similarity_threshold,
            'features': [
                'similarity_based_suggestions',
                'multi_vectorstore_search',
                'focused_re_search',
                'threshold_testing'
            ]
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500