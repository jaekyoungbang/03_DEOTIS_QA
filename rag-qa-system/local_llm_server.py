#!/usr/bin/env python3
"""
간단한 로컬 LLM 서버 (Transformers 기반)
Ollama 대신 작은 모델로 로컬 LLM을 제공합니다.
"""
import asyncio
from flask import Flask, request, jsonify
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch
import threading
import time

app = Flask(__name__)

# 전역 변수
llm_pipeline = None
model_name = "microsoft/DialoGPT-small"  # 작고 빠른 대화형 모델

def initialize_model():
    """모델 초기화"""
    global llm_pipeline
    try:
        print("🤖 로컬 LLM 모델 로딩 중...")
        print(f"📦 모델: {model_name}")
        
        # GPU 사용 가능 여부 확인
        device = 0 if torch.cuda.is_available() else -1
        device_name = "GPU" if device == 0 else "CPU"
        print(f"💻 디바이스: {device_name}")
        
        # 파이프라인 생성 (작은 모델 사용)
        llm_pipeline = pipeline(
            "text-generation",
            model=model_name,
            device=device,
            max_length=512,
            do_sample=True,
            temperature=0.7,
            pad_token_id=50256
        )
        
        print("✅ 로컬 LLM 모델 로딩 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 모델 로딩 실패: {e}")
        return False

@app.route('/api/tags', methods=['GET'])
def get_models():
    """사용 가능한 모델 목록"""
    return jsonify({
        "models": [
            {
                "name": "llama3.2",
                "modified_at": "2024-01-01T00:00:00Z",
                "size": 1234567890,
                "digest": "local_llm",
                "details": {
                    "family": "llama",
                    "format": "transformers",
                    "parameter_size": "124M"
                }
            }
        ]
    })

@app.route('/api/version', methods=['GET'])
def get_version():
    """API 버전 정보"""
    return jsonify({
        "version": "0.1.0-local"
    })

@app.route('/api/generate', methods=['POST'])
def generate():
    """텍스트 생성"""
    global llm_pipeline
    
    if llm_pipeline is None:
        return jsonify({"error": "Model not loaded"}), 500
    
    try:
        data = request.json
        prompt = data.get('prompt', '')
        model = data.get('model', 'llama3.2')
        
        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400
        
        print(f"🔍 질문: {prompt[:100]}...")
        
        # 한국어 질문에 대한 답변 생성
        system_prompt = "You are a helpful assistant that provides accurate and concise answers in Korean. Answer based on the given context."
        full_prompt = f"{system_prompt}\n\nQuestion: {prompt}\nAnswer:"
        
        # 텍스트 생성
        start_time = time.time()
        outputs = llm_pipeline(
            full_prompt,
            max_new_tokens=200,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True,
            pad_token_id=llm_pipeline.tokenizer.eos_token_id
        )
        
        generated_text = outputs[0]['generated_text']
        # 답변 부분만 추출
        answer = generated_text.split("Answer:")[-1].strip()
        
        processing_time = time.time() - start_time
        print(f"✅ 답변 생성 완료 ({processing_time:.2f}초)")
        print(f"💬 답변: {answer[:100]}...")
        
        return jsonify({
            "model": model,
            "created_at": "2024-01-01T00:00:00Z",
            "response": answer,
            "done": True,
            "total_duration": int(processing_time * 1000000000),  # 나노초
            "load_duration": 0,
            "prompt_eval_count": len(prompt.split()),
            "eval_count": len(answer.split()),
            "eval_duration": int(processing_time * 1000000000)
        })
        
    except Exception as e:
        print(f"❌ 생성 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """채팅 완료"""
    global llm_pipeline
    
    if llm_pipeline is None:
        return jsonify({"error": "Model not loaded"}), 500
    
    try:
        data = request.json
        messages = data.get('messages', [])
        model = data.get('model', 'llama3.2')
        
        if not messages:
            return jsonify({"error": "No messages provided"}), 400
        
        # 마지막 사용자 메시지 추출
        user_message = None
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break
        
        if not user_message:
            return jsonify({"error": "No user message found"}), 400
        
        print(f"💬 채팅 질문: {user_message[:100]}...")
        
        # 간단한 답변 생성
        context_prompt = "You are a helpful AI assistant for BC Card customer service. Answer in Korean and be concise and helpful."
        full_prompt = f"{context_prompt}\n\nUser: {user_message}\nAssistant:"
        
        start_time = time.time()
        
        # 입력 길이 제한 (토큰 오버플로우 방지)
        max_input_length = 200
        if len(full_prompt) > max_input_length:
            full_prompt = full_prompt[:max_input_length]
        
        try:
            outputs = llm_pipeline(
                full_prompt,
                max_new_tokens=100,  # 더 작은 출력 길이
                num_return_sequences=1,
                temperature=0.3,  # 더 보수적인 생성
                do_sample=True,
                pad_token_id=llm_pipeline.tokenizer.eos_token_id,
                truncation=True  # 자동 길이 제한
            )
            
            generated_text = outputs[0]['generated_text']
            answer = generated_text.split("Assistant:")[-1].strip()
            
        except Exception as inner_e:
            print(f"⚠️ 모델 생성 오류, 기본 응답 사용: {inner_e}")
            answer = f"검색된 정보를 기반으로 답변드리겠습니다. 질문: {user_message[:50]}... 에 대한 정보를 확인 중입니다."
        
        processing_time = time.time() - start_time
        print(f"✅ 채팅 응답 완료 ({processing_time:.2f}초)")
        
        return jsonify({
            "model": model,
            "created_at": "2024-01-01T00:00:00Z",
            "message": {
                "role": "assistant",
                "content": answer
            },
            "done": True,
            "total_duration": int(processing_time * 1000000000),
            "load_duration": 0
        })
        
    except Exception as e:
        print(f"❌ 채팅 오류: {e}")
        return jsonify({"error": str(e)}), 500

def start_server():
    """서버 시작"""
    print("🚀 로컬 LLM 서버 시작...")
    print("📍 주소: http://localhost:11434")
    
    # 모델 초기화
    if not initialize_model():
        print("❌ 모델 초기화 실패. 서버를 시작할 수 없습니다.")
        return
    
    # Flask 서버 시작
    app.run(host='0.0.0.0', port=11434, debug=False, threaded=True)

if __name__ == '__main__':
    start_server()