"""
Yanolja LLM (vLLM 원격 서버)
"""
import requests
import json
import os
from typing import List, Dict, Any

class YanoljaLLM:
    """Yanolja EEVE Korean LLM"""
    
    def __init__(self, 
                 base_url: str = None,
                 model: str = "yanolja/EEVE-Korean-Instruct-10.8B-v1.0",
                 temperature: float = 0.7,
                 max_tokens: int = 2000):
        self.base_url = base_url or os.getenv('VLLM_BASE_URL', 'http://192.168.0.224:8701')
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        print(f"✅ Yanolja LLM 초기화: {self.model}")
        print(f"   vLLM 서버: {self.base_url}")
        
    def invoke(self, prompt) -> 'YanoljaLLMResponse':
        """LangChain 호환 인터페이스"""
        # 프롬프트 처리
        if hasattr(prompt, 'content'):
            message_content = prompt.content
        elif isinstance(prompt, str):
            message_content = prompt
        else:
            message_content = str(prompt)
        
        try:
            # vLLM OpenAI 호환 API 호출
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": message_content}],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "stop": ["</s>", "[/INST]", "Human:", "Assistant:"]
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                return YanoljaLLMResponse(content)
            else:
                error_msg = f"Yanolja LLM 오류: {response.status_code} - {response.text}"
                print(f"❌ {error_msg}")
                return YanoljaLLMResponse(error_msg)
                
        except Exception as e:
            error_msg = f"vLLM Yanolja LLM 호출 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return YanoljaLLMResponse(error_msg)
    
    def stream(self, prompt) -> List['YanoljaLLMResponse']:
        """스트리밍 인터페이스 (간소화)"""
        return [self.invoke(prompt)]
    
    def test_connection(self) -> bool:
        """연결 테스트"""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            if response.status_code == 200:
                models = response.json().get('data', [])
                model_names = [m['id'] for m in models]
                if self.model in model_names:
                    print(f"✅ Yanolja 모델 확인됨")
                    return True
                else:
                    print(f"❌ Yanolja 모델을 찾을 수 없음")
                    print(f"   사용 가능한 모델: {model_names}")
                    return False
        except Exception as e:
            print(f"❌ vLLM 서버 연결 실패: {e}")
            return False
    
    def generate_with_template(self, question: str, context: str) -> str:
        """한국어 최적화 템플릿으로 생성"""
        prompt = f"""[INST] 당신은 BC카드 고객 서비스 전문가입니다. 
주어진 정보를 바탕으로 고객의 질문에 정확하고 친절하게 답변해주세요.

컨텍스트:
{context}

고객 질문: {question}

답변: [/INST]"""
        
        response = self.invoke(prompt)
        return response.content

class YanoljaLLMResponse:
    """Yanolja LLM 응답 객체"""
    
    def __init__(self, content: str):
        self.content = content
        self.additional_kwargs = {}
        self.response_metadata = {
            'model_name': 'yanolja-eeve-korean-10.8b',
            'finish_reason': 'stop',
            'service_tier': 'ollama'
        }
        self.id = 'yanolja-response'
    
    def __str__(self):
        return self.content