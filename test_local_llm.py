import openai
import requests
import json

# OpenAI 클라이언트 설정
openai.api_base = "http://192.168.0.224:8412/v1"
openai.api_key = "EMPTY"

print("=== OpenAI 클라이언트 테스트 ===")
try:
    response = openai.ChatCompletion.create(
        model="./models/kanana8b",
        messages=[{"role": "user", "content": "안녕!"}],
        max_tokens=50
    )
    print("✅ OpenAI 클라이언트 성공:")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"❌ OpenAI 클라이언트 실패: {e}")

print("\n=== cURL 형태 테스트 ===")
try:
    url = "http://192.168.0.224:8412/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "yanolja/EEVE-Korean-Instruct-10.8B-v1.0",
        "messages": [{"role": "user", "content": "안녕하세요!"}],
        "max_tokens": 50
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ cURL 형태 성공:")
        print(result.get('choices', [{}])[0].get('message', {}).get('content', 'No content'))
    else:
        print(f"❌ cURL 형태 실패: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ cURL 형태 실패: {e}")

print("\n=== 서버 상태 확인 ===")
try:
    # Health check
    health_url = "http://192.168.0.224:8412/health"
    response = requests.get(health_url, timeout=5)
    print(f"Health check: {response.status_code}")
    
    # Models list
    models_url = "http://192.168.0.224:8412/v1/models"
    response = requests.get(models_url, timeout=5)
    if response.status_code == 200:
        models = response.json()
        print("사용 가능한 모델:")
        for model in models.get('data', []):
            print(f"  - {model.get('id', 'Unknown')}")
    else:
        print(f"모델 목록 조회 실패: {response.status_code}")
        
except Exception as e:
    print(f"서버 상태 확인 실패: {e}")