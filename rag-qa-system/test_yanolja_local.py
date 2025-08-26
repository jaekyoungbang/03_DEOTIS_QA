#!/usr/bin/env python3
"""
야놀자 LLM 로컬 테스트 스크립트
Windows/Linux 모두에서 실행 가능
"""

import os
import sys
import time
import requests
from dotenv import load_dotenv

# .env.local 로드
load_dotenv('.env.local')

def check_ollama_status():
    """Ollama 서비스 상태 확인"""
    print("🔍 Ollama 서비스 확인 중...")
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✅ Ollama 서비스 정상 작동 중")
            print(f"📦 설치된 모델 수: {len(models)}")
            for model in models:
                print(f"   - {model['name']} ({model.get('size', 'N/A')})")
            return True
        else:
            print(f"❌ Ollama 서비스 응답 오류: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama 서비스 연결 실패: {str(e)}")
        print("💡 Ollama가 실행 중인지 확인하세요:")
        print("   Windows: Ollama 앱이 실행 중인지 시스템 트레이 확인")
        print("   Linux: sudo systemctl status ollama")
        return False

def test_yanolja_models():
    """야놀자 모델 테스트"""
    print("\n🏨 야놀자 모델 테스트 시작...")
    
    from yanolja_llm_client import get_yanolja_client
    client = get_yanolja_client()
    
    # 헬스체크
    health = client.check_health()
    print(f"\n📊 시스템 상태: {health['status']}")
    print(f"🔗 Ollama URL: {health.get('ollama_url')}")
    print(f"✅ 사용 가능 모델: {health.get('available_models', [])}")
    print(f"❌ 누락된 모델: {health.get('missing_models', [])}")
    
    if health['status'] != 'healthy':
        print("\n⚠️  필요한 모델을 설치하세요:")
        for model in health.get('missing_models', []):
            print(f"   ollama pull {model}")
        return False
    
    # 각 모델 테스트
    test_cases = [
        ('travel', "제주도 3박4일 여행 추천해줘"),
        ('hotel', "서울 강남에서 5만원대 호텔 추천해줘"),
        ('general', "야놀자 앱 사용법 알려줘")
    ]
    
    for model_type, query in test_cases:
        print(f"\n📝 {model_type.upper()} 모델 테스트")
        print(f"질문: {query}")
        
        start_time = time.time()
        try:
            response = client.chat(query, model_type=model_type)
            elapsed = time.time() - start_time
            
            print(f"✅ 응답 시간: {elapsed:.2f}초")
            print(f"답변: {response[:200]}...")
        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}")
    
    return True

def test_rag_integration():
    """RAG 시스템 통합 테스트"""
    print("\n🔧 RAG 시스템 통합 테스트...")
    
    try:
        # Flask 앱이 실행 중인지 확인
        response = requests.get("http://localhost:5000/health")
        if response.status_code == 200:
            print("✅ Flask 앱 정상 작동 중")
            
            # 야놀자 LLM으로 테스트 쿼리
            test_query = {
                "question": "야놀자 서비스에 대해 알려줘",
                "use_memory": False,
                "llm_model": "yanolja"
            }
            
            response = requests.post(
                "http://localhost:5000/api/chat/query",
                json=test_query
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ RAG 응답 성공")
                print(f"답변: {result.get('answer', '')[:200]}...")
            else:
                print(f"❌ RAG 응답 실패: {response.status_code}")
        else:
            print("❌ Flask 앱이 실행되지 않음")
            print("💡 다음 명령으로 실행하세요:")
            print("   python app.py")
    except Exception as e:
        print(f"❌ 통합 테스트 실패: {str(e)}")

def main():
    print("="*60)
    print("🏨 야놀자 LLM 로컬 테스트")
    print("="*60)
    
    # 1. Ollama 상태 확인
    if not check_ollama_status():
        print("\n❌ Ollama 설치 및 실행이 필요합니다.")
        print("\n📌 설치 방법:")
        print("Windows: https://ollama.com/download/windows")
        print("Linux: curl -fsSL https://ollama.com/install.sh | sh")
        return
    
    # 2. 야놀자 모델 테스트
    if test_yanolja_models():
        print("\n✅ 야놀자 모델 테스트 완료")
    
    # 3. RAG 통합 테스트
    test_rag_integration()
    
    print("\n="*60)
    print("✅ 로컬 테스트 완료!")
    print("\n다음 단계:")
    print("1. 모든 테스트가 성공하면 리눅스 서버에 동일하게 설치")
    print("2. .env 파일을 서버 환경에 맞게 수정")
    print("3. systemd 서비스로 등록하여 자동 시작 설정")
    print("="*60)

if __name__ == "__main__":
    main()