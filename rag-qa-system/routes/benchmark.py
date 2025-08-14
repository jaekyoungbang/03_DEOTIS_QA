from flask import Blueprint, jsonify, request
from services.enhanced_rag_chain import EnhancedRAGChain
from models.vectorstore import get_vectorstore
import json
import os

benchmark_bp = Blueprint('benchmark', __name__)

# 전역 RAG 체인 인스턴스
enhanced_rag_chain = None

def get_enhanced_rag_chain():
    """Enhanced RAG Chain 인스턴스 가져오기"""
    global enhanced_rag_chain
    if enhanced_rag_chain is None:
        vectorstore = get_vectorstore()
        enhanced_rag_chain = EnhancedRAGChain(vectorstore)
    return enhanced_rag_chain

@benchmark_bp.route('/api/benchmark/query', methods=['POST'])
def benchmark_query():
    """벤치마킹 모드로 질의 처리"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': '질문을 입력해주세요.'}), 400
        
        # Enhanced RAG Chain으로 처리
        rag_chain = get_enhanced_rag_chain()
        result = rag_chain.process_query(query)
        
        # 벤치마킹 결과 저장
        if result.get('type') == 'benchmark':
            _save_benchmark_result(result)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'처리 중 오류 발생: {str(e)}'}), 500

@benchmark_bp.route('/api/benchmark/system-info', methods=['GET'])
def get_system_info():
    """시스템 정보 반환"""
    try:
        rag_chain = get_enhanced_rag_chain()
        info = rag_chain.get_system_info()
        
        # 추가 시스템 정보
        from config import Config
        info.update({
            'python_version': Config.SYSTEM_INFO['python_version'],
            'port': Config.SYSTEM_INFO['port'],
            'embedding_model': Config.SYSTEM_INFO['current_embedding'],
            'chunking_strategy': Config.SYSTEM_INFO['current_chunking']
        })
        
        return jsonify(info)
        
    except Exception as e:
        return jsonify({'error': f'시스템 정보 조회 오류: {str(e)}'}), 500

@benchmark_bp.route('/api/benchmark/results', methods=['GET'])
def get_benchmark_results():
    """저장된 벤치마킹 결과 조회"""
    try:
        results_path = 'data/benchmark_results.json'
        
        if not os.path.exists(results_path):
            return jsonify({'message': '저장된 벤치마킹 결과가 없습니다.'}), 404
        
        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': f'결과 조회 오류: {str(e)}'}), 500

@benchmark_bp.route('/api/benchmark/clear-results', methods=['DELETE'])
def clear_benchmark_results():
    """벤치마킹 결과 초기화"""
    try:
        results_path = 'data/benchmark_results.json'
        
        if os.path.exists(results_path):
            os.remove(results_path)
        
        # RAG 체인의 벤치마커도 초기화
        rag_chain = get_enhanced_rag_chain()
        rag_chain.benchmarker.results_history = []
        
        return jsonify({'message': '벤치마킹 결과가 초기화되었습니다.'})
        
    except Exception as e:
        return jsonify({'error': f'초기화 오류: {str(e)}'}), 500

def _save_benchmark_result(result: dict):
    """벤치마킹 결과를 파일에 저장"""
    try:
        rag_chain = get_enhanced_rag_chain()
        rag_chain.benchmarker.save_results()
    except Exception as e:
        print(f"벤치마킹 결과 저장 오류: {e}")