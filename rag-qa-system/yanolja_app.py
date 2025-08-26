#!/usr/bin/env python3
"""
야놀자 RAG QA 시스템 메인 애플리케이션
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, stream_template
from flask_cors import CORS
import json
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from yanolja_config import YanoljaConfig
from yanolja_llm_client import YanoljaLLMClient, get_yanolja_client

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/yanolja/logs/yanolja-rag.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Flask 앱 생성
app = Flask(__name__)
config = YanoljaConfig()
app.config.from_object(config)
CORS(app)

# 전역 변수
executor = ThreadPoolExecutor(max_workers=4)

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('main_rag_system.html')

@app.route('/yanolja')
def yanolja_main():
    """야놀자 전용 메인 페이지"""
    models_info = config.get_all_models()
    return render_template('yanolja_main.html', models=models_info)

@app.route('/health')
def health_check():
    """헬스체크 엔드포인트"""
    try:
        client = get_yanolja_client()
        health_status = client.check_health()
        
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'service': 'Yanolja RAG System',
            'version': config.VERSION,
            'llm_status': health_status
        })
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/yanolja/models', methods=['GET'])
def get_models():
    """사용 가능한 야놀자 모델 목록 조회"""
    try:
        client = get_yanolja_client()
        health_status = client.check_health()
        models_config = config.get_all_models()
        
        models_info = []
        for model_type in models_config.keys():
            model_info = client.get_model_info(model_type)
            models_info.append(model_info)
        
        return jsonify({
            'status': 'success',
            'models': models_info,
            'health': health_status
        })
    except Exception as e:
        logger.error(f"모델 목록 조회 실패: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/yanolja/chat', methods=['POST'])
def yanolja_chat():
    """야놀자 LLM 채팅 API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '요청 데이터가 없습니다'}), 400
        
        message = data.get('message', '').strip()
        model_type = data.get('model_type', 'travel')
        context = data.get('context', [])
        
        if not message:
            return jsonify({'error': '메시지를 입력해주세요'}), 400
        
        # 지원되는 모델 타입인지 확인
        if model_type not in config.YANOLJA_MODELS:
            return jsonify({'error': f'지원되지 않는 모델 타입: {model_type}'}), 400
        
        logger.info(f"야놀자 채팅 요청 - 모델: {model_type}, 메시지: {message[:50]}...")
        
        # LLM 호출
        client = get_yanolja_client()
        start_time = time.time()
        
        response = client.chat(
            message=message,
            model_type=model_type,
            context=context
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        logger.info(f"야놀자 응답 완료 - 시간: {response_time:.2f}초")
        
        return jsonify({
            'status': 'success',
            'response': response,
            'model_type': model_type,
            'model_name': config.get_model_config(model_type)['display_name'],
            'response_time': round(response_time, 2),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"야놀자 채팅 API 에러: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/yanolja/chat/stream', methods=['POST'])
def yanolja_chat_stream():
    """야놀자 LLM 스트리밍 채팅 API"""
    try:
        data = request.get_json()
        if not data:
            return Response("요청 데이터가 없습니다", status=400)
        
        message = data.get('message', '').strip()
        model_type = data.get('model_type', 'travel')
        context = data.get('context', [])
        
        if not message:
            return Response("메시지를 입력해주세요", status=400)
        
        logger.info(f"야놀자 스트리밍 요청 - 모델: {model_type}, 메시지: {message[:50]}...")
        
        def generate():
            try:
                # 스트리밍 시작 이벤트
                yield f"data: {json.dumps({'type': 'start', 'model_type': model_type, 'timestamp': datetime.now().isoformat()}, ensure_ascii=False)}\\n\\n"
                
                client = get_yanolja_client()
                response_chunks = []
                
                # 스트리밍 응답 처리
                for chunk in client.chat_stream(message, model_type, context):
                    if chunk:
                        response_chunks.append(chunk)
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\\n\\n"
                
                # 완료 이벤트
                full_response = ''.join(response_chunks)
                yield f"data: {json.dumps({'type': 'complete', 'full_response': full_response}, ensure_ascii=False)}\\n\\n"
                
            except Exception as e:
                logger.error(f"스트리밍 처리 중 에러: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\\n\\n"
        
        return Response(
            generate(),
            mimetype='text/plain',
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'  # Nginx 버퍼링 비활성화
            }
        )
        
    except Exception as e:
        logger.error(f"야놀자 스트리밍 API 에러: {e}")
        return Response(f"에러: {str(e)}", status=500)

@app.route('/api/yanolja/benchmark', methods=['POST'])
def benchmark_models():
    """야놀자 모델 성능 벤치마크"""
    try:
        data = request.get_json()
        test_query = data.get('test_query', '안녕하세요, 서울 여행 추천해주세요')
        models_to_test = data.get('models', list(config.YANOLJA_MODELS.keys()))
        
        client = get_yanolja_client()
        results = []
        
        for model_type in models_to_test:
            if model_type in config.YANOLJA_MODELS:
                logger.info(f"벤치마크 테스트 - 모델: {model_type}")
                result = client.benchmark_model(model_type, test_query)
                results.append(result)
        
        return jsonify({
            'status': 'success',
            'test_query': test_query,
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"벤치마크 테스트 실패: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/yanolja/parallel-chat', methods=['POST'])
def parallel_chat():
    """여러 야놀자 모델 병렬 처리"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        model_types = data.get('model_types', ['travel', 'hotel'])
        context = data.get('context', [])
        
        if not message:
            return jsonify({'error': '메시지를 입력해주세요'}), 400
        
        def process_model(model_type):
            try:
                client = get_yanolja_client()
                start_time = time.time()
                response = client.chat(message, model_type, context)
                end_time = time.time()
                
                return {
                    'model_type': model_type,
                    'model_name': config.get_model_config(model_type)['display_name'],
                    'status': 'success',
                    'response': response,
                    'response_time': round(end_time - start_time, 2)
                }
            except Exception as e:
                return {
                    'model_type': model_type,
                    'status': 'error',
                    'error': str(e)
                }
        
        # 병렬 실행
        futures = []
        for model_type in model_types:
            if model_type in config.YANOLJA_MODELS:
                future = executor.submit(process_model, model_type)
                futures.append(future)
        
        # 결과 수집
        results = []
        for future in futures:
            results.append(future.result(timeout=30))
        
        return jsonify({
            'status': 'success',
            'message': message,
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"병렬 처리 실패: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # 로그 디렉토리 생성
    os.makedirs('/opt/yanolja/logs', exist_ok=True)
    
    logger.info(f"🏢 야놀자 RAG QA 시스템 시작...")
    logger.info(f"📋 설정: {config.PROJECT_NAME} v{config.VERSION}")
    logger.info(f"🤖 LLM URL: {config.OLLAMA_BASE_URL}")
    logger.info(f"🌐 서버: http://{config.HOST}:{config.PORT}")
    
    # 야놀자 LLM 상태 체크
    try:
        client = get_yanolja_client()
        health = client.check_health()
        logger.info(f"🔍 LLM 상태: {health}")
    except Exception as e:
        logger.warning(f"⚠️ LLM 초기 상태 체크 실패: {e}")
    
    # 서버 실행
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        threaded=True
    )